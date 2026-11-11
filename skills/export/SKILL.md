---
name: kicad-export
description: Generate deterministic KiCad ERC, DRC, fabrication, assembly, documentation, and 3D export outputs with kicad-cli.
---

Run KiCad's CLI as plain `kicad-cli`. In Backplane that is the KiCad Backplane has selected: it is first on your PATH, and `$BACKPLANE_KICAD_CLI` names the same program. Never call a kicad-cli by another install's path (a stock `/usr/bin` or `~/.local/bin` one, a macOS KiCad.app, an old Backplane folder): its version and export behaviour differ. Check which KiCad you have with `kicad-cli version` before the first export.

Using kicad-cli, parse this documentation and use the necessary items to generate ERC/DRC reports, then proceed to create GERBERs, drill files, position files, and BOM files depending on the user's manufacturer. To make this deterministic, store your order of commands in a Python or bash script and modify it per-project.

JLCPCB and NextPCB require a specific format for their position files:
A .csv file with 5 columns: Designator, Mid X, Mid Y, Layer (T or B) and rotation
KiCad does not permit this, so please use the Python script under scripts/convert_position.py to do this. If the user does not have Python installed please inform them before making changes to their computer, unless they have already specified to use a virtual environment or you see one at the root of the project where this skill is being called.

JLCPCB BOMs also require an LCSC part number. Ensure that the JLCPCB BOM preset is available and if not inform the user that this needs to be added. 

Determine which PCB and scheamtic output commands you need to use (documentation is available under the references/ directory under this skill). For example, we often use this set of commands:

  kicad-cli version

  kicad-cli sch erc \
    --output build/<project>-erc.rpt \
    --format report --units mm \
    --severity-warning --severity-error \
    --exit-code-violations <project>.kicad_sch

  kicad-cli pcb drc \
    --output build/<project>-drc.rpt \
    --format report --units mm \
    --severity-warning --severity-error \
    --refill-zones --schematic-parity \
    --exit-code-violations <project>.kicad_pcb

  kicad-cli sch export pdf \
    --output build/schematic.pdf \
    [--variant <name>] [--theme <theme>] \
    <project>.kicad_sch

  kicad-cli sch export bom \
    --preset JLCPCB --format-preset CSV \
    --output build/bom_JLCPCB.csv \
    [--variant <name>] <project>.kicad_sch

  kicad-cli sch export bom \
    --preset NextPCB --format-preset CSV \
    --output build/bom_NextPCB.csv \
    [--variant <name>] <project>.kicad_sch

  kicad-cli sch export netlist \
    --format kicadxml \
    --output build/llm-review/netlist.xml \
    [--variant <name>] <project>.kicad_sch

  kicad-cli sch export netlist \
    --format kicadsexpr \
    --output build/llm-review/netlist.kicadsexpr \
    [--variant <name>] <project>.kicad_sch

  kicad-cli sch export bom \
    --output build/llm-review/components.csv \
    --fields Reference,Value,Footprint,Datasheet,DNP,EXCLUDE_FROM_BOM,EXCLUDE_FROM_BOARD \
    --labels Reference,Value,Footprint,Datasheet,DNP,ExcludeFromBOM,ExcludeFromBoard \
    --sort-field Reference \
    [--variant <name>] <project>.kicad_sch

  kicad-cli pcb export gerbers \
    --output build/gerbs \
    --layers <detected-layer-list> \
    --crossout-DNP-footprints-on-fab-layers \
    --sketch-DNP-footprints-on-fab-layers \
    --subtract-soldermask \
    --precision 5 <project>.kicad_pcb

  kicad-cli pcb export drill \
    --output build/gerbs \
    --format excellon \
    --drill-origin absolute \
    --excellon-units in \
    --excellon-zeros-format decimal \
    --gerber-precision 5 <project>.kicad_pcb

  kicad-cli pcb export pos \
    --output build/positions_raw.csv \
    --format csv --units mm \
    --side both --exclude-dnp \
    --use-drill-file-origin <project>.kicad_pcb

  kicad-cli pcb export pdf \
    --output build/pcb_layout \
    --layers <detected-layer-list> \
    --black-and-white \
    --crossout-DNP-footprints-on-fab-layers \
    --sketch-DNP-footprints-on-fab-layers \
    --include-border-title \
    --drill-shape-opt 2 \
    --mode-multipage <project>.kicad_pcb

  kicad-cli pcb export step \
    --output build/board.step \
    --force --subst-models --no-dnp \
    <project>.kicad_pcb

  kicad-cli pcb render \
    --output build/top.png \
    --width 1280 --height 720 \
    --background transparent --quality basic \
    --preset follow_pcb_editor \
    --light-top 0 --light-bottom 0 \
    --light-side 0.5 --light-camera 0 \
    --light-side-elevation 60 \
    --side top <project>.kicad_pcb

  kicad-cli pcb render \
    --output build/bottom.png \
    --width 1280 --height 720 \
    --background transparent --quality basic \
    --preset follow_pcb_editor \
    --light-top 0 --light-bottom 0 \
    --light-side 0.5 --light-camera 0 \
    --light-side-elevation 60 \
    --side bottom <project>.kicad_pcb

Unless otherwise specified by the user, DRC and ERC errors will result in you throwing a FAILURE to export. If there is a FAILURE you can prompt them: "Should we proceed with export? Please reply with OVERRIDE to restart."
