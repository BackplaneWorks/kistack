---
name: kicad-pcb
description: Review KiCad PCB layouts with DRC, layer renders, and 3D-model interference inspection.
---

Run KiCad's CLI as plain `kicad-cli` (in Backplane, the KiCad Backplane has selected, first on your PATH; `$BACKPLANE_KICAD_CLI` is the same program), never by another install's path.

# Skill for PCB design and review

## Editing the active board in place

For normal placement, routing, and cleanup work, first identify the project's canonical configured `.kicad_pcb` path—the board opened by the project or viewer—and keep using that exact path. Save each meaningful milestone to it so the active board and collaborators show progress. Keep backups and intermediate tool outputs in a separate backup or build directory. If a tool writes a staging or alternate file, validate it and promote the result back to the canonical path with a backup before continuing; do not silently switch the active filename. Use an alternate board only when the user explicitly requests an experiment or alternate design, and label it clearly. Coordinate ownership so only one agent or process writes the active board at a time; other agents may inspect it or prepare changes for integration.

## Placement

Place components like decoupling capacitors in orientations and locations that minimize loop area for ground and minimize trace length for inductance. If packages do not fit, consult the engineer to confirm that their recommended size per the schematic may need to change.

Your goal is to optimize placement of components, that is paramount. Good placement brings good routing. 

Review placement by carefully thinking about the actual size of the component, its relation to the other packages. Keep things neatly aligned. Consult the engineer before proceeding with double-sided designs, unless this is explicitly stated. You can render images of specific areas of the PCB or render SVGs from GERBERs with the $kicad-gerbers skill to review this. kicad-monkey also has some capabilities here to allow you to parse the schematic more easily.

You are unlikely to one-shot perfect placement, so do not spend time over-optimizing. Place parts in reasonable locations so that it is easier for the engineer to modify them.

Board outlines should have rounded or chamfered corners, confirm with the engineer. 

Connectors that are horizontal should be placed near board edges as a rule. Vertical connectors may be placed in various locations depending on the engineer's requirements.

## Review

Confirm with kicad-cli that DRC rules pass. 

Use kicad-cli to render SVGs of board layers to validate that their connections look reasonable.

Use kicad-cli to render images of various areas of the PCB to validate interference with 3D models.
