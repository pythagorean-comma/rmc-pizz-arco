"""Draw a simulation schematic for the design in design.py.

Open the result in KiCad and press Simulate. There is nothing to install: KiCad
ships ngspice, and this sheet carries the SPICE annotations that let its
built-in simulator run the circuit.

It is a *separate* sheet from the fabrication one, and deliberately so. What a
board needs and what a simulator needs are different: the board has connectors
where the simulator needs sources, and it has no load on OUT at all because the
Poly-Drive II supplies one. Annotating the fabrication schematic to serve both
would compromise the document that goes to a fab in order to please a tool.
Both are generated from the same `design.py`, so neither can drift from the
circuit.

**One channel, not six.** The six are electrically independent -- they share
`V+`, `V-` and `SW_CTL`, all low-impedance or DC, and nothing else. Five more
copies would add no question that this one cannot answer. That is the opposite
of `summing-mixer`, where every channel met at one node and isolation between
them was the whole claim.

What differs from the fabrication sheet, and why each difference is safe:

  * the supply becomes two ideal VDC sources at the rails `design.py` predicts.
    There is no supply section on this board to model -- the rails arrive from
    the Poly-Drive II ready-made, and what the signal path cares about is the
    number.
  * `J1` becomes two element models, each a voltage source behind its own
    1700 pF, from source.py. This is the single most important difference on
    the sheet and the one it would be easiest to skip; see source.py for what
    skipping it does.
  * `J7` becomes a load, because the board has none and SPICE cannot solve a
    node with no DC path. The value is an assumption and source.py says so.
  * the CD4066 cell becomes a controlled resistance. TI publish no SPICE model
    for the CD4066B -- see SWITCH_RON below -- so this one part is modelled
    rather than fetched, and its on-resistance is swept rather than quoted.
  * the buffer and the all-pass are drawn as two single op-amps rather than
    two units of a quad, because TI's model is a single amplifier. Same
    silicon, same model, one instance each.

The three ways a simulation returns confident wrong answers are in
`docs/simulating.md`. Two of them are now impossible -- `kisim.ground()` can
only return node 0, and `kisch.auto_junctions()` refuses to emit a sheet where
two net names share a coordinate. The third has no tool behind it: a test that
cannot fail is not evidence. Every analysis in directives() below therefore
says what a failure would have looked like, and where the answer is guaranteed
by the test rig rather than by the circuit, it says that too.
"""

import pathlib

import design as circuit
import kisim
import source
from kisch import Schematic

PROJECT = f"{circuit.PROJECT}-sim"

# TI's OPAx191 macromodel: https://www.ti.com/lit/zip/SBOMA30
#
# Not committed, and it must not be. TI's model licence is a grant to use, not
# to redistribute, and this repository is public. Fetch the zip, unpack
# OPAx191.LIB beside this file's output, and .gitignore keeps it out of the
# tree.
#
# The sheet is generated whether or not the file is present. A missing model is
# KiCad's error to report at simulation time, not a reason for the build to
# fail over something it cannot legally ship.
#
# `.SUBCKT OPAx191 IN+ IN- VCC VEE OUT` -- one amplifier, which is why this
# sheet draws two single op-amps where the board has one quad. Read out of the
# file rather than assumed; TI renamed the subcircuit from OPA191 to OPAx191 in
# model version Final 1.2 and a sheet written against the old name would fail
# at simulation time with nothing to say why.
MODEL_FILE = "OPAx191.LIB"
MODEL_NAME = "OPAx191"
MODEL_SOURCE = "https://www.ti.com/lit/zip/SBOMA30"

# The CD4066B has no vendor model at all.
#
# DESIGN.md's simulation section assumed TI publish one. They do not: the
# product page, its tools-and-software tab and TI's own E2E forum all say the
# same thing, and the models that circulate are community rebuilds from CD4007
# gates. So the switch is modelled here, and the honest form of "R_on does not
# perturb the all-pass" is a *sweep* rather than a number.
#
# What is being replaced is specifically the R_on-against-supply curve a vendor
# model would have carried. This board runs the switch at 9 V total, near the
# bottom of the part's range, where R_on is highest and rising fastest.
# DESIGN.md quotes ~100 ohms; the datasheet's own tables could not be read in
# the environment this was written in, so 100 ohms is the *nominal* and the
# sweep spans an order of magnitude above it, which brackets any plausible
# CD4066B at these rails including worst case over temperature.
#
# Two things this model does not do, stated because assuming otherwise is how
# a switch analysis comes back clean for free:
#
#   * R_on does not vary with signal level. A real CD4066's does, and that
#     variation is what would produce distortion. This model cannot show it.
#   * R_off is a resistor, not a reverse-biased junction with capacitance. The
#     off state here is cleaner than the part's.
#
# Neither affects the question actually being asked, which is how much of the
# switched leg's ground reference leaks back through R05.
SWITCH_RON = 100.0
SWITCH_RON_SWEEP = (100.0, 300.0, 1000.0)
SWITCH_ROFF = 1e8

# How wide the control window is, in volts, and why the switch is a resistor.
#
# `Simulation_SPICE:SWITCH` is the obvious part to use here and it is wrong, in
# the specific way this project's documentation is about. ngspice's SW device
# **always contributes roff in AC analysis**, whatever its control voltage is
# doing. Its DC operating point is correct -- SWN sits at 0 V with the cell on
# and follows BUFOUT with it off -- so nothing looks amiss, and then every AC
# run returns the switch-open circuit for both switch positions.
#
# Measured, because that is the only way it shows: with a SW device the two
# states came out identical to four decimal places at every frequency, which
# reads as a triumphant confirmation of "no level jump" and is the same answer
# it would have given for a circuit with no switch in it at all. Sweeping ron
# changed nothing; sweeping roff changed both. See docs/simulating.md.
#
# So the cell is modelled as what it electrically is: a resistance controlled
# by a voltage. ngspice linearises a behavioural resistor about its operating
# point, so the AC small-signal conductance is the one the DC solution chose,
# which is the whole requirement.
#
# 0.15 V of control window is narrower than a real CD4066's, which spans
# something closer to a volt. That is the conservative direction for the only
# analysis that depends on it: a transition modelled faster than the part's is
# more likely to show a click, not less.
SWITCH_EDGE = 0.15

# The single-amplifier symbol borrowed for the buffer and the all-pass. Same
# borrowing pattern design.LIBS uses for the fabrication schematic, where
# OPA4197xD supplies OPA4191's body: take a stock body of the right shape and
# rename it, so the sheet says what the BOM says.
#
# LM321 rather than a quad, because TI's model is one amplifier: five pins, all
# on one unit, in the order this design needs.
SIM_LIBS = {
    **kisim.LIBS,
    "rmc:OPA4191_SIM": ("rmc", "Amplifier_Operational", "LM321", "OPA4191_SIM"),
}

# LM321's pinout, as the borrowed body presents it.
AMP = {"+": 1, "V-": 2, "-": 3, "out": 4, "V+": 5}

# -- sheet geometry ---------------------------------------------------------
# Lanes, absolute. The channel keeps gen_sch.py's arrangement -- inverting
# input above, switched node below, feedback pair above both -- so the two
# drawings can be read against each other and against RMC's original.
Y_OUT = 38.1        # red element straight through to the summing node
Y_APN_LBL = 50.8    # label stubs, clear of the red run above them
Y_FBR = 55.88       # all-pass feedback resistor
Y_FBC = 60.96       # all-pass feedback capacitor
Y_MAIN = 66.04      # white element, buffer input, all-pass inverting input
Y_BUF = 68.58       # buffer body centre, and its output
Y_AP = 76.2         # all-pass body centre
Y_APP = 86.36       # all-pass non-inverting input -- the switched lane
Y_BUFFB = 88.9      # the buffer's own feedback, returning under the package
Y_CTRL = 139.7      # the pizz/arco control network

X_SRC = 30.48       # both element sources
X_ELCAP = 45.72     # both element capacitances
X_INW = 83.82       # IN_W, where R02 hangs
X_R01 = 92.71
X_BUFIN = 104.14
X_FBRET = 107.95    # the buffer feedback's return column
X_BUF = 119.38
X_BUFOUT = 132.08   # buffer output column, feeding both all-pass legs
X_ALLPASS_R = 142.24   # R04 and R05
X_APN = 157.48      # all-pass inverting column
X_SWN = 165.1       # switched column, down to C03
X_FB = 168.91       # the feedback pair
X_SWBRANCH = 152.4  # down to the switch cell
X_AP = 180.34
X_APOUT = 195.58
X_C04 = 208.28
X_OUT = 220.98
X_LOAD = 233.68
X_STRAY = 246.38

RAIL_ORIGIN = (279.4, 127.0)

# The notes run to about 140 lines, which is three columns on an A2 sheet
# below the circuit. One column runs off the bottom of the page -- the text
# still renders and still simulates, so nothing complains; it is simply
# unreadable, which is the same class of quiet failure as everything else here.
NOTE_ORIGIN = (12.7, 180.34)
NOTE_PITCH = 4.445
NOTE_ROWS = 51             # 180.34 + 51 * 4.445 = 407 mm, inside A2's 420
NOTE_COLUMN = 190.5

# The mechanics live in kisim.py, which copies between these repositories
# unchanged. What is left here is this circuit: what to simulate, and where the
# parts sit on the sheet.
place = kisim.place
resistor = kisim.resistor
capacitor = kisim.capacitor
ground = kisim.ground


def board(sch, ref, x, y, angle=0):
    """Place a part at the value design.py gives it.

    Read from design.PARTS rather than written as a literal, so the simulated
    circuit cannot drift from the fabricated one. A resistor or a capacitor is
    decided by the same lib_id the board uses.
    """
    part = circuit.PARTS[ref]
    maker = resistor if part.lib_id == "Device:R" else capacitor
    return maker(sch, ref, part.value, x, y, angle=angle)


def amplifier(sch, ref, x, y, mirror=None):
    """One OPA4191 unit, as a single amplifier carrying TI's model.

    TI's subcircuit is .SUBCKT OPAx191 IN+ IN- VCC VEE OUT -- one amplifier,
    which is why this sheet draws two single op-amps where the board has one
    quad serving two channels with four of them.
    """
    return kisim.subckt(sch, ref, "rmc:OPA4191_SIM", "OPA4191", x, y,
                        model=MODEL_NAME, library=MODEL_FILE, mirror=mirror,
                        pins=f"{AMP['+']}=IN+ {AMP['-']}=IN- {AMP['V+']}=VCC "
                             f"{AMP['V-']}=VEE {AMP['out']}=OUT")


def switch(sch, ref, value, x, y, control, ron, angle=0):
    """A switch, drawn as the controlled resistance it actually is.

    On when `control` is above ground and off below it, which is what the real
    CD4066 does with its control referred to Vss. See SWITCH_EDGE for why this
    is not `Simulation_SPICE:SWITCH`, which is the obvious choice and returns
    the same answer for both switch positions in AC.

    The expression reaches ngspice verbatim: KiCad's netlister passes an
    ideal resistor's value through unchanged, so writing ngspice's own
    behavioural syntax into it is what gets `R107 SWN 0 R='...'` on the other
    side. Checked against the exported netlist rather than assumed.
    """
    expr = (f"R='{ron:g}+{SWITCH_ROFF:g}"
            f"/(1+exp(V({control})/{SWITCH_EDGE:g}))'")
    return place(sch, ref, "Device:R", value, x, y, angle=angle,
                 sim={"Sim.Device": "R", "Sim.Params": f'r="{expr}"'})


def element(sch, ref, cap_ref, label, x, lane, amplitude, ground_below):
    """One PZT element: a voltage source behind its own capacitance.

    The part of this sheet that matters most, and the part with no vendor model
    behind it. A PZT element is a charge source; above the frequency where the
    external impedance stops dominating its own reactance it behaves as a
    voltage source in series with that capacitance, and source.C_ELEMENT is
    RMC's figure for it.

    Putting the source straight onto the node instead is not a simplification.
    An ideal source has no output impedance, so it pins its node to its own
    value whatever the circuit does: R02 would load nothing, the 28 Hz input
    corner would vanish, and every low-frequency answer would come back flat
    and plausible. That is exactly how an isolation test on `summing-mixer`
    came to confirm a circuit it could not have distinguished from a broken
    one. See docs/simulating.md.
    """
    src = kisim.source(sch, ref, "VSIN", label, x, lane + 5.08,
                       f"dc=0 ampl={amplitude:g} f=1k ac={amplitude:g}")
    sch.wire(src.pin(2), (x, ground_below))
    ground(sch, x, ground_below)
    cap = capacitor(sch, cap_ref, kisim.as_value(source.C_ELEMENT, "F"),
                    X_ELCAP, lane, angle=90)
    sch.wire(src.pin(1), cap.pin(1))
    return cap.pin(2)


def rail_stub(sch, part, x, y_from, y_to, rail):
    """Take an amplifier's supply pin to a label, clear of the signal lanes."""
    sch.wire((x, y_from), (x, y_to))
    sch.label(rail, x, y_to, angle=90 if y_to < y_from else 270)


def white_element(sch):
    """PZT 2, its bias and stopper, and the unity-gain buffer."""
    node = element(sch, "V801", "C801", "PZT2 white", X_SRC, Y_MAIN,
                   amplitude=1, ground_below=Y_MAIN + 15.24)
    sch.wire(node, (X_INW, Y_MAIN))
    sch.label("IN_W", X_INW, Y_MAIN)

    bias = board(sch, "R102", X_INW, Y_MAIN + 8.89)
    sch.wire((X_INW, Y_MAIN), bias.pin(1))
    sch.wire(bias.pin(2), (X_INW, Y_MAIN + 17.78))
    ground(sch, X_INW, Y_MAIN + 17.78)

    stopper = board(sch, "R101", X_R01, Y_MAIN, angle=90)
    sch.wire((X_INW, Y_MAIN), stopper.pin(1))
    sch.wire(stopper.pin(2), (X_BUFIN, Y_MAIN))
    sch.label("BUFIN", X_BUFIN, Y_MAIN)

    rf = board(sch, "C101", X_BUFIN, Y_MAIN + 8.89)
    sch.wire((X_BUFIN, Y_MAIN), rf.pin(1))
    sch.wire(rf.pin(2), (X_BUFIN, Y_MAIN + 17.78))
    ground(sch, X_BUFIN, Y_MAIN + 17.78)

    buf = amplifier(sch, "U101", X_BUF, Y_BUF)
    sch.wire((X_BUFIN, Y_MAIN), buf.pin(AMP["+"]))
    # The feedback is a wire, not a part -- RMC took R03 out and asked for OUT
    # tied straight back to -IN. On the board those are adjacent pins 1.27 mm
    # apart; here it is drawn as the return it is, under the package.
    out = buf.pin(AMP["out"])
    sch.wire(out, (out[0], Y_BUFFB), (X_FBRET, Y_BUFFB),
             (X_FBRET, Y_MAIN + 5.08), buf.pin(AMP["-"]))
    sch.wire(out, (X_BUFOUT, Y_BUF))

    rail_stub(sch, buf, buf.pin(AMP["V+"])[0], Y_BUF - 7.62, Y_FBR - 2.54, "V+")
    rail_stub(sch, buf, buf.pin(AMP["V-"])[0], Y_BUF + 7.62, Y_AP + 6.35, "V-")

    sch.wire((X_BUFOUT, Y_MAIN - 2.54), (X_BUFOUT, Y_APP))
    sch.label("BUFOUT", X_BUFOUT, Y_MAIN - 2.54, angle=90)


def all_pass(sch):
    """The +-1 stage, and the switch that chooses which.

    Note what is drawn here and what DESIGN.md calls it. C02 sits in parallel
    with R06, which is what RMC drew, so the feedback impedance is not a
    resistor -- and a first-order all-pass needs it to be one. The stage is
    +1 or -1 only well below the 34 kHz corner. Analyses 1 to 3 are about
    exactly how far "well below" reaches.
    """
    r_in = board(sch, "R104", X_ALLPASS_R, Y_MAIN, angle=90)
    sch.wire((X_BUFOUT, Y_MAIN), r_in.pin(1))
    sch.wire(r_in.pin(2), (X_APN, Y_MAIN))

    r_lag = board(sch, "R105", X_ALLPASS_R, Y_APP, angle=90)
    sch.wire((X_BUFOUT, Y_APP), r_lag.pin(1))
    sch.wire(r_lag.pin(2), (X_SWBRANCH, Y_APP), (X_SWN, Y_APP))

    amp = amplifier(sch, "U102", X_AP, Y_AP, mirror="x")
    sch.wire((X_APN, Y_FBR), (X_APN, Y_AP - 2.54), amp.pin(AMP["-"]))
    sch.wire((X_APN, Y_FBR), (X_APN, Y_APN_LBL))
    sch.label("APN", X_APN, Y_APN_LBL, angle=90)

    sch.wire(amp.pin(AMP["+"]), (X_SWN, Y_AP + 2.54), (X_SWN, Y_APP + 5.08))
    lag = board(sch, "C103", X_SWN, Y_APP + 8.89)
    sch.wire((X_SWN, Y_APP + 5.08), lag.pin(1))
    sch.wire(lag.pin(2), (X_SWN, Y_APP + 17.78))
    ground(sch, X_SWN, Y_APP + 17.78)

    for ref, lane in (("R106", Y_FBR), ("C102", Y_FBC)):
        part = board(sch, ref, X_FB, lane, angle=90)
        sch.wire((X_APN, lane), part.pin(1))
        sch.wire(part.pin(2), (X_APOUT, lane))
    sch.wire(amp.pin(AMP["out"]), (X_APOUT, Y_AP))
    sch.wire((X_APOUT, Y_FBR), (X_APOUT, Y_AP))
    sch.wire((X_APOUT, Y_FBR), (X_APOUT, Y_APN_LBL))
    sch.label("APOUT", X_APOUT, Y_APN_LBL, angle=90)

    rail_stub(sch, amp, amp.pin(AMP["V-"])[0], Y_AP - 7.62, Y_FBC + 2.54, "V-")
    rail_stub(sch, amp, amp.pin(AMP["V+"])[0], Y_AP + 7.62, Y_APP + 3.81, "V+")

    # One CD4066 cell, grounding the switched node. On the board this is one of
    # six cells across two packages driven from a single control line; the other
    # five are copies of it serving copies of this channel.
    cell = switch(sch, "R802", "CD4066B cell", X_SWBRANCH, Y_APP + 21.59,
                  control="SW_CTL", ron=SWITCH_RON)
    sch.wire((X_SWBRANCH, Y_APP), (X_SWBRANCH, Y_APP + 12.7), cell.pin(1))
    sch.label("SWN", X_SWBRANCH, Y_APP + 12.7, angle=90)
    sch.wire(cell.pin(2), (X_SWBRANCH, Y_APP + 30.48))
    ground(sch, X_SWBRANCH, Y_APP + 30.48)


def summing_node(sch):
    """PZT 1 straight through, C04 in beside it, and the load that is not ours.

    The equation DESIGN.md states -- OUT = (V_red.C_red + V_white.C04) /
    (C_red + C04 + C_stray) -- is this node, and it is where the board's whole
    reason for existing is decided. The two elements meet nowhere else.
    """
    node = element(sch, "V802", "C802", "PZT1 red", X_SRC, Y_OUT,
                   amplitude=1, ground_below=Y_OUT + 15.24)
    sch.wire(node, (X_OUT, Y_OUT))

    summing = board(sch, "C104", X_C04, Y_FBR, angle=90)
    sch.wire((X_APOUT, Y_FBR), summing.pin(1))
    sch.wire(summing.pin(2), (X_OUT, Y_FBR))
    sch.wire((X_OUT, Y_FBR), (X_OUT, Y_OUT))

    # The Poly-Drive II's input, which is not on this board and is not stated
    # anywhere. source.py carries the assumption and what turns on it.
    load = resistor(sch, "R801", kisim.as_value(source.R_LOAD),
                    X_LOAD, Y_OUT + 8.89)
    sch.wire((X_OUT, Y_OUT), (X_LOAD, Y_OUT), load.pin(1))
    sch.wire(load.pin(2), (X_LOAD, Y_OUT + 17.78))
    ground(sch, X_LOAD, Y_OUT + 17.78)

    stray = capacitor(sch, "C803", kisim.as_value(source.C_STRAY, "F"),
                      X_STRAY, Y_OUT + 8.89)
    sch.wire((X_LOAD, Y_OUT), (X_STRAY, Y_OUT), stray.pin(1))
    sch.wire(stray.pin(2), (X_STRAY, Y_OUT + 17.78))
    ground(sch, X_STRAY, Y_OUT + 17.78)

    sch.wire((X_STRAY, Y_OUT), (X_STRAY + 12.7, Y_OUT))
    sch.label("OUT", X_STRAY + 12.7, Y_OUT)


def control(sch):
    """RMC's control network, with the toggle as a switch so it can be flipped.

    Drawn rather than replaced by a DC level because the 10 ms it takes to
    change is a claim in its own right -- DESIGN.md says the transition is
    click-free, and R701 x C701 is what makes it slow enough to be.
    """
    sch.label("V+", X_INW - 7.62, Y_CTRL, angle=0)
    sch.wire((X_INW - 7.62, Y_CTRL), (X_INW, Y_CTRL))

    limit = board(sch, "R702", X_INW + 3.81, Y_CTRL, angle=90)
    sch.wire((X_INW, Y_CTRL), limit.pin(1))
    sch.wire(limit.pin(2), (X_BUFIN - 8.89, Y_CTRL), (X_BUFIN - 3.81, Y_CTRL))
    sch.label("SW_TOG", X_BUFIN - 8.89, Y_CTRL)

    # J8's toggle, which is a mechanical contact and a piece of cable. Modelled
    # the same way as the cell so there is exactly one switch idiom on the
    # sheet and no second thing to be wrong about.
    toggle = switch(sch, "R803", "J8 PIZZ/ARCO", X_BUFIN, Y_CTRL,
                    control="TOGGLE", ron=1.0, angle=90)
    sch.wire(toggle.pin(2), (X_FBRET + 13.97, Y_CTRL), (X_BUFOUT + 2.54, Y_CTRL))
    sch.label("SW_CTL", X_BUFOUT + 2.54, Y_CTRL)

    pull = board(sch, "R701", X_FBRET + 13.97, Y_CTRL + 8.89)
    sch.wire((X_FBRET + 13.97, Y_CTRL), pull.pin(1))
    sch.wire(pull.pin(2), (X_FBRET + 13.97, Y_CTRL + 17.78))
    sch.label("V-", X_FBRET + 13.97, Y_CTRL + 17.78, angle=270)

    debounce = board(sch, "C701", X_BUFOUT + 2.54, Y_CTRL + 8.89)
    sch.wire((X_BUFOUT + 2.54, Y_CTRL), debounce.pin(1))
    sch.wire(debounce.pin(2), (X_BUFOUT + 2.54, Y_CTRL + 17.78))
    ground(sch, X_BUFOUT + 2.54, Y_CTRL + 17.78)

    # The toggle's own control. Not a component on the board -- it is the
    # player's thumb, and it is here so a transient run has something to flip.
    #
    # y1 is what every AC and DC analysis sees, because that is the value a
    # pulse holds at the operating point: y1=-1 is arco, y1=+1 is pizz, and
    # flipping that one field is how analyses 1 to 4 change state. Left at -1
    # the source also steps arco -> pizz at td, which is analysis 6.
    drive = kisim.source(sch, "V803", "VPULSE", "pizz/arco", X_BUFIN,
                         Y_CTRL + 17.78,
                         "y1=-1 y2=1 td=10m tr=1u tf=1u tw=40m per=100m")
    sch.wire(drive.pin(1), (X_BUFIN, Y_CTRL + 7.62))
    sch.label("TOGGLE", X_BUFIN, Y_CTRL + 7.62, angle=270)
    sch.wire(drive.pin(2), (X_BUFIN, Y_CTRL + 27.94))
    ground(sch, X_BUFIN, Y_CTRL + 27.94)


def rails(sch):
    """Two ideal sources at the voltages the Poly-Drive II delivers.

    Not a model of a supply -- a statement of its result. There is no supply
    section on this board to model: DESIGN.md's "What is not on the board" is
    a list of nine things, and all of them are power.
    """
    ox, oy = RAIL_ORIGIN
    for index, (net, volts) in enumerate((("V+", 4.5), ("V-", -4.5))):
        x = ox + index * 25.4
        src = kisim.source(sch, f"VR{index + 1}", "VDC", f"{volts:+.2f}V",
                           x, oy, f"dc={volts:.4g}")
        sch.wire(src.pin(1), (x, oy - 10.16))
        sch.label(net, x, oy - 10.16, angle=90)
        sch.wire(src.pin(2), (x, oy + 10.16))
        ground(sch, x, oy + 10.16)


def directives(sch):
    """The analyses, as text KiCad reads as SPICE directives.

    Only one may be active at a time, so the rest are commented. The numbers in
    them come from design.py and source.py, so what is simulated is what the
    design claims -- and each one carries what a failure would have looked
    like, because a test that cannot fail is not evidence.
    """
    tau = (kisim.magnitude(circuit.PARTS["R105"].value)
           * kisim.magnitude(circuit.PARTS["C103"].value))
    corner = 1.0 / (2 * 3.14159265 * tau)
    lines = [
        "* The model is included by U101/U102's Sim.Library field -- adding an",
        "* .include here as well would load it twice.",
        "",
        "* Not optional for anything driven near a rail. TI's macromodel stalls",
        "* when the output is pinned: ngspice reports 'Timestep too small' from",
        "* inside the amplifier and returns a flat zero, which reads exactly",
        "* like clipping and is a failed solve.",
        kisim.CONVERGENCE_OPTIONS,
        "",
        "* V803's y1 picks the mode and every analysis below depends on it,",
        "* because y1 is what a pulse holds at the operating point:",
        "*   y1=1  switch ON  -- all-pass -1, elements in phase     -- PIZZ",
        "*   y1=-1 switch OFF -- all-pass +1, elements out of phase -- ARCO",
        "",
        "* CHECK THE STATE BEFORE TRUSTING ANY SWEEP, and check it in the same",
        "* analysis you are about to run. Sweep to 100 Hz and read",
        "* vp(APOUT)-vp(BUFOUT): near 0 deg is arco, near 180 deg is pizz. If",
        "* both states give the same answer the switch is not reaching the",
        "* small-signal solution and every result below is the same circuit",
        "* twice -- which is what Simulation_SPICE:SWITCH does here, silently.",
        "*",
        "* A .op will NOT catch it. With no signal applied the switched node",
        "* sits at 0 V either way, so the operating point looks identical in",
        "* both states and reads as agreement. The state has to be checked",
        "* where the state is used.",
        "",
        "* Results below are what this sheet returned on 2026-08-07, kept",
        "* beside each analysis so a later run that disagrees is visible as a",
        "* disagreement. DESIGN.md carries the same numbers in prose.",
        "",
        "* --- 1. LEVEL JUMP: does flipping the switch change the gain? ------",
        "* design.py: 'the all-pass form keeps gain magnitude and source",
        "* loading identical either way, so flipping it produces no level",
        "* jump.' Plot vdb(APOUT)-vdb(BUFOUT) in each state and subtract.",
        "*",
        "* C02 is in parallel with R06, so the feedback impedance is not a",
        "* resistor and the stage is not an all-pass: it is 1/(1+sT)^2 open",
        f"* and -1/(1+sT) closed, T = {tau * 1e6:.2f} us.",
        "*",
        "* MEASURED, pizz minus arco: -0.032 dB at 20 Hz (that part is R_on,",
        "* analysis 4), -0.028 at 1 kHz, crossing zero near 3 kHz, then +0.078",
        "* at 5 kHz and +1.464 at 20 kHz. So: no audible level jump below a few",
        "* kHz, and 1.5 dB at the top of the band, against 'a fraction of a",
        "* decibel'. The two error terms pull opposite ways and cancel at 3 kHz.",
        "*",
        "* RED: a perfect overlay to 20 kHz. That is what a true all-pass does",
        "* -- i.e. C102 is not actually across R106 on this sheet, and the",
        "* drawing has stopped matching design.py.",
        ".ac dec 50 10 1meg",
        "",
        "* --- 2. POLARITY: is it a flip, and how good a one? -----------------",
        "* Plot vp(APOUT)-vp(BUFOUT) in each state; the claim is 180 deg apart.",
        "* MEASURED separation 180.2 deg at 100 Hz, 181.8 at 1 kHz, 188.8 at",
        "* 5 kHz, 211.7 at 20 kHz. Predicted 181.7 / 188.4 / 210.6 by hand from",
        "* the transfer functions above, so the algebra and the solver agree to",
        "* about a degree and the stage is a clean flip only below ~2 kHz.",
        "* RED: exactly 180.000 at every frequency. That is an ideal inverter,",
        "* not this circuit, and it means the reactive parts are not in play.",
        "*.ac dec 50 10 1meg",
        "",
        "* --- 3. THE CORNER: does 34 kHz survive contact with the circuit? ---",
        f"* R05 x C03 = {corner / 1000:.1f} kHz, quoted in design.py and never checked",
        "* against the built network.",
        "* MEASURED at 33.9 kHz: arco -92.7 deg, which is the -90 of a matched",
        "* two-pole; pizz 133.9 deg, which is the 180-45 of one pole. The",
        "* arithmetic holds AND the two states differ in order, not just sign.",
        "*",
        "* Above ~200 kHz the stage stops attenuating and turns back up,",
        "* reaching +4.5 dB at 1 MHz. That is the amplifier, not the network:",
        "* swapping U102 for an ideal VCVS gives a clean -40 dB/decade all the",
        "* way (-19.8, -38.9, -58.8 dB at 100k, 300k, 1M). An op-amp cannot",
        "* attenuate past its own open-loop gain, and C02 is a passive path",
        "* from APN to APOUT that does not need it. Two decades above audio.",
        "* RED: a single-pole rolloff in BOTH states. Open should be two-pole",
        "* -- one from R05/C03 and one from R06/C02 -- and a single pole there",
        "* means one of the two capacitors is doing nothing.",
        "*.ac dec 100 1k 1meg",
        "",
        "* --- 4. R_on: does the switch perturb the closed state? -------------",
        "* Edit R802's ron (the leading term in its expression) and repeat.",
        "* MEASURED level jump against arco at 1 kHz:",
        "*    0 ohm  +0.009 dB      300 ohm  -0.102 dB",
        "*  100 ohm  -0.028 dB     1000 ohm  -0.360 dB",
        "*                         3000 ohm  -1.101 dB",
        "* Hand prediction was -0.037 / -0.111 / -0.370 relative to the ideal",
        "* switch; measured -0.037 / -0.111 / -0.369. R_on divides against",
        "* R05's 47k and leaks the switched node's ground reference into the",
        "* sum, so it moves the closed state only.",
        "* DESIGN.md says 'well under a tenth of a decibel'. True to ~300 ohms.",
        "* RED: no effect, or an effect that does not scale with ron. An ideal",
        "* short returns that for free, for any circuit at all.",
        "*.ac dec 20 20 20k",
        "",
        "* --- 5. LOW FREQUENCY: the result, not the setup --------------------",
        "* Drive the elements in antiphase, which is vertical string motion:",
        "* set V801 to ac=-1 and leave V802 at ac=1. Then arco should null and",
        "* pizz should sum. Plot vdb(OUT) in each state; the gap is the null.",
        "*",
        f"* The white element sees its own {source.C_ELEMENT * 1e12:.0f} pF into R02's 3M3, a",
        f"* {source.input_corner():.1f} Hz high-pass. The red element sees no bias resistor at",
        "* all. That corner is on ONE path, so the two arrive at OUT with a",
        "* frequency-dependent phase error and the arco null fills in.",
        "*",
        "* MEASURED arco rejection: 1.9 dB at 10 Hz, 9.9 at 40, 15.2 at 73",
        "* (D2, the bottom string), 21.4 at 150, 28.9 at 300, 38.7 at 500,",
        "* 35.0 at 1k, 25.2 at 2k, 16.4 at 5k. A peak, not a plateau: the",
        "* 28 Hz corner eats the bottom and analysis 1's C02 eats the top.",
        "*",
        "* And the finding that was not predicted. C01's 100 pF divides against",
        "* the element's 1700 pF and costs the white path 0.53 dB before the",
        "* buffer, so the two paths balance when C04 = element + C01 = 1800 pF,",
        "* not when C04 = element. Measured null depth at 500 Hz: 29.5 dB with",
        "* C104 at 1n7, 31.1 at 1n72 (RMC's 220p||1n5), 39.0 at 1n8 as built,",
        "* 31.6 at 1n9. Deleting C101 moves the optimum from 1n82 to 1n72 --",
        "* a shift of exactly C01. The built value is right for a reason",
        "* nobody wrote down, and C01 is now part of the balance.",
        "*",
        f"* R801 is an ASSUMPTION ({source.R_LOAD / 1e6:g}M, see source.py). Measured pizz",
        "* response at 73 Hz relative to 1 kHz: -1.89 dB at 1M, -0.50 at 4M7,",
        "* -0.44 at 10M. It is common to both paths, so it moves the bass",
        "* without moving the null. This is the open question for RMC.",
        "*",
        "* RED: a FLAT rejection curve. Replacing the element capacitances with",
        "* shorts was run as a control and returns 0.00 dB rejection at every",
        "* frequency -- the red element's ideal source simply pins OUT and the",
        "* white path becomes invisible, so pizz and arco read identical. A",
        "* clean, plausible, uninformative number for a circuit that need not",
        "* work at all. Exactly the failure docs/simulating.md records.",
        "*.ac dec 50 1 1k",
        "",
        "* --- 6. THE FLIP: is it click-free? ---------------------------------",
        "* V803 steps arco -> pizz at 10 ms. Set V801 and V802 to f=200 and",
        "* watch V(OUT) through the transition.",
        f"* R701 x C701 = {kisim.magnitude(circuit.PARTS['R701'].value) * kisim.magnitude(circuit.PARTS['C701'].value) * 1e3:.0f} ms, but that is the control's own slew, not",
        "* the audible transition: the cell only changes while the control is",
        "* crossing its threshold.",
        "* MEASURED: envelope 10% of the way 1.48 ms after the step, 90% at",
        "* 3.44 ms. Largest step between adjacent 2 us samples 3.97 mV, against",
        "* 2.35 mV for a clean 200 Hz sine of the settled amplitude over the",
        "* same interval -- so nothing in the transition moves faster than",
        "* about twice what the audio itself does. No edge, no spike.",
        "* RED: a step or a spike at OUT, which would mean DC somewhere in the",
        "* switched leg. DESIGN.md says there is none.",
        "*.tran 20u 40m",
    ]
    ox, oy = NOTE_ORIGIN
    for index, line in enumerate(lines):
        column, row = divmod(index, NOTE_ROWS)
        sch.text(line, ox + column * NOTE_COLUMN, oy + row * NOTE_PITCH,
                 size=1.6)


def build(path):
    sch = Schematic(PROJECT,
                    title="RMC pizz/arco switching board -- simulation",
                    rev="D", company="pythagorean-comma",
                    date="2026-08-07", paper="A2")
    for lib_id, (nick, libname, symname, rename) in SIM_LIBS.items():
        sch.use(nick, libname, symname, rename=rename)

    white_element(sch)
    all_pass(sch)
    summing_node(sch)
    control(sch)
    rails(sch)
    directives(sch)

    sch.auto_junctions()
    sch.save(path)
    return sch


if __name__ == "__main__":
    here = pathlib.Path(__file__).parent
    out = here / circuit.PROJECT / f"{PROJECT}.kicad_sch"
    out.parent.mkdir(parents=True, exist_ok=True)
    schematic = build(out)
    model = here / circuit.PROJECT / MODEL_FILE
    print(f"wrote {out} ({len(schematic.parts)} symbols, "
          f"{len(schematic.wires)} wires)")
    if not model.exists():
        print(f"  NOTE: {MODEL_FILE} is not present. Fetch {MODEL_SOURCE},")
        print(f"        unpack it, and put {MODEL_FILE} in {model.parent}/")
        print(f"        It is deliberately not committed -- TI's licence does")
        print(f"        not grant redistribution and this repository is public.")
