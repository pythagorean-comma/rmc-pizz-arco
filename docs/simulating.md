# Simulating these boards

Notes that apply to any of the three repositories. The mechanics are in
`kisim.py`, which copies between them unchanged; this is the part that is not
code.

## There is nothing to install

KiCad ships ngspice. `./build.sh` writes a simulation schematic alongside the
fabrication one; open it in the schematic editor and use **Inspect → Simulator**.

The simulation sheet is generated from the same `design.py` as the fabrication
sheet, so it cannot drift from the circuit. It differs only where it has to:
connectors become sources, a supply section becomes ideal rails at the voltages
the design predicts, and anything the analysis depends on that the board takes
for granted — stray capacitance, source impedance — is modelled explicitly.

## The four ways it lies to you

Every one of these returns numbers. None of them errors. Three were hit on
`summing-mixer` and the fourth on `rmc-pizz-arco`; two are now impossible.

### Ground must be node 0

SPICE has exactly one ground and it is node `0`. A `power:GNDA` symbol yields a
net named `AGND`, and nothing ties that to `0` — so the whole circuit floats.
It simulates happily and answers a different question. The symptom was an output
58 dB down that should have been unity.

`kisim.ground()` returns `Simulation_SPICE:0`. Use nothing else on a simulation
sheet.

### Two net names at one coordinate is one net

A global label and a power symbol are both a name attached to a point. Land them
together — by a placement slip, or because a row pitch happens to equal a drop
length — and KiCad merges the nets without a word. The sheet opens, ERC is
clean, the netlist is well-formed, and it is a different circuit.

On `summing-mixer` the bleed resistors dropped to ground exactly one channel
pitch below their row, putting each ground on the *next* channel's input label.
The entire ground net became `IN2`, and a resistor appeared in the netlist as
`R290 IN2 IN2` — shorted end to end. Nothing on the drawing showed it.

**`kisch.auto_junctions()` now refuses to emit any sheet where two different net
names share a coordinate.** That is why the check exists.

### A switch that is open in AC whichever way it is thrown

`Simulation_SPICE:SWITCH` is the obvious part for a analog switch and it is
wrong. ngspice's `SW` device **always contributes `roff` in AC analysis**,
whatever its control voltage is doing. Its DC operating point is right — on
`rmc-pizz-arco` the switched node sat at 0 V with the cell on and followed the
buffer with it off — so nothing looks amiss, and then every AC sweep returns
the switch-open circuit for both switch positions.

The symptom is a *perfect* result. The two states came out identical to four
decimal places at every frequency, which reads as a triumphant confirmation of
"flipping the switch produces no level jump" and is the same answer the run
would have given for a circuit with no switch in it at all. Sweeping `ron`
changed nothing; sweeping `roff` changed both states together. That pair of
observations is the diagnosis.

The fix is to model the switch as what it electrically is, a resistance
controlled by a voltage. ngspice linearises a behavioural resistor about its
operating point, so its AC conductance is the one the DC solution chose:

```
R802 SWN 0 R='100+1e8/(1+exp(V(SW_CTL)/0.15))'
```

KiCad's netlister passes an ideal resistor's value through unchanged, so
writing ngspice's own syntax into the `r` parameter is what gets that line out
the other side. Check the exported netlist rather than assuming it.

And the guard, which is cheap but has to be the right one: **read the switch's
effect out of the same analysis you are about to trust.** On `rmc-pizz-arco`
that is the phase of the switched stage at 100 Hz — near 0° open, near 180°
closed. An `.op` does *not* catch it: with no signal applied the switched node
sits at 0 V either way, so the operating point looks identical in both states
and reads as agreement. The first version of the guard was an `.op`, and it was
useless for exactly the reason the bug existed.

### A test that cannot fail is not evidence

The one worth internalising, because no tool will catch it.

An isolation analysis on `summing-mixer` put each channel's source directly on
its input node. An ideal voltage source has no output impedance, so it pins its
node to its own value whatever the circuit does. The undriven channels read
exactly zero — not because the summing node is a virtual earth, but because an
ideal source cannot be disturbed. **It would have returned the same answer for a
circuit that did not work at all**, and it was reported as a success.

With the real source modelled — the capsule's own coupling capacitor and bleed
resistor, from `source.py` — the result became frequency-dependent and matched
the analytical prediction to a decibel.

Before trusting a green result, ask what red would have looked like. If you
cannot say, the test is not testing.

## Vendor models

Manufacturers publish PSpice models. TI's are at `ti.com/lit/zip/<sbom-number>`,
linked from the product page.

**Not for everything, and the gap is not advertised.** TI have a model for the
OPA4191 (`sbomA30`) and none at all for the CD4066B — not on the product page,
not under tools and software, not anywhere; what circulates is community
rebuilds from CD4007 gates. Check before planning an analysis around a model,
because "TI publish PSpice models" is true in general and false in particular.
Where there is no model, the honest substitute for a datasheet curve is a
**sweep**: on `rmc-pizz-arco` the switch's on-resistance is swept across an
order of magnitude rather than quoted at one value, which answers the question
that was actually being asked (how sensitive is this to R<sub>on</sub>) instead
of a question the model could not have answered anyway.

**Do not commit them.** The licence grants use, not redistribution, and these
repositories are public. Fetch the zip, unpack the `.LIB` beside the schematic
that uses it, and add it to `.gitignore`. `gen_sim.py` should generate the sheet
whether or not the file is present — a missing model is KiCad's error to report
at simulation time, not a reason for the build to fail over something it cannot
legally ship.

**A dual or quad symbol cannot carry a single-amplifier model.** Vendor
subcircuits are one amplifier. Borrow a single-amp body and rename it, the way
`design.LIBS` already borrows symbols for the fabrication schematic —
`summing-mixer` uses `LM321` renamed to `OPA1612_SIM` for exactly this.

**Large-signal runs need `kisim.CONVERGENCE_OPTIONS`.** Driven hard into a rail,
a macromodel stalls: ngspice reports "Timestep too small" from inside the
amplifier and returns a flat `0.000 V`. That reads exactly like clipping and is
a failed solve. Gear integration and relaxed tolerances get through it —
measured on `summing-mixer`, an overdrive case returned 0.000 V without them and
−8.337 V with.

## If you drive ngspice directly

Only needed for scripting; the GUI handles all of this. The library is inside
KiCad — `PlugIns/sim/libngspice.dylib` on macOS — and is drivable from stdlib
`ctypes`.

- **Load the `.cm` code models explicitly.** Without `spinit`, ngspice loads
  none, and every XSPICE `a` device in a vendor macromodel fails with
  `MIF-ERROR - unable to find definition of model`. This looks exactly like an
  incompatible model and is not. `codemodel <dir>/analog.cm`, and likewise
  `xtradev`, `xtraevt`, `spice2poly`.
- **`set ngbehavior=psa`** for PSpice-dialect models.
- **Exported netlists end with `.end`.** Directives appended after it are
  silently ignored — strip it first.
- **`kicad-cli` does not expand `${KIPRJMOD}`**, because it does not load the
  project file. Use bare filenames for model libraries and run the export from
  the project directory.

## What is worth simulating

Not everything. On `summing-mixer` the noise model was already correct and
analytically checkable, and simulation only confirmed it. The analyses that
earned their place were the ones checking a claim that could have been wrong:

- a **headroom** prediction, which turned arithmetic into evidence
- a **stability** margin, which turned an argument into a test
- the **central claim of the topology**, whatever that is for the board in hand

Pick the assertions in `DESIGN.md` that are falsifiable and check those.
