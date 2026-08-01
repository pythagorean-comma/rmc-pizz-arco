"""Build the PCB for the design in design.py.

Four layers: signals on F.Cu and B.Cu, a solid AGND plane on In1.Cu and a
solid V- plane on In2.Cu. The high-impedance piezo traces on the front run
directly over unbroken ground, and every ground and V- connection is a via
rather than a track.

In2 carried V+ until rev C. RMC, reviewing rev B: "most op amps used for
audio applications are V- referenced because many designs operate from a
single supply." The rail the op-amp's own circuitry references had the
0.25mm track and 45mm to the nearest capacitor, and the other one had a
plane. Swapping them is the substance of this revision.

V+ is routed instead, in route_supply(), as a U on B.Cu: down the west
margin past the three quads, along the bottom, back up the east margin to
the switches. Neither rail is poured on B.Cu -- a B.Cu pour was this
project's worst failure mode, fragmenting into unconnected items in parts of
the board nowhere near the cause -- so B.Cu stays a second signal layer.

The board is three blocks, each one OPA4191 serving two channels. The quad's
pinout does most of the work: every pin of buffers A and B is on the left of
the package and every pin of all-passes C and D is on the right, so a
channel's buffer feedback stays entirely left, its all-pass feedback entirely
right, and the only net that has to cross the package is BUFOUT -- which is a
low-impedance node and can go anywhere.

Track waypoints are given relative to real pad positions read back from the
placed footprints, so nothing here depends on guessing KiCad's rotation
conventions.

Reading order, roughly outwards: route_planes() drops every plane pad onto
its plane; route_critical() lays BUFIN before anything can take its space;
route_channel() does one channel and is called six times; route_board()
carries OUT and the switched nodes out to the tail connector and the
switches; route_supply() does V+ and the control net.
"""

import pathlib
import sys

import pcbnew

sys.path.insert(0, str(pathlib.Path(__file__).parent))
import design as circuit  # noqa: E402
import kicad  # noqa: E402
import rules  # noqa: E402
# The schematic writer's UUID helper, so the board derives exactly the same
# symbol identifiers the schematic wrote rather than re-implementing the hash.
from kisch import _uuid as symbol_uuid  # noqa: E402

FOOTPRINT_DIR = kicad.FOOTPRINT_DIR

# From rules.py, which gen_project.py writes into the .kicad_pro for DRC to
# enforce. Declared in one place so copper cannot be laid to one set of numbers
# and checked against another.
TRACK = rules.TRACK
POWER_TRACK = rules.POWER_TRACK
VIA_DIAMETER = rules.VIA_DIAMETER
VIA_DRILL = rules.VIA_DRILL
CLEARANCE = rules.CLEARANCE
VIA_PAIR_PITCH = rules.VIA_PAIR_PITCH

BLOCK_PITCH = 23.0           # between quads
BLOCK_ORIGIN = (3.0, 14.0)   # centreline of block 1, in board coords
ROW_OFFSET = 4.6             # channel rows, above and below the quad centre
CORRIDOR_X = 51.0            # OUT and SWN run up this lane to the right column
# The right-hand column. 64 rather than 62 because the corridor between the
# switched-node bus and the OUT bus has to be wide enough to land a via in:
# channel 6's switched node crosses U3's V- run, and one of the two has to
# change layer where they meet.
RIGHT_X = 64.0               # switch ICs, DIN header and control live here
BOARD_MARGIN = 3.0

# Channel placement, relative to the row: ref suffix -> (x, rank, kind).
#
# `rank` 0 sits on the row line itself, 1 on a sub-row further from the quad.
# `kind` decides orientation: "series" parts lie along the row, "shunt" parts
# stand on end so their grounded pad hangs clear of the signal lane -- a
# horizontal shunt would put its ground pad in the middle of the lane its own
# signal pad is feeding.
#
# The split into two sub-rows is what keeps the block narrow. The row carries
# the all-pass feedback pair and the summing capacitor, the sub-row carries
# what hangs off them. Order on the row is set by RMC's addendum rather than by
# the signal's own order -- see C02 below.
ROW_PLACEMENT = {
    "J":   (5.0, 0, "conn"),      # 1=shield, 2=white (on the lane), 3=red
    "R02": (5.0, 1, "shunt"),     # 3M3 bias to ground
    "C01": (10.5, 1, "shunt"),    # 100p RF filter
    "R01": (15.0, 0, "series"),   # 1k stopper
    # The all-pass feedback pair comes first, nearest the package, with the
    # capacitor ahead of the resistor. RMC, 2026-08-01: "the OPA191 op amp has
    # a 5V/uS slew rate, so with a fast IC, the feedback capacitor (100pF in
    # the inverter feedback loop) needs to be located closest to -IN. Since
    # the cap is in parallel with a 47K resistor, you can place both of them
    # adjacent to the IC with the capacitor most proximate to the -IN pin."
    #
    # Rev C had them at dx 38.5 with C02 on the sub-row, which put the
    # capacitor 11.8mm from the pin and the resistor 9.3mm -- the pair in the
    # wrong order and both too far. C02 at dx 31.8 puts its near pad 3.1mm
    # from -IN, and its west pad edge 0.80mm from the package's own pads,
    # which also clears RMC's 0.030" component spacing.
    #
    # 5.0mm between centres throughout, not the old 5.5: a 1206's pads span
    # +/-2.05mm, so 4.87 is the floor for 0.030" and 5.0 is the round number
    # above it. That is what pays for the extra slot on the row.
    "C02": (31.8, 0, "series"),   # 100p all-pass feedback, closest to -IN
    "R06": (36.8, 0, "series"),   # 47k across it
    "C04": (41.8, 0, "series"),   # 1n8 summing into the red element
    "R04": (31.8, 1, "series"),   # 47k into the all-pass inverting input
    "R05": (36.8, 1, "series"),   # 47k lag into the switched node
    "C03": (41.8, 1, "shunt"),    # 100p lag to ground
}

# Row parts laid the other way round, so a named pad faces the way the routing
# needs. R04 carries BUFOUT and APN; turning it puts its APN pad directly
# beneath C02's, which makes the two a straight vertical run across the band
# and keeps its BUFOUT pad next to R05's, so one via off the B.Cu run feeds
# both. Left alone it lands APN in the middle of the sub-row with BUFOUT
# either side of it, and the sub-row interleaves.
ROW_MIRRORED = {"R04"}

SUB_ROW = 5.5        # between rank 0 and rank 1, measured away from the quad
REFERENCE_OFFSET = 2.2   # sub-row designators, measured back towards the row

# Quad position relative to the block centreline.
QUAD_X = 25.5

# Bypass pair position, as an offset from the block origin along the
# centreline. Both capacitors go WEST of the quad, which is counter-intuitive
# until you look at what is east of it.
#
# Pin 4 (V+) and pin 11 (V-) sit at (-2.475, 0) and (+2.475, 0) on the
# SOIC-14, so the obvious placement is one each side. It does not fit. East of
# the package the centreline is a bundle of switched nodes at 1.27mm pitch
# running from the pads to the buses, and there is no room beside it. West of it
# only the BUFIN lanes flank the centreline, and they stop at the pad column,
# leaving x=10..18 clear on every block. That is the only space in a block big
# enough for a 1206, and it is measured, not assumed.
#
# Which is survivable because V- no longer needs a local capacitor at all: it
# is a plane. The V+ capacitor is the one that has to be close now, so it
# takes the eastern of the two positions, 8mm from pin 4. The V- capacitor
# only has to exist -- both its pads are plane nets -- and it is there because
# _GROUND_RULE requires the bypassing to be symmetric, not because V- needs
# it.
BYPASS_PLUS_DX = 15.0    # x=18.0: measured, and still the limit after rev D
                         # freed the BUFFB vias that used to be the blocker
BYPASS_MINUS_DX = 12.0   # x=15.0
BYPASS_ROTATION = 90     # standing on end, so the centreline run passes between the pads
BYPASS_REFERENCE_DX = 2.6   # designator, measured outboard from each capacitor

# Board-level placement: ref -> (x, y, rotation).
BOARD_PLACEMENT = {
    # Switch packages, each beside the three channels it serves.
    "U4":  (RIGHT_X, 19.0, 0),
    "U5":  (RIGHT_X, 51.0, 0),
    # Control network, between the two packages where the spine passes.
    # Spread rather than evenly spaced: y = 37 is block 2's centreline, which
    # is where that quad's V- pin has to come out, and a control part there
    # blocks the only clear row it has.
    "R702": (RIGHT_X - 2.0, 30.0, 0),
    "R701": (RIGHT_X - 2.0, 34.0, 0),
    "C701": (RIGHT_X - 2.0, 44.0, 0),
    # Switch bypass, RMC's "a pair of bypass caps between the two CD4066 IC's".
    # Midway between U4 and U5 in y, but outboard of the three risers in x
    # rather than among them. The column between the packages and the spine
    # carries the control spine, the control network, the toggle run and both
    # risers, and measuring it says there is no 1206-sized hole anywhere in
    # it -- not one with room for a stub via, not one even for the bare part.
    #
    # x=73 is where rev B's four bypass capacitors sat. Putting these two back
    # there also restores the east margin: with that column empty the board
    # had shrunk to 70.7mm wide, which left the control riser 0.15mm from the
    # edge against the 0.5mm rule.
    "C941": (73.0, 31.0, BYPASS_ROTATION),
    "C942": (73.0, 39.0, BYPASS_ROTATION),
    # Supply-entry bulk, on the east leg of the V+ spine rather than at J7
    # itself. J7 lies flat from x=26.0 to x=46.32 with J8 immediately east of
    # it, and the rows below carry the two control nets out to J8, so there is
    # no room at the connector for a 1206 pair. This strip is clear: east of
    # the OUT bus, which ends at x=58.4, and west of the control riser.
    #
    # It is about 14mm of 0.8mm B.Cu from J7 pin 7, so call it what it is --
    # bulk on the incoming rail, not decoupling at the connector.
    # Supply entry, on the header row east of J8 where the row is empty. C901
    # drops onto the bottom leg of the V+ spine; C902 needs no routing at all,
    # since both its pads are plane nets now.
    #
    # Two measured constraints set these positions. A 1206's courtyard is
    # 4.69 x 2.39mm, half as big again as the part, so the pair has to be at
    # least 5.2mm apart. And C902 has to keep its ground pad's stub via clear
    # of the V+ spine at x=68, which puts its eastern pad no further east
    # than about 66.5.
    "C901": (59.0, 76.5, 0),
    "C902": (64.5, 76.5, 0),
    # Tail connectors laid flat along the bottom edge: standing up, the 1x09
    # is 23.95mm tall and needs a column of its own.
    "J7":  (26.0, 77.6, 90),
    "J8":  (50.0, 77.6, 90),
}

# Where the tail headers' reference designators go, since lying flat puts the
# default position on top of their own pads.
TAIL_REFERENCE = {"J7": (22.6, 77.6), "J8": (56.2, 77.6)}


def to_mm(value):
    return pcbnew.ToMM(value)


def point(x, y):
    return pcbnew.VECTOR2I_MM(float(x), float(y))
class Board:
    def __init__(self):
        self.board = pcbnew.BOARD()
        self.board.SetCopperLayerCount(4)
        self.nets = {}
        self.footprints = {}
        self._make_nets()

    # -- nets and parts ---------------------------------------------------
    def _make_nets(self):
        for name in sorted(circuit.NETS):
            net = pcbnew.NETINFO_ITEM(self.board, name)
            self.board.Add(net)
            self.nets[name] = net

    def net(self, name):
        return self.nets[name]

    def place(self, ref, x, y, rotation):
        part = circuit.PARTS[ref]
        library, name = part.footprint.split(":", 1)
        footprint = pcbnew.FootprintLoad(str(FOOTPRINT_DIR / f"{library}.pretty"), name)
        if footprint is None:
            raise SystemExit(f"could not load footprint {part.footprint} for {ref}")
        self.board.Add(footprint)
        # FootprintLoad returns the footprint under its bare name; without the
        # library nickname KiCad cannot tie it back to a library, so
        # "Update Footprints from Library" has nothing to work from.
        footprint.SetFPIDAsString(part.footprint)
        # Link back to the schematic symbol of the same reference. The UUIDs
        # are derived from the project name, so both generators compute the
        # same value independently -- this is what makes cross-probing work
        # and stops "Update PCB from Schematic" treating every footprint as
        # a new part. Multi-unit parts link via their first unit.
        footprint.SetPath(pcbnew.KIID_PATH(
            f"/{symbol_uuid(f'{circuit.PROJECT}:part:{ref}:1')}"))
        footprint.SetSheetname("/")
        footprint.SetSheetfile(f"{circuit.PROJECT}.kicad_sch")
        footprint.SetPosition(point(x, y))
        if rotation:
            footprint.SetOrientationDegrees(rotation)
        footprint.SetReference(ref)
        footprint.SetValue(part.value)
        footprint.Reference().SetVisible(True)
        footprint.Value().SetVisible(False)
        if part.dnp:
            footprint.SetDNP(True)
        self.footprints[ref] = footprint

        # Attach every pad to the net design.py put it on.
        owner = circuit.DESIGN.pin_owner()
        for pad in footprint.Pads():
            key = (ref, pad.GetNumber())
            if key in owner:
                pad.SetNet(self.net(owner[key]))
        return footprint

    def pad(self, ref, number):
        """Absolute position of a pad, in millimetres."""
        for candidate in self.footprints[ref].Pads():
            if candidate.GetNumber() == str(number):
                position = candidate.GetPosition()
                return (round(to_mm(position.x), 4), round(to_mm(position.y), 4))
        raise KeyError(f"{ref} has no pad {number}")

    # -- copper -----------------------------------------------------------
    def track(self, net, points, layer=pcbnew.F_Cu, width=TRACK):
        for start, end in zip(points, points[1:]):
            if start == end:
                continue
            segment = pcbnew.PCB_TRACK(self.board)
            segment.SetStart(point(*start))
            segment.SetEnd(point(*end))
            segment.SetWidth(pcbnew.FromMM(width))
            segment.SetLayer(layer)
            segment.SetNet(self.net(net))
            self.board.Add(segment)

    def via(self, net, x, y):
        item = pcbnew.PCB_VIA(self.board)
        item.SetPosition(point(x, y))
        item.SetWidth(pcbnew.FromMM(VIA_DIAMETER))
        item.SetDrill(pcbnew.FromMM(VIA_DRILL))
        item.SetViaType(pcbnew.VIATYPE_THROUGH)
        item.SetLayerPair(pcbnew.F_Cu, pcbnew.B_Cu)
        item.SetNet(self.net(net))
        self.board.Add(item)

    def power_via(self, net, x, y, along=(1.0, 0.0)):
        """Two vias where one would do, side by side across `along`.

        RMC: "go with double vias for connecting Power & Ground traces on
        different layers ... double vias and larger holes are low-cost
        insurance against plating problems." A barrel that plates thin is not
        an open circuit you find at test; it is one that opens later, and the
        second barrel is a few pence against having to find that.

        Placed across the direction of travel rather than along it, so the
        pair straddles the track it belongs to instead of queueing up behind
        it, and separated by a full pad plus a clearance -- two vias touching
        are one via with a worse hole.
        """
        length = (along[0] ** 2 + along[1] ** 2) ** 0.5
        across = (-along[1] / length, along[0] / length)
        for sign in (-0.5, 0.5):
            self.via(net, round(x + across[0] * sign * VIA_PAIR_PITCH, 4),
                     round(y + across[1] * sign * VIA_PAIR_PITCH, 4))
        self.track(net, [(round(x - across[0] * 0.5 * VIA_PAIR_PITCH, 4),
                          round(y - across[1] * 0.5 * VIA_PAIR_PITCH, 4)),
                         (round(x + across[0] * 0.5 * VIA_PAIR_PITCH, 4),
                          round(y + across[1] * 0.5 * VIA_PAIR_PITCH, 4))],
                   width=POWER_TRACK)

    def stub_via(self, ref, number, offset, double=False):
        """Short track from a pad to a via beside it -- how AGND, V+ and V-
        pads reach their planes.

        The net comes from design.py rather than the caller, so a via can
        never be dropped onto the wrong rail. Vias sit beside the pad, never
        in it, which keeps the board buildable with plain fab processes.

        `double` puts two vias there instead of one. It is not the default
        because most of these stubs are among the passives, where the pair
        would not fit; see route_planes() for which ones get it.
        """
        net = circuit.DESIGN.pin_owner()[(ref, str(number))]
        pad = self.pad(ref, number)
        target = (round(pad[0] + offset[0], 4), round(pad[1] + offset[1], 4))
        self.track(net, [pad, target], width=POWER_TRACK if net in
                   ("V+", "V-", "AGND") else TRACK)
        if double:
            self.power_via(net, *target, along=offset)
        else:
            self.via(net, *target)
        return target

    def zone(self, net, layer, rectangle, priority=0):
        left, top, right, bottom = rectangle
        item = pcbnew.ZONE(self.board)
        item.SetLayer(layer)
        item.SetNet(self.net(net))
        item.SetAssignedPriority(priority)
        item.SetLocalClearance(pcbnew.FromMM(CLEARANCE))
        item.SetMinThickness(pcbnew.FromMM(0.2))
        outline = item.Outline()
        outline.NewOutline()
        for x, y in ((left, top), (right, top), (right, bottom), (left, bottom)):
            outline.Append(pcbnew.FromMM(float(x)), pcbnew.FromMM(float(y)))
        self.board.Add(item)
        return item

    def outline(self, rectangle):
        left, top, right, bottom = rectangle
        corners = [(left, top), (right, top), (right, bottom), (left, bottom), (left, top)]
        for start, end in zip(corners, corners[1:]):
            shape = pcbnew.PCB_SHAPE(self.board)
            shape.SetShape(pcbnew.SHAPE_T_SEGMENT)
            shape.SetStart(point(*start))
            shape.SetEnd(point(*end))
            shape.SetLayer(pcbnew.Edge_Cuts)
            shape.SetWidth(pcbnew.FromMM(0.1))
            self.board.Add(shape)

    def text(self, body, x, y, size=1.0, layer=pcbnew.F_SilkS):
        item = pcbnew.PCB_TEXT(self.board)
        item.SetText(body)
        item.SetPosition(point(x, y))
        item.SetLayer(layer)
        item.SetTextSize(pcbnew.VECTOR2I(pcbnew.FromMM(size), pcbnew.FromMM(size)))
        item.SetTextThickness(pcbnew.FromMM(size * 0.15))
        self.board.Add(item)



def block_centre(index):
    """Y of block `index`'s centreline -- the quad sits on it."""
    return BLOCK_ORIGIN[1] + (index - 1) * BLOCK_PITCH


def row_y(channel):
    """Y of a channel's passive row.

    Odd channels take the row above their quad and even channels the row
    below, matching the package: buffer A and all-pass D occupy the top half
    of the pinout, buffer B and all-pass C the bottom half.
    """
    centre = block_centre((channel + 1) // 2)
    return centre - ROW_OFFSET if channel % 2 else centre + ROW_OFFSET


def row_ref(suffix, channel):
    """Row-local part name -> the design's reference (R02 -> R102)."""
    if suffix == "J":
        return f"J{channel}"
    return f"{suffix[0]}{channel}{suffix[1:]}"


def place_blocks(board):
    """Place three quads and their six channel rows.

    `s` is the direction away from the quad for this channel: negative for the
    odd channel, which takes the row above, positive for the even one below.
    Everything about a row is mirrored through it, so both channels are laid
    out by the same code and cannot drift apart.
    """
    for index in range(1, circuit.CHANNELS // 2 + 1):
        centre = block_centre(index)
        quad_x = BLOCK_ORIGIN[0] + QUAD_X
        board.place(f"U{index}", quad_x, centre, 0)
        # The bypass pair, both west of the quad on the centreline -- see
        # BYPASS_PLUS_DX for why not one each side. Refs come from
        # design.BYPASS rather than being spelled out again here, so the
        # circuit names the pairs and the board only places them.
        plus, minus, _ = circuit.BYPASS[f"U{index}"]
        for ref, dx, away in ((plus, BYPASS_PLUS_DX, 1.0),
                              (minus, BYPASS_MINUS_DX, -1.0)):
            x = BLOCK_ORIGIN[0] + dx
            footprint = board.place(ref, x, centre, BYPASS_ROTATION)
            # Designators outboard, horizontal, and away from each other.
            # Standing on end, these two inherit the part's rotation and land
            # on their own neighbours: the V+ one over R01's designator, the
            # V- one over the channel legend. Neither is a DRC error and both
            # make the block unreadable, which for a board going out for
            # review is worse.
            footprint.Reference().SetPosition(
                point(round(x + away * BYPASS_REFERENCE_DX, 4), centre))
            footprint.Reference().SetTextAngleDegrees(0)
        for channel in (index * 2 - 1, index * 2):
            s = -1 if channel % 2 else 1
            row = row_y(channel)
            for suffix, (dx, rank, kind) in ROW_PLACEMENT.items():
                x = BLOCK_ORIGIN[0] + dx
                y = row + s * rank * SUB_ROW
                if kind == "conn":
                    # Laid flat: standing up, the 1x03 header is 8.71mm tall
                    # and becomes the tallest thing in the block, forcing the
                    # block pitch wider than the passives need.
                    rotation = 90
                else:
                    rotation = 180 if suffix in ROW_MIRRORED else 0
                footprint = board.place(row_ref(suffix, channel), x, y, rotation)
                if rank:
                    # Reference designators on a sub-row go towards the row,
                    # not away from it. KiCad's default is to sit them above
                    # the part, which for an odd channel points straight at
                    # the previous block's sub-row -- 2.8mm away -- and the
                    # two blocks' designators land on top of each other. It
                    # is not a DRC error and it makes the board unreadable,
                    # which is worse: the reference designators are what a
                    # reviewer and an assembler both work from.
                    footprint.Reference().SetPosition(
                        point(x, round(y - s * REFERENCE_OFFSET, 4)))


def place_rest(board):
    for ref, (x, y, rotation) in BOARD_PLACEMENT.items():
        footprint = board.place(ref, x, y, rotation)
        if ref in TAIL_REFERENCE:
            # The tail headers lie flat along the bottom edge, and a rotated
            # footprint puts its reference designator across its own pads.
            # Park them off the ends instead, where the board is empty.
            footprint.Reference().SetPosition(point(*TAIL_REFERENCE[ref]))


def free_offset(board, ref, number, candidates):
    """Pick the first stub direction whose via actually clears every foreign pad.

    Hand-tuning fifty-odd via offsets is where the previous board burned its
    iterations. This tries a few directions and takes the first that is far
    enough from foreign copper, so adding a part cannot silently push a via
    into its neighbour.

    The test measures the via's edge against each pad's rectangle, because
    pads on this board are not one size: a 1206 is 1.12 x 1.75mm and a 2.54mm
    header pad is 1.70mm square, and a via needs VIA_DIAMETER/2 + CLEARANCE of
    room from the pad's edge rather than from its centre. An earlier version
    compared centres against a single 0.55mm scalar, which asks for less than
    half what a header pad needs -- it happened to pass only because the
    candidate offsets below are all 1.5mm or more, so the offsets were doing
    the protecting and the test was decorative.

    Same-net pads are skipped: no clearance rule applies inside a net, and
    counting them would reject good directions.
    """
    origin = board.pad(ref, number)
    net = circuit.DESIGN.pin_owner()[(ref, str(number))]
    keep_out = VIA_DIAMETER / 2 + CLEARANCE
    boxes = []
    for other, footprint in board.footprints.items():
        for pad in footprint.Pads():
            if pad.GetNetname() == net:
                continue
            box = pad.GetBoundingBox()
            boxes.append((to_mm(box.GetLeft()), to_mm(box.GetRight()),
                          to_mm(box.GetTop()), to_mm(box.GetBottom())))

    def clears(x, y):
        for left, right, top, bottom in boxes:
            dx = max(left - x, 0.0, x - right)
            dy = max(top - y, 0.0, y - bottom)
            if (dx * dx + dy * dy) ** 0.5 < keep_out:
                return False
        return True

    for dx, dy in candidates:
        if clears(origin[0] + dx, origin[1] + dy):
            return (dx, dy)
    # Deliberately fatal rather than best-effort: a stub with nowhere clear to
    # go is a placement problem, and the fix is to move the part or add a
    # direction, not to let the build put a via somewhere it does not fit.
    raise SystemExit(f"no clear stub direction for {ref}.{number}")


# In2 carries V-, not V+. RMC, reviewing rev B: "most op amps used for audio
# applications are V- referenced because many designs operate from a single
# supply." The rail the op-amp's own circuitry references is the one that wants
# plane copper, and rev B had it the wrong way round -- V+ got an inner layer
# and V- got a 0.25mm track running up to 51mm to the nearest capacitor.
#
# Swapping them costs the V+ routing in route_supply() and buys three things:
# every op-amp V- pin reaches its rail through one via, the whole V- spine and
# its dives under the buses disappear, and the three-lane bundle east of each
# quad (SWN odd, V-, SWN even) loses its middle lane.
PLANE_NETS = {"AGND": pcbnew.In1_Cu, "V-": pcbnew.In2_Cu}

# Bypass capacitors whose plane stub vias do not go axially -- see the
# BYPASS_STUB branch in route_planes(). Both of these lie flat on the header
# row, where north is the SW_TOG and SW_CTL approach rows and south is empty
# board down to the edge.
BYPASS_STUB = {"C901": (0.0, 1.6), "C902": (0.0, 1.6)}


def channel_signs():
    """ref -> the direction away from that part's quad, for row parts only.

    The two halves of a block are mirror images, so a stub offset that is
    right for the odd channel is wrong for the even one. Without this the
    offsets are chosen by trial order alone, and the odd channel's ground
    stubs land clear while the even channel's land in the lane -- a fault
    that shows up on exactly half the board and looks like a routing error.
    """
    return {row_ref(suffix, channel): (-1 if channel % 2 else 1)
            for channel in range(1, circuit.CHANNELS + 1)
            for suffix in ROW_PLACEMENT}


def route_planes(board):
    """Drop every AGND and V- pad onto its plane through a via beside the pad.

    V- rather than V+ since rev C -- see PLANE_NETS. That one change connects
    every op-amp and switch supply-return pin, J7 pin 8, R701 and five
    capacitors with nothing but a via each, and deletes the spine, the taps
    and the three dives under the buses that rev B needed to do the same job
    worse. V+ is routed instead, in route_supply().
    """
    owner = circuit.DESIGN.pin_owner()
    # Every 14-pin package on this board is on a 1.27mm pitch and too narrow
    # for a row of stub vias beside its pads, the switches as much as the
    # op-amps.
    quads = {ref for ref, part in circuit.PARTS.items()
             if "-14_" in part.footprint and part.footprint.endswith("_P1.27mm")}
    bypass_caps = {ref for pair in circuit.BYPASS.values() for ref in pair[:2]}
    signs = channel_signs()
    count = 0
    for (ref, number), net in sorted(owner.items()):
        if net not in PLANE_NETS:
            continue
        if ref.startswith("#"):
            continue
        if ref in bypass_caps:
            # Explicit, not chosen. free_offset() checks courtyards, and every
            # obstacle that matters to a bypass capacitor's stub via is a
            # track: the rail run passing between its own two pads, the OUT
            # bus, the V+ spine. Left to choose, it put one via 0.125mm from
            # the very run the capacitor is there to bypass.
            #
            # The default is axial -- straight out past the pad, along the
            # part -- which is right for the five that stand on end. The two
            # on the header row lie flat, so both their pads are level with
            # the part centre and there is no axis to follow; they are named
            # in BYPASS_STUB instead, pointing south, away from the two
            # control approach rows above them.
            pad = board.pad(ref, number)
            centre_y = to_mm(board.footprints[ref].GetPosition().y)
            offset = BYPASS_STUB.get(
                ref, (0.0, 1.6 if pad[1] > centre_y else -1.6))
        elif ref in quads:
            # Inboard, under the package body: the space between the two pad
            # columns is the only clear ground on a 1.27mm-pitch package. Each
            # column keeps to its own side of the centreline, so two pads at
            # the same height -- which the 4066s have and the op-amps do not --
            # cannot be given the same via.
            centre = to_mm(board.footprints[ref].GetPosition().x)
            pad = board.pad(ref, number)
            inboard = -0.9 if pad[0] < centre else 0.9
            offset = (centre - pad[0] + inboard, 0.0)
        else:
            # Towards the quad first. From a row part that is the empty strip
            # inboard of the row; from a sub-row part it is the far side of
            # the band from the lanes. The same choice for both halves of a
            # block, which is what keeps them symmetrical.
            s = signs.get(ref, -1)
            offset = free_offset(board, ref, number,
                                 [(0.0, -s * 1.6), (0.0, s * 1.6),
                                  (1.9, 0.0), (-1.9, 0.0),
                                  (1.5, 1.5), (-1.5, 1.5), (1.5, -1.5), (-1.5, -1.5)])
        # Doubled where there is room for it, which is the bypass capacitors:
        # they stand alone in the margins and their stubs point into open
        # board. The channel passives cannot have it -- they sit two lanes
        # apart by design -- and the 14-pin packages certainly cannot, with
        # 3.0mm between their pad columns and 1.27mm between their pins. This
        # is RMC's own "where it is practical to do so".
        board.stub_via(ref, number, offset, double=ref in bypass_caps)
        count += 1
    return count


# Lanes in the band -- the clear strip between the row pads and the sub-row
# pads, measured from the row and running away from the quad. Only three nets
# ever travel along it; everything else merely crosses it, so it is spacing
# between these three that matters and they are set a full via's width apart.
OUT_LANE = 1.35      # B.Cu, the full width of the block
IN_LANE = 2.2        # F.Cu, connector to stopper
BUFIN_LANE = 3.1     # F.Cu, C01 up to the stopper -- deeper than IN_W
APOUT_LANE = 2.4     # B.Cu, all-pass output across the right-hand half


def route_critical(board):
    """Route BUFIN first, before anything else can take the space it needs.

    BUFIN is the 3M3 node -- the highest-impedance point in the design, where
    surface leakage and stray coupling actually matter. It gets the short
    direct path from the stopper to the buffer's + input, on F.Cu over
    unbroken In1 ground for its whole length, with no via anywhere on it.

    The path leaves R01.2 *away* from the row, into the clear strip between
    the row and the block centreline, and runs east at the height of the pin
    it is aiming at. That strip is empty -- the two feedback nets that share
    this side of the package travel it on B.Cu -- so BUFIN never crosses
    anything and never changes layer.
    """
    for channel in range(1, circuit.CHANNELS + 1):
        s = -1 if channel % 2 else 1
        index = (channel + 1) // 2
        quad = f"U{index}"
        half = "odd" if channel % 2 else "even"
        _, (_, _, buf_in) = circuit.QUAD_UNITS[half]["buf"]
        target = board.pad(quad, buf_in)
        stopper = board.pad(row_ref("R01", channel), 2)
        filt = board.pad(row_ref("C01", channel), 1)
        net = f"BUFIN{channel}"
        board.track(net, [stopper, (stopper[0], target[1]), target])
        # C01 joins from the sub-row on the far side of IN_W's lane: it comes
        # up to a lane of its own, runs east past where IN_W turns down, and
        # drops onto the stopper pad. Deeper than IN_W, so their verticals
        # never meet.
        joint = round(row_y(channel) + s * BUFIN_LANE, 4)
        board.track(net, [filt, (filt[0], joint), (stopper[0], joint), stopper])


def route_channel(board, channel):
    """Route one channel. Six identical calls, so a fix here is a fix everywhere.

    `s` points away from the quad: -1 for the odd channel on the row above,
    +1 for the even one below. Every offset is multiplied by it, so both
    halves of a block come out of the same code and cannot drift apart.

    Two structural facts decide the whole thing.

    **The row line is the only place a net can change sides.** Row parts and
    sub-row parts sit on two parallel lines with the band between them, and
    the quad sits on the far side of the row. So every net that leaves the
    package for a sub-row part crosses the row line exactly once, and the
    crossings have to be shared out between the gaps in it. The gaps are
    measured, not assumed: a 1206 leaves 1.8mm between its own two pads, and
    that is where most of the crossings go.

    **A net leaving the package deeper than another cannot turn towards the
    row inside the other's span.** The three right-hand pins come out at
    three different depths, and their targets run the opposite way along the
    row -- so the natural order is exactly backwards. APOUT, the shallowest
    pin with the furthest target, is the one that has to give: it crosses the
    row line immediately and makes its traverse on B.Cu, under the band, and
    the other two then cross it without touching it. It is a low-impedance
    op-amp output, so the layer change costs nothing.

    B.Cu carries what has to traverse the block -- OUT, APOUT, the switched
    node's jump under C02, and both buffer feedback nets under the package.
    That is only affordable because V- is no longer a pour: a crossing costs
    two vias rather than a hole in the negative rail.
    """
    s = -1 if channel % 2 else 1
    index = (channel + 1) // 2
    quad = f"U{index}"
    half = "odd" if channel % 2 else "even"
    _, (buf_out, buf_fb, _) = circuit.QUAD_UNITS[half]["buf"]
    _, (ap_out, ap_n, ap_p) = circuit.QUAD_UNITS[half]["ap"]
    n = channel
    row = row_y(n)
    sub = round(row + s * SUB_ROW, 4)

    def p(suffix, number):
        return board.pad(row_ref(suffix, n), number)

    def q(number):
        return board.pad(quad, number)

    def lane(k):
        """A track offset k mm from the row, away from the quad.

        The clear band runs from the edge of the row pads to the edge of the
        sub-row pads. Straying outside it puts a track straight through a pad
        row, which DRC reports as dozens of shorts far from the real mistake --
        exactly how SWN was routed along the sub-row itself for a while.
        """
        assert 1.175 < k < SUB_ROW - 1.175, (
            f"lane({k}) is outside the clear band "
            f"(1.175 .. {SUB_ROW - 1.175}) -- it would cross a pad row")
        return round(row + s * k, 4)

    def between(left, right):
        """x midway between two pads -- where a crossing of the row line goes.

        Taking the midpoint of the two pad centres rather than a fixed offset
        means the gap is always found even if a part moves, and a 1206's own
        1.8mm pad gap is wide enough that the midpoint is comfortable.
        """
        return round((left[0] + right[0]) / 2, 4)

    def hop(net, start, end, layer=pcbnew.B_Cu):
        """Dive to `layer` at `start` and surface at `end`."""
        board.via(net, *start)
        board.track(net, [start, end], layer=layer)
        board.via(net, *end)

    # -- white element in: J.2 out to a lane, then back to the stopper -------
    # J's three pads sit along the row, so nothing can leave the connector
    # along it -- the shield and the red element are in the way.
    white = f"IN_W{n}"
    board.track(white, [p("J", 2), (p("J", 2)[0], lane(IN_LANE)),
                        (p("R01", 1)[0], lane(IN_LANE)), p("R01", 1)])
    board.track(white, [(p("J", 2)[0], lane(IN_LANE)),
                        (p("R02", 1)[0], lane(IN_LANE)), p("R02", 1)])

    # -- red element straight through to the summing node -------------------
    # OUT is the high-impedance piezo node and has to cross the whole block,
    # so it goes under it rather than fighting for a lane on the front. Its
    # B.Cu run is the reason every other crossing of the band is on F.Cu.
    out = f"OUT{n}"
    dive = (p("J", 3)[0], lane(OUT_LANE))
    land = (p("C04", 2)[0], lane(OUT_LANE))
    board.track(out, [p("J", 3), dive])
    hop(out, dive, land)
    board.track(out, [land, p("C04", 2)])

    # -- buffer feedback: the whole of it ------------------------------------
    # RMC: "connect OUT to -IN with the shortest possible trace at least .010"
    # wide". Their own pinout makes that one segment. The buffer's output and
    # its inverting input are adjacent pins in the same column, 1.27mm apart,
    # so the feedback never leaves the package footprint and adds essentially
    # no capacitance at the inverting node -- which is the point of taking the
    # 1k out. At 0.30mm the trace is 0.0118", comfortably over their floor.
    #
    # Rev C had a 1k here and paid for it twice: the resistor sat west of the
    # package and both feedback nets had to dive inboard, cross under the
    # package on B.Cu and surface on the row line at its pads.
    outnet = f"BUFOUT{n}"
    board.track(outnet, [q(buf_fb), q(buf_out)])

    # BUFOUT then leaves eastward only, under the package on B.Cu at its own
    # pin's height, and surfaces in C02's pad gap to cross the band on F.Cu.
    #
    # It has to surface to get across: OUT already owns a B.Cu lane through
    # the band, so a B.Cu descent would cross it. And it has to do so here,
    # west of where APOUT surfaces, because APOUT owns an F.Cu lane through
    # the band east of that point. The 1.8mm gap between a 1206's own two pads
    # is the only place wide enough to land a via in, and C02's is the one in
    # the right place.
    out_pin = q(buf_out)
    out_dive = (round(out_pin[0] + 1.5, 4), out_pin[1])
    out_cross = between(p("C02", 1), p("C02", 2))
    board.track(outnet, [out_pin, out_dive])
    board.via(outnet, *out_dive)
    board.track(outnet, [out_dive, (out_cross, out_dive[1])], layer=pcbnew.B_Cu)
    board.via(outnet, out_cross, out_dive[1])
    board.track(outnet, [(out_cross, out_dive[1]), (out_cross, sub),
                         p("R04", 1)])
    board.track(outnet, [p("R04", 1), p("R05", 1)])

    # -- all-pass inverting input: the one the layout is now built around ----
    # C02 sits first on the row so its APN pad is 3.1mm from this pin, and the
    # price is that APN and APOUT interleave along the row -- APN, APOUT, APN,
    # APOUT. Neither has to fight for it, because neither travels along the
    # row at all.
    #
    # APN runs east on its own pin's lane instead, between the package and the
    # row, and drops onto each pad it needs. That lane clears a capacitor
    # standing on the row by 1.0mm, so it can pass straight over C02 on its
    # way to R06. Three drops off one lane, no row run, no interleave.
    apn = f"APN{n}"
    an_pin = q(ap_n)
    an_lane = an_pin[1]
    board.track(apn, [an_pin, (p("R06", 1)[0], an_lane)])
    for target in (p("C02", 1), p("R06", 1)):
        board.track(apn, [(target[0], an_lane), target])
    # and straight down through the band to R04, which is turned round so its
    # APN pad sits directly beneath C02's.
    board.track(apn, [p("C02", 1), p("R04", 2)])

    # -- all-pass output: across the block on B.Cu, under the band -----------
    # Cannot use the same trick: its pin lane is 0.79mm from the row line and
    # would close to 0.15mm of a capacitor standing on it. So it dives at once,
    # travels under the band, and surfaces in the band to feed its three pads
    # from below. R06.2 and C04.1 are adjacent, so they join along the row and
    # only two stubs are needed.
    apout = f"APOUT{n}"
    ao_pin = q(ap_out)
    ao_turn = between(ao_pin, p("C02", 1))
    ao_cross = p("C02", 2)[0]
    ao_dive = (ao_turn, lane(APOUT_LANE))
    ao_land = (ao_cross, lane(APOUT_LANE))
    board.track(apout, [ao_pin, (ao_turn, ao_pin[1]), ao_dive])
    hop(apout, ao_dive, ao_land)
    for target in (p("C02", 2), p("R06", 2)):
        board.track(apout, [ao_land, (target[0], ao_land[1]), target])
    board.track(apout, [p("R06", 2), p("C04", 1)])

    # -- switched node ------------------------------------------------------
    # The deepest of the three right-hand pins, so it crosses the row line
    # furthest east -- through C04's own pad gap, past both the others. R05.2
    # and C03.1 are adjacent on the sub-row now, so the jump under C02 that
    # rev C needed is gone with it.
    swn = f"SWN{n}"
    sw_pin = q(ap_p)
    sw_cross = between(p("C04", 1), p("C04", 2))
    board.track(swn, [sw_pin, (sw_cross, sw_pin[1]), (sw_cross, sub)])
    board.track(swn, [(sw_cross, sub), p("C03", 1)])
    board.track(swn, [p("C03", 1), p("R05", 2)])


# The corridor between the blocks and the right-hand column. Twelve nets
# leave the blocks here -- six OUT and six SWN -- and the two families pull in
# opposite directions, which is what decides the layers.
#
# OUT leaves at the top of the board and has to reach a header pin at the
# bottom, and J7's pins run the same way as the channels while the corridor
# fills from the outside in. So OUT's corridor lane order and its fan-in
# order are reversed with respect to each other and cannot both be satisfied
# on one layer: the descent goes on B.Cu and only the fan-in surfaces.
#
# SWN stays entirely on F.Cu, which is why the two never meet.
OUT_BUS_X = 55.4         # channel 6's lane; channel 1 is the outermost
OUT_BUS_PITCH = 0.6
# Channel 1's approach row is the one nearest the header, because its header
# pin is the furthest west: it has to leave the bus before any of the others
# and pass under none of their drops. Only the drop onto the pin surfaces --
# the fan-in itself stays on B.Cu, which is what lets the bus keep channel 1
# outermost at the same time.
# Each approach row ends in a via, so the pitch is set by via-to-track and not
# by track-to-track: 0.4 of via radius, 0.25 of clearance and 0.15 of the
# neighbouring row. 0.80mm minimum, against the 0.765 that carried 0.6mm vias
# and the 0.625 the old notes record.
#
# Six rows at that pitch do not fit between the last sub-row and the header
# where the header was, which is why J7 and J8 moved 1.1mm down the board.
# The alternative -- keeping the whole fan-in on B.Cu and landing straight on
# the through-hole pins, no vias at all -- does not work: each channel's drop
# would cross the row of every lower-numbered channel, whose pins are further
# west and whose rows are below it.
OUT_FANIN_Y = 76.0       # channel 1, just clear of the header pads
OUT_FANIN_PITCH = -0.82
SWN_BUS_X = 50.4         # channel 1's lane; the bus fills outwards
SWN_BUS_PITCH = 0.7
SWITCH_CLEARANCE = 2.2   # below a switch package, for the right-column cells
# Lane order on the SWN bus, innermost lane first. Channel 2 leaves its block
# below channel 1's cell, so channel 1 has to turn off the bus outside it --
# otherwise the row channel 1 leaves on and the lane channel 2 arrives on run
# 0.08mm apart. Everywhere else the channel order already matches the cells.
SWN_BUS_ORDER = (2, 1, 3, 4, 5, 6)


def route_board(board):
    """Carry OUT and the switched nodes out of the blocks.

    Both families leave a block at a height the channel already established
    -- OUT on its own B.Cu spine, SWN at the height of the quad pin it came
    from -- so neither needs a lane inside the block to get here.
    """
    switches = {ref: to_mm(board.footprints[ref].GetPosition().x)
                for ref in ("U4", "U5")}
    count = 0
    for channel in range(1, circuit.CHANNELS + 1):
        s = -1 if channel % 2 else 1
        row = row_y(channel)
        index = (channel + 1) // 2
        half = "odd" if channel % 2 else "even"
        _, (_, _, ap_p) = circuit.QUAD_UNITS[half]["ap"]

        # -- OUT: B.Cu the whole way down, surfacing only to fan in ---------
        # Channel 1 takes the outermost lane and the highest approach row:
        # its header pin is the furthest west, so it has to leave the bus
        # before any of the others and cross none of their drops.
        net = f"OUT{channel}"
        head = board.pad(row_ref("C04", channel), 2)
        bus = round(OUT_BUS_X + (circuit.CHANNELS - channel) * OUT_BUS_PITCH, 4)
        fan = round(OUT_FANIN_Y + (channel - 1) * OUT_FANIN_PITCH, 4)
        assert fan > row + s * SUB_ROW + 1.2, (
            f"OUT{channel} approach row at {fan} clips the last sub-row")
        spine = round(row + s * OUT_LANE, 4)
        pin = board.pad("J7", channel)
        board.track(net, [(head[0], spine), (bus, spine), (bus, fan),
                          (pin[0], fan)], layer=pcbnew.B_Cu)
        board.via(net, pin[0], fan)
        board.track(net, [(pin[0], fan), pin])

        # -- SWN: F.Cu out to its switch cell -------------------------------
        # The cells on the package's right-hand column cannot be reached
        # along their own row without crossing the package, so those come
        # round underneath it instead.
        net = f"SWN{channel}"
        leave = round((board.pad(row_ref("C04", channel), 1)[0] +
                       board.pad(row_ref("C04", channel), 2)[0]) / 2, 4)
        lane = board.pad(f"U{index}", ap_p)[1]
        bus = round(SWN_BUS_X + SWN_BUS_ORDER.index(channel) * SWN_BUS_PITCH, 4)
        cell = next((ref, number) for ref, number in circuit.NETS[net]
                    if ref in switches)
        target = board.pad(*cell)
        if target[0] > switches[cell[0]]:
            box = board.footprints[cell[0]].GetCourtyard(pcbnew.F_CrtYd).BBox()
            approach = round(to_mm(box.GetBottom()) + SWITCH_CLEARANCE, 4)
            tail = [(target[0], approach), target]
        else:
            approach = target[1]
            tail = [target]
        board.track(net, [(leave, lane), (bus, lane), (bus, approach)] + tail)
        count += 2
    return count


# The three nets that have to get past the corridor rather than into it.
#
# OUT fills B.Cu from top to bottom and SWN fills F.Cu, so between them the
# corridor is closed to anything travelling the length of the board. All three
# of these run instead down the strip between the switch packages and the
# bypass caps -- the one column east of every switched node -- and reach the
# tail connectors along the bottom edge, below the headers rather than above,
# where the OUT fan-in already occupies every row.
# V+ is the only rail that is routed now, and it is routed as a U on B.Cu:
# down the west margin past the three quads, along the bottom below the tail
# connectors, and back up the east margin to the switches. All three legs were
# measured clear end to end on B.Cu before being written here -- B.Cu carries
# 77 segments against F.Cu's 303, and the whole west margin, the whole bottom
# and the whole east margin are empty on it.
#
# The west leg is what the swap bought. It exists because pin 4 is on the
# package's west side, and rev B's spine was on the east because pin 11 was.
# The west leg goes in the far margin, not between the parts. Measured pad
# extents across the block, all of them through-hole or 1206 and so blocking
# every layer: R02 5.98-7.10 and 8.90-10.03, J 7.15-8.85, 9.69-11.39 and
# 12.23-13.93, C01 11.45-12.60 and 14.40-15.55. From 5.98 to 15.55 the widest
# gap between two of them is 0.47mm, which is not a corridor. West of 5.98 the
# margin is empty all the way to the board edge.
#
# The taps are long as a result -- 22mm from pin 4 -- and that is fine: the
# bypass capacitor is 8mm from the pin, and it is the loop through the
# capacitor that has to be short, not the feed behind it.
VPLUS_WEST_X = 4.0       # B.Cu, in the west margin outboard of the R02 column
VPLUS_EAST_X = 68.0      # B.Cu, inboard of the control riser
# 80.4, not 79.5: J7's own ground and V- pads drop their plane stubs 1.6mm
# south into exactly that strip, and the bottom leg has to pass beneath them.
VPLUS_BOTTOM_Y = 80.4    # B.Cu, below the tail connectors and their stubs
CTL_RISER_X = 70.4       # B.Cu, for the two right-column cells
CTL_SPINE_X = 59.3       # between the OUT bus and the control network's pads
# 69.2, between the V+ spine and the control riser. It was 76.8, outboard of
# the four bypass capacitors that used to sit in a column at x=73.5; those are
# gone, the board is 5mm narrower for it, and 76.8 is now off the edge.
TOG_RISER_X = 69.2
# The approach rows above the tail connectors, on F.Cu. V- no longer needs one
# -- it is a plane, and J7 pin 8 reaches it through a via like every other V-
# pad on the board -- so the two that are left move up into the space it used
# to take.
TAIL_Y = {"SW_TOG": 72.0, "SW_CTL": 73.0}


def route_supply(board):
    """V+, the switch control net and the toggle line.

    V+ is the one rail that is routed. V- and AGND are planes, so their pads
    are done by route_planes() and never appear here. In rev B it was the
    other way round and this function carried V-; the swap is RMC's point that
    an audio op-amp is V- referenced, and what it cost is the west leg below.
    """
    F, B = pcbnew.F_Cu, pcbnew.B_Cu
    p = board.pad

    def tap(net, pad, x, y=None, layer=F, width=POWER_TRACK, double=True):
        """Run from a pad to the spine at `x` and drop vias onto it.

        Defaults to POWER_TRACK. It used to default to TRACK, which is how
        every rail tap on rev B came out at 0.25mm while the spine they fed
        was 0.5mm -- not a decision, just an argument nobody passed. RMC:
        "beef up your Vcc, Vdd & Vss traces".

        Doubled by default too: every tap here lands in a margin with room
        for the pair, and each one is a power net changing layer, which is
        exactly what RMC asked to see doubled.
        """
        y = pad[1] if y is None else y
        board.track(net, [pad, (pad[0], y), (x, y)], layer=layer, width=width)
        if double:
            board.power_via(net, x, y, along=(0.0, 1.0) if x == pad[0]
                            else (1.0, 0.0))
        else:
            board.via(net, x, y)

    def hop(net, x, top, bottom, layer=B):
        board.via(net, x, top)
        board.track(net, [(x, top), (x, bottom)], layer=layer)
        board.via(net, x, bottom)

    # -- V+ ----------------------------------------------------------------
    # V- is a plane now, so every V- pin on the board -- both switch packages,
    # all three quads, J7 pin 8, R701, five capacitors -- is already connected
    # by route_planes() and nothing about it appears here. What is left is V+,
    # and this is the whole of it.
    #
    # A U on B.Cu, laid out so that no leg crosses anything: down the west
    # margin past the three quads, east along the bottom below the tail
    # connectors, and back up the east margin to the switches. J7 pin 7 is
    # through-hole, so the bottom leg reaches it without a via of its own.
    top = round(p("U4", 14)[1], 4)
    board.track("V+", [(VPLUS_WEST_X, p("U1", 4)[1]),
                       (VPLUS_WEST_X, VPLUS_BOTTOM_Y),
                       (VPLUS_EAST_X, VPLUS_BOTTOM_Y),
                       (VPLUS_EAST_X, top)], layer=B, width=POWER_TRACK)
    board.track("V+", [(p("J7", 7)[0], VPLUS_BOTTOM_Y), p("J7", 7)],
                layer=B, width=POWER_TRACK)

    # Each quad taps the west leg along its own centreline. Pin 4 is the
    # middle of the package's west column, so this run leaves the pad going
    # west and meets nothing: the BUFIN lanes flank the centreline at 1.27mm
    # and stop at the pad column, and west of them the block is empty.
    for index in range(1, circuit.CHANNELS // 2 + 1):
        pad = p(f"U{index}", 4)
        board.track("V+", [pad, (VPLUS_WEST_X, pad[1])], width=POWER_TRACK)
        board.power_via("V+", VPLUS_WEST_X, pad[1], along=(0.0, 1.0))
        # and the bypass capacitor sits on that run, 8mm from the pin. Its V+
        # pad is the southern one -- the run passes between the two pads, so
        # this is a stub off it rather than a break in it.
        cap = p(circuit.BYPASS[f"U{index}"][0], 1)
        board.track("V+", [(cap[0], pad[1]), cap], width=POWER_TRACK)

    # The east leg serves the switches and the control network. Pin 14 is the
    # top of each package's east column, which is the side the leg is on, so
    # both taps are 1.5mm long.
    for switch in ("U4", "U5"):
        # Single via, not the pair. Pin 13 leaves along the row 1.27mm below
        # on its way to the control riser, and a pair spread across the tap
        # closes to 0.195mm of it; spread along the tap instead and the far
        # via closes to 0.125mm of the toggle riser. There is no room here,
        # which is the whole of RMC's "where it is practical to do so".
        tap("V+", p(switch, 14), VPLUS_EAST_X, double=False)
    # R702's V+ pad is its western one, and its eastern one is SW_TOG, so this
    # cannot leave along its own row without crossing the part. It steps north
    # into the clear row above the control network instead.
    step = round(p("R702", 1)[1] - 2.5, 4)
    tap("V+", p("R702", 1), VPLUS_EAST_X, y=step)
    # The remaining two V+ capacitors. C941 runs west to the east leg, over
    # the two control risers -- they are on B.Cu and this is not. C901 sits on
    # the header row and drops straight onto the bottom leg beneath it.
    tap("V+", p("C941", 1), VPLUS_EAST_X)
    tap("V+", p("C901", 1), p("C901", 1)[0], y=VPLUS_BOTTOM_Y)

    # -- SW_CTL ------------------------------------------------------------
    # Nine pins on one net, spread over both switch packages and the control
    # network. The spine runs on B.Cu wherever it has to pass one of the
    # switched nodes' approach rows or a quad's V- run, and surfaces only
    # where something taps it.
    ctl = "SW_CTL"
    board.track(ctl, [p("U4", 5), (CTL_SPINE_X, p("U4", 5)[1])])
    board.track(ctl, [p("U4", 6), (CTL_SPINE_X, p("U4", 6)[1])])
    board.track(ctl, [(CTL_SPINE_X, p("U4", 5)[1]), (CTL_SPINE_X, 24.0)])
    hop(ctl, CTL_SPINE_X, 24.0, 32.5)
    board.track(ctl, [(CTL_SPINE_X, 32.5), (CTL_SPINE_X, 35.5)])
    board.track(ctl, [(CTL_SPINE_X, p("R701", 1)[1]), p("R701", 1)])
    hop(ctl, CTL_SPINE_X, 35.5, 42.5)
    board.track(ctl, [(CTL_SPINE_X, 42.5), (CTL_SPINE_X, 45.5)])
    board.track(ctl, [(CTL_SPINE_X, p("C701", 1)[1]), p("C701", 1)])
    hop(ctl, CTL_SPINE_X, 45.5, 51.0)
    board.track(ctl, [(CTL_SPINE_X, 51.0), (CTL_SPINE_X, p("U5", 6)[1])])
    board.track(ctl, [(CTL_SPINE_X, p("U5", 5)[1]), p("U5", 5)])
    board.track(ctl, [(CTL_SPINE_X, p("U5", 6)[1]), p("U5", 6)])
    # The two right-column cells and the toggle get their own riser, joined
    # to the spine on the one row between the control parts that is free.
    board.track(ctl, [(CTL_SPINE_X, 39.5), (CTL_RISER_X, 39.5)])
    board.via(ctl, CTL_SPINE_X, 39.5)
    board.via(ctl, CTL_RISER_X, 39.5)
    board.track(ctl, [(CTL_RISER_X, p("U4", 13)[1]),
                      (CTL_RISER_X, TAIL_Y[ctl])], layer=B)
    tap(ctl, p("U4", 13), CTL_RISER_X)
    tap(ctl, p("U5", 13), CTL_RISER_X)
    board.via(ctl, CTL_RISER_X, TAIL_Y[ctl])
    board.track(ctl, [(CTL_RISER_X, TAIL_Y[ctl]),
                      (p("J8", 2)[0], TAIL_Y[ctl]), p("J8", 2)])

    # -- SW_TOG ------------------------------------------------------------
    # One resistor to one header pin, but the whole board is in between.
    tog = "SW_TOG"
    tap(tog, p("R702", 2), TOG_RISER_X)
    board.track(tog, [(TOG_RISER_X, p("R702", 2)[1]),
                      (TOG_RISER_X, TAIL_Y[tog])], layer=B)
    board.via(tog, TOG_RISER_X, TAIL_Y[tog])
    board.track(tog, [(TOG_RISER_X, TAIL_Y[tog]),
                      (p("J8", 1)[0], TAIL_Y[tog]), p("J8", 1)])


def add_copper(board, rectangle):
    """AGND on In1, V- on In2. B.Cu is a signal layer, not a pour.

    Two planes rather than three, and V- is the one that gets the second --
    see PLANE_NETS for why. V+ is routed instead, in route_supply().
    """
    board.zone("AGND", pcbnew.In1_Cu, rectangle)
    board.zone("V-", pcbnew.In2_Cu, rectangle)


def silkscreen(board, rectangle):
    """Legends, sized so they fit on the board they are printed on.

    The stroke font advances about one text height per character, so a line
    of n characters at size s is roughly n*s wide. Both bottom lines are
    checked against the board width rather than trusted -- the previous pair
    ran off both edges, which a fab silently clips, taking the polarity
    warning with it.
    """
    left, top, right, bottom = rectangle
    middle = (left + right) / 2

    def legend(body, y, size):
        assert len(body) * size < (right - left) - 2 * BOARD_MARGIN, (
            f"silkscreen line is wider than the board: {body!r}")
        board.text(body, middle, y, size=size)

    legend("RMC pizz/arco  6 channel  rev D", top + 1.8, 1.4)
    # Below the tail connectors, not above them: above is the OUT fan-in, six
    # approach rows deep, and the header pads themselves.
    legend("J7  1-6=STRINGS  7=+4.5V  8=-4.5V  9=SHELL/GND", bottom - 2.9, 1.1)
    # The polarity is the thing that destroys the board if the loom is built
    # backwards, and there is deliberately no reverse-protection diode -- at
    # 9V total a series Schottky would cost about 0.6dB of headroom we do not
    # have. This silkscreen is the only defence, so it says why and not just
    # what.
    legend(f"{circuit.SUPPLY_RANGE}  CHECK POLARITY - NO REVERSE PROTECTION",
           bottom - 1.1, 0.9)
    # Channel labels sit on the quad side of their row, mirrored like
    # everything else in a block. On the other side is the sub-row, and its
    # designators are already there.
    for channel in range(1, circuit.CHANNELS + 1):
        s = -1 if channel % 2 else 1
        board.text(f"CH{channel} G/W/R", BLOCK_ORIGIN[0] + 6.0,
                   round(row_y(channel) - s * 2.6, 4), size=0.9)
    board.text("PIZZ=CLOSED", BOARD_PLACEMENT["J8"][0] - 6.0,
               BOARD_PLACEMENT["J8"][1] - 3.2, size=0.9)


def board_extent(board):
    """Outline from the placed parts, so the board is never bigger than it is."""
    xs, ys = [], []
    for footprint in board.footprints.values():
        box = footprint.GetCourtyard(pcbnew.F_CrtYd).BBox()
        xs += [to_mm(box.GetLeft()), to_mm(box.GetRight())]
        ys += [to_mm(box.GetTop()), to_mm(box.GetBottom())]
    return (0.0, 0.0,
            round(max(xs) + BOARD_MARGIN, 1), round(max(ys) + BOARD_MARGIN, 1))


def main():
    board = Board()
    place_blocks(board)
    place_rest(board)

    stubs = route_planes(board)
    route_critical(board)
    for channel in range(1, circuit.CHANNELS + 1):
        route_channel(board, channel)
    route_board(board)
    route_supply(board)

    rectangle = board_extent(board)
    board.outline(rectangle)
    inner = (rectangle[0] + rules.ZONE_INSET, rectangle[1] + rules.ZONE_INSET,
             rectangle[2] - rules.ZONE_INSET, rectangle[3] - rules.ZONE_INSET)
    add_copper(board, inner)
    silkscreen(board, rectangle)

    here = pathlib.Path(__file__).parent
    destination = here / circuit.PROJECT / f"{circuit.PROJECT}.kicad_pcb"
    pcbnew.ZONE_FILLER(board.board).Fill(board.board.Zones())
    pcbnew.SaveBoard(str(destination), board.board)

    print(f"wrote {destination}")
    print(f"  {len(board.footprints)} footprints, {stubs} plane stubs, "
          f"{len(list(board.board.GetTracks()))} track/via items")
    print(f"  board {rectangle[2]:.1f} x {rectangle[3]:.1f} mm "
          f"= {rectangle[2] * rectangle[3]:.0f} mm2")


if __name__ == "__main__":
    main()
