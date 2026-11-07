<p align="center"><img src="img/american-embedded-logo.png" alt="American Embedded Logo" width="300"></p>

<h1 align="center">KiStack - By American Embedded</h1>

## KiStack is a HUMAN WRITTEN set of skills to automate use of KiCad and validate schematics, layout (a bit), and even GERBERs (a bit)

## Install

Install the KiStack skills with the Skills CLI:

```bash
npx skills add American-Embedded/kistack
```

The package currently provides focused skills for schematic work, PCB review,
parts and BOM decisions, KiCad exports, and Gerber review.

## Field lessons (keep feeding back)

When agents use these skills on real boards, fold hard-won failures back into the
skill text and small helper scripts—do not leave them only in chat history.

Recent additions from production use:

- Schematic: netlist **and** pin-tip geometry; I2C/VDD level traps; PMIC EN
  cold-start deadlocks; duplicate hierarchical BOM hazards
- Export: Windows `kicad-cli` paths; avoid stale netlists; pcbnew DLL pitfalls;
  `scripts/check_sch_geo_vs_netlist.py`
- PCB: Specctra SES apply without moving footprints; freeroute keepout blindness

Fork / install from your preferred remote (`American-Embedded/kistack` or a
maintainer fork) and open PRs upstream when lessons generalize.
