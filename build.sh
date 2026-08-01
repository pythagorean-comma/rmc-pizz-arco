#!/bin/bash
# Regenerate the whole project from design.py and check it.
#
# The schematic writer is plain Python; the board needs KiCad's own bundled
# interpreter for pcbnew, which is why the two are kept apart below.
set -euo pipefail
cd "$(dirname "$0")"

# Everything except gen_pcb.py is pure standard library -- there is no venv and
# no requirements.txt, because there is nothing to install. Any Python 3 will
# do; the only real dependency of this repository is KiCad itself.
PY="${PYTHON:-python3}"
if ! command -v "$PY" >/dev/null 2>&1; then
    echo "no '$PY' on PATH. Set PYTHON to a Python 3 interpreter." >&2
    exit 1
fi

# Where KiCad lives is decided in one place, by kicad.py. Set KICAD_APP to
# override. Doing the lookup up front means a missing install is reported
# before anything is generated, with instructions rather than a path error.
if ! "$PY" kicad.py >/dev/null 2>&1; then
    "$PY" kicad.py || true
    exit 1
fi
KICAD_PY="$("$PY" kicad.py python)"
KICAD_CLI="$("$PY" kicad.py cli)"
export KICAD10_SYMBOL_DIR="$("$PY" kicad.py symbols)"
export KICAD10_FOOTPRINT_DIR="$("$PY" kicad.py footprints)"
"$PY" -c 'import kicad,sys; w=kicad.check_version(); w and sys.stderr.write(w+"\n")'

if [ -z "$KICAD_PY" ]; then
    echo "This KiCad has no bundled Python, so pcbnew is not available to" >&2
    echo "gen_pcb.py. On Linux, install the system python3-pcbnew package" >&2
    echo "and run gen_pcb.py with the interpreter that provides it." >&2
    exit 1
fi

PROJECT=rmc-pizz-arco/rmc-pizz-arco
mkdir -p build fab

echo "== schematic and project =="
"$PY" gen_sch.py
"$PY" gen_project.py

echo "== board =="
"$KICAD_PY" gen_pcb.py 2>&1 | grep -v "assert" || true

# After the board, not before: this checks the drawing against design.py and
# the board's footprint linkage against the drawing, so both must be current.
echo "== checking the drawing and the board against design.py =="
"$PY" verify.py

echo "== ERC / DRC =="
"$KICAD_CLI" sch erc --severity-error --severity-warning -o build/erc.rpt "$PROJECT.kicad_sch" | tail -1
"$KICAD_CLI" pcb drc --severity-error -o build/drc.rpt "$PROJECT.kicad_pcb" | tail -2
DRC_ERRORS=$(grep -cE '^\[' build/drc.rpt || true)

echo "== documentation outputs =="
"$KICAD_CLI" sch export pdf -o fab/rmc-pizz-arco-schematic.pdf "$PROJECT.kicad_sch" >/dev/null
"$KICAD_CLI" sch export bom --group-by Value,Footprint \
    --fields 'Reference,Value,Footprint,${QUANTITY},Datasheet' \
    -o fab/rmc-pizz-arco-bom.csv "$PROJECT.kicad_sch" >/dev/null
"$KICAD_CLI" pcb export pos --format csv --units mm \
    -o fab/rmc-pizz-arco-pos.csv "$PROJECT.kicad_pcb" >/dev/null
# The layout asset a reviewer can actually comment on. One page per copper
# layer, each carrying the board outline and the reference designators, so every
# page is a drawing you can read on its own. Splitting the designators onto a
# page of their own was tried and is worse: it leaves every other page unable to
# tell you what you are looking at.
#
# Three settings here are all load-bearing, and each fixes something that made
# earlier versions unreadable.
#
# --bg-color: without it KiCad paints no page background at all, so the PDF is
# transparent and renders on whatever the viewer puts behind it -- white in one
# reader, black in another, which turned dark plots invisible.
#
# --theme: left alone the colours come from whatever theme the local PCB editor
# is set to, so the same board plots differently on another machine. "KiCad
# Classic" is built in, so it is identical everywhere, and it is the one that
# plots silkscreen dark enough to read on white -- 4.5:1, against 1.2:1 for the
# default theme, which is why the designators used to vanish.
#
# Not --black-and-white. It looks like the safe choice and is the worst one:
# designators become the same ink as the pads under them, and the two plane
# layers turn into solid black sheets carrying nothing.
#
# Each copper layer comes out a different colour, and that means nothing here.
# A theme colours the layers apart because the PCB editor draws them stacked;
# with one layer per page the page already says which layer it is. The cost is
# that the same silkscreen colour meets a different background on every page,
# which is why the V+ plane reads worst. Levelling it needs a theme file of our
# own -- --theme takes a name resolved against built-ins and the user's KiCad
# colors directory, never a path -- so it means either shipping a theme and
# redirecting KICAD_CONFIG_HOME, or writing into the user's KiCad config.
# Considered and declined: not worth either for a document that is already
# legible.
#
# No border or title block: autoscale sizes the board to the whole sheet, so the
# title block lands across the bottom-right corner -- over the silkscreen line
# warning there is no reverse protection, the last text here worth obscuring.
#
# The designators are 1 mm on an 81 mm board, so they are small at fit-to-page.
# It is vector and stays sharp; this is a document to zoom into.
"$KICAD_CLI" pcb export pdf --mode-multipage \
    --theme "KiCad Classic" --bg-color "#FFFFFF" \
    --layers F.Cu,In1.Cu,In2.Cu,B.Cu \
    --common-layers Edge.Cuts,F.SilkS --scale 0 \
    -o fab/rmc-pizz-arco-layout.pdf "$PROJECT.kicad_pcb" >/dev/null
# Decorative, and the one artefact that reads at a glance to someone who has not
# opened a CAD tool. Deliberately not --quality high: the raytracer samples
# stochastically, so it returns a different file byte for byte on every run even
# from an identical board, and this is a 1.4 MB binary in a tracked directory.
# `basic` is reproducible to the byte, a fifth the size, and loses only the soft
# shadows -- which nothing here is asking the render to show.
"$KICAD_CLI" pcb render --side top --quality basic --background opaque \
    --width 2400 --height 2400 \
    -o fab/rmc-pizz-arco-top.png "$PROJECT.kicad_pcb" >/dev/null

# The set a fab actually gets: copper, mask, silk, outline, drill -- and
# nothing else. A blanket export also writes Fab, Courtyard and User layers,
# and F.Fab carries a second closed board outline; if CAM picks that one up
# instead of Edge.Cuts the board comes back the wrong shape.
echo "== fab package =="
if [ "$DRC_ERRORS" -ne 0 ]; then
    rm -f fab/rmc-pizz-arco-pcbway.zip
    echo "SKIPPED: $DRC_ERRORS DRC error(s) outstanding -- see build/drc.rpt."
    echo "No fabrication package is written while the board has known errors."
    exit 0
fi
rm -rf fab/pcbway
"$KICAD_CLI" pcb export gerbers \
    --layers F.Cu,In1.Cu,In2.Cu,B.Cu,F.Mask,B.Mask,F.SilkS,B.SilkS,Edge.Cuts \
    -o fab/pcbway/ "$PROJECT.kicad_pcb" >/dev/null
# Omitting --excellon-separate-th gives one combined PTH/NPTH file, which is
# what fabs expect; it is a bare flag, not a key=value.
"$KICAD_CLI" pcb export drill --format excellon \
    -o fab/pcbway/ "$PROJECT.kicad_pcb" >/dev/null
cp fab/ORDER.md fab/pcbway/
(cd fab/pcbway && zip -q -r ../rmc-pizz-arco-pcbway.zip .)
echo "wrote fab/rmc-pizz-arco-pcbway.zip -- upload this, and see fab/ORDER.md"
