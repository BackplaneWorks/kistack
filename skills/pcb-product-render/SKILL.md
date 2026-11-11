---
name: pcb-product-render
description: Create realistic Blender product renders from KiCad PCB projects, including refreshed 3D exports, physically plausible PCB materials, camera/stage setup, and visual validation.
---

Run KiCad's CLI as plain `kicad-cli` (in Backplane, the KiCad Backplane has selected, first on your PATH; `$BACKPLANE_KICAD_CLI` is the same program), never by another install's path.

# PCB Product Render

Use this skill when a user wants a KiCad PCB exported to STEP/GLB and rendered as realistic product imagery. The desired result is a clean product photograph/render, not a flat KiCad preview or vector-like orthographic diagram.

## Required workflow

1. Identify the project root and the authoritative `.kicad_pcb`. If the user says “latest board,” always regenerate the STEP and GLB before rendering; never reuse an older GLB based only on its filename.
2. Run a current DRC report. Stop on violations unless the user has explicitly authorized proceeding (an earlier authorization applies only to that project/task). Record the report path and counts in the handoff.
3. Export with `kicad-cli pcb export step` and `kicad-cli pcb export glb`, using `--force --no-dnp --subst-models`. For the GLB include tracks, pads, zones, silkscreen, soldermask, and `--cut-vias-in-body` when supported.
4. Inspect the exported scene before rendering. Confirm the rounded outline and every mounting/cutout hole are present. Remove only unnecessary 3D header models; retain their footprints and pads. If a known vendor model is missing, use a deterministic custom Blender fallback and state that it is a fallback.
5. Render at least hero, near-overhead top, sensor/detail, and back views. Use Cycles with denoising and inspect the actual PNGs—not only a successful Blender exit code.
6. Verify dimensions, output timestamps, and any gallery/server endpoints. If an HTML gallery already exists, keep its filenames stable so it refreshes without breaking links.

## Material targets

- Blue soldermask: deep royal blue LPI resin, non-metallic, moderately glossy rather than matte or mirror-polished. Use a smooth clear coat with low coat roughness, restrained micro-roughness/bump, and only subtle optical depth. Avoid high-contrast procedural grain.
- Bare FR-4: muted warm tan/amber fiberglass, slightly cloudy and translucent at the routed edges. Use controlled transmission/subsurface/volume absorption and soft underlighting. Keep the clear fraction low enough that stage graphics do not appear as sharp stripes through the laminate; open holes may reveal the stage below.
- ENIG: exposed copper/pads should read as pale metallic gold, not orange paint or raw copper. Adjust roughness and lighting so highlights do not clip to featureless white.
- Solder: if the source model has dry passive blocks, add small silver SAC-style solder fillets at their pad interfaces. Keep them irregular and subdued; do not turn them into bright white dots.
- Connector plastic: matte molded nylon with slight warm-gray variation, microscopic bump, and small physical edge bevels. Avoid opaque white blocks.
- Sensor housing: matte charcoal molded plastic with restrained pebbled texture; emitter/receiver materials should follow the user’s reference images.

## Camera and stage

The top view should be a near-overhead perspective product shot, not an orthographic CAD view: retain a small tilt so board thickness, component height, and contact shadows are visible, with enough background margin for the stage. A dark brutalist/Marathon-style stage is acceptable, but colored accents must support the object rather than dominate it. Hide under-board tracers and backlights when they make the top view look diagrammatic; preserve them only when they produce soft, plausible FR-4 transmission.

## Current project reference

The workflow was developed against:

`/home/h/Documents/AmericanEmbedded/AmericanEmbedded/VL53L9CX_Pi_Cam`

Important project artifacts:

- Board: `VL53L9CX_Pi_Cam.kicad_pcb` (31 mm × 25 mm in the current scene).
- Export helper: `build/product-renders/export_board_3d.sh`.
- Blender scene builder: `build/product-renders/build_product_scene.py`.
- Blender source: `build/product-renders/VL53L9CX_STEMMA_QT.glb`.
- Final scene: `build/product-renders/VL53L9CX_STEMMA_QT-product-renders.blend`.
- PNGs: `VL53L9CX-STEMMA-QT-hero.png`, `VL53L9CX-STEMMA-QT-top.png`, `VL53L9CX-STEMMA-QT-sensor-detail.png`, and `VL53L9CX-STEMMA-QT-back.png`.
- Gallery: `VL53L9CX-render-gallery.html`, served in the current setup at `http://100.64.84.41:8765/`.
- Latest DRC report: `build/render-review/drc-latest-render.rpt`. The current project was rendered under the user’s prior override despite 12 violations, 53 unconnected items, and one schematic-parity issue.

The current project intentionally has no rendered through-hole pin-header model. Its footprint/pads remain in KiCad. Y1’s missing vendor STEP is handled by the custom oscillator fallback in the Blender script.

## Handoff requirements

Report the output directory, the gallery URL if available, the DRC status, and any missing-model fallback. Link local files with absolute paths. Do not describe a render as photorealistic without inspecting the resulting images; call out remaining source-model limitations when the KiCad footprint geometry is simplified.
