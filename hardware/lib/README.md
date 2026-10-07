# hardware/lib: everything the board is drawn with

Made by `gen/library.py`; do not edit by hand.

- `GPiBridge.kicad_sym`: KiCad's own symbols (flattened, so nothing points
  at a library you may not have), plus the ones drawn for this board in
  `gen/symbols.py` (RP2354A, SN75160B, SN75161B, the IEEE-488 plug, the debug
  connectors, the power flags).
- `GPiBridge.pretty/`: KiCad's own footprints; Raspberry Pi's QFN-60,
  inductor and 0402 footprints from their RP2350A Minimal design
  (`gen/rpi_minimal/`, MIT licence), used so that their regulator layout can be
  copied exactly; and the IEEE-488 plug (`gen/footprints.py`).
- `GPiBridge.3dshapes/`: KiCad's STEP models, plus the ones drawn in
  `gen/models3d.py` for parts KiCad's AppImage does not ship (the RP2354A's
  QFN-60, the HRO USB-C, the AOTA inductor, the IEEE-488 plug).

Licences: KiCad's symbols, footprints and 3D models are CC-BY-SA 4.0 with the
KiCad libraries' exception (using them in a design does not put the design
under CC-BY-SA).  Raspberry Pi's footprints are MIT licensed
(`gen/rpi_minimal/LICENSE.txt`).  The rest is this project's (see `LICENSE`).
