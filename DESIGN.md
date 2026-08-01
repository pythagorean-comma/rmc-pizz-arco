# RMC pizz/arco switching board design

Six channels of RMC's pizz/arco switching circuit
([`docs/Pizz-Arco-Switching-260729.png`](docs/Pizz-Arco-Switching-260729.png),
2026-07-29, one channel drawn), one for each saddle of a viola da gamba bridge,
plus the supply distribution and switching that drawing leaves open. Why that
circuit needs to exist is best said by RMC themselves.

## The pickup, in RMC's words

> Bowed instruments like Cello and Upright Bass are bowed in 2
> directions and plucked in one main direction. Violin is the
> same, but the direction of plucking is opposite because the
> instrument soundbox is placed on the shoulder instead of being
> resting on an end-pin contacting the floor.
>
> In the current Pizz-Arco saddle, the piezo elements are
> out of phase and connected together by a resistor which
> progressively de-phases the two signals and provides
> a quasi-omniplanar response with some polar/directivity
> limitations. See US Patent 5,206,449 for more details.
>
> The Pizz-Arco pickup saddle is quasi omniplanar and will
> reproduce string vibrations in any plane of vibration.
> However it is blind to one direction of string rotation.
>
> Since a picked/plucked string starts vibrating in a rotary/
> elliptical manner upon release from under the exciting finger/
> nail/pick, the attack of the note will be thick for one direction
> of picking/plucking and thin for the opposite direction.
>
> This type of polar/directional response is ideally suited for
> bowed instruments which aren't picked alternatively up & down
> like a guitar.
>
> ............
>
> Eliminating this rotation-specific sensitivity characteristic
> to obtain omniplanar response AND attack tone symmetry for
> picking purposes cannot be performed by a static electronic
> circuit.
>
> The signal from each piezo element of each saddle must be
> managed dynamically by smart polyphonic circuitry which
> detects the phase relationship between the vertical and
> horizontal components of string vibration for each pickup
> saddle and optimizes the phase relationship between the
> piezo elements for best effect in real time in the joint
> signal.
>
> Alternatively, one can use a pizz/arco switch to connect
> the piezo elements in-phase (for a vertical direction of
> maximum sensitivity) or out-of-phase (for a horizontal
> direction of maximum sensitivity) depending on the desired
> response for the musical passage of interest. This requires
> active circuitry, but smart dynamic action is not required.

## What follows from it

**This board is the alternative.** Not the smart dynamic option: the switch.
Active circuitry, no real-time detection of anything, one toggle for the whole
instrument.

**The two elements come out of each saddle separately here.** In the saddle as
sold they are joined by the de-phasing resistor described above, which fixes the
polar response at one compromise. This build brings both elements out on their
own wires (J1–J6 carry three each: shield, white and red), because independent
access to the two signals is precisely what is needed to switch their relative
phase. RMC's drawing shows them accordingly, as two independent sources with no
combining resistor between them.

**That is what gives the switch its meaning.** Each channel sums one saddle's two
elements into a single high-impedance output that behaves like a piezo, which is
what the Poly-Drive II expects to see. In phase is the vertical direction of
maximum sensitivity: **pizz**. Out of phase is the horizontal: **arco**.

## Status

The board is generated from source rather than drawn. `design.py` is the single
source of truth; `gen_sch.py` draws the schematic from it, `gen_pcb.py` places
and routes the board from it, and `verify.py` reads KiCad's netlist back and
compares it net by net. See [`README.md`](README.md) for the toolchain and its
requirements.

Placed, routed and DRC-clean at 78.8 × 81.3 mm: 53 nets, 233 pin connections,
80 placements, 0 violations, 0 unconnected items. Nothing has been fabricated.
The design is with RMC for review; three questions are awaiting reply, listed
under [Open with RMC](#open-with-rmc).

---

## The circuit

### Per channel, ×6

- **PZT 1 (red)** goes straight to `OUT`, unbuffered. It never passes through an
  op-amp.
- **PZT 2 (white)** is loaded by R02 3M3 to ground, filtered by R03 1k/C01 100p
  (corner ≈1.6 MHz), buffered at unity gain, passed through a first-order
  all-pass, and summed into `OUT` through a single **1.8 nF**.

R01, a 1 kΩ stopper, sits in front of the buffer input. It is doing two jobs;
see [Headroom](#headroom).

**The summing capacitor matches the element, deliberately.** RMC give the
element's own capacitance as **1700 pF**, and the red element works into C04
directly, so equal capacitance means equal weighting at the summing node:

```
OUT = (V_red · C_red + V_white · C04) / (C_red + C04 + C_stray)
```

That is why the six must match *each other*: it is string balance, not
tolerance fussiness. Against R02's 3M3, 1700 pF puts the input corner at
**28 Hz**, well below the bottom string of a gamba (D2, 73 Hz).

**The all-pass is a polarity flip, not a phase shift.** Its RC corner is
1/(2π·47k·100p) ≈ **34 kHz**, well above the audio band, so in band the stage is
+1 with the switch open and −1 with it closed (the switch grounds the
non-inverting input). PZT 2 then sums with PZT 1 either in phase or in
anti-phase, and that is the pizz/arco character change. The all-pass form rather
than a plain switched inverter is what keeps gain magnitude and source loading
identical in both positions, so flipping the switch produces no level jump.

The 100 pF capacitors are doing HF stability and RF rejection duty only. RMC:
*"the 100pF capacitors have no audible effect."*

**Nothing in RMC's circuit needed changing.** It is on the board part for part.

### What was added

The drawing shows one channel and leaves the supply and switching open. Two
things were added:

- **Switching.** The drawing shows one switch per channel. Bussing six channels
  to a single mechanical SPST would short them all together when open, so each
  channel gets its own contact: **six CD4066B cells across two packages**, U4 and
  U5, driven from one control line. On-resistance ~100 Ω against 47 k is −54 dB,
  and the switched node carries no DC, so there is no click; R701/C701 slow the
  transition to about 10 ms. Each package sits beside the three channels it
  serves, and the spare cell in each is parked with its signal pins on AGND and
  its control on V−, so nothing floats.

  The control network is RMC's: **R701 1 MΩ to Vss, R702 20 kΩ in series to Vdd
  through the toggle, C701 10 nF to ground.**

- **Decoupling.** Four 4.7 µF/25 V capacitors: a V+→AGND and a V−→AGND pair at
  each end of the rails (C901–C904), exactly as RMC specified. This replaced
  eighteen local capacitors an earlier revision carried; the In1/In2 plane pair
  already supplies the local V+-to-AGND decoupling those were doing. This is the
  one item taken on RMC's authority rather than our own analysis, and it is
  question 1 under [Open with RMC](#open-with-rmc).

### What is not on the board

No battery, no power section, no regulator, no charge pump, no mid-rail buffer,
no fuse, no series Schottky, no TVS, no protection of any kind. The supply
arrives ready-made from the Poly-Drive II.

Losing the mid-rail buffer in particular is what makes the grounding rule below
free rather than expensive; it was the one real source of DC in the ground
return.

---

## Supply, grounding and polarity

> **This board has no supply of its own.** It is powered entirely by the
> Poly-Drive II, over the same DIN-8 that carries the audio.

**±4.5 V arrives on DIN pins 7 and 8, with the shell as ground.** RMC settled
this over three rounds and recommend it explicitly: *"power management performed
only in the Poly-Drive II preamp and keeping the instrument electronics slaved
to the preamp."*

| | |
| --- | --- |
| **Pin 7** | **+4.5 V** |
| **Pin 8** | **−4.5 V** |
| Shell / shield | ground, both audio and DC |
| Source | a 1350 mAh USB-rechargeable 9 V in the PD2, through a transistor rail splitter |
| Our draw | **~2 mA**, of an under-6 mA total shared with the PD2's own 3.5 mA |

RMC's ~2 mA figure and the 1.7 mA computed here from the part count (12 op-amp
halves × 140 µA) agree, which is a useful independent check.

**Pins 7 and 8 are spare preamp inputs as the PD2 ships**, and have to be
disconnected from the preamp before they can carry power. **RMC do that
themselves when they assemble our unit.** It is not an aftermarket job on
someone else's hardware, and there is nothing for us to open.

`JP1` from the earlier revision **is deleted, not merely left unfitted.** It tied
DIN pin 8 to ground, and pin 8 is now a supply rail.

### Polarity: the fault that destroys the board

**There is deliberately no reverse-protection diode.** A series Schottky per rail
would cost about 0.6 V of a 9 V total supply, roughly 0.6 dB of headroom this
design does not have to spare. A loom built backwards therefore puts 9 V
backwards across every op-amp and destroys the board.

The mitigation is procedural, not electrical:

> **Pin 7 = +4.5 V, pin 8 = −4.5 V.** Printed on the silkscreen, repeated here,
> in [`ENCLOSURE.md`](ENCLOSURE.md) and in [`fab/ORDER.md`](fab/ORDER.md).
> **Continuity-check the loom from the DIN plug to J7 before first power-up.**

The polarity is ours to define. RMC called their own pin 7 = + *"arbitrary…
just my knee-jerk response"*, so the board sets the convention and the loom
follows it. Confirmation is still outstanding; see
[Open with RMC](#open-with-rmc).

### Grounding

> **Ground is the DIN shell, and there is nothing else.** No mid-rail, no
> battery negative, no second ground. RMC: *"Shell/Shield is Ground - no need
> for multiple Grounds here."*

What follows from that is a design rule, and it must not be broken later:

> **No DC path from either rail to AGND anywhere on the board.**

The reason is structural. The PD2's ground is the midpoint of a transistor rail
splitter, and it reaches this board down the DIN shell, the same single
conductor that carries all six string returns. Any DC imbalance flows in that one
conductor, straight through the audio return path. RMC put it as *"the current
flowing in the Ground terminal is only related to the Audio signals"*, and asked
that the drain on the two rails be symmetrical.

Audited against what is built, the rule holds. Total DC into ground is leakage
only:

| Connection to AGND | DC it carries |
| --- | --- |
| J1–J6 pin 1, six saddle shields | audio return only |
| R02 3M3 ×6, piezo bias | op-amp bias current, ~20 pA |
| C01, C02, C03 100p ×18; C701 10 n debounce | none (capacitive) |
| CD4066 cell, grounded side ×6 | audio only, and only when ON |
| C901–C904, 4 × 4.7 µF rail bypass | leakage only |

Everything else runs rail-to-rail with no ground reference. The OPA4191s draw
V+ to V− through the die, and **the CD4066 has no ground pin at all**: pin 7 is
Vss = −4.5 V, pin 14 is Vdd = +4.5 V. The control network runs V+ → 20 kΩ →
SW_CTL → 1 MΩ → V−, about 9 µA, with no ground leg.

**What this forbids, if the board is ever modified:** no power LED, no
rail-to-ground divider, no single-ended pull-up, no asymmetric bypass. All four
look harmless and all four put DC in the audio return.

The toggle on J8 carries DC only, so its wiring is uncritical; just keep its
terminals clear of anything grounded.

### The CD4066 supply ceiling

RMC add: *"power to the CD4066 quad switch should not exceed ±9VDC (18 volts
total)."* The switches take Vdd and Vss straight from the rails, so they see
**9 V total against an 18 V ceiling, half the limit.** The largest signal is
about ±4.35 V, inside the rails. Nothing here approaches it, and ±9 V is the top
of any supply this board could ever be given.

---

## Headroom

The rails allow about **±4.35 V** of swing. There is no gain anywhere on the
board (the buffer is unity and the all-pass is ±1), so the requirement is
simply the white element's own peak output into the 3M3.

**RMC's answer (2026-08-01) is that this is fine, and that clipping on hard
pizzicato is acceptable when it happens.** There is no single peak figure to
quote, because output depends on excitation, string tension and break angle:

- **Arco cannot clip.** A bowed attack is *"a short noisy fade-in without any
  large initial percussive transient"*, and out of phase the two elements cancel
  vertical force variations at the summing node.
- **Pizz can, and it is inaudible.** In phase, vertical sensitivity is at its
  maximum and a picking transient may saturate the buffer. But the red element
  bypasses the electronics entirely and dominates for those milliseconds, so what
  results is *"an extremely short change in polar pattern, not an audible click
  or buzz"*.

**This rests on the amplifier not latching up, which was checked rather than
assumed.** OPA191/2191/4191 datasheet SBOS701D §8.3.3: the family has internal
phase-reversal protection, and input signals beyond the rails do not cause phase
reversal; the output simply limits into the appropriate rail.

One consequence worth knowing when servicing: the datasheet's absolute maximum on
an input pin is only 0.5 V beyond the rail, with a ±10 mA input current limit.
**R01, the 1 kΩ stopper in each channel, is what keeps the input clamps inside
that rating:** even 5 V of overdrive draws 5 mA, half the limit. It was placed
as a stopper and it is also what makes accepting clipping safe. **Do not reduce
it.**

**What would falsify this**, recorded because "settled" means settled on RMC's
judgement plus one datasheet paragraph, not measured on this instrument: audible
artefacts on hard pizzicato, meaning a click, a buzz, or a change in timbre that
comes and goes with playing strength rather than smoothly with it; or anything
worse than a momentary change in polar pattern.

**If it is falsified, the fix needs no respin.** RMC's mitigation is component
values only: a capacitor in parallel with R02 (3M3) divides against the element's
own 1700 pF and attenuates the white signal into the buffer, and increasing C04
loads the red element correspondingly to restore the balance.

---

## Requirements that no file carries

These are electrical requirements invisible in the gerbers, the netlist and the
BOM. An assembler substituting on footprint and nominal value alone gets all four
wrong. [`fab/ORDER.md`](fab/ORDER.md) holds the copy that travels with the
fabrication package, in full.

| Parts | Requirement |
| --- | --- |
| **C104…C604**, six 1.8 nF | **C0G/NP0, ±2%, 50 V, all six ordered as ONE line item from a single reel.** What matters is that the six match each other, not that each matches 1.8 nF: a ±5% part permits a 10% spread between two channels, which is looser than the balance the matching exists to protect. Parts from one reel and date code track far tighter than the tolerance band. |
| **Every capacitor ≤10 nF** (the 18 × 100 pF, the six 1.8 nF, C701) | **C0G/NP0. Not optional, not substitutable with X7R**, which drifts with temperature and signal voltage at these values. |
| **The 18 × 47 k** | **±1%.** They set the all-pass inverter's gain at exactly −1. RMC specified this explicitly. |
| **U1–U3** | **OPA4191**, by that part number. The project library carries the symbol under a borrowed body (`OPA4197xD`, renamed) as a drawing convenience only. |

Everything else (the 1 M, 20 k, 3M3, 1 k and 4.7 µF) is standard tolerance.

---

## The board as built

- **78.8 × 81.3 mm, 4 layers.** 80 placements: 72 SMD (1206 passives, SOIC-14
  and SO-14) and 8 through-hole 2.54 mm pin headers.
- **Stackup:** F.Cu signals · In1.Cu solid AGND plane · In2.Cu solid V+ plane ·
  B.Cu signals. Four layers rather than two is what keeps this tractable: every
  supply and ground pad reaches its rail through a single via, and the
  high-impedance piezo traces run over unbroken ground.
- **V− is not a plane.** At about 2 mA it never needed one, and a B.Cu pour was
  this project's worst failure mode: fragmenting it produced unconnected items
  in parts of the board nowhere near the cause. It is routed like any other net,
  and B.Cu is a second signal layer.
- **Three blocks** down the left, each one OPA4191 quad serving two channels,
  with the two channels mirrored above and below it. Each has its own 3-pin
  pickup header. Then a corridor for the six outputs and six switched nodes, the
  two switch packages and the control network, and the tail connectors laid flat
  along the bottom.

**Quad assignment: buffers on A and B, all-passes on C and D.** Both buffer
inputs are then pins 3 and 5, on the same side as the connectors, and only the
buffer *outputs* cross to the right-hand half, low-impedance nodes that can run
anywhere. The obvious alternative (one channel per half) puts channel 2's buffer
input on pin 10, dragging a 3M3 high-impedance node across the whole footprint
and forcing the six pickup connectors onto both edges of the board. SOIC-14 was
chosen over TSSOP-14 to keep the 1.27 mm pitch, so an AGND guard ring still fits
around each buffer's + input.

**1206 passives throughout, not 0805.** This is RMC's advice, *"whenever you
need to pass 2 lines side-by-side between a component's terminals, you can use a
1206 size component and that way you can eliminate a lot of vias"*, applied
uniformly. Measured clear gap between pads: 0402 ~0.5 mm (no track fits), 0805
0.80–0.90 mm (one), **1206 ~1.80 mm (two)**. At 0.65 mm lane pitch that is one
lane against two, and on this board a 1206's own pad gap is where most of the
routing crosses from one side of a channel to the other. Going bigger bought
more than going smaller ever did.

**The board is not dense, and that is the point.** Land utilisation is about
14%, lower than either previous revision (the original 88 × 112 mm board was
17%). What sets the size is not area for parts but room for lanes: each channel
must get five nets past its own op-amp, each needing ~0.65 mm of width and
clearance, and tile pitches of 9.5 mm and 10 mm were both tried and both failed.
12 mm is what the routing demanded. The right-hand column sits 2 mm further out
than the parts need and the tail connector 0.5 mm lower than it has to, both
spent on measured crossings. **A smaller number from an unroutable placement is
not a smaller board.**

---

## Installing and wiring it

Every pin number below comes from `design.py`, which is the source of truth;
`verify.py` checks the schematic still agrees with it on each build.

```
6 saddles -- each RMC pizz/arco holds TWO piezo elements
  red --+   white --+   shield --+       3 wires per saddle, 18 in total
        v           v            v
   J1..J6:       pin 3        pin 2     pin 1
        |
        +-- red -------------------------------------+   never sees an op-amp
        |                                             |
        +-- white -> 3M3 bias -> 1k/100p -> buffer -> +-1 --+ via 1.8 nF
                                     (polarity from J8)     v
                                                        OUT (1 of 6)

   6 x OUT + ground + the two supply rails, all on the same connector
        v
   J7, 9-way --> instrument DIN-8 socket --> RMC cable --> Poly-Drive II
```

Two things follow that are easy to get wrong:

- **The red element never passes through the electronics.** It runs straight from
  the saddle to the DIN. Only the white one is buffered and polarity-switched,
  then summed back into the red through 1.8 nF.
- **The board applies no gain, and its output is still piezo-like:** high
  impedance, with no load resistor on board. That is deliberate: it is what the
  Poly-Drive II expects to see, and the Poly-Drive supplies the load. The board
  exists to do the two-element mix, which the Poly-Drive cannot, because it has
  only one input per string.

### Connectors

| | Pin 1 | Pin 2 | Pin 3 | |
| --- | --- | --- | --- | --- |
| **J1–J6** saddle 1–6 | shield | white | red | |
| **J7** to DIN-8 | pins 1–6 = channels 1–6 | 7 = **+4.5 V**, 8 = **−4.5 V** | 9 = shell / ground | check polarity before power-up |
| **J8** pizz/arco toggle | switch | control | | DC only, no audio |

**J7 has nine pins for an eight-pin DIN.** Pins 1–8 are the DIN's own pins and
pin 9 is the shell, which is the ground connection.

### The switch

Switch **closed** grounds the all-pass and inverts the white element relative to
the red. The elements are out of phase on the transducer plate, so that brings
them electrically *into* phase: the vertical direction of maximum sensitivity,
which is pizz. See [What follows from it](#what-follows-from-it).

| Toggle | Control line | CD4066 | All-pass | Elements | Mode |
| --- | --- | --- | --- | --- | --- |
| closed | +4.5 V via 20 kΩ | ON | −1 | in phase | **PIZZ** (picking) |
| open | −4.5 V via 1 MΩ | OFF | +1 | out of phase | **ARCO** (bowing) |

> **The rest state is ARCO.** The control line is pulled to the negative rail
> through 1 MΩ, so that is what the instrument does with the toggle
> disconnected, the loom broken, or the switch not yet wired. If a newly built
> instrument sounds like it is permanently in arco, suspect the toggle wiring
> before suspecting the board.

### Power, in practice

**There is nothing to switch off here.** The board is live exactly when the
Poly-Drive II is live, and goes away with it. Whatever power switching the PD2
has is the power switching this instrument has.

**If the PD2's battery goes flat, everything stops, including the passive path.**
This is a change from the previous revision, where the red element reached the
DIN through copper alone and survived a dead battery. The battery now lives in
the preamp the whole instrument feeds; if it is flat there is no output at all,
from either element, whatever this board is doing.

**There is no low-battery warning, and there cannot be one.** RMC specify a
regulated USB-rechargeable pack, which holds 9 V for its whole life and then
falls off a cliff, so a preamp watching battery voltage has nothing to watch.
Their answer is a habit rather than a circuit: **charge it once a week.** At
about 70 hours of playing per charge that covers a week comfortably, and charging
takes under an hour. This is worth telling whoever plays the instrument; it is
the one maintenance task the design has, and the one failure mode with no
warning.

### A footswitch is free; moving the board out is not

J8 carries DC control only (the CD4066 keeps the toggle out of the signal path
entirely), so the pizz/arco switch can sit on an arbitrarily long two-conductor
cable in a footswitch box with no audio penalty at all, and it will be
click-free. If hands-free switching is what is wanted, that is the whole answer.

Housing the *board* outside the instrument was considered and not taken:

- **Conductor count is the blocker.** The instrument currently sends six signals
  plus ground, which is exactly what the 8-pin DIN carries, and that only works
  because the combining happens at the bridge. Outboard, the raw elements have
  to travel: 2 × 6 = **12**, plus ground.
- **It relocates the highest-impedance node in the design.** The white element's
  3M3 load and its buffer would move to the far end of that cable, where cable
  capacitance divides against the element's 1700 pF and twelve high-impedance
  lines in one multicore risk exactly the crosstalk a hex system exists to
  avoid. Roland GK cables work because the GK pickup buffers *at the instrument*.
- **Powering it is now the hard part.** The rails arrive from the PD2 over the
  DIN, so an outboard box would either carry them down a cable already full of
  high-impedance element signals, or generate its own: the local power
  management RMC have twice recommended against.

[`ENCLOSURE.md`](ENCLOSURE.md) covers the tail-mounted housing inside the
instrument, which is where this board actually goes.

---

## Decisions, and their reasons

Ours rather than RMC's, each stated so that disagreeing with one is cheap:

- **Two CD4066 packages, not three.** An earlier revision used three, restricted
  to the A and B cells, on the theory that keeping signal and control apart
  mattered. RMC pointed out this is wrong: one side of every cell is grounded and
  the control lines are all paralleled, so there is very little to route around
  the package.
- **R702 on the rail side of the toggle.** RMC said the switch shorts the control
  lines to Vdd through a low-value series resistor. Putting R702 on the **rail**
  side rather than the switch side means a pinch anywhere in the toggle cable
  draws about 450 µA instead of shorting V+, and that cable leaves the board.
  Closed, the divider holds the control within 0.2 V of V+ and draws about 9 µA.
  This is the one place a sentence of RMC's was reinterpreted rather than
  followed, and it is flagged to them as such.
- **A single 1n8 rather than 220 p ‖ 1.5 n.** The pair was approximating
  1700 pF; one capacitor does it with one part and no interleaving problem.
  Specified ±2% where RMC accepted ±5%, because ±5% permits a 10% spread between
  two channels.
- **Four bypass capacitors, not eighteen.** Taken on RMC's authority as the
  circuit's designer; see [Open with RMC](#open-with-rmc), where the V− half of
  it is still a question.
- **No reverse-protection diode**, traded against 0.6 dB of headroom the design
  has not got. Recorded as a deliberate trade, mitigated procedurally.
- **1206 passives and turnkey assembly.** An earlier revision was deliberately
  specified in 0805 and SOIC-8 so it could be built by hand. Dropping that
  constraint is what allowed the 1206 passives the routing now depends on. Do
  not read the part sizes as evidence that hand assembly was intended.

### RMC advice deliberately not taken

Four of their suggestions assume a self-built board, and this one is going to a
turnkey line. Recorded so they are not re-litigated:

- **"Select 1.8 nF capacitors with a 1.7 nF ±50 pF value."** Impossible on a
  turnkey line. Solved instead by ordering all six from one reel, so they track
  each other far more tightly than the tolerance band suggests.
- **"A multi-layer ceramic capacitor can be trimmed by abrading it"** with a
  rubber abrasive, between the terminals. A hand-selection method by another
  route. **Kept as a field-service note**, genuinely useful if one of these ever
  needs adjusting after the fact, but the board is specified so it never has to
  be used.
- **"Through-hole jumpers (wire-wrap AWG #30) when a long jump is a pain."**
  Reintroduces manual operations to a board built in one pass. Solved with the
  1206 trick instead.
- **"Manual assembly isn't difficult with 0805 and SOIC."** True, and why the
  board started that way, but turnkey assembly is what freed the package choice,
  and the 1206 passives it allowed are what made the routing work.

---

## Open with RMC

The finished design has gone to RMC for review. Three questions are awaiting
reply. Nothing has been ordered, so all three can still change the board.

**1. V− decoupling: the one where our own reasoning ran out.** RMC's *"a pair of
4.7 µF/25 V caps at each end of the power rails"* was taken literally: four
capacitors for the whole board, replacing eighteen local ones. In1 is a solid
ground plane and In2 a solid V+ plane, so V+ decoupling is distributed across the
whole board. But **V− is not a plane**, and that leaves the V− decoupling for
twelve op-amp halves resting on C902 and C904. Both sit on the right-hand edge
while the three op-amps run down a column on the far left: **no op-amp is closer
than 45 mm to a V− capacitor**, and U2 is 51 mm from the nearest, along a routed
track rather than a plane. Adding five local 100 n is a cheap change now and an
impossible one after fabrication.

**2. Polarity confirmation.** We print pin 7 = +4.5 V and build the loom to
match, on their own *"arbitrary… knee-jerk"* pin 7 = +. Round three stated it and
invited objection; none came, but silence is not agreement when the failure mode
destroys every op-amp on the board and there is no diode to catch it. This wants
an explicit yes.

**3. The USB socket.** RMC offered to fit a USB socket in the Poly-Drive II
enclosure so the preamp can be phantom-powered and the battery kept topped up.
Charging is fine; running permanently from USB may not be. The battery's negative
terminal *is* the −4.5 V rail, because the splitter's midpoint is signal ground.
So if the socket's ground is common with battery negative and it is fed from an
earthed source while the PD2's output reaches earth through a mixer, the −4.5 V
rail is tied to earth through the audio ground. That is a short across the lower
half of the splitter. It only bites in the permanently-powered case; occasional
charging can always be done unplugged. It affects their enclosure, not this
board, and they may already isolate the charging circuit.

---

## Building and verifying

```bash
./build.sh
```

Regenerates schematic *and* board from `design.py`, runs ERC, checks both against
`design.py`, runs DRC, and writes `fab/rmc-pizz-arco-pcbway.zip`, but **only
when DRC is clean**, so a board with known faults cannot reach a fab by accident.
Needs KiCad 10.x; see [`README.md`](README.md).

> **Anything changed in the KiCad GUI is destroyed by the next build.** Use the
> editor to inspect, measure and try things out; changes that should survive
> belong in the generator.

**Where it stands:** ERC clean. The 10 remaining warnings are all one benign
case, a CD4066 bidirectional pin meeting a power flag, which is what those pins
are. The generated schematic is read back through KiCad and compared against
`design.py` net by net: **53 nets, 233 pin connections, exact match.** The board
is fully routed with **0 DRC violations and 0 unconnected items**; routing is
entirely in `gen_pcb.py` and no autorouter is involved.

**Three checks the build cannot make:**

1. **Open the project in KiCad once** and confirm no symbol shows a broken
   library link. Nothing else catches this: the schematic embeds its own copy of
   every symbol, so ERC and `verify.py` pass regardless.
2. **Re-audit AGND by hand** against the table under [Grounding](#grounding).
3. **Confirm `design.NO_CONNECT` is still empty.**

### The build is reproducible in content, not in bytes

Symbol UUIDs are deterministic: `kisch._uuid` derives them from a name hash,
which is what makes cross-probing work and stops *Update PCB from Schematic*
offering to re-add every footprint. **Footprint UUIDs are not.** `FootprintLoad`
assigns a fresh random UUID to every item and KiCad writes footprints in UUID
order, so every build reshuffles the whole `.kicad_pcb` and, through the aperture
numbering, every gerber, with no source change at all. Measured: two consecutive
builds share **zero of 1822 UUIDs** while the content is identical.

> **`git status` is not evidence about `fab/`.** It reports dirty after every
> build whether or not anything changed. What can tell you: compare the outputs'
> mtimes against the sources, or read the board size straight out of
> `fab/pcbway/rmc-pizz-arco-Edge_Cuts.gm1`, which should measure 78.8 × 81.3 mm.
> Do not commit a build that changed nothing; discard it with `git checkout --`
> and keep the diff honest.

Fixable if it becomes irritating: derive footprint UUIDs from the reference the
way `kisch._uuid` already derives symbol ones. The cost is one rewrite of every
UUID in the committed board, once.

### Layout lessons that still bite

- **Never predict rotated pad positions; measure them.** Place the parts, dump
  real pad coordinates and courtyards from the placed footprints, and write the
  routing against those. Guessing KiCad's rotation conventions was the single
  largest source of wasted iterations.
- **Heavy B.Cu routing fragments a B.Cu pour**, and the symptom is
  `unconnected_items` in distant parts of the board, not anything that looks like
  a routing error.
- **A 0.65 mm pin pitch cannot take a row of stub vias.** A 0.6 mm via needs
  0.8 mm; move them inboard under the package body and alternate between two
  columns.
- **Two parallel components between the same two nets always interleave** when
  laid side by side; one of the two nets has to cross the other. Stack them, or
  put one net on a jumper layer.
- **Lane pitch:** a lane that ends in a via needs ≥0.625 mm to its neighbour;
  lanes carrying no vias can go down to 0.5 mm.
- **Fan-in ordering matters.** With the output header below the tiles, channel 1
  needs the outermost lane and the lowest approach row, and the header's pin 1 at
  the far end. Get it backwards and every lane crosses every other.
- **Group DRC violations by rule and by board region.** The six channels are
  identical, so one tile fault shows up six times; fix it once and the count
  drops by six. Going 316 → 227 → 69 → 29 → 13 → 5 took five passes done this
  way.
- **SMD connector pads are F.Cu only**, so a B.Cu run to a connector needs a via
  to get there. Through-hole headers hide this.

---

## Ordering it

`./build.sh` writes **`fab/rmc-pizz-arco-pcbway.zip`**: upload that and nothing
else. Read [`fab/ORDER.md`](fab/ORDER.md) first: it carries the settings that
cannot be expressed in gerbers, the four electrical requirements above, and the
polarity convention.

**The one that must not be missed: this is a 4-layer board.** Order forms default
to 2, which would silently drop both inner planes.
