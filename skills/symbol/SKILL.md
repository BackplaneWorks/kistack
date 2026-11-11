---
name: kicad-symbol
description: Generate compliant KiCad symbols
---

Run KiCad's CLI as plain `kicad-cli` (in Backplane, the KiCad Backplane has selected, first on your PATH; `$BACKPLANE_KICAD_CLI` is the same program), never by another install's path.

# This skill allows an LLM to generate KiCad symbols using a variety of data sources, validated against KLC standards.

## Setup
Clone the https://gitlab.com/kicad/libraries/klc standard. This includes a means of checking if a symbol is KLC compliant. In some cases, it is acceptable to be non-compliant but this should be the way, the truth, and the light for looping to create a compliant symbol. https://gitlab.com/kicad/libraries/kicad-library-tools can also be used to generate symbols if necessary, but this may not be a requirement.

## Usage

- If available, use easyeda2kicad for ground truth pin table. If this is not available, that's okay, but ask the user to install it. This takes an LCSC part number and returns a symbol if available.
- If this doesn't help, look for the pin table in HTML format. If this fails, get an image of the pin table from a PDF and convert it there. These methods require the user to approve the pin table so please ask them to review it!
- Use proper text formatting, pin formatting, and pin type. If there are alternate values for a pin, make sure you use alternates with proper pin type instead of creating a long list delimited with slashes! KiCad supports bars with ~{FOO} syntax, underscores with _{BAR}, and superscripts with ^{BAZ}.
- Per KLC, keep inputs on the left, outputs on the right, grounds on the bottom, NC pins invisible and on outline of symbol, power pins on top. This isn't a hard and fast set of rules honestly but it's helpful.
- Combine/stack pins whenever possible! Do not use legacy stacking, create a proper pin group that displays these pin number groups.
- Render the symbol as an image to confirm that it looks correct. kicad-cli should be able to assist here.
- Pins that are internally connected should be handled properly as well as a jumper group.
