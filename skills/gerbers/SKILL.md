---
name: kicad-gerbers
description: Generate, render, and visually review KiCad Gerber layers as a fabrication-output inspection step.
---

Run KiCad's CLI as plain `kicad-cli` (in Backplane, the KiCad Backplane has selected, first on your PATH; `$BACKPLANE_KICAD_CLI` is the same program), never by another install's path.

# This skill allows an LLM to review generated GERBER files for production of a PCB.

If no generated GERBERs exist, please request for the user to generate them or generate them yourself for the purpose of review only, in a separate directory.

Generate GERBERs per layer with kicad-cli and then use pygerber in a venv to view them, rendered as images. Requires pygerber >= 2.0 - 1.x ships a different, specfile-driven CLI without this command. uv pip install pygerber

    uv venv .venv-gerber --python 3.12
    uv pip install --python .venv-gerber/Scripts/python.exe pygerber    # Linux/macOS: .venv-gerber/bin/python
    pygerber raster-2d source.gbr -o output.png --dpi 600 -s copper_alpha

`--dpi` is dots per *inch*, not per mm: a 65 mm board renders ~1535 px wide at 600 dpi. Use 600-1000 dpi so 0.1 mm outline lines stay visible, and expect harmless "Drawing zero surface circle" warnings on layers with tiny flashes. Render at least Edge_Cuts, F_Cu and B_Cu; keep the renders next to the documentation as evidence of the review.

Review checklist:

- outline: the profile is closed, and every corner arc is the *minor* arc. A G02/G03 sweep of 270 deg curls into the board and encloses whatever sits near the corner - KiCad's DRC does not flag it, and it has shipped to a fab before.
- copper: every connector and footprint field is present where the layout expects it, pours are contiguous, no unexpected shorts, vias do not intersect foreign copper.
- keepouts: mounting holes and board-edge clearances are actually clear.
- keep the renders with the project; re-run the review after any routing change.
