"""What this board is actually connected to, at both ends.

Neither end is on the board, and neither is in `design.py` -- which is right,
because `design.py` is a netlist of what gets fabricated. But every number that
matters at low frequency lives out here, so the numbers are named and sourced
rather than left as literals inside `gen_sim.py`.

`summing-mixer/source.py` does the same job at ten times the length, because
its source was a published schematic that could be read part for part. Here
there are three numbers and one of them is an assumption.

**The transducer end.** RMC's pizz/arco saddle holds two PZT elements per
string. A PZT element is a charge source, which at any frequency where the
external impedance is far above its own reactance behaves as a voltage source
in series with its own capacitance. RMC give that capacitance as 1700 pF, and
`design.py` matches `C04` to it deliberately -- see DESIGN.md, "The summing
capacitor matches the element".

Modelling it as an ideal voltage source instead is not a simplification, it is
a different circuit: `R02`'s 3M3 would then load nothing, the 28 Hz input
corner would disappear, and every low-frequency result would come back flat and
plausible and meaningless. That failure has a precedent on the sibling project;
`docs/simulating.md` records it.

**The preamp end.** Nothing on this board loads `OUT`. DESIGN.md is explicit
that this is deliberate -- the board's output is meant to look like a piezo,
and the Poly-Drive II supplies the load. The consequence for simulation is that
the red element's node has no DC path to ground at all, and SPICE cannot solve
a circuit like that.

So a value has to be chosen, and RMC have never stated one.
"""

# -- the element ------------------------------------------------------------
# RMC's figure for one element of the pizz/arco saddle. The same 1700 pF
# design.py's C04 comment is matched against, and the same one DESIGN.md uses
# to compute the 28 Hz input corner.
C_ELEMENT = 1700e-12

# -- what OUT works into ----------------------------------------------------
# ASSUMED. Not stated by RMC, not derivable from anything in this repository,
# and it dominates a corner that DESIGN.md credits to R02's 3M3:
#
#     f = 1 / (2*pi * R_LOAD * (C_ELEMENT + C04 + C_STRAY))
#
# which at 1 M comes to about 45 Hz -- above the bottom string of a bass viol,
# and nearly twice the 28 Hz the white element's own corner sits at. At 10 M it
# is 4.5 Hz and irrelevant. That is a factor-of-ten swing in a figure that
# decides how the instrument sounds, resting on a number nobody has given us.
#
# 1 M is the conservative end of the range a piezo preamp input plausibly
# presents. gen_sim.py sweeps it; DESIGN.md carries it as an open question for
# RMC.
#
# The one piece of good news is structural: this impedance is common to both
# element paths at OUT, so it sets the absolute low-frequency corner without
# affecting the balance between red and white. The pizz/arco result does not
# depend on getting it right; the bass response does.
R_LOAD = 1.0e6
R_LOAD_SWEEP = (1.0e6, 4.7e6, 10.0e6)

# The DIN connector, the loom to the Poly-Drive II and the summing node's own
# copper. Small against 3520 pF of element and C04, and common to both paths
# for the same reason R_LOAD is, so nothing here turns on it. Present because
# leaving it out states a different, equally unmeasured number: zero.
C_STRAY = 20e-12


def input_corner(r_bias=3.3e6):
    """The white element's own high-pass, into R02.

    The corner DESIGN.md quotes at 28 Hz, computed rather than transcribed.
    """
    import math
    return 1.0 / (2 * math.pi * r_bias * C_ELEMENT)


def output_corner(c_sum=1.8e-9, r_load=R_LOAD):
    """The high-pass both paths share at OUT, set by the preamp's input.

    Common to red and white, so it moves the whole response together and
    cancels out of the pizz/arco balance.
    """
    import math
    return 1.0 / (2 * math.pi * r_load * (C_ELEMENT + c_sum + C_STRAY))


if __name__ == "__main__":
    print(f"element             {C_ELEMENT * 1e12:.0f} pF")
    print(f"white input corner  {input_corner():.1f} Hz  (R02 3M3)")
    for r in R_LOAD_SWEEP:
        print(f"OUT corner          {output_corner(r_load=r):5.1f} Hz  "
              f"(R_LOAD {r / 1e6:g}M)")
