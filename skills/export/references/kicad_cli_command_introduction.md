Software and Documentation Version

This user manual is based on KiCad 10.0.5. Functionality and appearance may be different in other versions of KiCad.

Documentation revision: a77c36a3.

Introduction to the KiCad Command-Line Interface
KiCad provides a command-line interface, which is available by running the kicad-cli binary. With the command-line interface, you can perform a number of actions on schematics, PCBs, symbols, and footprints in an automated fashion, such as plotting Gerber files from a PCB design or upgrading a symbol library from a legacy file format to a modern format.

In Backplane, run it as `kicad-cli` (first on your PATH) or `$BACKPLANE_KICAD_CLI`: both are the KiCad Backplane has selected. Don't call an install's own kicad-cli by its path.
The kicad-cli command has 6 subcommands: fp, jobset, pcb, sch, sym, and version. Each subcommand may have its own subcommands and arguments. For example, to export Gerber files from a PCB you could run kicad-cli pcb export gerbers example.kicad_pcb.

You can add the --help or -h flag to see information about each subcommand. For example, running kicad-cli pcb -h prints usage information about the pcb subcommand, and kicad-cli pcb export gerbers -h prints usage information specifically for the pcb export gerbers subcommand.
