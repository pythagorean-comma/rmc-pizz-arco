# rmc-pizz-arco

A six-channel phase-switching preamp for RMC pizz/arco piezo pickups, generated
from source rather than drawn by hand.

Each of the six saddles of a viola da gamba bridge holds **two** piezo elements.
This board sums each pair into a single high-impedance output that looks like a
piezo to an RMC Poly-Drive II, and lets a toggle flip the relative polarity of
the two: in phase for picking, out of phase for bowing. It is six copies of
one channel of RMC's own schematic
([`docs/Pizz-Arco-Switching-260729.png`](docs/Pizz-Arco-Switching-260729.png)),
plus the supply and switching that drawing leaves open.

The switch exists because the saddle is quasi-omniplanar but blind to one
direction of string rotation, so no static circuit can give both an omniplanar
response and a symmetric attack. [`DESIGN.md`](DESIGN.md) opens with RMC's own
account of it.

The bridge these pickups sit in is a separate project:
<https://github.com/pythagorean-comma/violet-bridge>.

## Everything is generated

`design.py` is the single source of truth for the circuit. `gen_sch.py` draws
the schematic from it, `gen_pcb.py` places and routes the board from it, and
`verify.py` reads KiCad's own netlist back and compares it net by net.

```bash
./build.sh
```

That regenerates schematic *and* board, runs ERC, checks both against
`design.py`, runs DRC, and writes `fab/rmc-pizz-arco-pcbway.zip`, but **only
when DRC is clean**, so a board with known faults cannot reach a fab by
accident.

> **Anything changed in the KiCad GUI is destroyed by the next build.** Use the
> editor to inspect, measure and try things out; changes that should survive
> belong in the generator.

## Requirements

**KiCad 10.x.** Install with `brew install --cask kicad`, or from
<https://www.kicad.org/download/>. The file formats written are version
specific: KiCad 9 will not open the generated schematic.

**No Python packages.** There is no virtual environment and no
`requirements.txt`, because there is nothing to install: the generators are
pure standard library. The one exception is `pcbnew`, which ships inside KiCad,
so `build.sh` runs `gen_pcb.py` under KiCad's own bundled interpreter and
everything else under `python3`. Set `PYTHON` to override which one.

`kicad.py` finds the installation. It checks `$KICAD_APP`, then
`/Applications/KiCad/KiCad.app`, then `~/Applications/KiCad/KiCad.app`, then
`kicad-cli` on `PATH`. If yours lives somewhere else:

```bash
export KICAD_APP=/path/to/KiCad.app
```

Run `python3 kicad.py` to see what it found.

## Where to read next

| | |
| --- | --- |
| [`DESIGN.md`](DESIGN.md) | What the circuit does and why, what must not be got wrong when wiring it, how the board came out, and what is still open with RMC. **Start here.** |
| [`fab/ORDER.md`](fab/ORDER.md) | How to order it, including the four requirements that are invisible in the gerbers and the BOM. |
| [`ENCLOSURE.md`](ENCLOSURE.md) | The tail-mounted housing study. Mounting and the loom are settled in principle; the box is not yet designed. |

## Status

Placed, routed and **DRC-clean** at 77.2 × 82.4 mm: 47 nets, 233 pin
connections, 80 placements, 0 violations, 0 unconnected items. Nothing has been
fabricated.

This is **rev D**, which is RMC's rev.3: it answers their layout review of
2026-08-01 and its addendum — the V− plane moved onto In2, the four bypass
capacitors became ten, every design rule widened, the all-pass feedback pair
moved up against the op-amp, and the buffer's 1 kΩ deleted. Two questions are still
awaiting reply and one of them blocks ordering; both are listed in
[`DESIGN.md`](DESIGN.md).
