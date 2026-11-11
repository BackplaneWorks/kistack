---
name: kicad-panelize
description: Use KiKit to panelize a given PCB
---

Run KiCad's CLI as plain `kicad-cli` (in Backplane, the KiCad Backplane has selected, first on your PATH; `$BACKPLANE_KICAD_CLI` is the same program), never by another install's path.

# Skill for PCB panelization 

## Setup
Ensure KiKit is installed with kikit --version

Check this installations resources/panelizePresets/default.json and panelize_ui_sections.py before adding parameters, these are the way, the truth, and the light.

## Usage

- Find the source .kicad_pcb requsted by the user
- Inspect its actual board files, Edge.Cuts, copper layers, pads and components that may interesect board edges to identify items like castellations, edge connectors, antennas, plated edges, etc.
- Resolve grid dimensions, spacing, rotation, tabs, separation, frame, and fabricator limits.
- Position tooling holes and fiducials relative to the panel outline
- Write strict json.
- Generate a versioned panel without overwriting the source in a "build" subdirectory
- Check the generated panel before notifying the user, ensuring that it looks proper from the baord file level as well as in render.

## Preferred starting values

- Board routing gap: 2mm
- Tab width: 3mm
- Mouse-bite drill: 0.5mm
- Mouse-bite spacing: 0.8mm
- Mouse-bite offset: 0mm
- Full frame width: 5mm
- Frame-to-array clearance: 2mm
- Frame break cuts: none
- Exterior frame radius: 2mm
- Interior routing radius: 0.25mm
- Tooling: three 1.5mm holes
- Tooling stencil apertures: enabled
- Fiducials: three, 1mm copper with 1mm openings
- Fiducial paste apertures: disabled

## KiKit behavior

- source.type: "auto" is appropriate for an ordinary single-board file.
- tabs.type: "spacing" places tabs symmetrically and cannot exclude a particular side.
- With fixed tabs:
  - hcount controls tabs projecting from left/right edges.
  - vcount controls tabs projecting from top/bottom edges.
  - A zero count suppresses that pair of directions.

- Use annotation tabs when only selected segments or one side must be excluded.
- Protected tab directions must be derived from each board’s geometry and rotation. Never hardcode “bottom” or “right” as a universal
rule.

- The global mouse-bite cut method processes every generated cut path, including framing.cuts.
- Therefore, framing.cuts: "both" with mouse bites drills break rows through the rails.
- Use framing.cuts: "none" for a continuous frame.
- Tooling and fiducial offsets are measured inward from the panel’s outer edges.
- To center a feature across a 5 mm frame, use a 2.5 mm perpendicular offset.
- Tooling holes and fiducials with identical counts and offsets overlap. Separate them along the rail.
- paste: true means the feature gets an aperture on the stencil paste layers. It does not control whether a drilled hole is visible.
- framing.fillet rounds exterior panel corners.
- post.millradius rounds concave interior routed corners.
- post.reconstructarcs: true produces real Edge.Cuts arcs instead of dense line-segment approximations.

## Useful commands

python3 -m json.tool panelize.json
kikit panelize -p panelize.json input.kicad_pcb output-panel.kicad_pcb

Dump the fully merged KiKit configuration with:

kikit panelize -p panelize.json -d resolved.json input.kicad_pcb output-panel.kicad_pcb

Render and open it with:

kicad-cli pcb render \
--output panel-top.png \
--width 1600 \
--height 1200 \
--side top \
--background opaque \
--quality high \
panel.kicad_pcb

kicad-cli pcb render \
--output panel-iso.png \
--width 1600 \
--height 1200 \
--perspective \
--rotate 325,0,35 \
panel.kicad_pcb
