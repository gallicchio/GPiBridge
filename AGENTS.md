# AGENTS.md: building, flashing and debugging GPiBridge (for LLMs and people)

GPiBridge is a USB-C to GPIB adapter: an RP2354A, two TI IEEE-488 transceivers, and a
24-pin GPIB plug under the board. Start with `README.md`, then `PLAN.md` (decisions)
and `DESIGN_NOTES.md` (why). This file is how to change it without breaking it.

**Rev A is being brought up (from 2026-11-15).** Read `bringup/STATUS.md` first: it
says where the bring-up stands and what the next thing at the bench is. "The bring-up"
below has the rules.

## Ground rules

- **Generated, not drawn.** `hardware/` is written by `gen/`: never edit the KiCad files
  by hand. Change the generator and rebuild. The sources of truth:
  - `gen/pins.py`: which GPIO does what. The schematic, the firmware's
    `board_pins.h` (`gen/firmware_pins.py`) and `docs/PINOUT.md` come from it.
  - `gen/parts.py`: every part, with its LCSC code and the words its JLCPCB
    description must contain.
  - `gen/placement.py`: where every part goes.
  - `gen/routes.py`: the connections, as coordinates computed from the pads (434 of
    the 460 tracks). The maze router (`gen/routing.py`) adds the rest: the +3V3 and
    +5V_GPIB fan-outs to their pours, and the crystal's two traces.
  - `gen/silk.py`: the silkscreen.
  - `gen/board_info.py`: name, revision, date, authors.
- **Checks gate everything.**
  - `tools/sch_check.py`: ERC must report 0 items.
  - `tools/check_pins.py`: every symbol pin against its datasheet.
  - `tools/pcb_check.py`: DRC must report 0 items at every severity, with schematic
    parity.
  - `tools/check_plug.py`: the plug's contacts lie as on UsbGpib V2's working board.
  - `mfg/make_release.py` refuses to write a release when:
    - any part has no LCSC code;
    - any code's JLCPCB description does not match its value;
    - DRC is dirty;
    - the zones are unfilled.
  - `mfg/footprint_check.py` checks that every ordered part fits its copper.
  - `mfg/jlc_rotation.py` holds the CPL corrections: per footprint where somebody has
    read them in JLCPCB's preview, per part (LCSC code) where they are predicted from
    JLCPCB's own drawing. When a preview has been read, record it there.
- **Look at what you made.**
  - `tools/render_pcb.py` gives layer images, `tools/render_sch.py` the schematic, and
    `kicad-cli pcb render` 3D views;
  - `tools/probe.py X0 Y0 X1 Y1` lists the copper in a window;
  - `tools/plot_board.py` draws the floorplan with net labels.
- **Board coordinates** are millimetres from the board's top-left corner, x right,
  y down. KiCad's page has that corner at (100, 100). Gerbers and placement files
  measure from the bottom-left corner, y up.
- **Rebuilds are deterministic.** The schematic and the board come out byte for byte
  the same from an unchanged design (the board's UUIDs come from a generator seeded
  afresh for each footprint, by its reference, and for each later stage). So `git diff`
  after a rebuild shows exactly what a change did, and only near the part it touched:
  read it.
- **Two boards, one pipeline.** `GPIBRIDGE_VARIANT=lite` in the environment makes any
  generator or check work on GPiBridge Lite instead of GPiBridge; `gen/board_info.py`
  holds every path that differs (`hardware/GPiBridgeLite.*`, `hardware/checks/lite/`,
  `mfg/release-lite/`, `docs/images/lite_*`). The Lite's differences are `if BI.LITE`
  branches in `gen/schematic.py`, `gen/placement.py` (`lite_place()`), `gen/routes.py`
  (`bus_side_lite`, `lanes_lite`), `gen/silk.py` and the housing's lid. `build.py` runs
  the per-board steps for both; `--full` or `--lite` narrows it. Change GPiBridge's
  board and check the Lite still builds, and the other way round: they share the core.

## Building

```sh
python3 build.py                   # everything; or: python3 build.py board  (from that step on)
python3 build.py --only release    # one step
```

Needs:
- KiCad 10, found by `tools/kienv.py` (`$KICAD_APPRUN` or `$KICAD_APPIMAGE`);
- Inkscape;
- FreeCAD 0.19+ (`freecadcmd`);
- CMake and `arm-none-eabi-gcc` for the firmware. `firmware/fetch_sdk.sh` fetches the
  pinned Pico SDK (2.1.1).

KiCad's Python runs as `AppRun python3.11`. The `gen/board.py`-style scripts relaunch
themselves inside it.

## Firmware

```sh
cd firmware && ./fetch_sdk.sh && cmake -S . -B build && cmake --build build -j
make -C firmware/test              # test_prologix: the "++" layer and the engine against a simulated
                                   # instrument; test_wire: the pin layer against the transceivers'
                                   # function tables (no two drivers on a wire, nothing into unpowered
                                   # chips); sigrok_check.py: sigrok's IEEE-488 decoder reads the
                                   # simulated bus (needs sigrok-cli, else skipped); builds sim_board
python3 bringup/run.py build       # all of it, into firmware/build-<this computer>/; use this on `bell`,
                                   # whose PATH puts Vitis's CMake 3.3 and an old arm-none-eabi-gcc first
pytest bringup/                    # every bring-up step against sim_board, good boards and planted faults
```

- `test/sim_board`: the firmware above the SDK behind a pseudo-terminal, on
  `test/wire_model.c`'s model of the transceivers. Anything that talks to an adapter
  runs against it: `tools/gpibridge.py --port PTY ...`, `bringup/run.py --sim STEP`,
  lab-instrument-control's `Link(gpib=10, prologix=PTY)`. Run a host program against it
  before running it against a board.
- **A check that says "skipped" has not run.** `sigrok_check.py` skipped itself on `bell`
  until sigrok-cli was installed there, and then failed 0 of 12 (`bringup/REVB.md` 2.3).
  The tools are in `~/.local/bin` now: `sigrok-cli`, `pulseview`, `picotool`,
  `openocd-xpack` (an OpenOCD with the RP2350; the system's has none), `probe-rs`.

- `src/gpib.c`: the IEEE-488 handshakes and addressing. Every wait has a timeout. It
  looks for another controller before it takes the bus (`gpib_start()`).
- `src/prologix.c`: the "++" command set. A data line past the buffer streams.
- `src/bringup.c`: `++t raw`, `++t lines`, `++t selftest`: the board as sixteen wires.
- `src/hal_rp2350.c`: the pins, and the direction changes that keep the RP2354A and
  the transceivers from driving one wire. `test/test_wire.c` checks every change.
- `src/capture*.c`: the bus capture on core 1, and its VCD.
- `src/main.c`: USB, settings in flash, the failsafes, the optional console.
- `src/usb_descriptors.c`: one serial port (or two with `++t console 1`), the reset
  interface, the Microsoft OS 2.0 descriptors.
- `test/sim_bus.c`: the simulated bus and instrument. Add a test there before changing
  the protocol code.

## Flashing and debugging a board on the bench

On Linux, install `tools/60-gpibridge.rules` first (the file says how; it needs sudo,
so it is Jason's to run). Then `picotool` reaches the reset interface without sudo, and
neither USB autosuspend nor ModemManager interferes.

- `python3 tools/gpibridge.py list | status | info | selftest | lines | identify | idn N |
  ask N "Q?" | send N "CMD" | test N | capture N "Q?" FILE | bootsel | flash FILE.uf2 |
  console-port on|off | console` (`--port PTY` for a simulated board)
- The firmware never needs the BOOT button:
  - `tools/gpibridge.py flash` sends `++t bootsel`, then `picotool load`;
  - `picotool reboot -f -u --vid 0x1209 --pid 0x0001` uses the reset interface (our IDs:
    picotool looks only for Raspberry Pi's unless told; `--ser SERIAL` too when more than one
    board is plugged in; `-a` for back into the firmware, which 0.4.6 first honoured);
  - three crashes in a row land in BOOTSEL by themselves.
- **One serial port by default.** `++t status` (JSON: counters, bus power, SRQ,
  `usb_ready_ms`, the capture) and `++t trace 1` work on it. `console-port on` adds the
  JSON console port; the adapter reconnects.
- **The UART (J4)** always carries the JSON log, from the boot line on.
- **The capture**: `tools/gpibridge.py capture 10 "*IDN?" idn` writes `idn.vcd`, and
  prints sigrok's decoding if `sigrok-cli` is installed. Look at it before guessing about
  a handshake.
- **A Raspberry Pi Debug Probe** (D port on J3, U port on J4) loads and debugs the
  firmware over SWD when USB does not work:
  `openocd-xpack -f interface/cmsis-dap.cfg -f target/rp2350.cfg` (the system's OpenOCD
  0.12.0 has no RP2350). An ST-Link V2 cannot do this (`BRINGUP.md`, "The SWD and UART
  connectors").

## The bring-up

`BRINGUP.md` is the plan; `bringup/` runs it (`bringup/README.md`).

- **Jason's time at the bench is the scarce thing.** He comes by for minutes, between
  other boards' bring-ups, and must be able to do the right physical thing at once. So:
  - **start every message of a bench session with where we are and the one next thing
    for him to do**, from `bringup/STATUS.md` (`python3 bringup/run.py` prints and
    refreshes it), naming the board (A1, L1), the connector or test point as the
    silkscreen prints it, and the instrument and channel;
  - never ask him to solder a wire or hold a probe for longer than a beep;
  - when a step fails, say whether the board should be left as it is (usually) and
    what, if anything, is his to do.
- **One step a call:** `python3 bringup/run.py bare A1`. A step writes its record to
  `bringup/results/<day>/`, appends to `bringup/BRINGUP_LOG.md` and rewrites
  `bringup/STATUS.md`. Commit those with the work they belong to, when asked to commit.
- **Every step leaves the board parked**: off the bus, `++t autostart 0` saved. Leave
  it so. `run.py unpark A1` is for the day a board goes into service.
- **Simulate first.** Change a step, or the firmware, and run `pytest bringup/` and
  `make -C firmware/test` before the board sees it. A new step gets a simulated run and
  a planted fault that it must catch.
- **What a board teaches goes into `bringup/REVB.md`** the same day: hardware for rev B,
  firmware as it is fixed, and the open-questions table as each is answered.
- **The bench is shared.** Before touching an instrument: Jason has said, in this
  session, that it is cabled to this board; then claim it
  (`python3 ../../lab-instrument-control/bench_claims.py claim SDS1104XE:1 --by GPiBridge
  --to "A1 test points, by hand" --limit "5.3 V"`), and release it when the board is
  uncabled. `bringup/bench.py` refuses an instrument this project does not hold.

## Bench instruments

`lab-instrument-control` (outside this repository) drives the lab's scopes and
generators from Python. The HP 33120A at GPIB address 10 is the test instrument for
`tools/gpibridge.py test 10`. **Ask what is cabled where** before a signal test. Do not
send `*RST` to the Siglents.

## This repository and lab-instrument-control (Jason, 2026-11-19)

Two public repositories, each usable without the other:
- **Here:** the board, the firmware, the udev rule, and what someone needs to get going
  on Linux, macOS or Windows: `README.md`, `HANDBOOK.md`, `tools/gpibridge.py` and
  `examples/`. That code stays at the "++" level, with pyserial alone, and imports
  nothing from lab-instrument-control. Point to it
  ([github.com/QuantumQuasars/lab-instrument-control](https://github.com/QuantumQuasars/lab-instrument-control))
  for instrument drivers, and never to a path inside it.
- **There:** instrument drivers, with a GPiBridge as one of several drop-in USB-GPIB
  adapters (Prologix, NI GPIB-USB-HS+, UsbGpib, ...). It carries its own copy of the
  udev rule and its own install notes, and must never need this repository.
- **The udev rule is in both**, as `60-gpibridge.rules`, byte for byte: change both.
- **`bringup/`** still uses lab-instrument-control, for the bench's test equipment
  (scope, meter, bench claims) and in stage 4 and the speed tests. Whether those last
  two move to the "++" level is Jason's call (2026-11-19).

## Git

This is its own public repository, github.com/gallicchio/GPiBridge. It was designed
inside Jason's private OpticsPCBs repository and moved here on 2026-10-06 (Prompt 9 in
`CLAUDE_CODE_CHAT.md`). Commit only what can be published:
- datasheets, NorComp's drawing and 3D model (`reference/`), JLCPCB's cached parts data,
  the fetched SDK and build products stay out of git (`.gitignore`);
- every path is relative: nothing committed names a place on one machine
  (`CLAUDE_PCB.md` §2). Check with `git grep -I -n -E '/home/|/Users/|/tmp/|/mnt/'`
  before committing. Expect hits in three files: this one and `CLAUDE_PCB.md` (the
  patterns themselves), and KiCad's own crystal model, whose STEP header names its
  author's folder. Vendored files stay as upstream ships them.

Do not commit or push unless asked. `CLAUDE_PCB.md` is a public snapshot of the lessons
file; when OpticsPCBs is at hand (`../../OpticsPCBs` on Jason's machines), read and
update the one there instead.
