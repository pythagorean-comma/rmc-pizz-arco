"""Read the generated schematic back through KiCad and compare it to design.py.

The schematic is drawn from geometry -- wires meeting at coordinates -- so a
misplaced endpoint would silently produce a different circuit. This exports
KiCad's own netlist and checks that the connectivity it found is exactly the
connectivity design.py asked for, net by net.
"""

import json
import pathlib
import subprocess
import sys

import re

import design as circuit
import gen_project
import kicad
import rules
import sexp

KICAD_CLI = kicad.KICAD_CLI


def export_netlist(schematic, destination):
    result = subprocess.run(
        [str(KICAD_CLI), "sch", "export", "netlist", "--format", "kicadsexpr",
         "-o", str(destination), str(schematic)],
        capture_output=True, text=True)
    if result.returncode != 0 or not destination.exists():
        raise SystemExit(f"netlist export failed:\n{result.stdout}\n{result.stderr}")
    return destination


def read_netlist(path):
    """net name -> set of (ref, pin), ignoring drawing-only power symbols."""
    tree = sexp.parse(path.read_text())
    found = {}
    for net in sexp.find_all(sexp.find(tree, "nets"), "net"):
        name = sexp.find(net, "name")[1]
        nodes = set()
        for node in sexp.find_all(net, "node"):
            ref = sexp.find(node, "ref")[1]
            pin = sexp.find(node, "pin")[1]
            if ref.startswith("#"):
                continue        # power symbols and flags name nets, they are not parts
            nodes.add((ref, str(pin)))
        found[name] = nodes
    return found


def compare(actual, expected):
    """Compare as partitions; report differences in both directions."""
    problems = []

    actual_by_nodes = {frozenset(nodes): name for name, nodes in actual.items() if nodes}
    expected_by_nodes = {frozenset(nodes): name for name, nodes in expected.items()}

    for nodes, name in expected_by_nodes.items():
        if nodes not in actual_by_nodes:
            # Find whatever the schematic did with these pins instead.
            landed = {}
            for pin in sorted(nodes):
                for actual_name, actual_nodes in actual.items():
                    if pin in actual_nodes:
                        landed.setdefault(actual_name, []).append(pin)
                        break
                else:
                    landed.setdefault("<nowhere>", []).append(pin)
            detail = "; ".join(f"{k}: {sorted(v)}" for k, v in landed.items())
            problems.append(f"net {name} not formed as drawn -> {detail}")

    for nodes, name in actual_by_nodes.items():
        if nodes not in expected_by_nodes and not name.startswith("unconnected-"):
            problems.append(f"unexpected net {name} = {sorted(nodes)}")

    # An unconnected pin is an error by default -- that is how a wire that
    # missed its target gets caught. design.NO_CONNECT lists the pins that are
    # supposed to float, so the exception is declared alongside the circuit
    # rather than hidden in here.
    for name in sorted(actual):
        if not name.startswith("unconnected-"):
            continue
        pins = actual[name]
        if pins and pins <= set(circuit.NO_CONNECT):
            continue
        problems.append(f"unconnected pin: {name}")

    # Names should line up too, for the nets the design names explicitly.
    for nodes, name in expected_by_nodes.items():
        actual_name = actual_by_nodes.get(nodes)
        if actual_name and actual_name != name and not actual_name.startswith("Net-"):
            problems.append(f"net {name} is called {actual_name} in the schematic")

    return problems


def _reference(node):
    for prop in sexp.find_all(node, "property"):
        if prop[1] == "Reference":
            return prop[2]
    return None


def _property(node, name):
    for prop in sexp.find_all(node, "property"):
        if prop[1] == name:
            return prop[2]
    return None


def read_schematic_symbols(path):
    """reference -> (uuid, value), for the first unit of each placed symbol.

    Only direct children of the sheet are instances; the definitions inside
    lib_symbols are nested one level deeper and are skipped for free.
    """
    tree = sexp.parse(path.read_text())
    found = {}
    for symbol in sexp.find_all(tree, "symbol"):
        unit = sexp.find(symbol, "unit")
        uuid_node = sexp.find(symbol, "uuid")
        reference = _reference(symbol)
        if unit is None or uuid_node is None or reference is None:
            continue
        if int(str(unit[1])) == 1 and not reference.startswith("#"):
            found[reference] = (uuid_node[1], _property(symbol, "Value"))
    return found


def read_board_footprints(path):
    """reference -> (schematic path, footprint identifier)."""
    tree = sexp.parse(path.read_text())
    found = {}
    for footprint in sexp.find_all(tree, "footprint"):
        reference = _reference(footprint)
        if reference is None:
            continue
        path_node = sexp.find(footprint, "path")
        found[reference] = (path_node[1] if path_node else None,
                            str(footprint[1]))
    return found


def check_supply_annotations(schematic, board):
    """The supply range must appear on both the sheet and the silkscreen.

    Both are generated from design.SUPPLY_RANGE, so they cannot drift on their
    own -- but the schematic PDF is what gets sent to RMC, and a stale figure
    there once survived a re-spec unnoticed. This catches the other direction:
    an annotation edited by hand, leaving the constant behind.
    """
    problems = []
    for name, path in (("schematic", schematic), ("board", board)):
        if circuit.SUPPLY_RANGE not in path.read_text():
            problems.append(f"{name} does not state the supply range "
                            f"{circuit.SUPPLY_RANGE!r}")
    return problems


def check_project_rules(project):
    """The .kicad_pro on disk must still carry the rules gen_project.py wrote.

    DRC enforces whatever is in this file, and this file is the one artefact in
    the project that something other than the build writes: opening the project
    in the KiCad GUI rewrites it in KiCad's own expanded form, dropping
    `netclass_patterns` and resetting the constraint floors to KiCad's
    defaults. That happened, and the rewritten file reached a commit -- so the
    committed board's rails had no Power net class and the committed
    constraints were looser than the layout was drawn to.

    A build regenerates the file first, so the DRC in a build was always
    correct. This catches the other case: a project file that has been edited
    out from under the geometry, before anyone trusts a DRC run made against
    it.

    Only the load-bearing fields are compared. The GUI also adds viewports,
    layer presets and 3D settings, and none of those change what DRC does.
    """
    intent = gen_project.project_document("")["board"]["design_settings"]
    intent_nets = gen_project.project_document("")["net_settings"]
    try:
        actual = json.loads(project.read_text())
    except (OSError, ValueError) as error:
        return [f"cannot read {project.name}: {error}"]

    problems = []
    settings = actual.get("board", {}).get("design_settings", {})
    for name, wanted in sorted(intent["rules"].items()):
        found = settings.get("rules", {}).get(name)
        if found != wanted:
            problems.append(f"{project.name}: rule {name} is {found}, "
                            f"gen_project.py says {wanted}")

    nets = actual.get("net_settings", {})
    classes = {c["name"]: c for c in nets.get("classes", [])}
    for wanted in intent_nets["classes"]:
        found = classes.get(wanted["name"])
        if found is None:
            problems.append(f"{project.name}: net class {wanted['name']!r} is "
                            f"missing -- DRC would fall back to Default")
            continue
        for key in ("track_width", "clearance", "via_diameter", "via_drill"):
            if found.get(key) != wanted[key]:
                problems.append(
                    f"{project.name}: {wanted['name']}.{key} is "
                    f"{found.get(key)}, gen_project.py says {wanted[key]}")

    wanted_patterns = {(p["netclass"], p["pattern"])
                       for p in intent_nets["netclass_patterns"]}
    found_patterns = {(p.get("netclass"), p.get("pattern"))
                      for p in nets.get("netclass_patterns") or []}
    for netclass, pattern in sorted(wanted_patterns - found_patterns):
        problems.append(f"{project.name}: {pattern!r} is not assigned to "
                        f"{netclass!r} -- that rail is being checked as Default")

    return problems


def board_figures(board):
    """The numbers fab/ORDER.md quotes, read back off the built board.

    Parsed with sexp rather than pcbnew, because verify.py runs under plain
    python3 and only gen_pcb.py gets KiCad's bundled interpreter. Everything
    needed is in the board file as text.
    """
    tree = sexp.parse(board.read_text())

    copper = [layer for layer in sexp.find(tree, "layers")[1:]
              if str(layer[1]).endswith(".Cu")]

    xs, ys = [], []
    for line in sexp.find_all(tree, "gr_line"):
        for end in ("start", "end"):
            point = sexp.find(line, end)
            xs.append(float(point[1]))
            ys.append(float(point[2]))

    vias = list(sexp.find_all(tree, "via"))
    via_drills = {float(sexp.find(v, "drill")[1]) for v in vias}

    # A footprint counts as through-hole if any of its pads is drilled. The
    # eight connectors are the only ones, and their holes are what the fab
    # drills at a different size from the vias.
    footprints = list(sexp.find_all(tree, "footprint"))
    through_hole, pad_holes = 0, []
    for footprint in footprints:
        drilled = [p for p in sexp.find_all(footprint, "pad")
                   if any(str(item) == "thru_hole" for item in p[:4])]
        if drilled:
            through_hole += 1
            pad_holes += [float(sexp.find(p, "drill")[1]) for p in drilled]

    return {
        "layers": len(copper),
        "width": round(max(xs) - min(xs), 1),
        "height": round(max(ys) - min(ys), 1),
        "vias": len(vias),
        "via_drill": via_drills.pop() if len(via_drills) == 1 else None,
        "connector_holes": len(pad_holes),
        "connector_drill": (set(pad_holes).pop()
                            if len(set(pad_holes)) == 1 else None),
        "plated": len(vias) + len(pad_holes),
        "placements": len(footprints),
        "through_hole": through_hole,
        "smd": len(footprints) - through_hole,
    }


def check_order_figures(board, order):
    """fab/ORDER.md must still be describing the board that was just built.

    ORDER.md carries about a dozen numbers that are all derivable -- the board
    size, the layer count, every design rule, the hole count, the placement
    split. They are written by hand, because the prose around them is worth
    more than a generated table, and **twice** they have gone stale: the board
    dimensions after the plane swap, and the hole count after the all-pass
    feedback pair moved, which said 177 vias and 206 plated holes when the
    board had 147 and 176.

    That is worse than an ordinary documentation slip, because build.sh copies
    this file into the fabrication zip. A stale figure is a wrong number in
    front of the contractor, in the one document whose whole job is to carry
    what the gerbers cannot.

    So the numbers are asserted rather than generated: write the prose freely,
    and the build refuses to package a board the document no longer describes.
    """
    text = order.read_text()
    figures = board_figures(board)
    problems = []

    def stated(pattern, what):
        """Pull one figure out of ORDER.md, or report that it has moved."""
        found = re.search(pattern, text)
        if found is None:
            problems.append(f"{order.name}: cannot find the {what} figure -- "
                            f"the wording moved, so this check stopped "
                            f"checking it")
            return None
        return found

    def show(values):
        """Whole numbers as integers, so 147 does not read as 147.0."""
        return " / ".join(f"{v:g}" for v in values)

    def compare(pattern, what, *expected):
        found = stated(pattern, what)
        if found is None:
            return
        actual = tuple(float(g) for g in found.groups())
        if actual != tuple(float(e) for e in expected):
            problems.append(
                f"{order.name}: {what} says {show(actual)}, "
                f"the board says {show(float(e) for e in expected)}")

    compare(r"\*\*Layers\*\* \| \*\*(\d+)\.", "layer count", figures["layers"])
    compare(r"Board size \| ([\d.]+) × ([\d.]+) mm",
            "board size", figures["width"], figures["height"])
    compare(r"Hole count: \*\*(\d+) vias at ([\d.]+) mm\*\* and "
            r"\*\*(\d+) connector holes at ([\d.]+) mm\*\*, (\d+)",
            "hole count", figures["vias"], figures["via_drill"],
            figures["connector_holes"], figures["connector_drill"],
            figures["plated"])
    compare(r"\*\*(\d+) placements: (\d+) SMD and (\d+) through-hole",
            "placement count", figures["placements"], figures["smd"],
            figures["through_hole"])

    # The design rules come from rules.py, which gen_project.py writes into the
    # .kicad_pro for DRC to enforce -- so this closes the loop from the rule,
    # through the checker, to what the fab is told.
    for pattern, what, expected in (
            (r"\| Min track width \| ([\d.]+) mm", "min track width",
             rules.TRACK),
            (r"\| Power track width \| ([\d.]+) mm", "power track width",
             rules.POWER_TRACK),
            (r"\| Min clearance \| ([\d.]+) mm", "min clearance",
             rules.CLEARANCE),
            (r"\| Min drill \| ([\d.]+) mm", "min drill", rules.VIA_DRILL),
            (r"\| Min annular ring \| ([\d.]+) mm", "min annular ring",
             rules.ANNULAR_RING),
            (r"\| Board edge clearance \| ([\d.]+) mm", "board edge clearance",
             rules.MIN_COPPER_EDGE_CLEARANCE)):
        compare(pattern, what, expected)
    compare(r"\| Via pad / drill \| ([\d.]+) / ([\d.]+) mm", "via pad / drill",
            rules.VIA_DIAMETER, rules.VIA_DRILL)

    return problems


def check_board_linkage(schematic, board):
    """Every footprint must point at its schematic symbol and name its library.

    Without the path KiCad cannot associate the two, so cross-probing dies and
    'Update PCB from Schematic' offers to add every footprint again as a new
    part. Without the library prefix it cannot update a footprint from its
    library. Both are silent -- nothing else in the build would notice.
    """
    symbols = read_schematic_symbols(schematic)
    footprints = read_board_footprints(board)
    problems = []

    # Values are set in three places -- design.py, the schematic and the BOM
    # that KiCad derives from it -- so check the drawing still agrees with the
    # design. A stale literal here is invisible until it reaches a BOM.
    for reference, (_, value) in sorted(symbols.items()):
        wanted = circuit.PARTS[reference].value
        if value != wanted:
            problems.append(f"{reference}: schematic says {value!r}, "
                            f"design.py says {wanted!r}")

    for reference, (path, identifier) in sorted(footprints.items()):
        expected = symbols.get(reference)
        if expected is None:
            problems.append(f"{reference}: on the board but not the schematic")
        elif path != f"/{expected[0]}":
            problems.append(f"{reference}: path {path} does not match "
                            f"schematic symbol /{expected[0]}")
        if ":" not in identifier:
            problems.append(f"{reference}: footprint {identifier!r} has no library")

    for reference in sorted(set(symbols) - set(footprints)):
        if not circuit.PARTS[reference].footprint:
            continue        # power flags are schematic-only, by design
        problems.append(f"{reference}: in the schematic but not on the board")

    return problems, len(footprints)


def main():
    here = pathlib.Path(__file__).parent
    schematic = here / "rmc-pizz-arco" / "rmc-pizz-arco.kicad_sch"
    netlist = here / "build" / "verify.net"
    netlist.parent.mkdir(parents=True, exist_ok=True)

    export_netlist(schematic, netlist)
    actual = read_netlist(netlist)
    expected = {name: {n for n in nodes if not n[0].startswith("#")}
                for name, nodes in circuit.NETS.items()}

    problems = compare(actual, expected)
    if problems:
        print(f"{len(problems)} problem(s):")
        for problem in problems[:60]:
            print(f"  - {problem}")
        if len(problems) > 60:
            print(f"  ... and {len(problems) - 60} more")
        return 1

    print(f"schematic matches design.py: {len(expected)} nets, "
          f"{sum(len(v) for v in expected.values())} pin connections")

    board = here / circuit.PROJECT / f"{circuit.PROJECT}.kicad_pcb"
    if not board.exists():
        print("board not generated yet; skipping linkage check")
        return 0
    problems, count = check_board_linkage(schematic, board)
    problems += check_supply_annotations(schematic, board)
    problems += check_project_rules(
        here / circuit.PROJECT / f"{circuit.PROJECT}.kicad_pro")
    problems += check_order_figures(board, here / "fab" / "ORDER.md")
    if problems:
        print(f"{len(problems)} board linkage problem(s):")
        for problem in problems[:20]:
            print(f"  - {problem}")
        return 1
    print(f"board linked to schematic: {count} footprints")
    print(f"design rules intact: {gen_project.TRACK_WIDTH}mm signal, "
          f"{gen_project.POWER_TRACK_WIDTH}mm power, "
          f"{gen_project.VIA_DIAMETER}/{gen_project.VIA_DRILL}mm vias, "
          f"{gen_project.CLEARANCE}mm clearance")
    figures = board_figures(board)
    print(f"fab/ORDER.md still describes this board: "
          f"{figures['width']} x {figures['height']}mm, "
          f"{figures['layers']} layers, {figures['placements']} placements, "
          f"{figures['plated']} plated holes")
    return 0


if __name__ == "__main__":
    sys.exit(main())
