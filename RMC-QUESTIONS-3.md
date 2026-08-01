# The design review — round four

Follows `RMC-QUESTIONS-2.md`. This is the message that sends RMC the finished
board, which `STATE.md` has had as the next external step since the rework
landed. The reasoning behind each item lives in `STATE.md`; this file holds the
outgoing wording.

Unlike rounds one to three, this one is not a list of things we need in order to
proceed. Only two answers are actually blocking, and one of them is a
confirmation. The rest is on the record so they can object.

---

## Attachments

**Attach these four:**

- `fab/rmc-pizz-arco-schematic.pdf` — **essential.** Their channel six times
  over, plus the switching, supply distribution, decoupling and connectors their
  drawing leaves undefined. One flat A2 sheet; everything below is visible on it.
- `fab/rmc-pizz-arco-layout.pdf` — four pages, one per copper layer in board
  order: **F.Cu, In1.Cu (AGND plane), In2.Cu (V+ plane), B.Cu**. Each carries
  the reference designators and the board outline, so any page can be read on
  its own; the two plane pages show as a solid tone with the antipads knocked
  out in white. Each page is a different colour only so the layers are told
  apart at a glance — the colour says nothing about the copper. The designators
  are 1 mm text on an 81 mm board, so it wants
  zooming into rather than reading at a glance — it is vector and stays sharp.
  This is what makes the bypass question answerable: the absence of a V− plane
  is visible rather than described.
- `fab/rmc-pizz-arco-bom.csv` — the substitutions, and the tolerances that
  matter.
- `fab/rmc-pizz-arco-top.png` — courtesy. It answers their original offer to
  have us do the layout. Decorative; expect nothing from it.

**Offer, do not attach** (one line in the message): the gerbers, the netlist
(`build/verify.net`) and the fabrication notes (`fab/ORDER.md`).

**Never send the gerber zip unsolicited** — the reasoning in `RMC-QUESTIONS.md`
still holds, and holds harder now that the layout PDF is per-layer: gerbers are
copper polygons with no nets, values or references, and they ask the wrong thing
of the person who designed the circuit.

---

## The message

**Subject: Pizz/arco board — finished, and ready for your eyes**

The board is done: six channels of your 2026-07-29 drawing, four layers,
78.8 × 81.3 mm, 80 parts, DRC clean. Nothing has been ordered and nothing is
committed, so anything in here can still change.

Your circuit is on it part for part — R01 1 k stopper, R02 3M3 bias, C01 100 p,
the unity buffer with its 1 k feedback, the all-pass on three 47 k and its
100 p, and the two elements summed through the 1n8. We did not change anything
inside the channel.

On your CD4066 caveat: noted, and we're a long way inside it. The board runs on
±4.5 V from the Poly-Drive II, so the switches see 9 V total against your 18 V
ceiling. Worth saying because the schematic you have on file is still the old
±9 V charge-pump version — that one would have sat exactly on the limit. It's
gone; the drawing attached here is the board as built.

Everything else is ours, and none of it appears in your drawing. That is where
your time is worth spending, so it is all below.

### Two things we'd like an answer on

**1. The bypass — this is the one we'd most like you to look at.**

We took your "a pair of 4.7 µF/25 V caps at each end of the power rails"
literally: four capacitors for the whole board, replacing the eighteen local
ones we had. We want to be sure that still holds given how the board came out.

In1 is a solid ground plane and In2 is a solid V+ plane, so V+ decoupling is
distributed across the whole board and we have no concerns there. **V− is not a
plane.** At about 2 mA it never seemed to need one, and an attempt at pouring it
on the bottom layer fragmented and caused problems well away from the cause, so
V− is routed as an ordinary net.

That leaves the V− decoupling for twelve op-amp halves resting on two
capacitors — C902 and C904. Both sit on the right-hand edge, one near the top
and one near the bottom, while the three op-amps run down a column on the far
left. **No op-amp is closer than 45 mm to a V− capacitor**, and U2 in the middle
is 51 mm from the nearest — along a routed track, not a plane.

Is that what you had in mind, or would you put something local on V− at each
package? There is room, and adding five 100 n is a cheap change now and an
expensive one after fabrication.

**2. Polarity — we'd like this confirmed rather than assumed.**

We're printing **pin 7 = +4.5 V, pin 8 = −4.5 V**, pin 9 the shell, and building
the loom to match. You called your own pin 7 = + arbitrary last time and we took
the silence since as agreement — but there is deliberately no reverse-protection
diode on the board, because a series Schottky per rail costs about 0.6 dB of
headroom we haven't got. So a loom built backwards destroys every op-amp on the
board, and this is the one thing worth being explicit about.

Since you're wiring the Poly-Drive end: is pin 7 = +4.5 V correct?

### And one still outstanding from last time

**3. The USB socket.** This never got an answer, and you may simply have judged
it not worth one — but you're assembling the unit, so it's still live. Charging
is fine; what we weren't sure about is leaving it *powered* from USB. If the
socket's ground is common with the battery negative, and that's our −4.5 V rail,
then an earthed charger plus an earthed mixer would short the lower half of the
supply. Is the charging circuit isolated, or is continuous USB running something
to avoid?

### Four decisions that are ours — say if you'd have done them differently

None of these needs a reply if you're happy with them.

**The op-amps.** Three OPA4191 quads rather than twelve singles, as you
suggested. Within each quad the two buffers are on A and B and the two all-passes
on C and D. That puts both buffer inputs on the connector side, so the only
things crossing the package are buffer outputs — the 3M3 nodes stay short. The
alternative grouping (one channel per half) drags a 3M3 node across the whole
footprint.

**The switches.** Six CD4066B cells across two packages, on your control network
— R701 1 M to Vss, R702 20 k in series, C701 10 n. The two spare cells have both
terminals parked on ground with their control tied to Vss, so nothing is left
floating.

**Where R702 sits.** You said the switch shorts the control lines to Vdd through
a low-value series resistor. We put R702 on the **rail** side of the toggle
rather than the switch side, so a pinch anywhere in the toggle cable draws about
450 µA instead of shorting V+ — that cable leaves the board. Closed, the divider
holds the control within 0.2 V of V+ and draws about 9 µA. If you meant it the
other way round, say so.

**The summing capacitors.** Single 1n8 C0G/NP0 rather than your 220 p ‖ 1.5 n,
specified ±2% rather than the ±5% you accepted, all six from one reel. ±5%
permits a 10% spread between two channels, which is looser than the balance the
matching exists to protect.

---

Happy to send the gerbers, the netlist or the fabrication notes if you'd like
any of those.

---

## Why it is worded this way

- **It opens by saying nothing is committed.** A review request that arrives
  after the boards are ordered is not a review request. Saying so first makes it
  worth their while to find something.
- **The channel itself is confirmed, not asked about.** It is faithful part for
  part, and inviting them to re-check it would spend the attention the four
  ours-decisions need. Listing the values shows we checked rather than claiming
  we did.
- **The bypass question leads because it is the only one where our own
  reasoning ran out.** `STATE.md` records the four-capacitor decision as taken
  on their authority pending this review, so it is the one item where the review
  is load-bearing rather than courteous.
- **It volunteers the V− weakness rather than waiting to be caught.** The
  absence of a V− plane is the fact that makes four capacitors a different
  proposition from what they pictured, and they cannot see it without being
  told. Giving them the reason (2 mA; a bottom-layer pour fragmented) lets them
  correct the premise instead of just the conclusion.
- **It names the remedy and its price.** "Five 100 n, cheap now and expensive
  after fabrication" makes the answer actionable in one line; "is the decoupling
  adequate?" invites "should be fine".
- **Polarity is asked as a question this time, not stated with an exit.** Round
  three stated it and let them object; they didn't reply, and silence is not
  agreement when the failure mode destroys the board. The no-diode reasoning is
  included so they can tell us the trade was wrong.
- **The USB question is re-asked with an excuse built in.** "You may simply have
  judged it not worth one" costs nothing and makes it easy to answer a question
  that has now been ignored once.
- **The four ours-decisions are marked as needing no reply.** Four items that
  each demand an answer would bury the two that do. Each is stated with its
  reason, so disagreeing is a single sentence for them.
- **R702 is flagged explicitly as a departure.** It is the one place we
  reinterpreted a sentence of theirs rather than following it, and finding that
  out from the schematic would read as us having quietly ignored them.

## Settled, and not raised here

- The per-channel passive chain, verified against the drawing node for node.
- Supply: ±4.5 V from the PD2 down DIN pins 7 and 8, shell as ground, no power
  section of our own. Settled in rounds two and three.
- Headroom: settled on their 2026-08-01 answer. Not reopened.
- Switch sense: closed = pizz, open = arco, rest position arco.
- AGND carries no DC anywhere on the board.
