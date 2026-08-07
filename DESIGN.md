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

Placed, routed and DRC-clean at 77.2 × 82.4 mm: 47 nets, 233 pin connections,
80 placements, 0 violations, 0 unconnected items. Nothing has been fabricated.

**This is rev D**, which is what RMC call rev.3 — they asked for gerbers of it
and the two numbering schemes should not be allowed to drift, so the silkscreen
says rev C and the covering note says it is their rev.3. It answers RMC's review
of 2026-08-01 and the addendum that followed it: the V− plane swap, the
ten-capacitor bypassing, the design-rule sweep, the all-pass feedback pair moved
up against the op-amp, and the buffer's 1 kΩ deleted. All of it comes from those
two messages. One question of ours is still
unanswered after three rounds, and it is the one that destroys the board — see
[Open with RMC](#open-with-rmc).

**The circuit has now been simulated as well as asserted**, and no board change
comes out of it: three of the four claims about the switching stage hold, the
fourth holds over most of the band, and the one component value that looked
approximate turns out to be nearly exact. It did add a question for RMC and two
constraints that were not previously written down. See
[Simulating it](#simulating-it).

---

## The circuit

### Per channel, ×6

- **PZT 1 (red)** goes straight to `OUT`, unbuffered. It never passes through an
  op-amp.
- **PZT 2 (white)** is loaded by R02 3M3 to ground, filtered by R01 1k/C01 100p
  (corner ≈1.6 MHz), buffered at unity gain, passed through a first-order
  all-pass, and summed into `OUT` through a single **1.8 nF**.

R01, that same 1 kΩ, is the stopper in front of the buffer input. It is doing two
jobs; see [Headroom](#headroom).

**The buffer's feedback is a wire.** It had a 1 kΩ in it (R03) until RMC's
addendum of 2026-08-01: *"please remove the 1k resistor in the feedback loop of
the unity gain non-inverting buffer and connect OUT to −IN with the shortest
possible trace at least .010" wide."* Their own pinout makes that a 1.27 mm stub
between adjacent pins — see [The feedback that became a
wire](#the-feedback-that-became-a-wire).

**The summing capacitor is matched to the element, deliberately.** RMC give the
element's own capacitance as **1700 pF**, and the red element works into C04
directly, so the two elements meet at the summing node weighted by capacitance:

```
OUT = (V_red · C_red + V_white · C04) / (C_red + C04 + C_stray)
```

That is why the six must match *each other*: it is string balance, not
tolerance fussiness. Against R02's 3M3, 1700 pF puts the input corner at
**28 Hz**, below the bottom string of a gamba (D2, 73 Hz) but not far below it;
see [Simulating it](#simulating-it), which is where that stops being a
comfortable margin.

> **Equal weighting is not equal capacitance**, and the difference is C01. Its
> 100 pF divides against the element's 1700 pF and costs the white path 0.53 dB
> before the buffer, so the balance condition is **C04 = C_element + C01 =
> 1800 pF** — the value actually fitted. Measured, not derived: see
> [What the simulation found](#what-the-simulation-found), finding 5.

**The all-pass is a polarity flip, not a phase shift.** Its RC corner is
1/(2π·47k·100p) ≈ **34 kHz**, well above the audio band, so in band the stage is
+1 with the switch open and −1 with it closed (the switch grounds the
non-inverting input). PZT 2 then sums with PZT 1 either in phase or in
anti-phase, and that is the pizz/arco character change. The all-pass form rather
than a plain switched inverter is what keeps gain magnitude and source loading
identical in both positions, so flipping the switch produces no level jump.

> **True to about 3 kHz, and not at the top of the band.** C02 sits across R06,
> so the feedback impedance is not a resistor and the stage is not strictly an
> all-pass: simulated, the two states are within 0.03 dB and 2° of each other
> below 3 kHz and **1.5 dB and 32° apart at 20 kHz**. See
> [What the simulation found](#what-the-simulation-found), findings 1 and 2.

The 100 pF capacitors are doing HF stability and RF rejection duty only. RMC:
*"the 100pF capacitors have no audible effect."* True of level — C01 costs half
a decibel — but **not of balance**, which is the note above.

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

- **Decoupling.** Ten 4.7 µF/25 V **multilayer ceramic** capacitors, in five
  symmetric pairs: one V+→AGND and one V−→AGND at each of U1, U2 and U3, one pair
  between the two CD4066s, and one at the supply entry. See
  [Bypassing](#bypassing).

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
| C901–C942, 10 × 4.7 µF rail bypass, five symmetric pairs | leakage only |

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

- **77.2 × 82.4 mm, 4 layers.** 80 placements: 72 SMD (1206 passives, SOIC-14
  and SO-14) and 8 through-hole 2.54 mm pin headers.
- **Stackup:** F.Cu signals · In1.Cu solid AGND plane · In2.Cu **solid V− plane**
  · B.Cu signals. The high-impedance piezo traces run over unbroken ground, and
  every ground and V− pad reaches its rail through one via.
- **In2 carried V+ until rev C.** RMC: *"most op amps used for audio applications
  are V− referenced because many designs operate from a single supply."* The rail
  the op-amp's own circuitry references had a 0.25 mm track and 45 mm to the
  nearest capacitor; the other one had a plane. See
  [The plane swap](#the-plane-swap).
- **V+ is routed**, as a U on B.Cu: down the west margin past the three quads,
  east along the bottom below the tail connectors, back up the east margin to the
  switches. All three legs were measured clear end to end before being written.
- **Neither rail is poured on B.Cu.** A B.Cu pour was this project's worst
  failure mode: fragmenting it produced unconnected items in parts of the board
  nowhere near the cause. B.Cu is a second signal layer and stays one.
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
  two channels. **It turned out to be right for a better reason than this one**:
  the balance condition is C_element + C01 = 1800 pF, so the single 1n8 is
  nearly exact and the pair it replaced was ~8 dB worse. See
  [What the simulation found](#what-the-simulation-found), finding 5. The
  simplification was made for convenience and happened to be correct, which is
  worth saying plainly rather than claiming as foresight.
- **Ten bypass capacitors, not four and not eighteen.** See
  [Bypassing](#bypassing).
- **No reverse-protection diode**, traded against 0.6 dB of headroom the design
  has not got. Recorded as a deliberate trade, mitigated procedurally.
- **1206 passives and turnkey assembly.** An earlier revision was deliberately
  specified in 0805 and SOIC-8 so it could be built by hand. Dropping that
  constraint is what allowed the 1206 passives the routing now depends on. Do
  not read the part sizes as evidence that hand assembly was intended.

### Four layers, and why

RMC asked directly: *"I'm not sure why you want 4 layers in this application. A
.030" or .060" thick double-layer board should work since the circuit will be
externally shielded and we're not exceeding 20 KHz … Are you having problems
routing Power & Ground on the top & bottom layers?"*

**No.** Power and ground would route on two layers. The board is about 14% land
utilisation, deliberately loose, and RMC are right that at 20 kHz with ±4.5 V
rails and 0.010" clearance there is no meaningful same-layer crosstalk. The
inner layers are not there for routing relief. The reasons, in descending order
of honesty:

1. **Every ground and V− pad reaches its rail through one via rather than a
   track.** This is what makes RMC's own *"beef up your Vcc, Vdd & Vss traces"*
   nearly free on two of the three: they are planes already.
2. **An unbroken reference under the buffer inputs.** SOIC-14 was chosen over
   TSSOP-14 specifically so an AGND guard ring fits around each buffer's
   + input, and a guard ring wants something to reference. RMC are right that
   the piezo source is not high-impedance at high frequency — the element is
   1700 pF, so 4.7 kΩ at 20 kHz — but at 100 Hz the element and the 3M3 bias in
   parallel are about 730 kΩ, and hum and handling noise live down there.
3. **The routing is solved on four layers and re-solving it on two is weeks of
   work.** That is a schedule argument, not an engineering one, and is labelled
   as such rather than dressed up as the first two.

The cost is roughly $20–30 more on a five-off prototype order, plus a standing
hazard: order forms default to 2 layers, and a 2-layer build of these gerbers
silently drops both planes.

**And the concession that belongs next to it**: four layers is what *caused* the
V− problem RMC found. Both inner layers went to AGND and V+, leaving V− as an
ordinary net — and a 2-layer board with a solid bottom pour might well have given
V− better copper than rev B did. Their two points connect, and the connection is
not flattering to the stackup. Rev C answers it by giving the plane to the rail
that needed it; if RMC still want two layers after seeing that, the evidence
would be theirs and worth more than ours.

### The feedback that became a wire

RMC's addendum, 2026-08-01: *"please remove the 1k resistor in the feedback loop
of the unity gain non-inverting buffer and connect OUT to −IN with the shortest
possible trace at least .010" wide."*

R03 was RMC's own part, in RMC's own drawing, and they took it out. The reason is
the one they give for the capacitor above: at a 10 MHz gain-bandwidth, stray
capacitance at the inverting node works against whatever impedance is in the
feedback path, and 1 kΩ with a few picofarads of trace is a pole inside the loop.
A wire has no such problem.

**Their pinout made it nearly free.** `QUAD_UNITS` puts each buffer's output and
its inverting input on *adjacent pins in the same column* — 1 and 2 on the odd
channel, 7 and 6 on the even. So the whole feedback is a single **1.27 mm segment
at 0.30 mm (0.0118")**, no vias, never leaving the package footprint. Measured
from the built board, not asserted.

It paid for itself twice over in the layout. Rev C's R03 sat west of the package,
which meant *both* buffer nets had to dive inboard between the pad columns, run
west under the package on B.Cu and surface on the row line at R03's own two pads —
and R03's position was itself dictated by which gaps in the row line were still
free. All of that is gone, along with six resistors and six nets.

### The all-pass feedback pair, moved up against the op-amp

RMC's addendum again: *"the OPA191 op amp has a 5V/µS slew rate, so with a fast
IC, the feedback capacitor (100pF in the inverter feedback loop) needs to be
located closest to −IN. Since the cap is in parallel with a 47K resistor, you can
place both of them adjacent to the IC with the capacitor most proximate to the
−IN pin."*

Rev C had the pair at dx 38.5 with C02 on the sub-row — which put them in the
wrong order as well as too far away:

| | rev C | rev D |
| --- | --- | --- |
| C02 (100 pF) to −IN | 11.8 mm | **3.1 mm** |
| R06 (47 k) to −IN | 9.3 mm | 7.6 mm |

C02 is now the first part on the row, its west pad edge **0.80 mm (31.5 mil)**
from the package's own pads. It cannot go closer: the strip between the row line
and pin 14 is **0.79 mm**, and a 1206 at pin-13 height closes to 0.37 mm of the
pin-12 lane, 0.03 mm short of clearance. Getting nearer than 3 mm means a smaller
package for that one part, which is RMC's call and not ours.

**What made it fit was moving APN off the row.** With C02 first, APN and APOUT
interleave along the row — APN, APOUT, APN, APOUT — and rev C's arrangement
existed precisely to avoid that. Neither net travels along the row now. APN runs
east on its own pin's lane, between the package and the row, and drops onto each
pad it needs; that lane clears a capacitor standing on the row by 1.0 mm, so it
passes straight over C02 on its way to R06. APOUT cannot do the same — its pin
lane is 0.79 mm from the row line and would close to 0.15 mm — so it dives to
B.Cu at once and feeds its pads from the band, which is what it already did.

The part pitch also went from 5.5 mm to **5.0 mm**, which is what paid for the
extra slot on the row. A 1206's pads span ±2.05 mm, so 4.87 mm is the floor for
RMC's 0.030" spacing and 5.0 is the round number above it.

### The plane swap

**In2 carries V−, not V+.** This is rev C's largest change and it came from one
sentence of RMC's: *"most op amps used for audio applications are V− referenced
because many designs operate from a single supply. The OPA191 data sheet doesn't
provide a detailed schematic, only a block diagram, but Texas Instruments should
be able to provide the necessary guidelines."*

Rev B had it backwards. V+ got a whole inner layer; V− got an ordinary 0.25 mm
track running to a capacitor 45 mm away, 51 mm for U2. The arithmetic that
matters is not DC — 50 mm of 0.25 mm copper is about 0.1 Ω and the board draws
2 mA — but inductance. That track is roughly **25 nH**, and 25 nH against 4.7 µF
resonates at about **460 kHz** with a Q of 5–10 against an MLCC's ESR. That put a
several-ohm impedance peak on the V− rail, half a megahertz inside the OPA4191's
10 MHz gain-bandwidth, on the rail the op-amp's own circuitry references.

Never audible, and not the kind of fault that shows up on the first board.

Swapping the two planes costs the V+ routing and buys three things: every op-amp
and switch supply-return pin, J7 pin 8, R701 and five capacitors are connected by
one via each; the V− spine and its three dives under the buses disappear; and the
three-lane bundle east of every quad loses its middle lane.

**What it does not buy is a free lunch — V+ is now the routed rail**, and it
carries the local capacitors instead. That is the right way round: V+ is the rail
whose PSRR is better, and it is the one that now has a capacitor 8.2 mm away
rather than a plane.

### Bypassing

RMC, on seeing rev B's four capacitors in a column on the far edge: *"I suggest
moving the power bypass caps as close as possible to the op amps (there's 4 of
them, so distribute them evenly between the 3 IC's) and beef up your Vcc, Vdd &
Vss traces. Maybe add a pair of bypass caps between the two CD4066 IC's. Use MLC
caps, not electrolytics."*

Ten capacitors, in five symmetric pairs:

| Refs | Where | |
| --- | --- | --- |
| C911/C912, C921/C922, C931/C932 | U1, U2, U3 | 8.2 mm from pin 4 |
| C941/C942 | between U4 and U5 | RMC's explicit request |
| C901/C902 | supply entry | bulk on the incoming rail |

Ten rather than the four RMC's wording implies, because *"distribute them evenly
between the 3 IC's"* does not divide four, and a pair per package is the nearest
thing that keeps every location symmetric. **Symmetry is not cosmetic**: the two
rails' return currents meet in the DIN shell, which is the same single conductor
carrying six string returns, so `_GROUND_RULE` forbids bypassing one rail harder
than the other. `design.check_bypass_symmetry()` enforces it.

**Both capacitors of each op-amp pair sit west of the quad**, which looks wrong
until you measure what is east of it. Pin 4 (V+) and pin 11 (V−) are at
(−2.475, 0) and (+2.475, 0) on the SOIC-14, so one each side is the obvious
placement — and it does not fit. East of the package the centreline is a
three-lane bundle at 1.27 mm pitch running unbroken from the pads to the buses.
West of it only the BUFIN lanes flank the centreline and they stop at the pad
column, leaving x = 10–18 clear on every block. **That is the only 1206-sized
space in a block.** Which is survivable precisely because of the plane swap: V−
no longer needs a local capacitor, so only the V+ one has to be close.

**No 100 nF in parallel.** A 1206 X7R 4.7 µF goes inductive above roughly
2–3 MHz and a parallel 100 nF would extend that to ~15 MHz, but once the
capacitor is at the pin the few millimetres of trace dominate the loop anyway. It
also doubles the count, back towards the eighteen RMC told us to delete. Offered
to them; not proposed.

### Design rules, and the ±0.003" budget

Every rule number went up in rev C. RMC: *"anticipate cumulative drilling & layer
registration errors/offsets totalling about ±.003", compensate for those in the
layout … and the chance of failure upon fabrication and over the long-term will
be greatly minimized. This way you can expect a good board from just about any
p.c.b. contractor."*

| | Rev B | Rev C |
| --- | --- | --- |
| Signal track | 0.25 mm | **0.30 mm** |
| Power track | 0.50 mm | **0.80 mm** |
| Via pad / drill | 0.60 / 0.30 mm | **0.80 / 0.40 mm** |
| Annular ring | 0.15 mm | **0.20 mm** |
| Clearance | 0.20 mm | **0.25 mm** |

0.003" is 0.076 mm. A 0.20 mm ring absorbs the full error and leaves 0.124 mm,
against an IPC-2221 Class 2 minimum of 0.05 mm; the old ring left 0.074 mm —
passing, but on the fabricator's good behaviour rather than our own arithmetic.
The numbers live in [`rules.py`](rules.py), which both generators import, so
copper cannot be laid to one set and checked against another.

**Power and ground vias are doubled where there is room**, per RMC's *"double
vias and larger holes are low-cost insurance against plating problems"* — the ten
bypass capacitors and the V+ taps. Not under the SOIC-14 and SO-14 packages,
whose pad columns are 3.0 mm apart, and not on the two switch supply taps, where
a pair closes to 0.195 mm of the pin-13 row. That is RMC's own *"where it is
practical to do so"*.

One shortfall, declared rather than buried: RMC said 0.010" clearance and 0.25 mm
is 0.0098". Four microns under, kept because the layout is on a metric grid.

**A rail tap that was never a decision.** `route_supply()`'s `tap()` helper took
no width argument, so every rail tap on rev B came out at 0.25 mm while the spine
it fed was 0.5 mm. Not a trade-off — just a default nobody passed. It is most of
*"beef up your Vss traces"* in one line.

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

Nothing has been ordered, so everything here can still change the board.

### Answered in the review of 2026-08-01

**V− decoupling** was question 1, and it is closed. RMC answered it twice over:
directly, by telling us to move the capacitors to the ICs and add a pair between
the CD4066s, and structurally, by pointing out that an audio op-amp is V−
referenced — which is what identified the plane assignment itself as the fault.
See [The plane swap](#the-plane-swap) and [Bypassing](#bypassing).

### Still open

**1. Polarity confirmation — the one that blocks ordering.** We print pin 7 =
+4.5 V and build the loom to match, on RMC's own *"arbitrary… knee-jerk"* pin
7 = +. It was stated and put to them in round three, restated in round four, and
has not been answered either time. Silence is not agreement when the failure mode
puts 9 V backwards across every op-amp on the board and there is deliberately no
diode to catch it — a series Schottky per rail would cost about 0.6 dB out of a
9 V total supply, which this design has not got.

> **Do not order until this is confirmed in writing.** The silkscreen carries the
> convention and the build procedure calls for a continuity check from the DIN
> plug to J7 before first power-up, but procedure is not confirmation.

**2. The USB socket.** RMC offered to fit a USB socket in the Poly-Drive II
enclosure so the preamp can be phantom-powered and the battery kept topped up.
Charging is fine; running permanently from USB may not be. The battery's negative
terminal *is* the −4.5 V rail, because the splitter's midpoint is signal ground.
So if the socket's ground is common with battery negative and it is fed from an
earthed source while the PD2's output reaches earth through a mixer, the −4.5 V
rail is tied to earth through the audio ground. That is a short across the lower
half of the splitter. It only bites in the permanently-powered case; occasional
charging can always be done unplugged. It affects their enclosure, not this
board, and they may already isolate the charging circuit. Also unanswered, but
not blocking.

**3. The Poly-Drive II's input impedance.** New, and it comes out of
[Simulating it](#simulating-it). This board deliberately puts no load on `OUT`
— the output is meant to look like a piezo and the PD2 supplies the load — and
nobody has ever said what that load is. It turns out to set the bass response
almost by itself, because it works against the element's 1700 pF and `C04`'s
1.8 nF together:

| PD2 input impedance | corner at `OUT` | level at D2, 73 Hz |
| --- | --- | --- |
| 1 MΩ | 45 Hz | **−1.9 dB** |
| 4.7 MΩ | 9.6 Hz | −0.5 dB |
| 10 MΩ | 4.5 Hz | −0.4 dB |

At 1 MΩ the bottom string is already down nearly 2 dB and the corner sits above
it. That is a bigger number than the 28 Hz corner `R02` was credited with, and
it is not ours to fix: it is one figure from RMC. Not blocking — it changes
nothing on the board either way — but it decides whether the instrument's bass
is flat.

### Offered and awaiting a view

- **The 4-layer stackup.** RMC asked *"I'm not sure why you want 4 layers in this
  application … Are you having problems routing Power & Ground on the top &
  bottom layers?"* The honest answer is no — power and ground would route on two
  layers. See [Four layers, and why](#four-layers-and-why).
- **A 100 nF in parallel with each 4.7 µF**, if they want the HF end extended.
  See [Bypassing](#bypassing).
- **`C01`'s 100 pF is part of the summing balance**, which neither of us
  noticed. It divides against the element's own 1700 pF and attenuates the white
  path by 0.53 dB, so the two elements balance when `C04` = element + `C01` =
  **1800 pF**, not when `C04` = element. The single 1n8 is therefore the right
  value and RMC's own 220 p ∥ 1.5 n would have been ~8 dB worse. See
  [What the simulation found](#what-the-simulation-found). Worth their view
  because it means `C01` can no longer be changed freely.

---

## Simulating it

```bash
./build.sh                     # writes rmc-pizz-arco/rmc-pizz-arco-sim.kicad_sch
```

Open that sheet in KiCad and use **Inspect → Simulator**. There is nothing to
install: KiCad ships ngspice. One file is needed and is deliberately not in this
repository — TI's OPAx191 macromodel, from <https://www.ti.com/lit/zip/SBOMA30>,
because their licence grants use but not redistribution.
[`gen_sim.py`](gen_sim.py) says where to put it and generates the sheet whether
or not it is there.

The sheet is generated from the same `design.py` as the fabrication one, so it
cannot drift from the circuit, and it carries the analyses as commented SPICE
directives with the results beside them. It draws **one channel**: the six are
electrically independent, sharing only the rails and one DC control line, so
five more copies would add nothing that could come out differently.

### What was being tested

`design.py`'s docstring makes four claims about the second stage:

> The second stage is a first-order all-pass whose RC corner sits at 34 kHz,
> well above the audio band, so in-band it is a polarity flip [...] The all-pass
> form keeps gain magnitude and source loading identical either way, so flipping
> it produces no level jump.

Three of the four hold. The fourth does not, and the reason it does not is
visible in RMC's own drawing.

### What the simulation found

**1. The second stage is not an all-pass.** `C02`'s 100 pF sits in parallel with
`R06`'s 47 k, so the feedback impedance is not a resistor — and a first-order
all-pass needs it to be one. With `R04 = R05 = R06` and `C02 = C03`, τ = 4.7 µs:

| | transfer function | 1 kHz | 5 kHz | 20 kHz |
| --- | --- | --- | --- | --- |
| switch open (arco) | `1/(1+sτ)²` | −0.02 dB | −0.21 dB | −2.78 dB |
| switch closed (pizz) | `−1/(1+sτ)` | −0.04 dB | −0.13 dB | −1.32 dB |
| **level jump** | | −0.028 dB | +0.078 dB | **+1.464 dB** |
| **phase separation** | (180° claimed) | 181.8° | 188.8° | **211.7°** |

So *"no level jump"* is true where it matters and false at the top of the band.
Below about 3 kHz the two states are within 0.03 dB and 2° of a perfect flip;
by 20 kHz they are 1.5 dB and 32° apart. The two error terms pull opposite ways
— `R`<sub>on</sub> holds the closed state down, `C02` pulls the open state down
faster — and they cancel at 3 kHz, which is why the jump changes sign.

Whether 1.5 dB at 20 kHz matters is RMC's call, not ours. A gamba's fundamentals
stop around 1 kHz; what lives at 20 kHz is bow noise and the top of the
brightness. It is recorded because it was asserted not to exist.

**2. The 34 kHz corner is real, and the two states differ in order.** At
33.9 kHz the open state measures −92.7° — the −90° of two matched poles — and
the closed state 133.9°, the 180° − 45° of one. `R05 × C03 = 33.9 kHz` survives
contact with the circuit. This is the same finding as 1 from the other side: it
is not that the corner moved, it is that only one state has two poles.

**3. R<sub>on</sub> costs less than a tenth of a decibel, up to about 300 Ω.**

| R<sub>on</sub> | 0 Ω | 100 Ω | 300 Ω | 1 kΩ | 3 kΩ |
| --- | --- | --- | --- | --- | --- |
| level jump at 1 kHz | +0.009 dB | −0.028 dB | −0.102 dB | −0.360 dB | −1.101 dB |

R<sub>on</sub> divides against `R05`'s 47 k and leaks the switched node's ground
reference back into the sum, so it moves the closed state only. Hand arithmetic
said −0.037 / −0.111 / −0.370 dB relative to an ideal switch; the solver said
−0.037 / −0.111 / −0.369. **The claim in [What was added](#what-was-added)
holds** at the ~100 Ω these rails give, with about a decade of margin before it
stops holding.

**4. The bass is where the surprises are.** Driving the two elements in
antiphase — vertical string motion, the case arco is supposed to reject —
gives this:

| | 10 Hz | 40 Hz | **73 Hz** | 150 Hz | 300 Hz | 500 Hz | 1 kHz | 2 kHz | 5 kHz |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| arco rejection | 1.9 dB | 9.9 | **15.2** | 21.4 | 28.9 | 38.7 | 35.0 | 25.2 | 16.4 |

A peak, not a plateau, and **the bottom string sits on the wrong side of it.**
At D2 the vertical component that arco exists to cancel is only 15 dB down,
against nearly 39 dB at 500 Hz. Two different mechanisms eat the two ends:

- **Below ~300 Hz it is the 28 Hz corner, and it is structural.** The white
  element works into `R02`'s 3M3 and the red element has no bias resistor at
  all, so the high-pass is on one path only. The two arrive at the summing node
  with a frequency-dependent phase error, and the null fills in. No component
  value fixes this — it was checked against `C04` at 1n7, 1n72, 1n8 and 1n9 and
  the 73 Hz figure moves by 0.35 dB across the lot. Giving the red element its
  own 3M3 would, and that is a board change nobody has asked for.
- **Above ~1 kHz it is `C02`**, which is finding 1 arriving at the output.

**5. `C01` is part of the summing balance, and that is why 1n8 is right.** This
one was not predicted and it reverses an argument this document was about to
make.

`C01`'s 100 pF divides against the element's own 1700 pF and costs the white
path **0.53 dB** before it even reaches the buffer. So the two elements balance
at the summing node when

```
C04 = C_element + C01 = 1700 pF + 100 pF = 1800 pF
```

not when `C04` equals the element. Measured null depth at 500 Hz:

| `C04` | 1n7 (element exactly) | 1n72 (RMC's 220 p ∥ 1.5 n) | **1n8 (built)** | 1n9 |
| --- | --- | --- | --- | --- |
| arco rejection | 29.5 dB | 31.1 dB | **39.0 dB** | 31.6 dB |

Deleting `C01` from the model moves the optimum from 1n82 to 1n72 — a shift of
exactly `C01` — which is the check that the explanation is the right one rather
than a coincidence in the neighbourhood.

Two things follow. **The single 1n8 was the right choice**, better than the pair
it replaced by about 8 dB, and [A single 1n8 rather than 220 p ∥ 1.5
n](#decisions-and-their-reasons) is more right than its own reasoning knew.
And **`C01` can no longer be changed freely**: it is described in [The
circuit](#the-circuit) as doing "HF stability and RF rejection duty only", and
RMC's *"the 100pF capacitors have no audible effect"* is true of level and not
of balance. Raising `C01` without raising `C04` to match trades arco depth for
RF rejection. This is the same mechanism as RMC's own headroom mitigation — a
capacitor across `R02` attenuating the white path, with `C04` increased to
restore the balance — applied to a capacitor that is already fitted.

**6. The flip is click-free.** Stepping the toggle with a 200 Hz signal running:
the envelope is 10% of the way across 1.48 ms after the step and 90% at 3.44 ms,
and the largest movement between adjacent 2 µs samples is 3.97 mV against
2.35 mV for a clean 200 Hz sine of the settled amplitude over the same interval.
Nothing in the transition moves faster than about twice what the audio does. No
edge, no spike. Note that the audible transition is ~2 ms, not the 10 ms of
`R701 × C701` — the cell only changes while the control is crossing its
threshold, and the RC is what makes that crossing slow.

### What a failure would have looked like

Every one of the above is a number, and a number is not evidence unless it could
have been a different number. What red looks like, analysis by analysis:

| | a wrong answer would have read as |
| --- | --- |
| 1, 2 | a perfect overlay and exactly 180.000° at every frequency — a true all-pass, i.e. `C02` not actually across `R06` on the sheet |
| 3 | a single-pole rolloff in *both* states, meaning one of the two capacitors is doing nothing |
| 4 (R<sub>on</sub>) | no effect, or an effect that does not scale with the swept value |
| 5 (bass) | **a flat rejection curve** |
| 6 | a step or a spike at `OUT`, which would mean DC in the switched leg |

The last one in that list is the one with history, and it was run as a control
rather than argued about. Replacing the element capacitances with shorts —
which is what modelling a piezo as a plain voltage source amounts to — returns
**0.00 dB of rejection at every frequency**: the red element's ideal source
simply pins `OUT`, the white path becomes invisible, and pizz and arco read
identical. Clean, plausible, and completely uninformative. That is the
`summing-mixer` failure `docs/simulating.md` records, reproduced on purpose so
the shape of it is on file for this board too.

**Two of these tests could not fail on the first attempt, and both were caught
by having predicted the answer first.**

- `Simulation_SPICE:SWITCH` is the obvious part for the CD4066 cell and it is
  wrong: ngspice's `SW` device always contributes `roff` in AC analysis whatever
  its control is doing, while its DC operating point is correct. Both switch
  states returned identical results to four decimal places at every frequency —
  which reads as a triumphant confirmation of *"no level jump"* and is the
  answer a circuit with no switch in it would have given. The cell is now a
  behavioural resistance controlled by `SW_CTL`. Recorded in
  [`docs/simulating.md`](docs/simulating.md) as the fourth way a simulation
  lies.
- The predicted arco rejection was ~31 dB midband and the measurement came back
  at 39 dB. Chasing the 8 dB is what found `C01` in finding 5. A prediction that
  is wrong in an interesting direction is worth more than one that is right.

### What the models are, and what they are not

- **OPA4191** — TI's `OPAx191` macromodel, from
  <https://www.ti.com/lit/zip/SBOMA30>. A *single* amplifier, so the sheet draws
  two single op-amps where the board has one quad serving four. Fetched, never
  committed; `.gitignore` keeps it out.
- **CD4066B** — **TI publish no SPICE model for it.** Not on the product page,
  not under tools and software, not anywhere; what circulates is community
  rebuilds from CD4007 gates. So the cell is modelled here, and the honest
  substitute for the R<sub>on</sub>-versus-supply curve a vendor model would
  have carried is the sweep in finding 3. What that model does *not* do:
  R<sub>on</sub> does not vary with signal level, so it cannot show the
  distortion a real cell's would; and its off state is a resistor rather than a
  reverse-biased junction, so it is cleaner than the part's.
- **The piezo** — no vendor model exists, and this is the part that mattered
  most. A voltage source in series with 1700 pF, RMC's own figure, in
  [`source.py`](source.py) rather than as a literal.
- **The Poly-Drive II's input** — 1 MΩ, and it is an **assumption**, flagged as
  one in `source.py` and raised with RMC in [Open with RMC](#open-with-rmc). It
  is common to both element paths, so it moves the bass response without moving
  the null: findings 4 and 5 do not depend on it, and the absolute low-frequency
  response does.

One observation that is not a finding about this board. Above about 200 kHz the
second stage stops attenuating and turns back up, reaching +4.5 dB at 1 MHz.
That is the amplifier, not the network: swapping `U102` for an ideal controlled
source gives a clean −40 dB/decade all the way down (−19.8, −38.9, −58.8 dB at
100 kHz, 300 kHz and 1 MHz). An op-amp cannot attenuate past its own open-loop
gain, and `C02` is a passive path from the inverting node to the output that
does not need the amplifier at all. Two decades above anything audible, and
recorded only because "it rolls off above 34 kHz" is the kind of story that
would get it wrong.

### What was not simulated, and why

- **Headroom and clipping.** Settled with RMC on judgement plus a datasheet
  paragraph — see [Headroom](#headroom) — and the falsification criterion there
  is an audible artefact on a real instrument, which no solver reaches. The
  large-signal convergence options are on the sheet for whoever wants to try.
- **Noise.** Nothing here has gain and the source is a 1700 pF element into
  3M3; the arithmetic is not in doubt and simulation would only restate it.
- **The other five channels.** They share the rails and one DC control line and
  nothing else. There is no summing node between them, which is exactly what
  made the equivalent test worth running on `summing-mixer` and pointless here.

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
`design.py` net by net: **47 nets, 233 pin connections, exact match.** The board
is fully routed with **0 DRC violations and 0 unconnected items**; routing is
entirely in `gen_pcb.py` and no autorouter is involved.

**`fab/ORDER.md` is checked against the board, not trusted.** It quotes about a
dozen figures that are all derivable — board size, layer count, every design
rule, the hole count, the placement split — and it is written by hand, because
the prose around those numbers is worth more than a generated table would be.
Twice that hand-maintenance failed: the board dimensions went stale after the
plane swap, and the hole count after the feedback pair moved, claiming 177 vias
and 206 plated holes when the board had 147 and 176. Both survived a commit.

That is worse than an ordinary documentation slip, because `build.sh` copies this
file into the fabrication zip: a stale figure is a wrong number in front of the
contractor, in the one document whose whole job is to carry what the gerbers
cannot. So `verify.check_order_figures()` reads the numbers back out of the
document and compares them against the built board and `rules.py`. A mismatch
fails the build, and the package is never written.

It also fails if the *wording* moves — if a figure can no longer be found, that
is reported rather than passed over, so rewording the document cannot quietly
switch the check off.

**`build.sh` runs `gen_project.py` twice, and that is not redundant.**
`pcbnew.SaveBoard()` writes the `.kicad_pro` as well as the board, through
KiCad's settings manager, and what it writes is KiCad's defaults — no `Power`
net class, no netclass patterns, `min_via_annular_width` back to 0.10 and
clearance back to 0.20. **Every DRC run in this project's history before rev C
was therefore checked against looser rules than the layout was drawn to**, and
nothing said so. Regenerating the project file after the board fixes it, and
`verify.check_project_rules()` reads it back afterwards and fails the build if
some later step learns to clobber it too.

**Three checks the build cannot make:**

1. **Open both sheets in KiCad once** and confirm no symbol shows a broken
   library link. Nothing else catches this: a schematic embeds its own copy of
   every symbol, so ERC and `verify.py` pass regardless. `gen_project.py` writes
   the library table and the project library from both sheets' symbol
   registries, which is what makes the answer *no* rather than a habit.
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
> `fab/pcbway/rmc-pizz-arco-Edge_Cuts.gm1`, which should measure 77.2 × 82.4 mm.
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
- **A courtyard is half as big again as the part.** A 1206's land is
  3.2 × 1.6 mm but its courtyard is **4.69 × 2.39 mm**, so two of them need
  5.2 mm between centres. Two placements were sized off the land and both
  failed `courtyards_overlap`.
- **Free space for a capacitor is not free space for its via.** `free_offset()`
  checks courtyards, and every obstacle that matters to a bypass capacitor's
  stub via is a *track*: the rail run passing between its own two pads, the OUT
  bus, the V+ spine. Left to choose, it put one via 0.125 mm from the very run
  the capacitor was there to bypass. Bypass stubs are now explicit.
- **Through-hole pads block every layer.** A corridor scan that only looks at
  tracks and vias will happily route a B.Cu spine through a pin header's pads.
  The west V+ spine was placed that way once and had to move to the margin.
- **Widening the rules moves the fan-in, not just the tracks.** Each OUT
  approach row ends in a via, so its pitch is set by via-to-track: 0.4 of via
  radius, 0.25 of clearance, 0.15 of the neighbour. Going to 0.8 mm vias pushed
  the six rows past what fitted below the last sub-row, and J7 and J8 had to
  move 1.1 mm down the board.
- **Measure the geometry against the generated board, not the committed one.**
  Two scans in the rev C work were run against a stale copy and gave answers
  that looked right and were not.
- **Interleaving only matters to a net that travels along the row.** Rev C's
  block order existed to keep APN and APOUT from crossing, which is what put the
  all-pass capacitor 11.8 mm from the pin it belonged to. Give each of them a
  route that is not the row — a pin-height lane on one side, B.Cu on the other —
  and the interleave stops being a constraint at all.
- **A pin's own lane is usable board.** The strip between a SOIC's pin row and
  the first component row is too narrow for a part, but a track at the height of
  the pin it comes from clears a 1206 standing on that row by 1.0 mm, and can
  serve several pads by dropping onto each. That one observation is what let the
  feedback pair move up against the package.
- **Deleting a part can be the cheapest layout change available.** Taking out
  the buffer's 1 kΩ removed six resistors, six nets, twelve vias and two B.Cu
  runs per channel, and made the feedback a 1.27 mm stub between adjacent pins.

---

## Ordering it

`./build.sh` writes **`fab/rmc-pizz-arco-pcbway.zip`**: upload that and nothing
else. Read [`fab/ORDER.md`](fab/ORDER.md) first: it carries the settings that
cannot be expressed in gerbers, the four electrical requirements above, and the
polarity convention.

**The one that must not be missed: this is a 4-layer board.** Order forms default
to 2, which would silently drop both inner planes.
