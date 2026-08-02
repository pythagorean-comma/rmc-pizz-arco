# Reply to RMC, 2026-08-01 — covering rev D (their rev.3)

*Answers RMC's layout review of 2026-08-01 and the addendum that followed it.
Sent with `fab/rmc-pizz-arco-pcbway.zip`, `fab/rmc-pizz-arco-layout.pdf` and
`fab/rmc-pizz-arco-schematic.pdf`. The engineering is recorded in
[`DESIGN.md`](../DESIGN.md); this is what was actually said to them, including
the two questions still outstanding.*

---

Thank you — that was a much more useful reply than I had any right to expect, and one sentence in it turned out to matter more than everything else put together. Your addendum arrived while I was still working through the first one, so this covers both.

Attached are the gerbers and drill files for rev.3. On the board it says rev D, which is our own lettering; rev D and your rev.3 are the same thing, and I'll keep saying both until one of us drops one. It is 77.2 x 82.4 mm, four layers, 80 parts, DRC clean, nothing ordered.

**The sentence that mattered**

"Most op amps used for audio applications are V- referenced because many designs operate from a single supply."

We had the two inner layers as ground and V+, and V- as an ordinary 0.25 mm track. So the rail the op-amp actually references was the one we gave the worst treatment to, and the one with better rejection got a whole plane. That is backwards and I would not have found it.

**In2 is now the V- plane.** Every op-amp and switch supply-return pin, the DIN pin 8, R701 and five capacitors reach V- through one via each. V+ is routed instead, as a U on the back layer: down the west margin past the three op-amps, along the bottom, back up the east margin to the switches.

The arithmetic, in case you want to check I have understood you. At 2 mA the DC case was never the problem — 50 mm of 0.25 mm copper is about 0.1 ohm. But that track is roughly 25 nH, and 25 nH against 4.7 uF resonates at about 460 kHz with a Q of five to ten against a ceramic's ESR. So there was a several-ohm peak on the V- rail half a megahertz inside the OPA4191's 10 MHz gain-bandwidth, on the rail its own circuitry references. Never audible. Not the kind of thing that shows up on the first board either, which is why I would rather fix it now.

**Bypassing**

Done as you said: ten 4.7 uF, multilayer ceramic, not electrolytic, in five pairs — one at each op-amp, one between the two CD4066s, one at the supply entry.

Ten rather than four because "distribute them evenly between the 3 IC's" doesn't divide four, and because the pairing has to stay symmetric: the two rails' return currents meet in the DIN shell, which is the same single wire carrying the six string returns, so bypassing one rail harder than the other puts the difference into the audio ground. One V+ and one V- at every location.

One thing I should flag because it looks wrong in the plot. **Both capacitors of each op-amp pair sit west of the package, not one each side.** Pins 4 and 11 are on opposite sides, so one each side is obviously right, and it does not fit. East of each op-amp the centreline is a three-lane bundle at 1.27 mm pitch — the two switched nodes with V- between them — running unbroken from the pads to the buses. There is no 1206-sized hole anywhere in it. West of the package only the buffer-input lanes flank the centreline and they stop at the pad column, which leaves about 8 mm of clear board. That is the only space in the block, and I only found it by measuring rather than assuming.

Which is survivable exactly because of the plane swap: V- doesn't need a local capacitor any more. So the V+ one takes the closer position, 8.2 mm from pin 4, against 45 to 51 mm to the nearest V- capacitor on the board you saw.

**The addendum: the feedback capacitor**

Done, and it was the biggest single change to the channel after the plane swap.

The board you reviewed had the pair in the wrong order as well as too far out — the capacitor was the further of the two:

| | before | now |
| --- | --- | --- |
| C02 (100 pF) to −IN | 11.8 mm | **3.1 mm** |
| R06 (47 k) to −IN | 9.3 mm | 7.6 mm |

C02 is now the first part on the row, its west pad edge 0.80 mm (31.5 mil) from the op-amp's own pads.

**It will not go closer than about 3 mm, and I want to be straight about why.** The strip between the row line and pin 14 is 0.79 mm, and a 1206 sitting at pin-13 height closes to 0.37 mm of the pin-12 lane — 0.03 mm short of my clearance rule. So "adjacent to the IC" bottoms out at one part-width away. If you want it nearer than that it means a smaller package for that one capacitor — 0603 would sit right beside the pin — and that is your call, not mine. Say the word and I'll do it.

What made even 3 mm possible is worth a sentence, because it is the opposite of what the previous layout was built on. With the capacitor first, the inverting input and the all-pass output interleave along the component row, and the old arrangement existed precisely to stop that. So neither of them runs along the row any more: the inverting input runs east on its own pin's lane, between the package and the row, and drops onto each pad it needs — that lane clears a capacitor standing on the row by 1.0 mm, so it passes straight over the top of C02 on its way to the 47 k. The all-pass output can't do the same (its pin lane is the 0.79 mm one) so it dives to the back layer immediately, which it already did.

**The 1 k in the buffer feedback**

Out, in all six channels, and the feedback is a trace.

Your own pinout made this almost free: on the OPA4191 each buffer's output and its inverting input are adjacent pins in the same column, 1.27 mm apart. So the feedback is a single 1.27 mm segment at 0.30 mm (0.0118"), no vias, and it never leaves the package footprint. That is about as little added capacitance at the inverting node as the part allows.

It paid for itself in the layout too. That resistor sat west of the package, which forced both buffer nets to dive between the pad columns, run west under the package on the back layer and surface at its pads — and its own position was dictated by which gaps in the component row were still free. All of that is gone, along with six resistors and six nets. The board lost 6 parts and a good deal of congestion.

**Component spacing**

Checked rather than assumed, pad edge to pad edge across every passive on the board: **the tightest gap anywhere is 0.925 mm, which is 36.4 mil.** No pair is under your 30 mil. The part pitch on the component rows came down from 5.5 mm to 5.0 mm to make room for the feedback pair, and 5.0 was chosen as the round number above the 4.87 mm floor that 30 mil implies for a 1206.

**Trace widths, vias, registration**

All up, on your ±0.003" argument:

| | you saw | now |
| --- | --- | --- |
| signal track | 0.25 mm | 0.30 mm |
| power track | 0.50 mm | 0.80 mm |
| via pad / drill | 0.60 / 0.30 | 0.80 / 0.40 |
| annular ring | 0.15 mm | 0.20 mm |
| clearance | 0.20 mm | 0.25 mm |

0.003" is 0.076 mm. A 0.20 mm ring absorbs the whole of it and still leaves 0.124 mm, against an IPC Class 2 floor of 0.05 mm. The old ring left 0.074 mm — it would have passed, but on the fabricator being better than they promised, which is precisely your point. The drill going to 0.40 takes the aspect ratio through 1.6 mm of board from 5.3:1 to 4:1.

Power and ground vias are doubled where there is room — the ten capacitors and the V+ taps. **Two places I did not double them**, and I would rather tell you than have you find them: not under the SOIC-14 and SO-14 packages, where the pad columns are 3.0 mm apart and the pins 1.27, and not on the two switch supply taps, where a pair closes to 0.195 mm of the pin-13 row. I took that as your "where it is practical to do so", but say if you meant it harder than that.

And a declared shortfall: you said 0.010" clearance and 0.25 mm is 0.0098". Four microns under. I kept the round metric number because the whole layout is on that grid, but you should hear it from me rather than measure it.

One embarrassment worth recording. The helper that runs each rail from a pin out to its spine took no width argument, so every rail tap on the board you reviewed came out at 0.25 mm while the spine it fed was 0.5. That was not a trade-off, just a default nobody passed. It is most of "beef up your Vss traces" in one line.

**Four layers — your question, answered straight**

No. We are not having trouble routing power and ground on two layers. They would route. The board is about 14% land utilisation, deliberately loose, and you are right that at 20 kHz with these rails and 0.010" clearance there is no crosstalk worth the name between neighbouring traces.

The inner layers are not there for routing relief. They are there because every ground and V- pad becomes one via instead of a track — which is what made your own "beef up the power traces" nearly free on two of the three rails — and because I wanted an unbroken reference under the buffer inputs, since we went to SOIC-14 rather than TSSOP specifically so a ground guard ring fits around each one. You are right that the piezo is not high impedance at high frequency; at 100 Hz, though, the element and the 3M3 bias in parallel are about 730 kOhm, and hum and handling noise live down there.

The third reason is honest rather than technical: it is routed on four layers and re-solving it on two is weeks. I would rather say that than dress it up.

**And the concession that goes with it.** Four layers is what caused the V- problem you found. Both inner layers went to ground and V+, which left V- as an ordinary net. A two-layer board with a solid bottom pour might well have given V- better copper than we did. Your two points are the same point, and it isn't flattering to the stackup. This revision answers it by giving the plane to the rail that needed it — but if you still want two layers having seen that, your evidence beats mine and I'll do it.

**The one thing I still need, third time of asking**

Is pin 7 = +4.5 V correct?

I asked in round three and round four and haven't had a yes or a no either time. I am not chasing this to be a nuisance: there is deliberately no reverse-protection diode, because a series Schottky per rail costs about 0.6 dB out of a 9 V supply we haven't got it to spare from, so a loom built backwards puts 9 V backwards across every op-amp on the board. The silkscreen carries the convention and the build procedure has a continuity check before first power-up, but neither of those is you telling me it's right. **I'm not ordering until you do.** A one-word answer is fine, including "no".

**And still open, but not blocking**

The USB socket. If its ground is common with the battery negative — and battery negative is our -4.5 V rail, since the splitter midpoint is signal ground — then an earthed charger plus an earthed mixer shorts the lower half of the supply. Occasional charging unplugged is fine either way. It only bites if the thing is left permanently on USB, it affects your enclosure rather than this board, and you may already isolate the charging circuit. Worth a line when you have one.

**Two offers**

If you want the HF end extended, I can put a 100 nF in parallel with each 4.7 uF. I left it out because once the capacitor is at the pin the few millimetres of trace dominate the loop anyway, and because it doubles the count back towards the eighteen you told me to delete. Easy to add if you disagree.

And as above: a 0603 for the six 100 pF all-pass feedback capacitors would put them right beside the −IN pin instead of 3 mm away. Everything else on the board is 1206 on your own advice about passing two tracks between a part's terminals, which is why I haven't done it unasked — but those six don't have anything routed between their pads, so they are the one place the argument doesn't apply.

Gerbers, drill and a layout PDF attached. Thank you again for the review — it changed the board.
