---
name: kicad-gerbers
description: Generate, render, and visually review KiCad Gerber layers as a fabrication-output inspection step.
---

Run KiCad's CLI as plain `kicad-cli` (in Backplane, the KiCad Backplane has selected, first on your PATH; `$BACKPLANE_KICAD_CLI` is the same program), never by another install's path.

# This skill allows an LLM to review generated GERBER files for production of a PCB.

If no generated GERBERs exist, please request for the user to generate them or generate them yourself for the purpose of review only, in a separate directory.

Generate GERBERs per layer with kicad-cli and then use pygerber in a venv to view them, rendered as images. uv pip install pygerber

For example: 

'''To convert a Gerber file to PNG, use the pygerber gerber convert png command. For example, following command converts source.gbr (a copper layer) to a PNG at 600 DPMM resolution:

pygerber gerber convert png source.gbr -o output.png -d 600 -s copper_alpha'''

Ensure that their are no unexpected shorts, that vias do not intersect, and that overall the board appears to be fabricatable. 
