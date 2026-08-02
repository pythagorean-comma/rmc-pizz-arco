# Rev.3 decision memo: what RMC's review costs and buys

Written before touching the generators, so the reasoning survives the change
rather than being reconstructed from it afterwards. Nothing is ordered and
nothing is committed; every decision below is still reversible.

> **This is a point-in-time record, not a description of the board.** It was
> written on 2026-08-01 between RMC's layout review and the work it prompted,
> and the board moved past it in two places. Where they disagree,
> [`DESIGN.md`](../DESIGN.md) is right.
>
> - **§1 held the In2 plane split "in reserve".** It did not stay there. The
>   block turned out to have no room for a bypass pair beside each op-amp, and
>   the answer was to give In2 to V− outright and route V+ instead. That is the
>   substance of the revision; see *The plane swap* in `DESIGN.md`.
> - **§5's diagnosis was wrong and has been corrected below.**
> - **RMC's addendum is not in here at all** — it arrived afterwards, and moved
>   the all-pass feedback pair up against the op-amp and deleted the buffer's
>   1 kΩ.

---

## 0. What RMC actually said, sorted

Their reply has five distinct instructions and one question. It is worth
separating them, because they are not equally binding and two of them turn out
to be the same observation.

| # | Their point | Status |
| --- | --- | --- |
| 1 | Move the bypass caps to the ICs, distribute them, add a pair between the 4066s, use MLC not electrolytic | **An answer to our question.** Binding. |
| 2 | Beef up the Vcc/Vdd/Vss traces | Binding, and cheaper than it sounds |
| 3 | Bigger via pads and drills, double vias on layer changes, design against ±0.003" registration | Unasked-for and correct |
| 4 | Op-amps are V− referenced; check TI's guidance | **The reason point 1 matters.** Not a separate instruction |
| 5 | Why 4 layers? Are you having trouble routing power and ground on two? | A question we owe a straight answer to |

**Points 1, 4 and 5 are one observation, not three.** RMC has noticed that the
important supply rail on this board is the one we gave the worst treatment to,
and has arrived at it twice by different routes: once from the op-amp's internal
topology, once from looking at the stackup and asking why two inner layers went
to AGND and V+ while V− was left as a 0.25 mm track. That is the substance of
the review. Everything else is good practice.

**And two things they did not say.** They did not answer the polarity question
(pin 7 = +4.5 V) and they did not answer the USB socket question. Polarity has
now gone two rounds unanswered. See §6.

---

## 1. The V− decoupling, with the arithmetic

### What is wrong today

Four 4.7 µF capacitors in a column on the right-hand edge. The three op-amps are
in a column on the far left. Measured from the placed footprints:

| | Nearest V− capacitor |
| --- | --- |
| U1 | C902, 45.0 mm |
| U2 | C902, **51.5 mm** |
| U3 | C904, 45.4 mm |

V+ does not have this problem, because In2 is a solid V+ plane and every V+ pin
reaches it through one via. V− has no plane, so those distances are real track.

### Why it is not a DC problem

A 0.25 mm track in 1 oz copper is 0.00875 mm² in section. Over 50 mm that is
about **0.1 Ω**. The whole board draws ~2 mA. So the DC drop is ~0.2 mV and the
audio-band impedance is negligible. Anyone reasoning only about current — which
is what "at about 2 mA it never needed one" amounted to — concludes correctly
that the copper is sufficient.

### Why it is a problem anyway

The same track is about **20–25 nH** of series inductance. That inductance and
the 4.7 µF at the far end of it form a series resonant circuit:

    f = 1 / (2π√(LC)) = 1 / (2π√(25 nH × 4.7 µF)) ≈ 460 kHz

with a Q, against the few tens of milliohms of ESR an MLCC contributes, of
**roughly 5–10**. So the V− rail as seen from U2's pin 11 has an impedance peak
of several ohms at around half a megahertz.

The OPA4191 has a 10 MHz gain-bandwidth product. That resonance sits well inside
its loop bandwidth, on the rail its internal circuitry references. This is not
an audio-band effect and it will not show up as a frequency-response error; it
shows up, if it shows up at all, as reduced phase margin, as a susceptibility to
the CD4066's switching edges when the toggle is thrown, and as the kind of fault
that appears on one board in ten and cannot be found afterwards.

**This is what RMC's point 4 is about.** "Most op amps used for audio
applications are V− referenced" is the statement that the negative rail is the
one whose PSRR is worst and whose local impedance therefore matters most. We had
it backwards: V+ got a whole plane, V− got a track.

### The fix, and why ten capacitors

A symmetric pair at each package plus a pair at the connector:

| Refs | Location | Purpose |
| --- | --- | --- |
| C901 / C902 | J7, the DIN entry | Terminates the supply cable's inductance where it arrives |
| C911 / C912 | U1 | Local |
| C921 / C922 | U2 | Local |
| C931 / C932 | U3 | Local |
| C941 / C942 | Between U4 and U5 | RMC's explicit request |

Ten, against RMC's implied six. The difference is that RMC said "distribute them
evenly between the 3 IC's" while there are four capacitors, which does not
divide; a pair per package is the nearest thing that both honours "as close as
possible to the op amps" and keeps every location symmetric.

**Symmetry is not cosmetic here.** `_GROUND_RULE` forbids asymmetric bypassing,
because the Poly-Drive's ground is the midpoint of a transistor rail splitter and
reaches us down the DIN shell — the same single conductor carrying the six string
returns. Any imbalance between the two rails' drains flows in that one wire, into
the audio ground. One V+ cap and one V− cap at every location, always.

With the caps at the pins, the loop inductance falls from ~25 nH to ~2 nH, and
the resonance moves to about 1.6 MHz with far less to excite it.

### What we are not doing

**No 100 nF in parallel.** A 1206 X7R 4.7 µF is inductive above roughly 2–3 MHz,
and a parallel 100 nF would extend that to ~15 MHz. The argument against is that
once the capacitor is at the pin, the few millimetres of trace between them
dominates the loop anyway, so the second capacitor buys much less than its
datasheet SRF suggests. It also doubles the count, back towards the eighteen
capacitors RMC told us to delete. Available if they want it; not proposed.

**Not splitting the In2 plane.** The clean structural fix is to make V− a plane
region rather than a net: pin 4 (V+) and pin 11 (V−) sit at (−2.475, 0) and
(+2.475, 0) on every SOIC-14, exactly opposite on the package centreline, so a
vertical split of In2 would give each rail solid copper under the pins that use
it. It is the better answer to RMC's point 5 and it is a bigger change than the
one RMC actually asked for. **Held in reserve**: if they push back on 4 layers,
this is the counter-proposal, because it turns the second inner layer from a
luxury into the thing that fixes their complaint.

---

## 2. The layer count: the honest answer

RMC asks a direct question — *"Are you having problems routing Power & Ground on
the top & bottom layers?"* — and the honest answer is **no**.

That needs saying plainly, because the temptation is to imply otherwise. Power
and ground would route on two layers. The board is 14% land utilisation, the
whole thing is deliberately loose, and RMC is right that at 20 kHz with ±4.5 V
rails and 0.010" clearance there is no meaningful same-layer crosstalk.

The actual reasons are three, in descending order of honesty:

1. **Every rail pad reaches its rail through one via rather than a track.** This
   is what makes RMC's own point 2 — beef up the power traces — nearly free on
   V+ and AGND. Two-thirds of the power distribution on this board is already as
   good as it can get, precisely because it is planes.
2. **An unbroken reference under the buffer inputs.** SOIC-14 was chosen over
   TSSOP-14 specifically so an AGND guard ring fits around each buffer's +
   input; a guard ring wants something to reference. RMC is right that the piezo
   source is not high-impedance at high frequency — the element is 1700 pF, so
   4.7 kΩ at 20 kHz — but at 100 Hz the element and the 3M3 bias in parallel are
   about 730 kΩ, and hum and handling noise live down there, not at 20 kHz.
3. **The routing is solved on four layers and re-solving it on two is weeks.**
   This is a schedule argument, not an engineering one, and should be labelled
   as such rather than dressed up.

**The cost**: roughly $20–30 more on a five-off prototype order (an estimate, not
a quote), plus a standing hazard — order forms default to 2 layers, and a
2-layer build of these gerbers silently drops both planes and yields a board with
no ground and no V+. `fab/ORDER.md` already carries that warning in bold.

**And the concession that should go to RMC rather than be hidden**: four layers
is what *caused* the V− problem they found. Both inner layers went to AGND and
V+, leaving V− as an ordinary net, and a 2-layer board with a solid bottom pour
might well have given V− better copper than we did. Their two points connect, and
the connection is not flattering to the stackup. Say so.

**Decision: keep 4 layers**, answer the question straight, offer the split-plane
option, and invite them to overrule it. The evidence would have to be theirs, not
ours — they have built more of these than we have.

---

## 3. Manufacturability: the ±0.003" arithmetic

RMC asks for the layout to absorb about ±0.003" of cumulative drill and layer
registration error. 0.003" = 0.076 mm.

| | Today | Rev.3 | |
| --- | --- | --- | --- |
| Via pad | 0.60 mm | **0.80 mm** | |
| Via drill | 0.30 mm | **0.40 mm** | |
| Annular ring | 0.150 mm | **0.200 mm** | |
| Ring remaining after ±0.003" | 0.074 mm | **0.124 mm** | IPC Class 2 floor is 0.05 mm |
| Aspect ratio (1.6 mm board) | 5.3 : 1 | **4.0 : 1** | RMC's "plating problems" point |
| Signal track | 0.25 mm | **0.30 mm** | |
| Power track | 0.50 mm | **0.80 mm** | |
| Clearance | 0.20 mm | **0.25 mm** | |

Today's board passes IPC Class 2 after full misregistration with 24 µm to spare.
Rev.3 passes with 124 µm — two and a half times the floor. That is the difference
between "should be fine" and RMC's "you can expect a good board from just about
any p.c.b. contractor", which is the actual goal.

**One quibble to declare rather than bury**: RMC said 0.010" clearance and
0.25 mm is 0.0098". Four microns short. The metric grid the whole layout is built
on is worth more than the 1.6%, but they should hear it from us.

### Double vias

RMC: "go with double vias for connecting Power & Ground traces on different
layers", qualified with "where it is practical to do so". Applied to AGND, V+ and
V− everywhere there is room — the 1206 passive stubs, the V− spine's layer
changes, the SW_CTL riser. Roughly 148 vias becomes roughly 200.

**Not applied under the SOIC-14 and SO-14 packages.** Those stubs sit in the
1.27 mm-pitch gap between the two pad columns, at ±0.9 mm from the centreline,
with the inner pad edges at ±1.775 mm. An 0.8 mm via there leaves 0.475 mm to the
pad — fine for one via, no room for two. This is RMC's own qualifier and should
be reported to them as a place we stopped, not silently skipped.

### The one that is free and was missed

`route_supply()`'s `tap()` helper passes no width, so **every V− tap on the board
is currently 0.25 mm**, not the 0.5 mm `POWER_TRACK` the design intends. Widening
those to 0.8 mm is most of RMC's "beef up your Vss traces" in a one-line change,
and it was never a decision — just a default argument nobody noticed.

---

## 4. What the sweep will cost

The rule widening is the only unbounded item. The lane geometry in `gen_pcb.py`
is hand-computed against 0.6 mm vias and 0.2 mm clearance, and the project's own
notes record five passes to take DRC from 316 violations to 5 last time.

Expected to break, in order:

- The OUT bus at 0.6 mm pitch and the SWN bus at 0.7 mm. A lane ending in an
  0.8 mm via now needs ~0.75 mm to its neighbour. The corridor widens and the
  board grows a few mm in x.
- The band lanes at 0.65 mm pitch survive 0.30 track + 0.25 clearance
  (0.55 mm needed) — but only just.
- The geometry around the switch packages, once V− taps go from 0.25 to 0.80 mm.

**Fallback if it stalls**: 0.7/0.35 vias and 0.25 mm track retained. That still
leaves 0.099 mm of ring after full misregistration — twice the IPC floor — and
disturbs the existing routing far less. It concedes the trace-width half of
RMC's advice and keeps the registration half, which is the half that carries the
argument.

---

## 5. A finding from reading the build, unrelated to RMC

**The committed `.kicad_pro` is not the generated one.** `gen_project.py` writes
a `Power` netclass at 0.5 mm and assigns V+, V− and AGND to it. The file at
`HEAD` has only `Default`, an empty `netclass_patterns`, empty preset lists, and
KiCad's stock constraint floors (`min_via_annular_width` 0.1 rather than the 0.13
we specify).

> **Corrected after the fact.** The two paragraphs that followed here blamed
> first `kicad-cli` and then the KiCad GUI, and both were wrong. Testing each
> step in turn settled it: **`gen_pcb.py` is the cause.** `pcbnew.SaveBoard()`
> writes the `.kicad_pro` as well as the board, through KiCad's settings
> manager, and what it writes is KiCad's defaults.
>
> That makes the finding worse than this memo concluded, not narrower.
> `build.sh` ran `gen_project.py` *before* `gen_pcb.py`, so the board generator
> reverted the rules on every run before DRC ever saw them: **every DRC result
> in this project's history before rev C was checked against KiCad's defaults**
> — 0.20 mm clearance, 0.10 mm annular ring, no `Power` net class — rather than
> against the rules the layout was drawn to. The moment it was fixed, DRC found
> six real violations that had been invisible.
>
> The fix is a second `gen_project.py` run after the board, plus
> `verify.check_project_rules()` reading the file back. Both are in place.

The evidence, kept because the reasoning is still worth following: the committed
file carries `3dviewports`, `ipc2581`, `layer_pairs`, `layer_presets` and a
36-key `defaults` block that `gen_project.py` never writes, which is what pointed
at an editor session rather than the generator. Each `kicad-cli` command was
tested individually — `pcb drc`, `sch erc`, `sch export netlist`, `sch export
pdf` — and every one leaves the `Power` class and the three patterns intact,
which correctly ruled out the CLI. What the test missed was that `pcbnew` writes
project settings too.

Worth fixing before the sweep, because the sweep's whole value is that the rules
are enforced. `verify.py` should read the on-disk project file back and assert
the netclasses and constraint floors are the generated ones — the same
read-back-and-compare discipline it already applies to the netlist. It does not
need to go to RMC: it is our tooling, not their design.

---

## 6. What RMC did not answer

**Polarity — pin 7 = +4.5 V.** Asked in round three, asked again in round four,
not answered either time. There is deliberately no reverse-protection diode (a
series Schottky per rail costs ~0.6 dB out of a 9 V total supply, which this
design has not got), so a loom built backwards destroys every op-amp on the
board. The convention is on the silkscreen and in `fab/ORDER.md`, and the build
procedure calls for a continuity check before first power-up, but procedure is
not confirmation. **This is the one item that should block ordering.**

**The USB socket.** If the socket's ground is common with battery negative — and
battery negative *is* the −4.5 V rail, because the splitter's midpoint is signal
ground — then an earthed charger plus an earthed mixer shorts the lower half of
the supply. It affects their enclosure rather than this board, and they may
already isolate the charging circuit. Worth re-asking briefly; not blocking.

---

## Summary of decisions

| | Decision |
| --- | --- |
| Bypassing | Ten 4.7 µF X7R MLCC, symmetric pairs at U1, U2, U3, between U4/U5, and at J7 |
| Parallel 100 nF | No. Offered if RMC wants it |
| Layers | Keep 4. Answer their question straight; offer the In2 split as the counter-proposal |
| Vias | 0.80/0.40, doubled on power and ground except under the 1.27 mm-pitch packages |
| Tracks | 0.30 signal, 0.80 power; fix the V− taps that were silently 0.25 |
| Clearance | 0.25 mm, and tell them it is 0.0098" not 0.010" |
| Reverse protection | Unchanged — still none, still a deliberate trade |
| Inside the channel | Untouched |
| Blocking on RMC | Polarity confirmation, third time of asking |
