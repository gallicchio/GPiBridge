# Pin audit: GPiBridge and GPiBridge Lite, rev A (2026-11-16)

Why: ECP5-2ADC-2DAC rev A (another of Jason's boards) came back with its USB port dead. Its FT2232H's VPHY and VPLL
got 1.8 V where the data sheet says 3.0-3.6 V, and its D+ and D- were swapped. The author's pin audit and five
reviews had passed both faults. This audit redoes the two checks of `CLAUDE_PCB.md` ("Two checks no board ships
without", section 10 gate 2a-2c) from the data sheets: every IC power pin by voltage, and every pair connector to chip
by pin function. It ran on the netlists as ordered and changed nothing in the design.

**Result: no BLOCKER or HIGH.** Every pin number the generator chose matches its data sheet. Every supply pin of every
IC is on a rail inside its range, with one exception: the transceivers' 5 V has no margin at USB's minimum VBUS.
USB D+/D- reach USB_DP/USB_DM the right way round, and so do all 16 GPIB lines, by function, through the SN75160B and
SN75161B. Board A1 (2026-11-16) confirms the USB pair, the crystal and the 3.3 V rail on hardware.

## Red flags

| severity | board | finding | evidence | on a built board | workaround / rework |
|---|---|---|---|---|---|
| MEDIUM | GPiBridge | The SN75160B and SN75161B get VCC from VBUS through Q1. At USB's minimum VBUS that is 4.737 V, against their recommended minimum of 4.75 V. A long cable or a bus-powered hub (4.40 V) takes it lower. A Type-C source may give up to 5.5 V, above their 5.25 V maximum (absolute maximum 7 V). | U2.20, U3.20 on `+5V_GPIB` = Q1.D. Q1.S is on `VBUS`. sn75160b.txt:227 and sn75161b.txt:370: "Supply voltage, VCC 4.75 5 5.25 V". AO3401A RDS(ON) < 60 mΩ (AO3401A_C15127.txt:12) × ≤ 222 mA gives 13 mV. VBUS is 4.75-5.25 V at a host port (USB 2.0 §7.2.1, from memory). The engine fails both pins (`GPiBridge_GPiBridge.out`). | It probably works: Schottky-TTL parts usually run at 4.5 V. Below 4.75 V, bus drive levels and timing are outside TI's specification. | Use a high-power port and a short cable. Measure `+5V_GPIB` with the bus driven (REVB.md's open question "Is +5V_GPIB above 4.75 V…", BRINGUP.md stage 1b). For rev B, consider a 5 V boost or a USB-PD request. DESIGN_NOTES.md risk 6 already records it. |
| LOW | Lite | With the Lite unpowered, its RP2354A pins sit on the bus through 100 Ω. An instrument's idle bus line may be as high as 3.7 V, above the 3.63 V an unpowered fault-tolerant pin is rated for. | J2 contacts → R30-R45 → U1 GPIO0-15. sn75160b.txt:264: bus port voltage, driver disabled, II(bus) = 0: "2.5 3.0 3.7" V. rp2350-datasheet.txt:86461 ("very little current … below 3.63 V and IOVDD is 0 V") and :86690 (VPIN_FT, IOVDD = 0 V, max 3.63 V). | At most (3.7 − 3.63) V across the instrument's ~2 kΩ, about 35 µA a line. Damage is unlikely. DESIGN_NOTES.md §8 computes 3.65 V from the IEEE-488 resistor tolerances; TI's 3.7 V is the higher figure. | None needed. Do not leave a Lite on a live bus unpowered for long. |
| LOW | Lite | The green BUS LED (D2, KT-0805G) is driven from GPIO21 through only 100 Ω, but its forward voltage is 2.6-3.1 V. Depending on the bin it may be dim, or draw up to ~5 mA. parts.py says "on the 5 V transceiver rail, so its 2.6-3.1 V drop does not matter", which is true only on the full board. | Lite net `/BUS_PWR_EN`: U1.33, R18 (100 Ω), D2.A. KT-0805G_C2297.txt:135: "VF 2.6 3.1 V IF = 5mA". | A dim BUS LED with a high-VF part. | None. Check by eye. |
| INFO | both | The RP2350 data sheet's Table 1679 lists IOVDD as "11, 20, 30, 38, 45, 54": it leaves out pin 1 and includes 54 (QSPI_IOVDD). The pinout figure has pin 1 as IOVDD. The board follows the figure, and both pins are on +3V3, so it does not matter here. | rp2350-datasheet.txt:86633 against :1012. | none | none |
| INFO | both | RUN (pin 26) is unconnected and relies on its internal pull-up. The data sheet allows this. With no reset pin, the only resets are SWD, USB (picotool) or a power cycle. | rp2350-datasheet.txt:86605: "RUN 26 … Digital In (FT) … Pull-Up … Chip enable / reset_n". | none | none |
| INFO, *uncertain* | GPiBridge | R21 (10 k to +3V3) holds the SN75161B's DC input high even while the chip's VCC is switched off. TI does not specify input current at VCC = 0. The inputs are pnp ("High-Impedance pnp Inputs"), so back-powering should be negligible. | `/DC`: R21, U1.31, U3.11. | To settle it: measure `+5V_GPIB` (TP4) with the bus off. It should read about 0 V. | none |

## What was covered

Netlists (both current): `hardware/checks/netlist.net` (exported 2026-10-06T21:42:29, one second after
`GPiBridge.kicad_sch`) and `hardware/checks/lite/netlist.net` (21:42:31, after `GPiBridgeLite.kicad_sch`). Both are in
commit e9c8bba ("rev A: ordered"), and nothing under `hardware/` has changed since. So they are the ordered revision.

| | GPiBridge | GPiBridge Lite |
|---|---|---|
| ICs tabled from the data sheets | 4 (RP2354A, SN75160B, SN75161B, XC6206P332MR) | 2 (RP2354A, XC6206P332MR) |
| supply, reference and ground pins checked by voltage | 25 (2 FAIL, the MEDIUM above) | 21 (0 FAIL) |
| lines traced, connector to chip, by pin function | 46 chip by chip, plus 20 end to end through the transceivers | 26 |
| PARTS rows written from memory | 0 | 0 |
| rails | 6 derived (VBUS's range is from memory, USB 2.0) | 5 |

- **Rails.** Each rail was derived from its source; none comes from its name:
  - `+3V3`: XC6206P332MR, 3.234-3.366 V at 30 mA (E-1 table, line 244), widened by load and line regulation to 3.21-3.37 V. A1 measured about 3.24 V (BRINGUP_LOG.md line 58).
  - `+1V1`: the RP2350's own regulator, 1.1 V ± 3 % (line 87035).
  - `VREG_AVDD`: +3V3 through 33 Ω at about 200 µA.
  - `+5V_GPIB`: VBUS through Q1.

  Every rail's name agrees with its derived voltage.
- **Pairs, by function** (`GPiBridge_GPiBridge.out`, `_e2e.out`, `_GPiBridgeLite.out`):
  - **USB:** J1 A6/B6 (D+) → R2 27 Ω → U1 pin 52 USB_DP, and J1 A7/B7 (D-) → R1 → pin 51 USB_DM (Table 1678, line 86615). On hardware, A1 enumerated at full speed (BRINGUP_LOG.md lines 23 and 60). With D+ and D- swapped it could not.
  - **GPIB:** each of the 16 signal contacts goes to its function's transceiver pin. The contact numbers follow IEEE 488.1 (checked against https://en.wikipedia.org/wiki/IEEE-488, fetched 2026-11-16). On the SN75161B each control line lands on its named bus pin, and that matters, because DC steers ATN, SRQ, REN and IFC while TE steers EOI, DAV, NDAC and NRFD. On the SN75160B each data line uses one channel for both its Bc and Dc pins. The same channel's terminal pin then goes to the GPIO in `gen/pins.py` and `firmware/src/board_pins.h`. End to end, each contact reaches only that GPIO. On the Lite, each contact goes through 100 Ω to the same GPIO.
  - **Control inputs and the rest:** TE, PE, TE and DC go to GPIO24, 20, 25 and 19. The SWD connector (Raspberry Pi debug connector specification: 1 SC, 3 SD) goes to SWCLK 24 and SWDIO 25. The UART connector (1 RX into the target, 3 TX) goes to GPIO17 UART0 RX and GPIO16 UART0 TX (data sheet lines 1306 and 1309). The crystal goes to XIN 21 and, through 1 k, to XOUT 22.
- **Pins the generator chose by number**, checked against the data sheets:
  - `gen/symbols.py` RP2354A: GPIO map, USB, XOSC, SWD, RUN, QSPI and all 18 power pins against Tables 1674-1679.
  - The SN75160B and SN75161B pin figures.
  - The GPIB contacts.
  - The debug connectors.
  - `gen/schematic.py`'s `pin("51")`, `"52"`, `"46"`, `"21"`, `"22"`, `"24"`, `"25"`, `"26"` and `"60"`.
  - XC6206 1 VSS / 2 VOUT / 3 VIN (data sheet line 74-76).

  The firmware header matches the netlist.
- **Discretes.**
  - **Q1 AO3401A:** G 1, S 2, D 3 (data sheet top view). Its source is on VBUS and its drain on the load, so the body diode blocks VBUS when Q1 is off. Its gate is pulled to VBUS by 100 k and to about -4.5 V VGS through 4.7 k when Q2 conducts. That is inside ±12 V, and RDS(ON) is specified at -4.5 V.
  - **Q2 2N7002:** 1 GATE, 2 SOURCE, 3 DRAIN (2N7002_C8545.txt:13-16). It is driven at 3.2 V against a VGS(th) of 2.5 V maximum, for a 50 µA load.
  - **LEDs:** pin 1 is K on the Device:LED symbol and on the LED_0805 footprint. The parts' own data sheets give polarity only in drawings.
- **Logic levels.**
  - RP2354A to SN7516x inputs: VOH ≥ 2.62 V against VIH 2.0 V, and VOL ≤ 0.5 V against VIL 0.8 V.
  - SN7516x terminal outputs to the RP2354A: VOH ≥ 2.7 V and VOL ≤ 0.5 V (sn75160b.txt:248-252, sn75161b.txt:399-403). Their unloaded high level (3.5 V typical) is above 3.63 V only at the extreme, and GPIO0-25 are fault-tolerant to 5.5 V while IOVDD = 3.3 V (lines 86459-86464, 86686). The transceivers' 5 V exists only while the RP2354A runs and holds GPIO21 high, so they cannot be powered while IOVDD is off.
  - QSPI_SS goes through 1 k to BOOT, per Raspberry Pi's minimal design.
  - TE_DATA, TE_CTRL and BUS_PWR_EN are pulled down by 10 k, and DC is pulled up by 10 k. No enable or strap pin floats where it is forbidden.
- **Regulators.**
  - **XC6206:** VIN 4.75-5.25 V against its 1.8-6.0 V range. Dropout at 100 mA is 680 mV maximum (line 246), so VBUS down to 4.05 V still regulates. It dissipates ≤ 0.1 W at 50 mA, against 250 mW.
  - **RP2350 core regulator:** VREG_VIN 3.3 V (range 2.7-5.5 V), VREG_AVDD 3.2-3.37 V (range 3.135-3.63 V), output 1.1 V ± 3 % into DVDD (range 1.05-1.16 V).

## What was not checked, and why

- **Which way round the plug is in its footprint** (mirrored or turned 180°). NorComp's drawings carry no contact
  numbers. The footprint's claim (contact 1 at the upper left of the plug's mating face, the receptacle's mirror image)
  agrees with what I remember of IEEE 488.1, but I did not check it against a drawing. HANDBOOK.md step 5 settles it:
  with two pins tacked, meter contact 24 to GND. That test catches both a 180° turn and a mirrored footprint, because
  either puts contact 24 on a signal pad. A1's plug is not soldered yet.
- **Placement orientation of the LEDs, Y1 and the SOT-23s** in JLCPCB's CPL. This is a placement question, not a pin
  question. On A1 the crystal and the switch work.
- **The USB-C pin names** (A6/B6 D+, A7/B7 D-) and the ABM8 crystal's pins (1 and 3 crystal, 2 and 4 ground) come
  from memory: the HRO and Abracon data sheets show them only in drawings. A1 proves both on hardware.
- **VBUS's range** (USB 2.0 §7.2.1) is from memory. The USB specification is not on disk.

## Where the configs and outputs are

- `~/OpticsPCBs/tools/pin_audit/boards/GPiBridge_GPiBridge.py` and `.out`: power and pairs, function by function.
- `~/OpticsPCBs/tools/pin_audit/boards/GPiBridge_GPiBridge_e2e.py` and `.out`: bus lines traced through the transceivers (PASSTHRU).
- `~/OpticsPCBs/tools/pin_audit/boards/GPiBridge_GPiBridgeLite.py` and `.out`.
- The engine is `~/OpticsPCBs/tools/pin_audit/pin_audit.py`, unchanged. Rerun with `python3 pin_audit.py <config> -v`.

## Check 3: connectors against their drawings (2026-11-16)

This is the third check of `CLAUDE_PCB.md`'s top block (section 10, gate 2d): every connector whose correctness depends
on where its pads are, worked out from the placed pads in `hardware/GPiBridge.kicad_pcb` and
`hardware/GPiBridgeLite.kicad_pcb` (both as ordered) and compared with the standard's or the maker's drawing. The pad
transform was checked first: on rotated and bottom-side parts, the track ends land inside the pads as read (203/243 and
173/211), and not under a negated rotation or a mirror.

**Result: no BLOCKER, HIGH, MEDIUM or LOW.** The IEEE-488 plug, the USB-C receptacle and both Raspberry Pi debug
connectors match their drawings on both boards. Neither board has a Raspberry Pi 40-pin header: GPiBridge meets its
host by USB-C only, and the "Pi" connectors are the two 3-pin debug sockets. So there is no HAT, mirroring or HAT
mounting-hole check to make.

### Red flags

| severity | board | connector | finding | evidence | on a built board | workaround / fix |
|---|---|---|---|---|---|---|
| INFO | both | J2, IEEE-488 plug | **The plug's footprint is the right way round; this closes the morning's open question.** Seen from below the board, looking at the plug's mating face with the D's wide side up, contact 1 is at the upper left, 12 at the upper right, 13 at the lower left and 24 at the lower right. That is the mirror image of the instrument's receptacle, as it must be when the two faces meet. | Pads: contact 1 at (143.88, 115.355), 12 at (120.12, 115.355), 13 at (143.88, 119.645), 24 at (120.12, 119.645), all on B.Cu at 180°. The row of 1-12 is north of the row of 13-24, and the back silkscreen's D is 33.6 mm wide on that row against 30.5 mm on the other. Pitch 2.160 mm and rows 4.290 mm apart (NorComp 111-YYY-113L001 sheet 1). The truth is Lake Shore's Model 335 manual, p. 138, Figure 8-7, the IEEE-488 receptacle "as viewed from the Model 335 rear panel": D wide side up, 12 … 1 left to right on top, 24 … 13 below. Wikipedia's "Female IEEE 488 connector" (File:IEEE-448.svg) agrees. Each contact carries its IEEE 488.1 signal (NI GPIB-140B manual, Figure 13). Independently, xyphro's UsbGpib V2 (`HW/REV2/KicadV2/xyp-gpib.kicad_pcb`, fetched from GitHub), which was built in quantity, has ATN, DIO5 and REN at the same offsets from DIO1 to 0.001 mm, also on B.Cu at 180°. | None. | None. |
| INFO | both | J2 | The pin grid is symmetric, so the plug can still be **soldered in turned round by 180°**, with every signal on the wrong contact. Nothing on the board prevents it; the D drawn on the back silkscreen shows the right way. This is already known (`DESIGN_NOTES.md` §2.5). | As above: the grid maps onto itself under a half turn. | A1's plug is not soldered yet (`bringup/STATUS.md`). | `HANDBOOK.md` step 5 / `BRINGUP.md` stage 2: with two pins tacked, contact 24 must read 0 Ω to GND and contact 1 must not. A plug turned round puts contact 24 on DIO1's hole. |

### Connectors checked

`~/OpticsPCBs/tools/pin_audit/connectors/GPiBridge.py`: 18 checks per board, 36 in all, 0 FAIL.

- **J2, IEEE-488 plug (B.Cu):** its mating face points away from the back. The contact grid matches NorComp. The D
  silkscreen is on the 1-12 row. The mating face is the mirror of the receptacle figure. All 24 contacts carry their
  IEEE 488.1 function: 1-4 DIO1-4, 5 EOI, 6 DAV, 7 NRFD, 8 NDAC, 9 IFC, 10 SRQ, 11 ATN, 12 shield to GND, 13-16 DIO5-8,
  17 REN, 18-24 GND. The layout matches UsbGpib V2.
- **J1, USB-C (HRO TYPE-C-31-M-12):** the pads in the order of HRO's recommended layout (component side, opening down):
  A1/B12, A4/B9, B8, A5, B7, A6, A7, B6, A8, B5, A9/B4, A12/B1. The opening faces west, over the board's west edge;
  the shell's front stands 1.20 mm past it. D+ is on A6 and B6 and D- on A7 and B7, so a plug works either way up;
  CC1 and CC2 are separate nets. (HRO's drawing: `datasheets/drawings/hro_typec-1.png`.)
- **J3 SWD and J4 UART (JST SH BM03B-SRSS-TB):** circuit 1 is where JST's SH top-entry drawing puts it. JST's layout,
  seen from the component side with the contacts above the solder tabs, has circuit 1 at the right; the footprint is
  that layout turned, not mirrored. The pinout is the Raspberry Pi 3-pin debug connector specification's (p. 1):
  J3 1 SC/SWCLK, 2 GND, 3 SD/SWDIO; J4 1 RX into the target, 2 GND, 3 TX. Its cable is straight, pin 1 to pin 1 (p. 2).
- **Anything else:** no other connector. H1 and H2 (M2) take the housing's screws and follow no standard.

### Not checked, and why

- **The housing's fit** around J1 and J2 (`enclosure/`). That is mechanical, not a pin question.
- **Which way the plug is actually soldered** on each board. That is assembly; the meter check above covers it.
- **The IEEE 488.1 standard's own figure** is not on disk. The receptacle view comes from an instrument maker's manual
  (Lake Shore) and agrees with Wikipedia and with a board built in quantity, so I did not mark this uncertain.

### Where the files are

- `~/OpticsPCBs/tools/pin_audit/connectors/GPiBridge.py` and `GPiBridge.out`; the helpers are in
  `connectors/_pcbs7_lib.py`.
- Drawings fetched for this check went to the session scratch area (`…/scratchpad/conn_pcbs/dl/`; it may be cleared).
  They are Lake Shore's `335_manual.pdf`
  (lakeshore.com), NI's GPIB-140B manual, Wikimedia's IEEE-448.svg, JST's SH catalogue (rapidonline mirror) and UsbGpib
  V2's board. Nothing was added to this repository except this section.
