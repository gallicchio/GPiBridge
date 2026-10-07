# GPiBridge: the plan

A USB-C to GPIB (IEEE-488) controller that plugs straight into an instrument's GPIB
socket. Its housing is no bigger than a GPIB cable's hood. To the computer it is either
a Prologix-compatible serial controller or a standard USB test-and-measurement
(USBTMC/USB488) device. It is designed so that an LLM can rebuild, reflash, test and
debug it over the one USB cable, with nobody pressing anything.

This file is the plan and the state of the work. It is kept current while the work
goes on, so that a new session can pick it up. The lessons it follows are in
`CLAUDE_PCB.md`, a public snapshot of the lessons file in Jason's private OpticsPCBs
repository, where this project was designed until it moved here on 2026-10-06.

## 1. Decisions

| question | decision | why |
|---|---|---|
| Name | **GPiBridge** (Jason's pick, 2026-10-06) | GPIB with a lowercase "i" for the Pi, the RP2350's maker, and it is a USB-to-GPIB bridge. No product or project of that name turned up (searched 2026-10-06). "RaspberryGPiB" was the first idea: Raspberry Pi Ltd's trademark rules forbid "Raspberry" as a brand for hardware. Also avoids Prologix, AR488, UsbGpib/GPIBee, GPIBUSB (Galvant), gpib4pi, GrasPiB, and the vendor names "USB-488", "488-USB", KUSB-488, TEK-USB-488. Repository: github.com/gallicchio/GPiBridge |
| What it emulates | The **Prologix "++" command set** over a USB CDC serial port, and a **USBTMC/USB488** interface | The "++" set is publicly documented (manual 6.0 in `datasheets/`), and PyVISA-py (`PRLGX-ASRL`), KE5FX, EZGPIB and `lab-instrument-control` already speak it. USBTMC needs no driver: Linux `usbtmc`, NI-VISA, Keysight VISA and PyVISA all know it. **Not NI's protocol:** that would mean NI's USB vendor ID, which a public design cannot use. |
| USB identity | Our own VID:PID (pid.codes, the open-hardware allocation), product string "GPiBridge" | Not "Prologix" (a trademark). `++ver` answers "GPiBridge ..." by default; a config option lets picky software see a Prologix-style string. |
| Microcontroller | **RP2354A** (QFN-60, RP2350 die plus 2 MB flash in the package), LCSC C41378174, 16 399 in stock, $1.24 | **PIO** state machines run the three-wire handshake at full IEEE-488.1 speed. The **ROM USB bootloader** can be entered from software (`picotool reboot -u`). The bootrom can boot **A/B images with "try before you buy"**, so a bad build falls back by itself. The flash in the package saves a part on a crowded board. |
| Bus drivers | **SN75160B** (DIO1-8) plus **SN75161B** (control), TI, SOIC-20W | They meet IEEE-488.1: 48 mA sinks, bus terminations, receiver hysteresis, glitch-free power-up, and **high impedance with VCC = 0**. The Prologix and UsbGpib drive the bus straight from the MCU and do none of this. The 75161B is the single-controller variant (the 75162B, with an SC pin, is out of stock). |
| Bus power switch | 5 V to the transceivers through a P-MOSFET that firmware turns on | Until firmware has set TE, DC, PE and every line to "released", the transceivers are unpowered and therefore off the bus. Plugging into a live bus cannot glitch it. It also keeps 5 V-level signals off the MCU's pins until its 3.3 V is up: the RP2350's pins are 5 V tolerant **only while powered**. |
| USB-C | HRO TYPE-C-31-M-12 (C165948), at one end, facing sideways (along the panel) | It was built correctly on the Lorenz board, and its edge datum is known (board edge = upper shell tab + 5.79 mm). Like UsbGpib V2, the cable runs along the instrument's panel, so it does not lever the GPIB connector. |
| Form factor | The board lies **parallel to the instrument's back panel**. The GPIB plug's pins pass through it from underneath; everything else is on top. Board 60 × 25.5 mm; housing 62.6 × 28.2 mm. | UsbGpib V2's form, which copies a GPIB cable's hood after its own V1 collided with instrument bodies. Our board is a little larger than V2's 54 × 15 mm: two SOIC-20W transceivers do not fit beside a 25 mm strip of connector pads at 15 mm. |
| Layers | **4** (JLC04161H-7628, 1.6 mm): signal / GND / power and signal / GND | A solid ground under the USB pair, the RP2350's switching regulator and the 0.4 mm QFN. Small boards make the 4-layer premium a few dollars. |
| Assembly | JLCPCB economic PCBA, **top side only**. The GPIB plug is **hand-soldered**, as on UsbGpib. | JLCPCB holds no GPIB plug (searched 2026-10-06: their library lists NorComp's, C5470282, with no stock: pre-order only, $9.96 each against Digi-Key's $4.22; the other "GPIB" entries are customers' placeholders). And the housing needs it soldered last: the base's front plate sits between the flange and the board, so the plug goes through the base first. A factory-fitted plug would need a different base. |
| GPIB plug | 24-pin IEEE-488 male, solder type, through the board: 2 × 12 at 2.16 mm, rows 4.29 mm apart. Pads are numbered by **IEEE-488 contact number**, not by solder-cup order. | UsbGpib V2's proven geometry, for the Norcomp 112-024-113R001 or the generic "24P male solder type". |
| Debug | **Two top-entry 3-pin JST-SH** (BM03B-SRSS-TB) at the right end, under openings in the lid, the Raspberry Pi debug-connector standard: **SWD** (pin 1 SWCLK, 2 GND, 3 SWDIO) and **UART0** (1 RX, 2 GND, 3 TX), 100 Ω in series at the connector. A **BOOT button** (QSPI_SS via 1 kΩ). | A Raspberry Pi Debug Probe plugs into both, with the housing closed: gdb and a console when USB itself is broken. The button is for recovery only; normal reflashing is software-only. |
| Crystal, regulator | Exactly Raspberry Pi's: ABM8-272-T3 with 15 pF and 1 kΩ; Abracon AOTA-B201610S3R3-101-T 3.3 µH (polarity-dotted) with 3 × 4.7 µF and 33 Ω; layout as on the Pico 2 | "Hardware design with RP2350" says deviating is at your own risk. Both parts are at JLCPCB (11 405 and 1 048). |
| Enclosure | Two-part print for JLC3DP (MJF PA12 nylon), drawn in **FreeCAD's Python** (headless) | FreeCAD writes STEP (KiCad's 3D view and JLC3DP both take it) and can intersect the housing with the board's own STEP export, so interference is checked, not guessed. Holes for the USB-C, the debug connectors, the LEDs and the BOOT button (paperclip). The USB-C face sits flush with the outside of the wall. |

Changes made while drawing the schematic (2026-10-06):

| question | decision | why |
|---|---|---|
| 3.3 V regulator | **XC6206P332MR** (C5446, Basic), not the AP2112K | The board draws about 50 mA at 3.3 V; the AP2112K is an Extended part (a setup fee) for headroom we do not need. Dropout 0.25 V at 100 mA. |
| USB ESD array | **None** (no USBLC6) | Raspberry Pi's own boards have none; one less Extended part whose rotation could short the bus. |
| Fuse | **None** | The transceivers want 4.75-5.25 V; a PPTC's drop (up to 0.3 V) would put them below spec on a weak port. The host port limits current. |
| MCU to transceiver | **No series resistors** (the 470 Ω arrays of the first draft are gone) | The transceivers' terminal outputs are short-circuit limited, and the firmware changes direction in one place (TE before the pins when talking, the pins before TE when listening). Dropping them let all sixteen lines run as one ribbon on the top layer. |
| Defaults | **10 k pulls**: DC up; TE_DATA, TE_CTRL and BUS_PWR_EN down | In reset or blank: the transceivers unpowered, and when the switch opens they are a listening device that cannot drive ATN, REN or IFC. NRFD, NDAC and SRQ need no pulls: for the 1 ms the switch takes, they can only pause a handshake or raise a spurious SRQ (`gen/pins.py`). |
| LEDs | **USB yellow, ERR red** (firmware); **BUS green**, lit by the switched 5 V itself | Only red and yellow have a forward voltage low enough for a 3.3 V pin (Basic 0805 parts). BUS shows in hardware that the transceivers have power. |
| Core regulator layout | **Raspberry Pi's own footprints, zones and vias**, extracted from their MIT-licensed RP2350A Minimal design (`gen/rpi_minimal/`) | Their guide says to copy it exactly. |

Changes after the first review (2026-10-06, Prompt 2):

| question | decision | why |
|---|---|---|
| Serial ports | **One by default**, as a Prologix; the JSON console is optional (`++t console 1`, saved) and always on the UART | Prologix software users should not have to guess between two COM ports |
| Windows | USB 2.1 with **Microsoft OS 2.0 descriptors**: WinUSB on the reset interface | No unknown device in Device Manager; `picotool` works with nothing installed |
| Bus debugging | **The board records its own bus** (core 1, `++t capture`, VCD for PulseView's IEEE-488 decoder); outside analysers through a GPIBtap pass-through | Most bus problems need no wires; `BRINGUP.md` §4 |
| Debug probe | **Raspberry Pi Debug Probe** ($12), on the existing JST-SH connectors (Raspberry Pi's debug-connector standard) | An ST-Link V2 cannot wake the RP2350's debug port |
| First test partner | **The bench Prologix in device mode**, then the HP 33120A, then the dearer instruments | Both ends of the bus scriptable before any real instrument (`BRINGUP.md` §2) |
| The plug's side | Silkscreen on both sides: "pins stick out on this side" on top, "the plug goes on this side" in the D on the back | The pins fit either way |
| Name | **GPiBridge**, not "RaspberryGPiB": Raspberry Pi Ltd's trademark rules forbid "Raspberry" as a brand for hardware | The URL, github.com/gallicchio/GPiBridge, is on the schematic and the back silkscreen |

Changes for Prompt 6 (2026-10-06): GPiBridge Lite, and NorComp's own files for the plug

| question | decision | why |
|---|---|---|
| GPiBridge Lite | **Designed now**, to be ordered with GPiBridge (5 boards, 2 assembled, each) and brought up after it | One order saves time and shipping; at worst the Lite's $66 is spent early |
| The Lite's form | **GPiBridge's outline, layers, parts and places**, less the transceivers and their 5 V switch; 100 R in each bus line | The same base fits, the core every GPiBridge test proves is the same copper, and nothing new is risked in this order. A smaller, two-layer Lite can follow |
| One firmware for both | **R21 on DC is the board ID**: 10 k up on GPiBridge, 1 k down on the Lite; read at start-up | GP26 was the plan, but GP26-29 are walled in by decoupling copper; DC already had a resistor in place |
| The Lite's bus pins | **Open-drain, with the pads' output forced low** (OUTOVER) | No software path can drive a line high against another device |
| The Lite's BUS LED | **On BUS_PWR_EN**, through 100 R | BUS means "on the bus" on both boards |
| The plug's body | **From NorComp's 3D model** (and drawing rev 15), not scaled from the drawing | Jason fetched both from Digi-Key; the model shows the pins' 1.0 mm shoulder and the flare under the flange |
| The housing's front plate | **3.5 mm** (was 3.3), and the plug's opening 0.3 mm clear with a 0.4 mm step at the face | Equal to the flange's height, so the lid's screws bend nothing; room for the flare |
| Quantities | **5 boards, 2 assembled**, both boards | JLCPCB's minimums |

## 2. GPIO map

`gen/pins.py` is the source of truth; the schematic, the MCU symbol's pin order, the
firmware's pin header and the pinout document are made from it. In short:

| GPIO | what | notes |
|---|---|---|
| 0-7 | DIO5-8, DIO1-4 | the data byte, **nibbles swapped** so all sixteen data wires run on the top layer without a crossing; the firmware swaps them back |
| 8 | EOI | follows the data, so one 9-bit PIO `in`/`out` takes both |
| 9, 10, 11 | DAV, NRFD, NDAC | NRFD and NDAC consecutive: one 2-bit side-set |
| 12-15 | IFC, REN, ATN, SRQ | |
| 16, 17 | UART0 TX, RX | to J4 |
| 18, 26-29 | spare | not connected |
| 19, 20 | DC, PE | SN75161B direction, SN75160B pull-up enable |
| 21 | BUS_PWR_EN | high switches 5 V to the transceivers |
| 22, 23 | LED_USB, LED_ERR | yellow and red, high = on |
| 24, 25 | TE_DATA, TE_CTRL | talk enables |

The bus lines are active low on the wire and the transceivers do not invert: the
firmware inverts them (in C now, in the pads when PIO takes over), so the bus engine
sees 1 = asserted.

## 3. Firmware (RP2350, Pico SDK 2 + TinyUSB)

This section is the target. v0.1.0 (`firmware/README.md`) has the Prologix
personality, the console, the reset interface and the failsafes, with the bus engine
in C. USBTMC, PIO and A/B images are still to come.

**USB composite device:**
1. **CDC 0, "GPiBridge GPIB"**: the Prologix-compatible controller (`++` commands,
   escaping, `++read eoi|char`, `++auto`, `++eos`, `++eot_*`, `++spoll`, `++srq`,
   `++trg`, `++clr`, `++ifc`, `++loc`, `++llo`, `++rst`, `++savecfg`, `++mode` 0/1,
   `++lon`, `++status`, `++ver`, `++help`), plus GPiBridge extensions under `++t ...`.
2. **CDC 1, "GPiBridge console"**: newline-delimited JSON logs and commands (`status`,
   `selftest`, `trace on`, `bus`, `pins`, `config`, `reboot bootsel`, `version`). It is
   written for an LLM to read.
3. **USBTMC/USB488** for one GPIB address at a time: `/dev/usbtmcN`, VISA
   `USB0::...::INSTR`, with REN control, SRQ as an interrupt-IN, and READ_STATUS_BYTE as
   a serial poll.
4. **Reset interface** for `picotool reboot -f -u`, so reflashing needs no button.

**Bus engine.**
- PIO programs: the source handshake (talker), the acceptor handshake (listener), and
  a passive bus sniffer.
- In C: controller functions (IFC, REN, ATN with addressing, SDC, DCL, GET, LLO, GTL,
  serial and parallel poll), and timeouts everywhere.
- A mutex arbitrates between the CDC and USBTMC front ends.

**Safety.**
- The transceivers stay powered off until the pins are configured.
- A crash counter in the watchdog scratch registers reboots into BOOTSEL after three
  crash loops.
- A/B images with "try before you buy": a new image confirms itself only after USB
  enumerates.

**Tests without hardware.**
- The bus engine and the Prologix parser compile for the host against a simulated
  IEEE-488 bus with scripted instruments: `make -C firmware test`.
- On hardware, `tools/gpibridge.py test` talks to a real instrument (the bench's HP
  33120A) through both personalities.

## 4. The work, in order

Status: `[ ]` to do, `[~]` under way, `[x]` done.

1. [x] Read the earlier boards; write `CLAUDE_PCB.md` (in OpticsPCBs then; its public
   snapshot is here).
2. [x] Name, directory, licences (CERN-OHL-P-2.0 hardware, MIT software), the prompt
   in `CLAUDE_CODE_CHAT.md`, this plan.
3. [x] Datasheets in `datasheets/` (ignored; `tools/fetch_datasheets.py` fetches all 22);
   parts chosen with JLCPCB stock and price (`gen/parts.py`, `tools/jlc_api.py`).
4. [x] Tooling, copied into `tools/` so the project stands alone:
   - the schematic writer (from ECP5-2ADC-2DAC's `kisch.py`);
   - the s-expression helpers;
   - JLCPCB parts, land-pattern and rotation tools;
   - KiCad discovery.
5. [x] Library: project-local symbols, footprints and 3D models. These are copied from
   KiCad's own where they exist; generated for the GPIB plug, its 3D model and the
   graphics. Every symbol pin is checked against its datasheet figure.
6. [x] Schematic: one page in the Art of Electronics style. USB and power on the left,
   the MCU in the middle, the transceivers and the plug on the right, power from the
   top, notes at the nodes. ERC clean, plus a netlist path trace. (Done 2026-10-06:
   ERC 0 at every severity; `tools/check_pins.py` checks every symbol pin against its
   datasheet.)
7. [x] PCB (2026-10-06):
   - floorplan, then placement by hand in code (`gen/placement.py`);
   - Raspberry Pi's regulator copper, footprints and USB lines copied from their RP2350A
     Minimal design, turned with the chip (`gen/rpi_minimal/`);
   - routing by plan (`gen/routes.py`: the ribbon to the transceivers, the bus side, the
     In2 lanes, every decoupling capacitor and the USB, VBUS and 5 V switch wiring); the
     maze router (`gen/routing.py`) adds only the supply fan-outs and the crystal's two
     traces;
   - zones filled and saved in the file;
   - DRC at every severity with schematic parity: **0 items** (`tools/pcb_check.py`);
   - silkscreen (`gen/silk.py`): connector, LED, button and test-point labels, the
     transceivers by part number, the plug's contact numbers and name, the identity on
     the back; designators of the chips and transistors only, the rest on the fab layer.
8. [x] Manufacturing (`mfg/make_release.py` writes `mfg/release/`):
   - gerbers, BOM, CPL native and JLC-corrected, assembly drawings, fabrication notes
     and a cost estimate (about $111 for five boards);
   - checks: codes against their descriptions, land patterns against the board
     (`FOOTPRINT_CHECK.txt`), and `PLACEMENT_CHECKS.txt`, with a CPL correction
     predicted for every polarized part from JLCPCB's own drawing of it.
9. [x] Enclosure: FreeCAD's Python (not OpenSCAD: FreeCAD can intersect the housing
   with the board's STEP export), STEP and STL for JLC3DP, 0 overlaps with the board's
   3D model, and renders.
10. [~] Firmware v0.3.0 (0.3.0: one image for both boards, the Lite's open-drain pin layer):
    - the Prologix personality, one serial port (the console optional), the reset
      interface with Microsoft OS 2.0 descriptors, settings in flash, the failsafes;
    - the bus engine in C, and the bus capture on core 1;
    - host tests: `test_prologix`, `test_wire`, and sigrok's decoder on the simulated
      bus.

    Still to do: USBTMC/USB488, device mode, the PIO engine, A/B images.
11. [x] Host tool `tools/gpibridge.py`: find the device, console client, flash, test.
12. [x] Documents: `README.md`, `HANDBOOK.md`, `AGENTS.md`, `DESIGN_NOTES.md`,
    `firmware/README.md`, `docs/` (renders, pinout, schematic PDF).
13. [x] A self-review: `DESIGN_NOTES.md` §4.
14. [x] A response in `CLAUDE_CODE_CHAT.md`.
15. [x] GPiBridge Lite (Prompt 6): the generators take `GPIBRIDGE_VARIANT=lite`; its
    schematic (ERC 0), board (DRC 0, every connection planned), JLCPCB release
    (`mfg/release-lite/`), lid, firmware pin layer and wire-level test.
16. [x] The plug from NorComp's own drawing and 3D model; the housing checked against
    the model.
17. [x] Both boards ordered from JLCPCB, 2026-10-06 (5 of each, 2 assembled).
18. [x] Its own public repository (Prompt 9): moved out of OpticsPCBs, every committed path
    relative, a public snapshot of `CLAUDE_PCB.md`. The housing's screws corrected to
    M2 x 8 (M2 x 10 would bottom out), with the stack checked on every build.
19. [ ] Bring-up, when the boards arrive (`BRINGUP.md`).

## 5. Open questions (to Jason, when he is back)

- **Ordered 2026-10-06, not yet received:** both boards, 5 of each with 2 assembled
  ($24.80 + $60.56 and $25.85 + $40.18). In GPiBridge's preview every rotation was
  right, and Jason moved the USB-C onto its pads by hand; the Lite's had the same
  1.57 mm offset. The JLCPCB CPLs now move it themselves, for later orders. Look at J1
  on both boards first when they come.
- **The SN75161B** had only 90 in JLCPCB stock on the day of the order. For later
  orders, check again, or consign TI's from Digi-Key.
- **A USB PID.** 1209:0001 is pid.codes' test PID. A release needs its own: free from
  pid.codes for open hardware once the repository is public, or from Raspberry Pi's own
  scheme (VID 0x2E8A) for products on their chips.
- **A real plug in hand** before the housing is ordered: its body now comes from
  NorComp's 3D model (2020), and the drawing has moved on to rev 15.
- **The Lite's plug.** It uses GPiBridge's footprint, so NorComp's plug fits it. A cheap
  "24P male solder type" plug probably fits too (UsbGpib V2's board has the same
  pattern), but its body may not fit the housing: try one before ordering more.
- **Jack screws: decided against.** The flange's holes fall over the board's USB and
  UART circuits, and UsbGpib V2 does without them too.
