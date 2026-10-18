# GPiBridge: design notes

Why the design is the way it is, what has been checked and how, and how rev A is most
likely to fail. `PLAN.md` has the decisions in short. This file has the reasons and
the evidence.

Board coordinates are millimetres from the board's top-left corner, x right, y down.

## 1. The circuit in one page

**Power.**
- USB-C (J1, HRO TYPE-C-31-M-12) has 5.1 k on CC1 and CC2, so it is a sink and
  C-to-C cables give it VBUS.
- VBUS feeds two rails:
  - **+3V3**, from an XC6206 LDO (U4), for the RP2354A, its in-package flash, the
    crystal and the LEDs. The RP2354A makes its own 1.1 V core with its on-chip
    switching regulator, L1, and Raspberry Pi's layout, copied exactly.
  - **+5V_GPIB**, through Q1 (AO3401A P-MOSFET), for the two transceivers only.
- **The 5 V switch.**
  - Q2 (2N7002) pulls Q1's gate down when GPIO21 (BUS_PWR_EN) is high.
  - R15 (10 k) holds BUS_PWR_EN low in reset, and R16 (100 k) holds Q1 off.
  - C8 (10 nF, gate to source) keeps Q1's gate with its source while VBUS rises at
    plug-in, so Q1 cannot turn on by itself then. It also delays the turn-on by some
    tens of µs, but the switching edge itself is fast.
  - The 2.2 µF behind the switch takes at most 11 µC, inside USB's 50 µC for a load
    switched on after configuration. The 11 µF on VBUS supplies it at first: VBUS dips
    by under 1 V for microseconds, still well above what U4 needs to hold +3V3.
  - The green BUS LED (D2) hangs on +5V_GPIB itself: it shows in hardware that the
    transceivers have power.

**The bus.**
- **SN75160B** (U2) carries DIO1-8. **SN75161B** (U3) carries DAV, NRFD, NDAC, EOI,
  ATN, SRQ, IFC and REN.
- Both sit between the RP2354A's GPIO0-15 and the plug (J2), without inverting.
- The RP2354A sets their direction:
  - TE_DATA (GPIO24) and TE_CTRL (GPIO25): talk enables;
  - DC (GPIO19): controller or device;
  - PE (GPIO20): totem-pole or open-collector data.
- Pulls that hold a safe state while the RP2354A is in reset or blank: DC up (device),
  both TEs down (listen), BUS_PWR_EN down (off).

**The rest.**
- A 12 MHz crystal with 15 pF and 1 k, as on the Pico 2.
- USB D+/D− through 27 Ω.
- BOOT (SW1) pulls QSPI_SS low through 1 k.
- Two Raspberry Pi debug connectors (JST-SH, top entry), 100 Ω in series at the
  connector: SWD (J3) and UART0 (J4).
- Yellow USB and red ERR LEDs on GPIO22 and 23.

**Current** (the transceivers from their datasheets; the 3.3 V side estimated):

| | typical | most |
|---|---|---|
| SN75160B, drivers on | 85 mA | 110 mA |
| SN75161B | | 110 mA |
| RP2354A at 150 MHz, flash, LEDs (3.3 V) | 30 mA | 45 mA |
| BUS LED | 2 mA | 2 mA |
| **from VBUS** | **about 200 mA** | **about 265 mA** |

The USB descriptor asks for 300 mA. An unconfigured USB device may take only 100 mA,
so the transceivers are switched on only once the host has configured it (§2.2).

## 2. Why it is built this way

### 2.1 Real IEEE-488 transceivers

The Prologix, AR488 and UsbGpib all drive the bus from microcontroller pins. That
works on a short bench bus, but it is not IEEE-488.1:
- no 48 mA sink;
- no bus terminations;
- no receiver hysteresis;
- with the adapter unpowered, its pins load the bus, or worse, power the
  microcontroller through its clamp diodes.

The SN75160B and SN75161B are the standard's own parts. They provide all of this, and
their bus pins go high-impedance at VCC = 0 (datasheet: "active bus-terminating
resistor circuits designed to provide a high impedance to the bus when supply voltage
VCC is 0"). The cost is board area (25.5 mm of height where UsbGpib V2 has 15 mm) and
about $7 in parts. The SN75161B is the single-controller version; the SN75162B, with a
separate SC pin, is out of stock.

### 2.2 Power comes last, and goes first

Plugging an adapter into a running bus must not disturb it:
1. The transceivers stay unpowered until the firmware has set every line to
   "released" and the host has configured USB (`tud_mount_cb`).
2. Then the firmware switches the 5 V on, waits 5 ms, and becomes system controller:
   - listener first (NRFD and NDAC held);
   - then DC low;
   - IFC for 150 µs;
   - REN;
   - ATN with UNT and UNL.
3. On USB unmount or suspend, it unwinds in the reverse order and switches the 5 V
   off.

In reset or blank, the pulls keep the transceivers unpowered. When the 5 V does come
on, they start as a listening device: DC high means they cannot drive ATN, REN or IFC.

Two details:
- **The RP2350's pins are 5 V tolerant only while IOVDD is powered.** The
  transceivers' TTL outputs can reach about 3.5 V. The 3.3 V rail comes up with VBUS,
  long before the firmware can switch the 5 V on.
- **RP2350-E9** (A2 stepping, fixed in A3): a pin with its input buffer on, held only
  by the pad's pull-down, can sit at 2.2 V. It does not touch the control pins:
  - after reset the input buffers are off, so the 10 k pulls work (datasheet appendix
    D.5.1);
  - the firmware drives those pins as outputs from then on.

  The bus pins do rest on pad pull-downs while the transceivers are off. The firmware
  turns their input buffers off then, which is the datasheet's workaround.

### 2.3 No series resistors, and one rule for changing direction

The first draft had 470 Ω arrays between the RP2354A and the transceivers. They are
gone:
- the transceivers' terminal outputs are short-circuit limited;
- without the arrays, all sixteen data wires run as one ribbon on the top layer;
- what the resistors would have excused, a transient fight between two drivers, the
  firmware does not do.

The rule, in `firmware/src/hal_rp2350.c`:
- stop driving the pins that are about to become the transceiver's outputs before
  switching it;
- start driving the pins that become its inputs after.

`firmware/test/test_wire.c` checks the rule. It runs the real pin layer and bus engine
against a model of the two chips built from their datasheets' function tables,
including the SN75161B's EOI, which turns with ATN. After each of the 7373 pin changes
in a session of queries, serial polls, power cycles and an absent instrument, it
checks two things:
- no wire has two drivers;
- nothing is driven high into the unpowered chips.

Four planted bugs (DAV driven before TE, the nibble swap removed, PE high while
unpowered, ATN still driven at power-off) were each caught.

### 2.4 The data byte, nibble-swapped

GPIO0-3 carry DIO5-8 and GPIO4-7 carry DIO1-4 (`gen/pins.py`). In that order the
RP2354A's pins meet the SN75160B's terminal pins, and its bus pins then meet the
plug's two rows (contacts 1-4 above, 13-16 below), without one crossing. The firmware
swaps the nibbles back:
- `wire_byte()` and `bus_byte()` live in `board_pins.h`, which is generated from
  `pins.py`;
- the generator asserts the order;
- `test_wire.c` sends every byte value through the real pin layer and back.

### 2.5 The plug, and which way round it goes

The 24-pin plug sits under the board, its pins up through it, the way UsbGpib V2 has
it and as on a GPIB cable's hood. It is a NorComp 111-024-113L001 or any 24-way male,
DIP solder, 2.16 mm pitch. The footprint numbers its pads by IEEE-488 contact number,
not by solder-cup order.

Its dimensions come from NorComp's own files (Jason fetched them from Digi-Key on
2026-10-06; they sit in the untracked `reference/`): the pin pattern from the drawing
(rev 15, 2025), the body from the 3D model, sliced in FreeCAD. The model settled what
the drawing left out:
- the standoff plate that touches the board is 30.40 × 11.00 mm, the insulator's body
  above it 32.70 × 14.30, the flange's back face 3.50 mm above the board;
- right under the flange the insulator flares out, to within 0.13 mm of the housing's
  first opening, which is now wider (§2.6);
- the pins are 0.6 × 0.3 mm, but 1.0 mm wide for their first 0.5 mm. That shoulder
  grips the recommended 1.00 mm hole, so the plug is pressed in until its standoff
  touches the board (the handbook says so). A 1.1 mm hole would let it drop in, but
  1.00 is NorComp's recommendation and UsbGpib V2's, and the grip holds the plug
  square while it is soldered;
- the drawing's rev 15 gives the pins 5.00 ± 0.38 mm below the body (the 2020 model
  5.50): either way they stand 3.4-3.9 mm above the board, clear of the lid.

The pin grid is symmetric, so the two ways the plug can be wrong both look right:
- **The footprint mirrored.** `tools/check_plug.py` compares four contacts' positions
  with xyphro's UsbGpib V2 board, built in quantity. They match to 0.001 mm.
- **The plug soldered turned round.** Nothing mechanical prevents it. The check is a
  meter after two pins are tacked (`HANDBOOK.md` step 5): turned round, contact 24
  lands in contact 1's hole.

### 2.6 The housing and where the forces go

Two MJF nylon parts (`enclosure/`), 62.6 × 28.2 mm, drawn in FreeCAD's Python from the
placement table, so a moved part moves its opening.

**Plugging in** pushes the instrument's socket against the plug's flange, the flange
against the base's 3.5 mm front plate, and the plate against your hand. The solder
joints carry none of it. The plate is exactly the flange's height above the board in
NorComp's model (3.50 mm), so the board lies on the plate, the plug's standoff on the
board and the flange on the plate's face, all at once. (It was 3.3 mm, so that the
flange would always bear; but then the plug held the board 0.2 mm up, and the lid's
screws would have pressed it down, bending the board over the plug and leaving the
flange 0.2 mm off the plate after all.)

The plug's body passes through the plate with 0.3 mm all round, and a 0.4 mm step at the
front face makes room for the insulator's flare under the flange. `enclosure/build.py`
puts NorComp's own model of the plug in place when `reference/` has it: no overlap, and
0.30 mm at the closest.

**Pulling out** does go through the 24 solder joints. The flange cannot be held from
the front, because the instrument's own flange sits there, and jack screws cannot be
fitted, because the flange's holes fall over the USB and UART circuits. Every adapter
of this shape (UsbGpib, the commercial ones) works the same way, and 24 through-hole
joints are far stronger than the pull it takes to unplug the connector.

`enclosure/build.py` intersects both parts with the board's full 3D model and reports
0 overlaps, with 0.38 mm over the tallest part (the debug connectors). One base fits
both boards; GPiBridge Lite has its own lid, engraved "GPiBridge Lite", and is checked
the same way.

**The screws** are M2 x 8 thread-forming. They pass freely through the lid's bosses and the
board, so their thread is only in the base's 3.5 mm plate. With the head on the
counterbore's floor, an M2 x 8 has 1.7 mm of thread there, and its tip stops 1.3 mm
short of the 3.0 mm pilot hole's bottom. The M2 x 10 first specified would have
bottomed out 0.7 mm early, its head never seated, or broken through to the front face.
`out/CHECK.txt` now states the stack on every build, and the build fails if a screw
would bottom out. The counterbores are 4.3 mm, wide enough for an M2 pan head (up to
4.0 mm) as printed.

### 2.7 Reflashing without anyone touching it

Four independent ways in, from the most to the least convenient:
1. **`tools/gpibridge.py flash`**: it asks for BOOTSEL through the console port, then
   runs `picotool load`. Alternatively, `picotool reboot -f -u` uses the USB reset
   interface.
2. **Three watchdog resets in a row** start the ROM bootloader by themselves, so an
   image that crashes can always be replaced over USB.
3. **The debug connectors**, for when the firmware runs but its USB does not: the UART
   console takes `bootsel`, and SWD works whatever the firmware does.
4. **BOOT through the lid's pinhole**, held while plugging in. The ROM bootloader
   cannot be overwritten.

### 2.8 Copied where copying is right

Raspberry Pi's "Hardware design with RP2350" asks for its regulator layout to be
copied exactly. `gen/rpi_minimal/` holds their footprints, zones and vias, extracted
from the MIT-licensed RP2350A Minimal design and turned with the chip. The same goes
for:
- L1, the Abracon AOTA inductor, whose polarity dot faces as on their board (the design keeps it;
  rev A was built with an unpolarised TDK VLS201612HBX-3R3M-1, C2042572, because JLCPCB's shelf ran
  out after the order: see risk 8);
- the crystal circuit;
- the 27 Ω USB resistors.

### 2.9 Four layers, every connection planned

- **Stackup:** F.Cu signals and a ground pour; In1 solid ground; In2 lanes and ground;
  B.Cu split between a +3V3 pour (x < 22) and a +5V_GPIB pour.
- **The copper is planned.** `gen/routes.py` lays 434 of the 460 tracks, and the
  ground fan-out vias, from pad positions. The maze router (`gen/routing.py`) adds the
  rest: short fan-outs from the +3V3 and +5V_GPIB pads to their pours, and the
  crystal's two traces. So the copper reads as intended and follows a part that moves.
- **Rebuilds are deterministic.** KiCad's UUIDs come from a seeded generator, so an
  unchanged design rebuilds byte for byte, and git shows only real changes.

### 2.10 Firmware: C first, PIO later

v0.2 runs the handshakes in C, with a timeout on every wait, so it is easy to read and
to test on a PC. Three tests run there:
- `test_prologix.c`, 31 checks: the "++" layer against a simulated HP 33120A;
- `test_wire.c`: the pin layer, as above;
- `sigrok_check.py`: sigrok's own IEEE-488 decoder reads `test_wire`'s recordings of the
  bus, and must find exactly the bytes that were sent. It does, for `*IDN?` and all 254
  byte values, both as the plug sees the bus and as the board's own capture does.

The pins were chosen so that PIO can take over without a board change:
- the data and EOI on consecutive pins (one 9-bit `in` or `out`);
- NRFD and NDAC adjacent (one side-set).

USBTMC/USB488, the PIO engine and A/B images ("try before you buy") are planned, not
written. `PLAN.md` §3 has the target.

### 2.11 One serial port, and its own logic analyser

- **To the computer it is one serial port, as a Prologix is.** A second port would leave
  Prologix software users guessing which COM port to pick. The JSON console is there
  when wanted (`++t console 1`, saved), and always on the UART.
- **Windows binds drivers by itself.** USB 2.1 with Microsoft OS 2.0 descriptors gets
  WinUSB on the reset interface, so there is no unknown device in Device Manager, and
  `picotool` works with nothing installed.
- **The board records its own bus.** The RP2354A's second core sits idle until
  `++t capture start`. Then it records every change of the 16 bus lines and the
  transceivers' direction pins, at 83 ns resolution. `++t capture dump` sends that as a
  VCD, which PulseView reads with sigrok's IEEE-488 decoder.

  Most bus debugging then needs no wires at all. `BRINGUP.md` §4 covers the rest.

## 3. What has been checked

| check | how | result (2026-10-06) |
|---|---|---|
| schematic ERC | `tools/sch_check.py` (kicad-cli) | 0 items |
| symbol pins against datasheets | `tools/check_pins.py` | RP2354A 51 pins and 3 supplies, SN75160B and SN75161B 20 each, plug 24 against IEEE 488.1 |
| board DRC with schematic parity | `tools/pcb_check.py` | 0 items, every severity |
| the same two, GPiBridge Lite | `GPIBRIDGE_VARIANT=lite` | 0 and 0 |
| plug pattern against a working board | `tools/check_plug.py` | same as UsbGpib V2, on both boards |
| every LCSC code against its value | `mfg/make_release.py` | all match |
| JLCPCB's land patterns against the copper | `mfg/footprint_check.py` | no part wants a hole; 5 notes, explained in `PLACEMENT_CHECKS.txt` |
| CPL rotations | predicted per part (`mfg/jlc_rotation.py`) | the method reproduces every top-side correction read on earlier boards: 7 footprints, 14 part numbers; and GPiBridge's own 11, all right in its preview (Jason, 2026-10-06) |
| CPL positions | JLCPCB's model origin per part (`mfg/footprint_check.py`'s datum) | J1, the USB-C, moved 1.572 mm in the JLCPCB CPL: their origin sits nearer the pad row. Before this, every USB-C hung off the board in the preview |
| housing against each board's 3D model | `enclosure/build.py` | 0 overlaps, both boards |
| housing against NorComp's own plug model | `enclosure/build.py`, with `reference/` | no overlap; 0.30 mm at the closest |
| "++" protocol | `firmware/test/test_prologix.c` | 32 of 32 |
| pin directions, power, data path | `firmware/test/test_wire.c` | 7378 pin changes, 0 contention, 0 back-power |
| the Lite's pins: open-drain, never high | `firmware/test/test_wire.c lite` | 10748 pin changes, 0 driven high, 0 without the override, 0 asserted off the bus |
| the bus, read by an independent decoder | `firmware/test/sigrok_check.py` (sigrok-cli's `ieee488`) | 12 of 12 recordings (6 per board) decode to exactly the bytes sent |
| a full rebuild | `python3 build.py` | both boards, every check passes, the same files byte for byte |

## 4. How rev A is most likely to fail

Ranked by likelihood times cost. Each item gives what would happen, what has been done
about it, and what is left.

1. **A part placed turned by JLCPCB.**
   - Every polarized footprint's CPL correction is predicted, not read: JLCPCB's own
     drawing of each part, turned until it lies on ours, by pin number or, for the LEDs
     and L1, by polarity mark.
   - The method reproduces every top-side correction read in earlier previews (7
     footprints, used by 14 part numbers on the Icepi Zero, GPSDO and ECP5-2ADC-2DAC
     boards).
   - Two parts on one footprint can differ, and here they do: JLCPCB draws the
     SN75160B lying down and the SN75161B upright (270 and 0).
   - JLCPCB numbers the yellow and green LEDs' cathode as pad 2, so their polarity
     came from the marks.
   - **Read in the preview, 2026-10-06:** every rotation right. The USB-C sat 1.57 mm
     off its pads, hanging over the board edge, as on every board before: JLCPCB's
     drawing of it has its origin nearer the pad row, and they place their origin where
     the CPL says. The JLCPCB CPL now carries that offset (`mfg/make_release.py`, from
     `mfg/footprint_check.py`).
2. **The plug soldered turned round.** Every signal would be on the wrong contact, and
   the board would see no listener. The meter check after two tacked pins (§2.5)
   catches it before it matters.
3. **No SN75161B.** JLCPCB had 90 on 2026-10-06, and the release flags it as thin
   stock. Its pin-compatible SN75ALS161 is out of stock there too. The SN75ALS162 is in
   stock (485), but it has 24 pins: a rev B footprint. **Left:** the first order went
   in on 2026-10-06. For later ones, check the stock again, or consign TI parts from
   Digi-Key or Mouser (the BOM line becomes "consigned").
4. **Firmware that has never met hardware.** The likely first bugs:
   - USB descriptors: a composite of one or two CDC interfaces and Raspberry Pi's reset
     interface, with Microsoft OS 2.0 descriptors, VID:PID 1209:0001;
   - the 2 µs data-settle and 150 µs IFC timings against a real bus;
   - an instrument that drives EOI or SRQ in ways the simulated one does not.

   **Done:**
   - four ways in (§2.7);
   - JSON on the UART (and the console port);
   - `++t trace 1` and `++t capture`;
   - `tools/gpibridge.py test 10` against the HP 33120A;
   - a staged plan, starting with the bench Prologix as a scriptable instrument
     (`BRINGUP.md`).
5. **The plug against the housing.** Its body is now NorComp's own 3D model (§2.5), and
   the housing fits it with 0.30 mm to spare. **Left:** a real plug; NorComp's model is
   from 2020 and the drawing has changed since (rev 15). A wrong housing is cheap to
   reprint.
6. **A weak USB port.**
   - A bus-powered hub cannot give 300 mA. The host then never configures the adapter:
     `lsusb` lists it, Linux logs "insufficient available bus power", no serial port
     appears, the bus stays off, and the yellow USB LED keeps blinking.
   - The transceivers want 4.75-5.25 V, and a long thin cable can pull VBUS below
     that. The parts usually work at 4.5 V, but that is outside their specification.
7. **Linux's helpful daemons.**
   - Power managers (TLP, `powertop --auto-tune`) suspend idle USB devices. On suspend
     the firmware switches the bus off, so instruments return to local, and the next
     program's open sends IFC again.
   - Older ModemManagers probe new serial ports with "AT" commands, which would go to
     the instrument.

   `tools/60-gpibridge.rules` turns both off for the adapter.
8. **L1 the wrong way round.** The regulator still works, with a little more switching
   noise near VREG_AVDD. The preview check covers it (item 1).
   - Rev A has this case by construction: on 2026-10-18, after the order, JLCPCB ran out of the
     AOTA (3 left for 4 boards) and asked for a replacement; Jason chose the TDK
     VLS201612HBX-3R3M-1, C2042572 (3.3 µH, 1.57 A, 174 mΩ, the same 2016 land, 1.2 mm tall,
     no polarity mark, so its winding is random on the reel). The design keeps the AOTA; the
     bring-up's scope on TP3 (1.1 V) under load is what says whether the orientation matters
     here, at this board's tens of milliamps. Next order: the AOTA's stock on the day, and the
     same substitution if it is short.
9. **ESD on the GPIB contacts.** There is no TVS array, and TI's 1995 datasheets give
   no ESD rating for the bus pins. The contacts sit recessed inside the D shell. Add
   an array only if a board dies this way.
10. **Small things:**
    - a settings write (`++savecfg`) stalls USB for about 45 ms, once, 2 s after the
      last change;
    - 1209:0001 is pid.codes' test PID, fine on the bench but not for release;
    - the 27 Ω USB resistors are an Extended part (no Basic 27 Ω 0402), $3 of setup.

## 5. Critiques considered

What an opinionated forum (EEVblog's test-equipment board, say) would say, and what was
done about it:

| critique | done |
|---|---|
| "Two COM ports and a yellow-bang 'Reset' device in Device Manager: support tickets." | One port by default; WinUSB bound by Microsoft OS 2.0 descriptors (§2.11). |
| "Linux's ModemManager will send AT commands to my instruments." | udev rule; the serial interface also declares no AT command set. |
| "'$22 a board' leaves out the plug and the housing." | The release notes now give the finished adapter: about $30. |
| "It solders in upside down and nobody notices." | Both silkscreens say which side the plug goes on, the back shows the D, and the meter check is in the handbook. |
| "How do I even get a logic analyser on GPIB?" | The board records its own bus as a VCD (§2.11), and `BRINGUP.md` §4 covers the outside options. |
| "Prologix emulation is a dead end: VISA wants USBTMC, like xyphro's UsbGpib." | Agreed for VISA users. USBTMC is next in the firmware, and needs no board change. The "++" set came first because the lab's scripts and PyVISA-py already speak it. |
| "No galvanic isolation: USB ground now ties the PC to every instrument's chassis." | True of the Prologix and UsbGpib too. For microvolt work, put a full-speed USB isolator (ADuM3160 or ADuM4160 type) in the cable. Building one in would double the board. |
| "linux-gpib cannot use it." | True: linux-gpib has no driver for "++" adapters. |
| "No jack screws." | They cannot fit (§2.6); UsbGpib V2 holds by friction too. |
| "No ESD array on USB." | As on Raspberry Pi's own boards. A rev B candidate (USBLC6) if boards die. |
| "The SN75161B is scarce." | Item 3 of §4. |
| "Bit-banged C will be slow for big trace dumps." | Measured at stage 5; the pins are already laid out for PIO. |

## 6. For rev B, if there is one

- A USB PID of our own: pid.codes, free for open hardware once the repository is
  public, or Raspberry Pi's own scheme for RP2040 and RP2350 products. Also the
  repository URL on the silkscreen (the board's back has room).
- An ESD array (USBLC6) on the USB lines, if the first boards suggest it.
- A smaller, cheaper GPiBridge Lite: the rev A Lite (§7) keeps GPiBridge's outline,
  layers and housing so that it can be ordered with it; a later one could shrink to
  UsbGpib V2's size on two layers, with a cheap plug.
- Whatever the first boards teach: the preview's rotations into `jlc_rotation.py`, and
  the real plug's dimensions into `gen/footprints.py`.
- The SN75162B, if it returns to stock, gives REN and IFC their own control (SC).
- The firmware: PIO, USBTMC/USB488 and A/B images. None of them needs a board change.

## 7. GPiBridge Lite

Designed on 2026-10-06 and ordered with GPiBridge the same day (5 boards, 2 assembled,
each), to be brought up after GPiBridge has proven the firmware.

**What it is.** GPiBridge without the SN75160B, SN75161B and their 5 V switch: the
RP2354A's sixteen bus pins meet the plug through 100 R each. Everything else is
GPiBridge's, part for part and place for place: the RP2354A and Raspberry Pi's regulator
layout, USB-C, the crystal, the debug connectors, BOOT, the LEDs, the plug's footprint
and the board's outline. So the same base and lid fit (the Lite's lid is engraved
"GPiBridge Lite"), and the core every GPiBridge test exercises is the same copper.

**One firmware image.** R21 sits on DC (GPIO19) on both boards: 10 k to 3.3 V on
GPiBridge (it keeps the SN75161B a device during reset), 1 k to ground on the Lite.
`hal_init()` reads DC before it drives anything: low, and it runs the Lite's pin layer.
GP26 was the first plan for this strap, but GP26-29 are walled in by the decoupling
capacitors' copper on the RP2354A's left side, and DC already had a resistor in the right
place. BUS_PWR_EN, which switches GPiBridge's transceivers on, lights the Lite's green
BUS LED directly, so BUS means the same on both: the firmware is on the bus.

**Open-drain, guaranteed by the chip.** A line is asserted by enabling its pin's output
and released by making it an input; the pads' output value is forced low with OUTOVER, so
no software path can drive a line high against another device. The instruments'
terminations pull the lines up. Off the bus (USB unconfigured or suspended) every bus pin
is an input with no pull and no input buffer, and the BUS LED is off. `test_wire lite`
checks after every one of its 10748 pin changes that no bus pin drives high, that no
output comes on without the override, and that nothing is asserted while off the bus.

**What 100 R costs and buys.** The RP2350's pins sink 12 mA at 0.5 V (12 mA drive
strength, which the firmware sets). An instrument's terminations (3 k to 5 V, 6.2 k to
ground) look like 3.4 V behind 2 kΩ, so a line held low sits at about:

| instruments on the bus | line held low | of the RP2350's 100 mA total, with all 16 lines low |
|---|---|---|
| 1 | 0.22 V | 25 mA |
| 2 | 0.41 V | 47 mA |
| 3 | 0.59 V | 66 mA |
| 4 | 0.74 V | 83 mA |

TTL reads below 0.8 V as low, and the standard's drivers promise 0.5 V. So the Lite is
for one instrument, and works with up to three on a short cable. In return the resistors
limit the current to under 35 mA if an instrument (a talk-only one, say) drives a line
high while the Lite holds it low, and static on a contact reaches the pin through them.

**The layout.** The RP2354A's pins leave it in the reverse of the plug's contact order,
so the lines must change layer somewhere. GPiBridge's ribbon runs unchanged from the
RP2354A and rises into a row of resistors where the transceivers' terminal pins were,
one over each contact; a via above each takes the line to the bottom layer, straight
down to its contact. REN crosses between contacts 9 and 10 and runs along the gap
between the rows to contact 17; DIO5-8 pass the end of the upper row and come back along
the gap to contacts 13-16. ATN and SRQ, which leave the RP2354A's top side, come under
the ribbon on In2 as on GPiBridge. As on GPiBridge, all the copper is planned except the
supply fan-outs and the crystal's two traces, and DRC is 0. The board's identity is on
the top, in the band the transceivers left; the back's top strip carries the bus lines.

**The cost.** JLCPCB's quote for 5 boards with 2 assembled (2026-10-06): $25.85 + $40.18,
about $66, against $24.80 + $60.56, about $85, for GPiBridge. In a run of 5 assembled,
about $22 an adapter with NorComp's plug and housing, against $30. It is not half the
price, because what both share dominates: JLCPCB's setup, Extended-part and through-hole
fees, the RP2354A, USB-C, crystal, inductor and debug connectors, four layers with ENIG
(most of the PCB price at this size) and the plug. A Lite built for cost would be smaller,
two layers, with a $1 plug and no debug connectors (§6).

## 8. Left plugged into an instrument with the USB unplugged

It happens all the time on a bench. An instrument that is on holds every GPIB line at
about 3.4 V through about 2 kΩ (its terminations, 3 k to 5 V and 6.2 k to ground), so an
unpowered adapter sees 3.4 V on all sixteen of its bus pins.

- **GPiBridge: no effect.** Its pins reach the bus only through the SN75160B and
  SN75161B, which TI specify as not loading the bus with VCC = 0 (glitch-free power-up
  and power-down; at most 40 µA a line). Their 5 V comes on only after USB is configured.
- **GPiBridge Lite: within the chip's ratings on a standard bus.** The RP2350's bus pins
  are fault-tolerant: unpowered, "very little current flows into the pin whilst it is
  below 3.63 V" (RP2350 datasheet, pin types; 3.63 V is the unpowered absolute maximum).
  A standard bus idles at 3.37 V; the worst case of the standard's tolerances (5.25 V,
  resistors 5 % off) is 3.65 V. An instrument with non-standard terminations, pulling
  its lines nearer 5 V, would exceed it: through its 3 k and the Lite's 100 R that is at
  most about 0.4 mA a line, back into the Lite's 3.3 V rail.
- **UsbGpib and the Prologix: back-powered, but unlikely to be harmed.** Both drive the
  bus straight from a 5 V AVR (UsbGpib V2's ATmega32U4, by its BOM; an ATmega164P and an
  FTDI FT245RL in the Prologix, by a teardown on EEVblog), with no transceivers and no
  series resistors. Unpowered, each bus pin's clamp diode to the AVR's supply conducts:
  up to about 1.4 mA a line, some 20 mA in all, into the adapter's dead 5 V rail. The
  rail floats up until the adapter's own draw matches, perhaps 2-3 V, and every bus line
  is pulled down towards it. The instrument still reads the lines as high, and 1.4 mA is
  far below the AVR's 40 mA a pin, so nothing is damaged. But the adapter is outside its
  specification and half-powered: its microcontroller may start, and if its firmware then
  drives a line, a bus that another controller is using could see it.

A minute's test on the bench, for the Prologix: plug it into an instrument that is on,
leave its USB cable unplugged, and measure across the USB cable's VBUS and GND (or the
adapter's USB connector). More than a volt means it is being powered through the bus.

