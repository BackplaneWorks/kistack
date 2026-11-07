---
name: kicad-schematic
description: Create, modify, and review KiCad schematics from selected parts, datasheets, reference designs, renders, and netlists.
---

# SKILL ON HOW TO WIRE UP OR MODIFY A KICAD SCHEMATIC

## For Humans:

This skill for fully wiring up a schematic after initial IC selection, or modifying subcircuits after

You need to give the agent a good idea of the goal/vision for the schematic. Ideally, you need to provide it with as many relevant datasheets as possible so it doesn't have trouble sourcing them.

## For Agents:

These are instructions on how to wire up a schematic after initial IC selection. If you were asked to choose/find parts (besides passives, oscillators, or similar) and create symbols, start with that.

This skill is not for selecting specific parts/part numbers, and you shouldn't do so if you weren't asked to.

### How to draw the schematic

You can move anything around and label things. Generally, do most wiring with labels instead of drawing lines, with an important exception listed further below. Ensure all labels have 50mil text size.

You should color related nets so they stand out (e.g., SPI1 is one color, I2C2 is another, power supply lines are divided by purpose, etc.). Critically, don't just lazily color all of the nets in a single block the same color unless this truly makes sense.

Prefer single-sheet schematics that you can view all at once, even if it means bigger sheets. Break them down into more sheets and hierarchy when repetition is required, stuff the schematic is requires bigger than A2 page size even when somewhat compacted, or if user supplied them like that to begin with.

After understanding what subcircuits need to look like in general, put each subcircuit in a simple KiCad rectangle, colored and labeled with brief, bold text somewhere inside it. Prefer big-ish subcircuits that are not too defined. For example, most power supplies can usually be one subcircuit; ICs and their passives/oscillators/etc. can certainly be one subcircuit.

I know for a fact that your skill set is not adequate for wiring cleanly and correctly by just looking/modifying at the schematic file and the netlist that you can export from KiCad.

You need, instead, to iterate based on image input. That means you need to plot high-resolution SVG files of the schematic in KiCad and convert them into images that you can take in as image input and use for what you need. This way you will be able to validate that it is connected correctly and looks right as well.

You still need to look at netlists to deterministically validate connections.

If eeschema's IPC API isn't usable in your environment (kicad-python has shipped broken against the IPC server in some KiCad releases — check by actually calling something like `get_open_documents()`, not just by confirming the import succeeds), you can still generate schematics reliably by writing the `.kicad_sch` S-expression text directly with a small script, then validating with `kicad-cli sch erc` and rendering — same iterate-on-images loop, just scripted instead of GUI-driven. Two facts make hand/script-authored coordinates tractable instead of guesswork: (1) with a symbol instance at `(at inst_x inst_y 0)` (no rotation), a pin's absolute position is `inst_x + local_x, inst_y - local_y` — the Y axis flips sign between symbol-library space and schematic space. Don't assume this, confirm it once by placing a test symbol and reading the real pin coordinates back out of a `kicad-cli sch erc` report. (2) A label only joins a wire/pin if its `(at)` coordinate is the *exact* same point — even a 0.5mm cosmetic offset "for readability" makes ERC report `label_dangling` and `unconnected_wire_endpoint`, because the label is no longer touching anything. If a rendered image looks fine (SVGs/PDFs still show a label's connection tick even when it's technically not on the wire) but ERC disagrees, trust the ERC report.

Important things you should be looking for are that all visible properties of components are not overlapping with other things or each other, and that everything is clean and tidy (no overly long wires, etc.).

You need to make it look like it's straight out of a reference schematic for the parts: clean and tidy.

To do that, you will need to modify symbols to make them clean, readable, easy to wire up, and easy to read. But this carries risk: make sure you deterministically check that symbols keep the exact same pins as originally and have the same pin name for each pin number.

You need to use a ton of image input; do not hesitate. Every time it's not clean, you need to make it look good and look at it again. Develop efficient ways to do that at the start of the project so it doesn't cause slowdowns later.

You should also be plotting pictures of subcircuits and more specific things you need to clean up. I know for a fact that you can't take in the whole schematic all at once, so zoom in. Iterate. It has to look clean and functional and be correct.

If your image tool struggles to preview a large rendered SVG (some environments cap what they'll show for a big file), export a PDF instead and read it as a document/image, or plot with a small custom page size that tightly wraps just the area you're reviewing — `(paper "User" width height)` in the `.kicad_sch` (in mm) — so the same fixed image resolution shows far more detail. Don't edit the real page size for this, just do it on a scratch copy for the review pass.

For passives, use the small KiCad standard symbols. Use the Resistor_Small_US symbol, regular capacitor and inductor though.

You will need to modify symbols of ICs to make passives look good.

Wire them up logically next to the component where it makes sense (for example, pull-downs/ups and decoupling). This is the exception to the "use nets" rule, these will need to be wired with normal wires, not nets, for the most part. Passives are an exception to the general "use labels instead of lines" rule. Use power symbols as well instead of labels for VDD, GND, +3V3, etc. these sort of nets need to be obvious, more than just a label. If a power symbol does not exist with that name, just rename an existing one. Preference is the default GND symbol for ground, VDD for positive power supplies (outline arrow pointing up), and VSS for negative power supplies (filled arrow pointing down). Ground must ALWAYS point down. Positive power supplies must ALWAYS point up. Negative power supplies must ALWAYS point down. Always ensure that these do not overlap with text, including their wires! 

If using PWR_FLAG symbols, put them near the source of the power supply rather than randomly on the sheet. Placing one nearby isn't enough by itself: it has to actually be wired onto the net (or share the exact same coordinate as a pin already on it) or ERC will still report `power_pin_not_driven`, since an unconnected flag doesn't join anything.

When you need a new named power net that isn't one of KiCad's built-ins (an isolated-domain rail, a second voltage plane, etc.) and follow the "rename an existing symbol" advice above: renaming only works if you create an actual new symbol *definition* with that name in `lib_symbols` (duplicate the whole `+3V3`/`GND` symbol block, change its own name and its `Value` property's default text, keep everything else). Overriding just the instance's `Value` property while leaving `lib_id` pointed at the original `+3V3`/`GND` (or worse, pointing `lib_id` straight at your new name with no matching symbol defined at all) does not create a new global net — confirmed by exporting a netlist (`kicad-cli sch export netlist`) and finding every such instance sitting on its own single-node net instead of merging. If ERC on a schematic like this looks chaotic (`power_pin_not_driven` and `unconnected_wire_endpoint` scattered everywhere with no obvious pattern), export the netlist and check whether same-named nets actually merged before chasing anything else — it's a fast, definitive way to confirm or rule this out. Also make sure the reference field on every power symbol/flag is a real unique designator (`#PWR001`, not a literal `#PWR?` left for GUI auto-annotation, which a script never gets) — when scripting a schematic directly, `kicad-cli sch export netlist` printed a Japanese-locale warning translating to "the schematic has annotation errors, fix them in the schematic editor" and produced a netlist anyway, so check for that warning rather than assuming a clean exit means annotation is fine.

When laying out several small decoupling/bypass nets that fan out from adjacent pins on the same IC edge (a scripted layout will often push each one out by the same fixed "stub" distance), watch for two of those fan-outs landing at the identical x column: if two pins are only a few mm apart and both stub out by the same amount, their two (unrelated) vertical wire runs end up sharing an x-coordinate, and if either run is tall enough to reach the other's y-range they touch at a coincident point and silently merge into one net — caught via `kicad-cli sch export netlist` showing a 2-pin capacitor's own two pins on the *same* net (i.e. shorted). Give nets like that different stub lengths so their columns don't overlap.

Don't just eyeball a render for "no overlapping text" — on a dense sheet it's easy to miss real overlaps at the zoom level a render tool shows you, and easy to falsely flag things that are actually fine. Export SVG (`kicad-cli sch export svg`) and parse the `<text>` elements' own `x`/`y`/`textLength`/`font-size`/`text-anchor` attributes directly: that gives you the renderer's real bounding boxes (font metrics and all) instead of a guess from character count. Build each box from `text-anchor` (`start` → box starts at `x`; `end` → box ends at `x`; `middle` → centered on `x`), with height roughly `0.78*font-size` above the baseline and `0.25*font-size` below, then flag any two boxes that intersect. This catches things a quick look at a render won't (a label sitting exactly on top of a component's own reference text, two labels 0.8mm apart) and, run before and after a layout change, gives you a real before/after count instead of "looks better to me." One gotcha: this project's own SVG output rendered `rotation=90` labels with the same `x`/`y`/`textLength` fields as horizontal ones, so a naive box (treating `textLength` as horizontal width regardless of rotation) produces false positives for vertical text — check each label's own `at ... <rot>` in the source `.kicad_sch` and swap width/height for anything rotated 90/270 before flagging it.

A KiCad label's text does NOT simply extend away from its wire in the "outward" direction you might expect — it anchors at the stub's far end and reads back TOWARD the pin (confirmed by checking the exported SVG's own `text-anchor="start"` position against the stub coordinate, not by assuming). This means a long net name on a short stub overshoots back past the pin into the IC's own pin-name text or a neighbour's label — and a *longer* net name needs a *longer* stub to keep clear, not the same fixed default every other label on the sheet uses. If a project has both short signal names (`SPI1_MOSI`) and long ones (an isolated-domain prefix like `OMNI_+3V3_ISO`, or anything 13+ characters), size the stub to the text (`max(default_stub, len(net) * ~0.95 + 3)` in mm was enough headroom at a 1.27mm label font in this project) rather than using one fixed distance for every label — a fixed default tuned against your shortest names will systematically undershoot your longest ones. Watch for the flip side too: pushing a stub out to clear a long name on one pin can push it far enough to collide with a *different*, unrelated component sitting nearby (e.g. a neighboring IC's own decoupling network) — after widening a stub, re-run the overlap check, don't just assume more clearance is strictly better.

If a symbol's pin table has two or more pins at the *exact same* local `(x, y)` (check the pin list, not just the pin count) — common on parts with multiple physically-identical pins the vendor ganged together (multiple IN, multiple GND, multiple OUT) — one wire touching that coordinate connects to all of them simultaneously; KiCad treats graphically-coincident points as joined regardless of which pin "owns" them. Drawing a separate wire and (for a power net) a separate power symbol for each duplicate pin doesn't add any connectivity the first one didn't already provide — it only adds a second, slightly-offset copy of the same net-name text next to the first, which reads as visual clutter or an actual overlap depending on how close the two stubs land. Wire the first pin in the group normally and skip the rest (a `pass` with a comment saying why, so it doesn't look like a missed connection) — verified via ERC before/after (identical violation count) and via the exported SVG (the duplicate label disappears) that nothing was actually lost.

When a small sub-block (a driver IC plus a handful of discretes plus a connector, say) gets repeated several times down a column, don't rely purely on per-label stub-length tuning to keep each repetition's labels clear of its neighbours above and below — that turns into whack-a-mole (fix pin A vs pin B, the fix now collides with pin C, fix that, it now reaches the *next* repetition's own labels) because the same short/long-name overshoot problem exists on every axis at once. Give the repeated block real vertical (or horizontal) pitch between repetitions first — enough that even a generously-long stub on the outermost pin of one repetition can't reach the next one — and only then tune stub lengths for collisions *within* one repetition. Increasing the pitch is a one-line, monotonic fix; chasing it with ever-more-precise per-pin stub values on a fixed pitch is not, and each iteration needs a fresh overlap check to know whether it actually helped or just moved the collision.

The page you draw on has to be big enough to hold everything you put on it — obvious in principle, easy to violate incrementally when a sheet grows one subcircuit at a time. If a new block's own bounding box (its zone rectangle, or its outermost wire/label) exceeds the sheet's declared `(paper ...)` width or height, part of it lands off the drawn page or on top of the title block that KiCad auto-anchors to the page's bottom-right corner — and a render at "fit whole page" zoom can make this hard to notice since the overflowing content and the title block area may not both be in view at once. Before finishing a pass that added a new block, sanity-check its own max x/y against the current paper size (a couple of `grep`/regex passes over the block's own wire and label coordinates is enough) rather than trusting that "the page hasn't complained." `(paper "User" width height)` (in mm) resizes the real page, not just a review copy — do this on the actual file once content genuinely needs more room, distinct from the review-only custom-size trick above.

When adding test points, add them near the actual net in question.

When adding values for symbols for passives, always use the unit. F, H, or R (not omega) for the passives please.

Labels for differential pairs should end in +,- or P,N to get picked up properly.

Again, you need to iterate with pictures to make sure they look clean.

For new passives, mostly as placeholders, add footprints from the standard KiCad library (unless otherwise instructed) of a roughly logical size based on the function.

Do use some discretion about what passives should be directly connected to what for aesthetics.

In general, groups of decoupling capacitors do not need a ground symbol per capacitor, or a VDD symbol per capacitor. Group them with comfortable breathing room between them, and by default physically connect them to the proper pins of the IC they are decoupling. If power supplies are sourced from the same regulator without any components in between, they can be bridged as well.

Watch the topology when you do this, especially scripting it: each decoupling cap is a PARALLEL branch off the rail down to ground, never IN SERIES between the pin and the rail. Wiring `pin -> cap -> rail` instead of `pin -> rail` (with the cap T-ing off separately to ground) silently leaves the pin floating at DC — a real capacitor blocks DC, so the "decoupled" pin would never actually reach the supply voltage. It'll look identical to the correct wiring in a quick glance at the render; ERC's `power_pin_not_driven` / `ground_pin_not_ground` is what actually catches it, so don't skip the ERC pass just because the picture looks right.

A shared decoupling branch (rail label/symbol + cap + ground) needs real room to extend into — its ref/value/ground text can easily span 15-20mm along the axis it grows on. If the pin it's hanging off is at the edge of a tightly-pitched pin column (adjacent pins only 2-3mm apart) and the branch extends toward the OTHER pins in that column, it will run straight through their own labels regardless of how far out you push it, because it's traveling parallel to a column of things it can't get around. If the pin is at the top or bottom of its column (nothing above/below it on that side), extend the branch AWAY from the column instead — into whatever open space sits beyond the topmost/bottommost pin — rather than pushing it further along the same axis and hoping the reach is enough.

You can't start looking for parts during the schematic wire-up process. If a part was not already given to you and you were not asked to find it, don't look for it.

If you need something like a voltage regulator, an oscillator, or small stuff like that, feel free to create a generic/abstact symbol for one and place it in the self-contained library in this directory (if it exists; otherwise, create one). Then use it. For more complex stuff, you might need to just leave a comprehensive but short note that a whole complex component is missing, continue with the schematic, and mention it briefly at the end as an important item.

Lastly the schematic should be somewhat compact, so if there is a lot of white space bring stuff closer together on the sheet so it's easier to read

Again, if you think you are done, check the whole schematic, for falsely rotated, misplaced, ugly text, overlapping stuff, illogical stuff, hard to read schematics, too much white space. and go back into fixing mode to fix them. You might need to loop around after actually finishing the schematic, at least 3-5 times on the whole schematic until you get it right, be sure it is at the end. 

### How to do research

Now that you know how to wire up a schematic in KiCad cleanly, we will go over research. These two parts are not separate; you might need to do them together. You can start wiring up subcircuits after researching how, looking at them and how they fit into the general schematic (with pictures and netlists), and then iterating in your research.

You really need to understand the science behind the board, really understand the goal and how everything ties together. Take time for introspection about what the goal is every step of the way. Every time you complete a part, think about it and how it helps the vision for the schematic.

Also, a very quick second step is looking for important datasheets based on the ICs and general vision. If you are missing some datasheets and realize that you really need them, look for them on the internet and try to download them. You might find it hard to get around bot protection; quickly find ways around that and see if you have any other skills available for that purpose as well.

Do not be hesitant to do internet searches to figure stuff out and understand what you need to do. If you have any uncertainty about how something should work, you can use internet search to clear things up.

But the real sources of truth are datasheets and reference material; you can base decisions on these. You will often need to extract information from PDFs, and very often you will need to take shots of pictures in the PDFs. Don't be hesitant to actually use image input to directly look at reference-design pictures or graphs (or other stuff like that) in PDF material. And contiually compare your schematic to the reference.

Once you know enough about how to wire up a subcircuit, you can start bit by bit, always referring to reference material. Be logical and precise, but don't overdo it. That means that you should not overthink decisions. Instead, you should note down all real liberties you took and provide them in a nice, readable, and brief report as part of your answer to the user.

You can take some liberties based on the goal of the project, but they should definitely be mentioned at the end.

For the most part, your job with this skill will be adding adding decoupling, wiring up MCUs to peripherals with legal pin selection for each function, adding oscillators, adding voltage conversion, and filtering if necessary, and other low level work like this. You need to look into reference materials and base your decisions on truths in them. Often you may choose a reference design in them, look at it as a picture, and follow it. But most importantly, you need to be thinking at a high level.

For example, for decoupling, think about derating depending on conditions, DC voltage, etc., and think about upstream circuitry like voltage regulators and switches and how much capacitance they can take.

If you need to do more high-level work than the work described above as "most of your job," you can go ahead, but make sure you understand why it's necessary and do not add a lot of bloat. Always be able to explain your decisions logically without much possibility of dispute, and do explain them in your answer at the end, along with other liberties you took.

### Connectivity truth: netlist AND pin geometry

ERC and an old `netlist.kicad_net` are not enough.

After schematic edits, **re-export** the netlist with `kicad-cli sch export netlist` and treat that export as the intent snapshot. Then also check that wires/global labels actually touch pin endpoints on the sheet.

KiCad schematic coordinates are **Y-down**. Symbol-editor local pin `(lx, ly)` on a placed symbol at `(ox, oy)` with rotation 0 maps to:

```text
world_x = ox + lx
world_y = oy - ly
```

Scripted wiring that uses the wrong transform (or places labels near an IC without hitting the pin tip) produces sheets that *look* labeled but geometrically leave pins floating. Labels sitting next to a body without a wire to the pin tip are a failure.

If geometry and netlist disagree: **geometry on the current sheet wins for what would fabricate after a fresh export**; a stale netlist must not be trusted as "design intent" until you re-export. Prefer regenerating stub wires from known pin maps over hand-nudging hundreds of labels.

A helper for this check lives at `skills/export/scripts/check_sch_geo_vs_netlist.py`.

### Electrical review ERC will not catch

Before you call a schematic "done," walk these with datasheets open. ERC will often stay green while the board is still dead or destructive.

1. **I2C / open-drain levels vs device VDD**  
   Pull-ups must not exceed each device's pin absolute max (often `VDD + 0.3 V`). Mixing 1.8 V sensors with 3.3 V pull-ups without level translation is a hard fail. If one device on the bus needs ≥2.5 V VDD (common for ALS parts), do not park it on a 1.8 V rail.

2. **Multi-rail chicken-egg enables**  
   If a PMIC's `EN*` pins enable the rail that powers the MCU/GreenPAK supposed to drive those same `EN*` pins, cold start can deadlock. Prefer a path that can assert EN before that rail exists (for example STATUS/ready → EN, or strap to an always-available logic high the datasheet allows). Never leave EN floating when the datasheet forbids it.

3. **Duplicate subcircuits across hierarchical sheets**  
   "Detail" sheets that re-place the same divider/battery symbols without DNP create parallel components and wrong thresholds. One sheet owns the real BOM parts; extras are DNP or text-only references.

4. **Stub / incomplete symbols for complex ICs**  
   A 4-pin "VDD/SDA/SCL/GND" stand-in for a part that also needs high-voltage AVDD (or many supplies) is not Phase-1 ready. Mark DNP and say so, or finish the supplies.

5. **LDO current limits vs burst loads**  
   Peak radio/MCU current may exceed LDO Imax; that is only acceptable if local bulk (e.g. polymer) is intentional and documented.

Report these as electrical findings even when ERC is clean.
