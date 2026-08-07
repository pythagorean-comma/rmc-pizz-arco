"""Write the KiCad project scaffolding around the generated schematic.

Produces the .kicad_pro (design rules and net classes), the symbol and
footprint library tables, and the one-symbol project library that holds
OPA2191 -- which KiCad does not ship.

Library paths go through KiCad's own ${KICAD10_*_DIR} variables rather than
absolute paths, so the project opens on any machine with KiCad 10 installed.
"""

import json
import pathlib

import design as circuit
import gen_sim
import rules
import symlib
from kisch import Schematic, _uuid
from sexp import Sym, dumps

PROJECT = circuit.PROJECT

# Every symbol either sheet in this project places. The simulation sheet uses
# stock libraries the board has no need of (Simulation_SPICE's sources and its
# node-0 ground) and borrows a single-amplifier body the board does not carry,
# and both have to reach the library table and the project library or the sheet
# opens with broken links.
#
# Nothing in the build catches that: kisch embeds its own copy of every symbol
# in lib_symbols, so ERC passes, verify.py passes, and the fault appears only
# when a human opens the project -- which is why it is DESIGN.md's first
# "check the build cannot make". The sibling project has exactly this omission.
SYMBOLS = {**circuit.LIBS, **gen_sim.SIM_LIBS}

# 4-layer, 1 oz outer / 0.5 oz inner, comfortably inside every low-cost fab's
# capability (JLCPCB and PCBWay both accept 0.127mm; this leaves a wide
# margin). The numbers themselves live in rules.py, because gen_pcb.py lays
# copper against the same ones and the two must not drift.
TRACK_WIDTH = rules.TRACK
POWER_TRACK_WIDTH = rules.POWER_TRACK
CLEARANCE = rules.CLEARANCE
VIA_DIAMETER = rules.VIA_DIAMETER
VIA_DRILL = rules.VIA_DRILL


def net_classes():
    default = {
        "bus_width": 12, "clearance": CLEARANCE, "diff_pair_gap": 0.25,
        "diff_pair_via_gap": 0.25, "diff_pair_width": 0.2, "line_style": 0,
        "microvia_diameter": 0.3, "microvia_drill": 0.1, "name": "Default",
        "pcb_color": "rgba(0, 0, 0, 0.000)", "priority": 2147483647,
        "schematic_color": "rgba(0, 0, 0, 0.000)", "track_width": TRACK_WIDTH,
        "via_diameter": VIA_DIAMETER, "via_drill": VIA_DRILL, "wire_width": 6,
    }
    power = dict(default, name="Power", track_width=POWER_TRACK_WIDTH,
                 priority=1, pcb_color="rgba(200, 52, 52, 0.800)")
    return [default, power]


def project_document(root_uuid):
    """The .kicad_pro as a dict.

    Separated from writing it so verify.py can read the file on disk back and
    check it still says what this says. It does not always: opening the
    project in the KiCad GUI rewrites the whole file in KiCad's own expanded
    form, and that rewrite drops `netclass_patterns` and resets the constraint
    floors to KiCad's defaults. A build regenerates it, so builds are never
    affected -- but the rewritten file can be committed, and then anyone who
    runs DRC without building first is checking against different rules from
    the ones the board was laid out to.
    """
    document = {
        "board": {
            "design_settings": {
                "defaults": {
                    "board_outline_line_width": 0.1,
                    "copper_line_width": 0.2,
                    "copper_text_size_h": 1.5, "copper_text_size_v": 1.5,
                    "copper_text_thickness": 0.3,
                    "courtyard_line_width": 0.05,
                    "other_line_width": 0.15,
                    "silk_line_width": 0.12,
                    "silk_text_size_h": 0.8, "silk_text_size_v": 0.8,
                    "silk_text_thickness": 0.12,
                },
                "diff_pair_dimensions": [],
                "drc_exclusions": [],
                "rules": {
                    "allow_blind_buried_vias": False,
                    "allow_microvias": False,
                    "max_error": 0.005,
                    "min_clearance": rules.MIN_CLEARANCE,
                    "min_connection": 0.0,
                    "min_copper_edge_clearance": rules.MIN_COPPER_EDGE_CLEARANCE,
                    "min_hole_clearance": rules.MIN_HOLE_CLEARANCE,
                    "min_hole_to_hole": rules.MIN_HOLE_TO_HOLE,
                    "min_microvia_diameter": 0.2,
                    "min_microvia_drill": 0.1,
                    "min_resolved_spokes": 2,
                    "min_silk_clearance": 0.0,
                    "min_text_height": 0.8,
                    "min_text_thickness": 0.08,
                    "min_through_hole_diameter": rules.MIN_THROUGH_HOLE_DIAMETER,
                    "min_track_width": rules.MIN_TRACK_WIDTH,
                    "min_via_annular_width": rules.MIN_VIA_ANNULAR_WIDTH,
                    "min_via_diameter": rules.MIN_VIA_DIAMETER,
                    "solder_mask_to_copper_clearance": 0.0,
                    "use_height_for_length_calcs": True,
                },
                "track_widths": [0.0, TRACK_WIDTH, POWER_TRACK_WIDTH, 1.0],
                "via_dimensions": [{"diameter": 0.0, "drill": 0.0},
                                   {"diameter": VIA_DIAMETER, "drill": VIA_DRILL}],
                "zones_allow_external_fillets": False,
            },
        },
        "boards": [],
        "cvpcb": {"equivalence_files": []},
        "libraries": {"pinned_footprint_libs": [], "pinned_symbol_libs": []},
        "meta": {"filename": f"{PROJECT}.kicad_pro", "version": 3},
        "net_settings": {
            "classes": net_classes(),
            "meta": {"version": 4},
            # The rails and the audio ground get the wider track class.
            "netclass_patterns": [
                {"netclass": "Power", "pattern": "V+"},
                {"netclass": "Power", "pattern": "V-"},
                {"netclass": "Power", "pattern": "AGND"},
            ],
        },
        "pcbnew": {"last_paths": {}, "page_layout_descr_file": ""},
        "schematic": {"legacy_lib_dir": "", "legacy_lib_list": []},
        "sheets": [[root_uuid, "Root"]],
        "text_variables": {},
    }
    return document


def project_file(path, root_uuid):
    path.write_text(json.dumps(project_document(root_uuid), indent=2) + "\n")


def library_tables(directory):
    """Point at KiCad's stock libraries plus the project's own."""
    used_symbol_libs = sorted({nick for nick, _, _, _ in SYMBOLS.values()
                               if nick != "rmc"})
    rows = [f'  (lib (name "{nick}")(type "KiCad")(uri '
            f'"${{KICAD10_SYMBOL_DIR}}/{nick}.kicad_sym")(options "")(descr ""))'
            for nick in used_symbol_libs]
    rows.append('  (lib (name "rmc")(type "KiCad")(uri '
                '"${KIPRJMOD}/rmc.kicad_sym")(options "")(descr '
                '"Parts not in the stock libraries"))')
    (directory / "sym-lib-table").write_text(
        "(sym_lib_table\n  (version 7)\n" + "\n".join(rows) + "\n)\n")

    footprint_libs = sorted({part.footprint.split(":", 1)[0]
                             for part in circuit.PARTS.values() if part.footprint})
    rows = [f'  (lib (name "{nick}")(type "KiCad")(uri '
            f'"${{KICAD10_FOOTPRINT_DIR}}/{nick}.pretty")(options "")(descr ""))'
            for nick in footprint_libs]
    (directory / "fp-lib-table").write_text(
        "(fp_lib_table\n  (version 7)\n" + "\n".join(rows) + "\n)\n")


def symbol_library(path):
    """The project library: every part borrowed under the `rmc` nickname.

    Driven off SYMBOLS, the same way library_tables() is, so adding a borrowed
    part to either registry is sufficient and the two cannot drift. This used
    to hard-code its single symbol, and nothing in the build would have caught
    the omission: the schematic embeds its own copy of every symbol in
    lib_symbols, so ERC and verify.py both pass and the fault only appears as
    a broken library link when a human opens the project in KiCad.

    Two symbols now: OPA4191 on the fabrication sheet, borrowed from OPA4197xD,
    and OPA4191_SIM on the simulation sheet, borrowed from LM321 because TI's
    macromodel is a single amplifier.
    """
    library = [Sym("kicad_symbol_lib"),
               [Sym("version"), 20251024],
               [Sym("generator"), "violet-bridge"],
               [Sym("generator_version"), "10.0"]]
    for lib_id, (nick, libname, symname, rename) in sorted(SYMBOLS.items()):
        if nick != "rmc":
            continue
        symbol = symlib.flatten(libname, symname, rename=rename)
        library.append(circuit.patch_symbol(lib_id, symbol))
    path.write_text(dumps(library) + "\n")


def main():
    directory = pathlib.Path(__file__).parent / PROJECT
    directory.mkdir(parents=True, exist_ok=True)
    root_uuid = Schematic(PROJECT).uuid
    project_file(directory / f"{PROJECT}.kicad_pro", root_uuid)
    library_tables(directory)
    symbol_library(directory / "rmc.kicad_sym")
    print(f"wrote project scaffolding in {directory}")


if __name__ == "__main__":
    main()
