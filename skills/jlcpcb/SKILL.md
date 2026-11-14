# Skill for ordering PCBA from JLCPCB

JLCPCB's placement preview is the only authority for their conventions:
their help docs are gated and their 3D model library has per-package
quirks. Upload BOM + CPL early in the quoting flow and confirm every
convention below in the preview before paying. Fix one thing per preview
round and re-check.

## BOM / CPL conventions

1. **Every BOM designator requires a CPL row - including through-hole
   parts.** The BOM checker rejects lines with no CPL row and silently
   drops them from assembly. Coordinates on THT rows are read by the
   assembly team; the SMT machines ignore them.

2. **CPL "Mid X / Mid Y" is the pad-field centre, not the footprint
   origin.** KiCad parks a connector's origin on pin 1; JLC centres each
   part model on its CPL point. Pin-1 origins render every through-hole
   connector half a body off its pads, by a different amount per part.
   SMT footprints' origins usually already coincide with their centres.

3. **Rotation is read from the side the part is mounted on.** KiCad's
   orientation is always CCW viewed from the top; a bottom-side part's
   CPL angle must be complemented: `(360 - rot) % 360`.

4. **One CPL row per physical part.** A footprint representing multiple
   physical parts must be replaced by one component per physical part.
   JLC's preview and operators place exactly one part per CPL row.

5. **Model-zero corrections are per package family.** Some of JLC's 3D
   models lie horizontal at rotation 0 while the footprint's pads run
   vertical. Keep a per-part correction table; never assume a global
   rotation convention.

6. **Verify connector gender on the LCSC page category line** -
   "Headers, Male Pins" vs "Headers, Receptacles, Female Sockets".
   Prose descriptions and part-number series naming are not reliable
   across vendors.

## Enforcing the geometry conventions

Conventions 2, 3 and 5 are easy to regress while editing an exporter.
Have the exporter emit a side-by-side audit file from the CAD kernel -
per reference: footprint origin, pad-field centre, rotation in both
conventions - and test the shipped CPL against it: through-hole centres
must differ from their origins, SMT centres must equal them, bottom-side
rows must carry the complemented angle.
