# Bringing up the first boards

What to buy, what plugs into what, and in what order. The aim: you plug things in,
Claude works on the firmware, and nobody fiddles with wires. `HANDBOOK.md` §1 is the
checklist for any one board; this file is the plan for the first five, with an LLM
doing the firmware work.

**Status:** rev A of both boards was ordered from JLCPCB on 2026-10-06 (5 boards of
each, 2 of them assembled) and has not arrived yet. When it does, look first at J1, the
USB-C: it should sit on its pads, its face flush with the board's end. JLCPCB's preview
put GPiBridge's 1.57 mm off, and Jason moved it by hand there; the Lite's had the same
offset.

## 1. What to buy

| item | what for | where, about |
|---|---|---|
| **Raspberry Pi Debug Probe** | SWD (load and debug the firmware) and a UART (its log) over one USB cable. It comes with a 3-pin JST-SH to JST-SH cable and two JST-SH-to-0.1" cables (one male, one female). | Digi-Key SC0889, Adafruit, The Pi Hut: $12 |
| a second JST-SH 3-pin cable, or nothing | the probe's two ports both go to JST-SH connectors on the board, but the box has one JST-JST cable. Without a second, push the male 0.1" cable into the female one: a JST-JST cable, pin 1 to pin 1. | |
| **IEEE-488 plugs**, NorComp 111-024-113L001 | one per board, GPiBridge and Lite alike; JLCPCB does not stock them | Digi-Key: $4.22 |
| **M2 x 8 thread-forming screws** (for plastic; pan head up to 4.0 mm across, or cheese head) | two per housing: not M2 x 10, which bottoms out in the base | any |
| **a USB-C data cable** | the adapter's own port. Charge-only cables are common and look identical | |
| **an inline USB current meter** (USB-C) | the current at power-up and with the transceivers on | $10-25 |
| **a GPIB cable** with stacking connectors, any length | puts the Prologix and the new adapter on one bus (stage 3) | used, about $20 |
| optional: **GPIBtap kit**, option E (one male, one female) with long headers | an outside logic analyser on all 16 lines, by DuPont wires (§4) | AnalysIR on Tindie: $20 |
| optional: a **16-channel logic analyser** that sigrok supports | the independent view in §4 | |

Already on the bench and used below:
- the Prologix GPIB-USB (firmware 6.107);
- the HP 33120A at GPIB address 10;
- the SDS2104X Plus;
- a multimeter.

No ST-Link: §5 says why.

## 2. The stages

Each stage says what you connect, what Claude then does, and what "done" means. Claude
works on this PC, through the adapter's USB port and the Debug Probe. Nothing is
soldered until stage 2.

**Stage 0, before power (you, 5 minutes).** Look at the parts listed in
`mfg/release/PLACEMENT_CHECKS.txt`: chip pin 1 marks, LED cathodes, L1's dot. Install
`tools/60-gpibridge.rules` (once per PC).

**Stage 1, the bare board (no plug, no housing).**
- You:
  - the Debug Probe's **D** port to **J3 (SWD)**, its **U** port to **J4 (UART)**;
  - the probe's USB to this PC;
  - the board's USB-C to this PC through the current meter.
- Claude:
  - reads the UART log and the current (you read the meter out, or the probe, once);
  - loads the firmware over SWD (`openocd ... program`, about 2 s, even if USB is broken)
    or over USB;
  - checks that USB enumerates, and reads `++t status`;
  - measures the start-up time (`usb_ready_ms`);
  - checks the 3.3 V, 1.1 V and switched 5 V test points with the scope, if you put
    probes on TP2-TP4.
- Done: the firmware loads, enumerates and reports itself; the currents and rails are as
  in `HANDBOOK.md` §1. Claude can now rebuild and reload the firmware by itself as often
  as it likes.

**Stage 2, the plug (you, 15 minutes: the only soldering).**
1. Push the plug through the housing's base.
2. Lay the board on it, press it down onto the plug (the pins grip their holes), and
   tack two pins.
3. Measure that contact 24 reads 0 ohms to GND (`HANDBOOK.md` step 5).
4. Solder the rest, then close the lid. The debug cables reach J3 and J4 through the lid.

**Stage 3, the cheapest instrument: the Prologix itself.** In device mode (`++mode 0`)
the bench Prologix answers at its own address like an instrument, and its USB side shows
Claude everything that arrived. So both ends of the bus are in software.
- You:
  1. Put the Prologix in device mode first: two controllers on one bus would fight.
     Claude can send the commands.
  2. Plug the GPIB cable's two stacking ends into the Prologix and the new adapter.
  3. Plug both USB cables into this PC.
- Claude, scripted at both ends:
  - every byte value, both ways;
  - EOI and terminators;
  - long transfers;
  - timeouts;
  - serial poll and SRQ (the Prologix sets its status byte with `++status`);
  - `++t capture` records of each, read with sigrok's IEEE-488 decoder.
- Done: the test suite passes at both ends, and the captures show clean handshakes.

**Stage 4, the HP 33120A** (bench, address 10; $200 used, and the bench's usual
GPIB instrument). Plug the adapter into its GPIB socket, the Prologix out of the way.
- Claude:
  - `*IDN?`, settings and readback;
  - a binary arbitrary-waveform upload, ended by EOI;
  - the error queue and SRQ;
  - the same test run through the Prologix for comparison
    (`lab-instrument-control`'s `hp_33120A.py` works through either).
- Done: the 33120A behaves the same through both adapters.

**Stage 5, the dearer instruments, one at a time.**
1. The Keithley 2000 and the SR830: fast reading streams, serial poll.
2. Last, the HP 8753D (RF lab): large binary trace dumps, the speed test.

Moving the bus engine from C to the RP2354A's PIO happens here, if the speed calls for
it.

**Stage 6, GPiBridge Lite** (ordered with GPiBridge, brought up after it). The same
firmware image, already proven on GPiBridge.
- You: stages 1 and 2 with a Lite board (its housing takes the "GPiBridge Lite" lid).
- Claude:
  - `++t status` says `"board":"GPiBridge Lite rev A"` (R21 read low);
  - stage 3 against the Prologix in device mode, then stage 4 on the 33120A;
  - with the scope on a bus line (DAV, say) at the plug: the low level, about 0.2 V
    with one instrument, and the edges through the 100 R;
  - `++t capture` records: on the Lite the pins are the bus itself.
- Done: the same tests pass as on GPiBridge, with one instrument and with two.

## 3. When something is wrong: what Claude looks at, in order

1. **The log**: the UART (Debug Probe), or `++t trace 1`, which logs every transfer.
2. **The counters**: `++t status` (bytes, timeouts, "no listener").
3. **The built-in capture**, no wires needed:
   - Run `python3 tools/gpibridge.py capture 10 "*IDN?" idn`. It records all 16 bus lines
     and the transceivers' direction pins during one query, at 83 ns resolution, and
     writes `idn.vcd`.
   - PulseView opens it, and its IEEE-488 decoder (sigrok's) prints the commands,
     addresses and bytes.
   - The capture sees both sides of every handshake the board takes part in. It cannot
     see traffic between two other devices, and on transmitting channels it sees what
     the board sends, not what the wire carries.
4. **SWD**:
   - halt the RP2354A where it is stuck, read the stack, the variables and the pin
     registers;
   - step through a handshake;
   - catch a hard fault.

   It works even when the firmware's USB is dead.
5. **An outside logic analyser** (§4): for what the board cannot see of itself.

## 4. An outside logic analyser: the wiring

The bus has 16 signal lines: DIO1-8, EOI, DAV, NRFD, NDAC, IFC, SRQ, ATN, REN.
`docs/PINOUT.md` gives each contact's signal.

- **Best: a GPIBtap pass-through** (option E: one male and one female connector, with long
  0.1" headers).
  - The instrument takes the tap's male end, and the adapter plugs into the tap's
    female end.
  - The analyser's flying leads, with their usual 0.1" sockets, push onto the tap's
    header pins: 16 signals and a ground. No clips.
  - It is a $20 kit: two connectors and the headers to solder.
- **8 channels only?** Take the eight control lines (EOI, DAV, NRFD, NDAC, IFC, SRQ, ATN,
  REN). That shows the handshakes, not the bytes.
- **The SDS2104X Plus**: its 16 digital channels, if its MSO option (the SLA1016 probe)
  is there, go on the same header. The inventory says the option exists for that model;
  whether this one has it is not recorded.
- **No tap**: take the lid off. The plug's pins stick out about 4 mm above the board,
  and micro-grabbers clip onto them, contact numbers 1, 12 and 13 marked beside the rows.
  This works, but 16 grabbers at 2.16 mm pitch are fiddly; the tap is worth its $20.

In PulseView or sigrok-cli, name the channels as above (DIO1 ... REN) and add the
IEEE-488 decoder. The board's own captures use those names already.

## 5. The SWD and UART connectors

**Why they are there.** In firmware development they are the way in that does not
depend on the firmware working.
- **SWD (J3)**:
  - load a new build in about 2 s, with no BOOTSEL and no USB, so a build that breaks
    USB costs nothing;
  - halt, inspect and step the code (gdb);
  - read the pin and pad registers, which is a logic probe on the RP2354A itself;
  - catch hard faults.
- **UART (J4)**: the firmware's log, from its first instruction:
  - it keeps going through USB enumeration, re-enumeration and crashes;
  - the start-up timing and every `++t trace` line come out here.

**They are standard** for this chip: Raspberry Pi's 3-pin debug connector (JST-SH,
1 mm), the one on the Pico H and Pico 2 H, pinned as their specification says. Pin 1 is
SWCLK or RX (into the RP2354A), pin 2 GND, and pin 3 SWDIO or TX. The board has the
specification's 100 Ω on each signal. The Raspberry Pi Debug Probe plugs straight into
both: **D** to J3, **U** to J4.

**Why not an ST-Link V2.** It will not talk to an RP2350.
- The RP2350's debug port starts out dormant and must be woken by a special
  line sequence.
- It is built on Arm's ADIv6 debug architecture.
- The ST-Link firmware handles neither, and OpenOCD's RP2350 support is written for
  CMSIS-DAP probes.

The $12 Debug Probe is a CMSIS-DAP probe, cheaper than an ST-Link V3, and fits these
connectors with no adapter. A spare Pico running Raspberry Pi's `debugprobe` firmware
also works, but needs loose wires. A J-Link works too, but it is $60 or more and needs a
JST adapter.

## 6. Start-up time

From plugging in to accepting "++" commands, on this PC (estimates; stage 1 measures them):

| step | time | what sets it |
|---|---|---|
| the RP2354A from reset to `main()` | a few ms | the crystal's start-up, then the boot ROM finding the image in flash |
| `main()` to USB attached | under 10 ms | clocks, pins, TinyUSB |
| attached to configured | 150-300 ms | the host: USB requires it to wait 100 ms after attach, then it resets and enumerates |
| configured to bus ready | 6 ms | the 5 V switch, 5 ms to settle, IFC (150 µs), REN |
| the serial port appearing | Linux and macOS: under 0.5 s in all | the OS's serial driver |

So: about half a second on Linux and macOS. On Windows it is about a second, and a few
seconds the very first time, while Windows installs its own built-in drivers. A Prologix
takes about as long, for the same reasons. The firmware reports its part: the UART's
boot line has `at_ms`, and `++t status` gives `usb_ready_ms`, the time from reset to
the host configuring it.
