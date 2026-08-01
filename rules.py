"""Fabrication rules, in one place because two generators need them.

`gen_pcb.py` lays copper against these and `gen_project.py` writes them into
the .kicad_pro for DRC to enforce. They used to be declared separately in both,
which meant a rule could be widened in the layout and not in the checker -- the
one kind of drift where the build still passes and the board is still wrong.

The numbers come from RMC's layout review of 2026-08-01. Their argument is not
about current or crosstalk, it is about yield: a fabricator's cumulative drill
and layer-registration error runs to about +/-0.003", and a layout that has not
budgeted for it is relying on the contractor being better than they promised.

    0.003" = 0.0762mm

An annular ring smaller than that misregistration is a broken via. Ours:

    ring = (VIA_DIAMETER - VIA_DRILL) / 2 = 0.200mm
    worst case after full misregistration = 0.200 - 0.076 = 0.124mm

against an IPC-2221 Class 2 minimum external annular ring of 0.05mm, so the
board tolerates the full error with 2.5x the standard's margin left. The
previous 0.6/0.3 via gave a 0.15mm ring and 0.074mm remaining -- passing, but
on the fabricator's good behaviour rather than on our own arithmetic.

The drill went up with the pad rather than staying at 0.3mm. RMC: "double vias
and larger holes are low-cost insurance against plating problems". A 0.4mm hole
through 1.6mm of board is a 4:1 aspect ratio against 5.3:1, and plating
throwing power falls off with depth, not diameter.

CLEARANCE is 0.25mm where RMC asked for 0.010" = 0.254mm. Four microns short,
kept because the whole layout is on a metric grid and 1.6% is not worth an
awkward number. Declared to them rather than quietly rounded.
"""

# Cumulative drill and registration error to design against, per RMC.
REGISTRATION = 0.0762     # 0.003 inch

TRACK = 0.30              # signal
POWER_TRACK = 0.80        # V+, V-, AGND -- RMC: "beef up your Vcc, Vdd & Vss"
VIA_DIAMETER = 0.80
VIA_DRILL = 0.40
CLEARANCE = 0.25

# How far a doubled power via sits from its partner, centre to centre. Two
# vias touching are one via with a worse hole; this is the pad plus a
# clearance, so a plating failure in one leaves the other intact -- which is
# the entire point of doubling them.
VIA_PAIR_PITCH = VIA_DIAMETER + CLEARANCE

ANNULAR_RING = (VIA_DIAMETER - VIA_DRILL) / 2
assert ANNULAR_RING - REGISTRATION > 0.05, (
    f"annular ring {ANNULAR_RING}mm does not survive {REGISTRATION}mm of "
    f"misregistration with IPC Class 2 margin -- see the module docstring")

# DRC constraint floors. These sit just *below* the geometry above rather than
# at it: they are the check that catches a rule being widened in one generator
# and not the other, so they must not be so tight that legitimate geometry
# trips them, nor so loose that they would pass the old board.
MIN_TRACK_WIDTH = 0.25
MIN_CLEARANCE = 0.20
MIN_VIA_DIAMETER = 0.70
MIN_VIA_ANNULAR_WIDTH = 0.18
MIN_THROUGH_HOLE_DIAMETER = 0.35
MIN_HOLE_CLEARANCE = 0.25
MIN_HOLE_TO_HOLE = 0.25
MIN_COPPER_EDGE_CLEARANCE = 0.50

# Board edge to the zone boundary. Matches MIN_COPPER_EDGE_CLEARANCE so the
# pours cannot be the thing that violates it.
ZONE_INSET = MIN_COPPER_EDGE_CLEARANCE

assert MIN_TRACK_WIDTH <= TRACK
assert MIN_CLEARANCE <= CLEARANCE
assert MIN_VIA_DIAMETER <= VIA_DIAMETER
assert MIN_THROUGH_HOLE_DIAMETER <= VIA_DRILL
assert MIN_VIA_ANNULAR_WIDTH <= ANNULAR_RING
