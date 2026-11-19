# Chat with Claude about GPiBridge, an open USB-C to GPIB (IEEE-488) adapter

Every prompt is recorded here as it was typed, with minor typos fixed, followed by
the response. The design files, scripts and documents in this directory are what the
responses produced. Times are US Pacific.

The project was called Tether488 until Response 2, when it became **GPiBridge**. This
log keeps the names as they were at the time; everything else in the repository uses
the new one.

Prompts 1-8 were worked in `OpticsPCBs/GPiBridge/`, inside Jason's private OpticsPCBs
repository. Prompt 9 moved the project here, to its own public repository. Paths in the
earlier responses are as they were then: `../CLAUDE_PCB.md`, for one, is now
`CLAUDE_PCB.md`, a public snapshot of that file, and since Prompt 10 the releases'
`<board>_cpl.csv` and `<board>_cpl_native.csv` are `<board>_cpl_jlcpcb_upload.csv` and
`<board>_cpl_kicad_native.csv`.

## Background: where the idea came from

The idea began in a conversation about the lab's bench-instrument library
(`lab-instrument-control`). Its GPIB support goes through a Prologix GPIB-USB controller
($299.95 today); NI's GPIB-USB-HS+ costs $1,189. Either costs more than many of the used
instruments it would talk to. The outline that came out of that conversation:

- **What to clone.** Clone the Prologix behaviour (its documented "++" command set
  over a USB serial port), not NI's undocumented USB protocol. Cloning NI would mean
  using NI's USB vendor ID, which a public design cannot do. Add a second, standard
  personality, USBTMC/USB488 as in xyphro's MIT-licensed UsbGpib. That one works with
  NI-VISA, Keysight VISA, PyVISA and Linux's `usbtmc` driver without impersonating
  anybody.
- **Microcontroller.** A Raspberry Pi RP2350:
  - its PIO state machines run the GPIB handshake at full speed;
  - its ROM USB bootloader can be entered from software, so new firmware goes in over
    the one USB cable with nobody pressing a button;
  - its partitioned boot can fall back to the last good image.
- **Bus transceivers.** Real IEEE-488 transceivers (SN75160B data, SN75161B control),
  which the Prologix lacks. They give the 48 mA drive the standard asks for, the bus
  terminations, and high impedance when unpowered, so an adapter left on a bus with
  the PC off does not drag every line low.
- **Price.** About $20-25 per board for 20, landed, against $299.95 and $1,189.

## Prompt 1

I will continue lab-instrument-control in a different claude session. Here let's switch
to the GPIB USB board that you outlined. A different claude is working on the
ecp5-2adc-2dac (or ECP5-2ADC-2DAC). I want you come up with a unique but descriptive
name for the USB GPIB project that won't conflict with any of the commercial or open
source projects. Then make a new project directory in OpticsPCBs. Write your plan there
and then start executing it. You should take inspiration from the other claude-generated
PCBs, which are GPSDO-PYNQ-Z2 and ECP5-2ADC-2DAC. They each have a long chat session,
where you can get a sense for what I care about and had to nudge other agents about with
respect to PCB design. There is also ~/ai_unleashes_chaos, which has also been
successfully assembled at JLCPCB. In fact, the first thing you should do is spend plenty
of time looking at what worked and didn't work about those projects and write a document
in OpticsPCBs/CLAUDE_PCB.md that contains all of the lessons learned, including my high
bar for neat, clear, well-labeled schematics, neat component placement, neat PCB layout,
and neat and informative PCB silkscreen. Then record this prompt at the start of a new
CLAUDE_CODE_CHAT.md under the new directory you make with the name of the project.
Eventually I might like to release this, so make an MIT or permissive open hardware
license. Keep this project self contained and not dependent on or referring too much to
other things in OpticsPCBs in case I decide to extract it to a stand-alone repo if this
is successful. Then go nuts all night in KiCad 10 and make this thing happen and make it
beautiful. You'll need to think about the housing and mounting. UsbGpib's single USB-C
receptacle out of the side of a thin board is good. Design the enclosure with it, either
3D printed or something that a place like JLCPCB can manufacture simply, in house. If
UsbGpib V2 is a better or more reliable starting point than Prologix, take inspiration
from that. Design whatever it is that you and other LLMs will have an easy time
debugging and using while I go off and work on other things.

<!-- typos fixed in the prompt above: "GPIP USB board" -> "GPIB USB board"; "USB GPIP
     project" -> "USB GPIB project"; "kicad 10" -> "KiCad 10"; "USBGpib V2" -> "UsbGpib V2" -->

## Response 1 2026-10-05 23:25 - 2026-10-06 06:06 Claude Opus 5.5 Max

*Nothing is committed: `Tether488/` and `../CLAUDE_PCB.md` are new, untracked files on
the `ecp5-2adc-2dac` branch, and nothing in the ECP5 project was changed.*

**Tether488** is a USB-C to GPIB adapter that plugs straight into an instrument's GPIB
socket. To the computer it is a Prologix-compatible controller.
- **Rev A is designed and every check passes.** The board is ready to order from
  `mfg/release/`, and the housing from `enclosure/out/`.
- **The firmware (v0.1.0)** builds and passes its host tests. Nothing has run on real
  hardware yet.

![the housing, closed](docs/images/housing_closed.png)

| | |
|---|---|
| ![the board, top](docs/images/board_top.png) | ![the housing, open](docs/images/housing_open.png) |

### What was done, in order

1. **Lessons.** I read the chats, reviews and release notes of GPSDO-PYNQ-Z2,
   ECP5-2ADC-2DAC and the Lorenz board (`~/ai_unleashes_chaos`), and wrote
   `../CLAUDE_PCB.md` from them. It covers how you work, sources of truth, sourcing,
   schematics in the Art of Electronics style, placement and routing, silkscreen,
   mechanics, the JLCPCB package, bring-up, the verification gates and KiCad 10's
   quirks. It grew during the night (§8, §9 and §11 have tonight's lessons).
2. **The name, Tether488.** A search on 2026-10-05 found no product, project or
   trademark using it. It avoids Prologix, AR488, UsbGpib/GPIBee, GPIBUSB, gpib4pi,
   GrasPiB and the vendor names USB-488, 488-USB, KUSB-488 and TEK-USB-488.
3. **The plan and licences:** `PLAN.md` (decisions, GPIO map, firmware target, the
   steps); CERN-OHL-P-2.0 for the hardware, MIT for the software (`LICENSE`).
4. **Library and schematic.** One page, ERC 0. Every symbol pin is checked against its
   datasheet figure in code (`tools/check_pins.py`), and the plug's 24 contacts against
   IEEE 488.1.
5. **Board.** 60 × 25.5 mm, four layers.
   - Placement is in code; Raspberry Pi's RP2350 regulator layout is copied exactly.
   - 434 of the 460 tracks are laid by plan from pad coordinates.
   - DRC is 0 at every severity, with schematic parity.
   - The silkscreen labels every connector, LED, test point and the plug's contacts.
6. **JLCPCB release:** `mfg/release/`, about $111 for five assembled boards (about $22
   each). The CPL carries a rotation correction predicted for every polarized part.
7. **Housing:** two MJF nylon parts drawn in FreeCAD's Python from the placement, 0
   overlaps with the board's full 3D model.
8. **Firmware v0.1.0** (Pico SDK 2.1.1 + TinyUSB):
   - the Prologix "++" set, a JSON console, Raspberry Pi's reset interface, settings in
     flash, and the failsafes;
   - two host tests: the protocol against a simulated HP 33120A, and the pin layer
     against the transceivers' function tables.
9. **Host tool:** `tools/tether488.py` finds the adapter by its USB names, asks
   instruments, tests, and reflashes.
10. **Documents:** `README.md`, `HANDBOOK.md` (bring-up, use, recovery), `AGENTS.md`
    (for the next LLM), `DESIGN_NOTES.md` (the reasons, the evidence and a self-review),
    `firmware/README.md`, and `docs/` (renders, pinout, schematic PDF).

`python3 build.py` remakes all of it from the generators, with every check, in about
90 s. The schematic and board come out byte for byte the same from an unchanged
design.

### The decisions

| question | decision | why |
|---|---|---|
| what the computer sees | a Prologix "++" controller on a USB serial port, plus a JSON console port; USBTMC/USB488 later | PyVISA-py, EZGPIB, KE5FX and `lab-instrument-control` speak "++" already. Not NI's protocol: that needs NI's USB vendor ID |
| starting point | UsbGpib V2's form (plug under a thin board, USB-C out of the end); the Prologix's command set | V2's form survived many builds; the plug footprint is checked against V2's board |
| microcontroller | RP2354A (RP2350 with 2 MB flash inside) | PIO for the handshake later; the ROM bootloader reachable from software; one part fewer |
| bus drivers | SN75160B + SN75161B, the standard's own transceivers | 48 mA sinks, terminations, hysteresis, off the bus when unpowered. The Prologix, AR488 and UsbGpib have none of these |
| bus power | 5 V to the transceivers through a P-MOSFET, on only after USB is configured and every line is released | plugging into a live bus cannot glitch it; the 100 mA rule before configuration |
| debugging | two Raspberry Pi 3-pin debug connectors (SWD, UART) under openings in the lid; BOOT behind a pinhole | a Debug Probe plugs in with the housing closed; four independent ways to reflash |
| layers and routing | 4 layers, all copper planned in code | a solid ground under the QFN and USB; copper that reads as intended |
| assembly | JLCPCB, top side only; the plug hand-soldered last, in the housing | JLCPCB does not stock the plug; its height comes from the housing |
| housing | two MJF PA12 parts, M2 thread-forming screws | inserting presses the flange on the housing, not on the solder joints |
| jack screws | none | the flange's holes fall over the USB and UART circuits |

### Found along the way

- **JLCPCB rotations can be predicted.**
  - Turning JLCPCB's own land pattern of each part until its pins lie on ours reproduces
    every top-side correction you have read in previews: 7 footprints, 14 part numbers
    on the Icepi, GPSDO and ECP5 boards.
  - It has to be **per part**: JLCPCB draws the SN75160B lying down and the SN75161B
    upright, on one footprint.
  - **Two-pad polarized parts go by their polarity mark, not their pad numbers.**
    JLCPCB's yellow and green LEDs call the cathode pad 2, and their inductor has its
    dot at the other pad from Raspberry Pi's.
  - `mfg/release/PLACEMENT_CHECKS.txt` lists every part with its prediction and what to
    look for.
- **The plug can be soldered in turned round.** The pin grid is symmetric and nothing
  mechanical stops it. The handbook now tacks two pins first and checks contact 24 for
  0 ohms to ground before the rest are soldered.
- **The RP2350's GPIO erratum E9** (pull-downs that do not pull) does not touch the
  control pins: they are pulled by 10 k resistors after reset, and driven as outputs
  after that. The firmware applies the datasheet's workaround to the bus pins anyway.
- **Every KiCad rebuild used to change about 20 000 lines** (random UUIDs). Seeding
  KiCad's UUID generator made rebuilds identical, so a diff shows only real changes.

### What I need from you

1. **The SN75161B:** JLCPCB had only 90 on 2026-10-06. Order soon, or consign TI parts.
2. **A real plug before the housing is ordered:** its rear body and standoff are scaled
   from NorComp's drawing. Measure one, or tell me the part you will buy.
3. **On ordering day:** read `mfg/release/PLACEMENT_CHECKS.txt` against JLCPCB's
   preview, and tell me what was wrong. It goes into `mfg/jlc_rotation.py`.
4. **When it goes public:** a repository URL for the silkscreen, and a pid.codes USB
   PID (1209:0001 is their test PID).

### How rev A is most likely to fail

From `DESIGN_NOTES.md` §4, which has the full list with mitigations:
1. **A part placed turned by JLCPCB.** The rotations are predicted, not yet read off a
   preview.
2. **The plug soldered turned round.** The meter check catches it.
3. **No SN75161B in stock.**
4. **Firmware that has never met hardware.** There are four ways in to debug it (USB
   console, UART, SWD, ROM bootloader), and `tools/tether488.py test 10` against the
   HP 33120A.
5. **The housing's plug dimensions are estimates.**

### Checks, 2026-10-06

| check | result |
|---|---|
| schematic ERC | 0 |
| symbol pins against datasheets | all agree |
| board DRC, every severity, with parity | 0 |
| plug pattern against UsbGpib V2's board | the same |
| LCSC codes against their values | all match |
| JLCPCB land patterns against the copper | no part wants a hole |
| housing against the board's 3D model | 0 overlaps |
| firmware: protocol test | 28 of 28 |
| firmware: pin-layer test | 7373 pin changes, 0 contention, 0 back-power (and 4 planted bugs caught) |
| full rebuild | 88 s, every step passes |


## Prompt 2

I don't love the name. Is "RaspberryGPiB" a problem for some reason? It's cute because of the RP connection, with the lower-case i. If this is a reasonable name, rename everything to that everywhere in all files, directoires, and references, except for this chat file to keep as a historic record. Add "http://github.com/gallicchio/RaspberryGPiB" on the schematic and silkscreen. That's where this will eventually live, as a self-contained repo.

How do you expect me to debug with logic analyzers? Especially terms of physically connecting wires? What is the exact bring-up plan, outlining exactly what hardware I need to buy and connect to this thing, hopefully with minimal soldering and connector fiddling. I have the hardware in ~/lab-instrument-control along with some other cheap USB logic analysers and things, which I could also buy more of if needed.

What do you expect to use the SWD and UART headers for during the firmware development and testing phase? If those connectors aren't standard for those things, make them standard. Then tell me what I need to buy get from USB to those two connectors. Would a generic ST-Link V2 work, or would I need something fancier? I don't want to waste a lot of time fiddling with custom connectors. I just want to get this thing in, plug it in, and let you work on the firmware for a while. Then you tell me to plug it into my least expensive GPIB instrument and you work on that for a while. Then we can test it on increasingly expensive instruments.

How fast will this boot and be ready for USB commands?

How will it show up under Linux, Windows, and Mac? Will it look exactly the same as the Prologix and be drop-in compatible? It will have a different vendor id and stuff, but how much additional work will people need to do on each OS? Will we only be able to use it with our software, or with any OS and software that is happy with the Prologix hardware (without additional fiddling or settings tweaking)? How is the "firmware updates over the USB-C connector" going to interact with the Prologix compatibility? Does UsbGpib V2 use Prologix commands or something else?

What will be the communities reaction to this? Pretend to be opinionated eevblog users who are both pro and con and give feedback. If that feedback can easilly be incorporated to improve the design, do that.

If "The plug can be soldered in turned round," the PCB silk screen needs an outline of the "D" shape the connector side and a label that says something like "pins stick out on this side" on the other side.

I don't know what "pid.codes PID of our own" means.

## Response 2 2026-10-06 09:04 - 10:04 Claude Opus 5.5 Max

*Still nothing committed. The rename waited for your answer to the first section; see
"Then: GPiBridge" at the end.*

### The name: "RaspberryGPiB" is a problem

[Raspberry Pi Ltd's trademark rules](https://www.raspberrypi.com/trademark-rules/)
forbid using their marks "as part of your company name, company logo or product name".
They also name "using the word 'RASPBERRY' on its own in a brand sense for commercial
purposes in relation to computer hardware, software and peripherals" as a violation.
- RaspberryGPiB is exactly that, and it reads as "Raspberry Pi GPIB": a GPIB board for
  the Raspberry Pi computer.
- That already exists: [GrasPiB](https://github.com/an-ven/graspib), an open GPIB HAT
  for linux-gpib.
- As a private joke it is fine; the day it is on GitHub, Tindie or EEVblog it is a
  liability.

So nothing is renamed yet. These keep your lowercase-i joke without "Raspberry"; none
turned up in use today:

| name | |
|---|---|
| **GPiBridge** | GPIB with the Pi inside it, and it is a USB-to-GPIB bridge (my pick) |
| **RP488** | the RP2350 chip family and IEEE-488 |
| **GPiB-C** | the pun, and USB-C |

Once you pick, the rename takes a few minutes: every file, directory and reference
except this chat, plus `github.com/gallicchio/<name>` on the schematic and the back
silkscreen.

### Logic analysers, and the bring-up plan

The new file `BRINGUP.md` has the whole plan. In short:

- **Mostly there is nothing to wire: the board records its own bus.** The RP2354A's
  second core records every change of the 16 bus lines, and of the transceivers'
  direction pins, at 83 ns resolution. `++t capture dump` sends the record as a VCD:
  - PulseView opens it, and sigrok's IEEE-488 decoder lists the commands, addresses and
    bytes;
  - `python3 tools/tether488.py capture 10 "*IDN?" idn` does it all in one go.

  I tested the path end to end on the simulated bus. sigrok's own decoder, written by
  other people, read back exactly the bytes the firmware sent, for `*IDN?` and for all
  254 byte values. That is now a test (`firmware/test/sigrok_check.py`).
- **For an outside view**, the clean way is AnalysIR's
  [GPIBtap](https://www.tindie.com/products/analysir/gpibtap-gpib-breakout-passthru-analyzer-board/),
  a $20 kit (option E: one male and one female connector, with long headers).
  - The instrument takes the tap, and the adapter plugs into the tap.
  - Your analyser's 0.1" flying leads push onto its header: 16 signals and a ground, no
    clips.
  - An 8-channel analyser gets the eight control lines.
  - The SDS2104X Plus's 16 digital channels also fit, if its MSO option is installed.
    The inventory lists the option for that model, not whether this one has it.
- **What to buy:**
  - a Raspberry Pi Debug Probe ($12);
  - the NorComp plugs ($4.22 each) and M2 screws;
  - a USB-C *data* cable and an inline USB current meter;
  - a GPIB cable with stacking connectors;
  - optionally, the GPIBtap and a 16-channel sigrok-supported analyser.
- **The stages:**
  - **1. The bare board.** You plug in the Debug Probe and USB. I do the rest: load
    firmware over SWD, read the log, check enumeration and the rails. No soldering yet.
  - **2. The plug.** 15 minutes of soldering, the only soldering.
  - **3. The bench Prologix in device mode, as the first "instrument".** Both ends of the
    bus are then scriptable from this PC, so I can test every byte value, EOI, timeouts,
    serial poll and SRQ before touching a real instrument.
  - **4. The HP 33120A.**
  - **5. Then dearer instruments one at a time,** the 8753D last.

### The SWD and UART connectors

- **What they are for:**
  - **SWD:**
    - load a new build in about 2 s whatever state USB is in;
    - halt, inspect and step the code;
    - catch hard faults;
    - read the pin registers.
  - **UART:** the log, from the first instruction, through USB enumeration and crashes.

  With both, I can iterate on the firmware with nobody touching the board.
- **Are they standard?** Yes. They are Raspberry Pi's 3-pin debug connector (JST-SH, 1 mm),
  the one on the Pico H and Pico 2 H, wired to their specification. Nothing to change.
- **What to buy:** the [Raspberry Pi Debug Probe](https://www.raspberrypi.com/documentation/microcontrollers/debug-probe.html),
  $12. Its D port goes to J3 and its U port to J4.
  - The box has one JST-JST cable. For the second port, push the box's male 0.1" cable
    into its female one (pin 1 to pin 1), or buy a second cable.
- **Not an ST-Link V2.** The RP2350's debug port starts out dormant, needs a wake-up
  sequence, and is built on Arm's ADIv6. ST-Link firmware handles neither, and OpenOCD's
  RP2350 support is written for CMSIS-DAP probes like the Debug Probe.

### Boot time

About half a second from plugging in to accepting "++" commands on Linux and macOS.
On Windows it is about a second, and a few seconds the very first time, while Windows
sets up its built-in drivers.
- The host's USB enumeration takes most of that: USB makes the host wait 100 ms after
  attach.
- The firmware's own part is a few milliseconds, then 6 ms to bring the bus up.
- A Prologix takes about as long, for the same reasons.

These are estimates. The firmware now reports `usb_ready_ms` in `++t status` and its
boot time on the UART, so stage 1 measures the real numbers.

### Linux, Windows, Mac, and Prologix compatibility

- **How it shows up.** No drivers to install anywhere.

  | | the port | driver |
  |---|---|---|
  | Linux | `/dev/ttyACM0`, plus a `/dev/serial/by-id/...` name | `cdc_acm`, built in |
  | macOS | `/dev/cu.usbmodem...` | built in |
  | Windows 10 and 11 | `COMn`, "USB Serial Device" | `usbser`, built in |

  On Linux the user needs the `dialout` group, as for a Prologix. The new
  `tools/60-tether488.rules` covers three more things: `picotool` access, autosuspend,
  and ModemManager's habit of probing new serial ports.
- **Drop-in compatible?**
  - **The same as a Prologix:** the "++" commands, the escaping, no baud rate, and no
    DTR needed. Any program that opens a serial port and speaks "++" works:
    - PyVISA-py: `PRLGX-ASRL0::/dev/ttyACM0::INTFC`;
    - EZGPIB, after `++t compat 1` once;
    - KE5FX's tools;
    - `lab-instrument-control`.
  - **Different:**
    - the port's *name* (`ttyACM` rather than `ttyUSB`; `usbmodem` rather than
      `usbserial`);
    - the USB IDs;
    - `++ver`'s text, unless `++t compat 1`;
    - no device mode yet.
  - **What will not find it:** programs that look for the Prologix's FTDI chip by its
    IDs, or use FTDI's D2XX library instead of a serial port.
- **Changed for drop-in use:**
  - It is now **one** serial port by default, as a Prologix is. The JSON console is
    `++t console 1` (saved), and is always on the UART.
  - Windows binds WinUSB to the reset interface by itself, through Microsoft OS 2.0
    descriptors, so there is no unknown device in Device Manager.
- **Firmware updates and Prologix programs** don't interact.
  - Updates go through a separate USB interface, or `++t bootsel`; no Prologix program
    sends either.
  - During an update the serial port disappears and an `RP2350` drive appears.
  - Afterwards the adapter returns with the same USB serial number, so the same COM port
    or `/dev/serial/by-id/` name, and its saved settings.
- **UsbGpib V2 does not use Prologix commands.** It is a
  [USBTMC/USB488 device](https://github.com/xyphro/UsbGpib): it looks like a USB
  instrument to NI-VISA, Keysight VISA and PyVISA, and appears only while the instrument
  is on. That is our planned second personality.

### What EEVblog would say

> **ratsnest_rick:** Finally someone puts real 75160/161s on one of these. Every hobby
> adapter hangs microcontroller pins straight on the bus. That is fine for one DMM on a
> metre of cable, not for a rack.

> **hpib_herbert:** Switching the transceivers' 5 V only after enumeration is the
> sleeper feature. My Prologix clone drags ATN low when the laptop sleeps, and the
> 8566B goes nuts.

> **voltnut_vera:** Open KiCad sources, JLC files, about $30 all in. I'll take five. The
> board recording its own bus into a VCD for PulseView is clever: I've lost evenings
> clipping a Saleae onto a GPIB breakout.

> **scpi_sam:** Prologix emulation in 2026? VISA wants USBTMC. xyphro already did that,
> and it appears only while the instrument is on. Why another serial-port hack?

> **groundloop_gus:** No isolation. Your PC's USB ground is now bonded to every chassis
> on the bus. Enjoy the 50 Hz in your microvolt measurements.

> **winadmin_wendy:** Two COM ports plus a yellow-bang "Reset" device in Device Manager?
> That's a support ticket per user.

> **bom_bob:** "$22 a board" leaves out the $4 plug, the housing and the shipping. And the
> SN75161B: 90 left at JLC.

> **linuxgpib_lars:** No linux-gpib driver, no thanks. Also ModemManager will spray AT
> commands at my instruments.

> **slowpoke_steve:** Bit-banged handshakes in C? An 8753D trace dump will crawl.

> **lawyer_lou:** And don't call it Raspberry-anything.

What I did with it:

| critique | done |
|---|---|
| two COM ports, yellow-bang device (Wendy) | one port by default; Windows binds WinUSB by itself |
| ModemManager (Lars) | udev rule; the serial interface also declares no AT command set |
| the cost (Bob) | the release notes now give a finished adapter: about $30 |
| debugging (Vera) | the board's own capture, a test proving sigrok decodes it, and `BRINGUP.md` §4 |
| the name (Lou) | the first section above |
| the SN75161B (Bob) | its ALS twin is out of stock at JLC too; consign TI parts (`DESIGN_NOTES.md` §4) |
| USBTMC (Sam) | agreed: it is the next firmware personality; no board change needed |
| isolation (Gus) | not on a board this size: for microvolt work, put an ADuM3160-type USB isolator in the cable (`DESIGN_NOTES.md` §5) |
| linux-gpib (Lars) | true, and out of scope |
| speed (Steve) | measured at stage 5; the pins are laid out for PIO |

`DESIGN_NOTES.md` §5 keeps this table.

### The silkscreen

- **The back already had the D outline**, with contacts 1, 12, 13 and 24 numbered; the
  3D render hides it under the plug. I added "the plug goes on this side" inside the D,
  and moved the J2 fab text out of its way.
- **The top now says "pins stick out on this side"** between the pin rows.
- With the meter check in the handbook, that covers both ways to get it wrong: the wrong
  side, and turned round.

### What "a pid.codes PID of our own" means

- **USB devices identify themselves by two numbers:** a vendor ID (VID), which the
  USB-IF sells for about $6,000, and a product ID (PID) that the vendor assigns. Operating
  systems and tools such as `picotool` and our udev rule find a device by that pair.
- **[pid.codes](https://pid.codes/howto/)** owns VID 0x1209 and gives PIDs free to open
  hardware. You send a pull request to their GitHub repository once our repository is
  public with its licences.
- **The adapter now uses 1209:0001,** their *test* PID: fine on the bench, not for
  boards we give away.
- **The alternative:** Raspberry Pi hands out free PIDs under its own VID (0x2E8A) to
  products built on its chips ([raspberrypi/usb-pid](https://github.com/raspberrypi/usb-pid),
  a form).
- **Either way** it is a one-line change in the firmware, the host tool and the udev
  rule.

### Checks, 2026-10-06 09:40

| check | result |
|---|---|
| schematic ERC, overlaps | 0, 0 |
| board DRC, every severity, with parity | 0 |
| silkscreen | 115 labels, 0 problems |
| plug pattern against UsbGpib V2 | the same |
| housing against the board's 3D model | 0 overlaps |
| firmware v0.2.0 build | no warnings; 47.8 kB of code, plus the 192 kB capture buffer in RAM |
| protocol test | 31 of 31 |
| pin-layer test | 7373 pin changes, 0 contention, 0 back-power |
| sigrok's decoder on the simulated bus | 6 of 6 recordings, exact |
| full rebuild | 90 s, every step passes |

New:
- `BRINGUP.md`;
- `firmware/src/capture.c`, `capture_rp2350.c`, `capture.h`;
- `firmware/src/usb_descriptors.h`;
- `firmware/test/sigrok_check.py`.

Changed:
- the firmware: one serial port, the console optional, Microsoft OS 2.0 descriptors,
  `usb_ready_ms`, `++t capture`, version 0.2.0;
- `tools/tether488.py`: `capture`, `console-port`, and working with one port;
- `tools/60-tether488.rules` (ModemManager);
- `gen/silk.py`;
- the cost lines in the release notes;
- `README.md`, `HANDBOOK.md`, `DESIGN_NOTES.md`, `PLAN.md`, `AGENTS.md`;
- `../CLAUDE_PCB.md`.

### Then: GPiBridge

You picked **GPiBridge** (09:50). Everything is renamed except this chat:
- the directory (`OpticsPCBs/GPiBridge`);
- the KiCad project and library, and the release files;
- the housing's engraving and the board's silkscreen;
- the firmware's USB strings, `gpibridge.uf2`, `tools/gpibridge.py` and
  `tools/60-gpibridge.rules`;
- every document, and `../CLAUDE_PCB.md`.

The URL is on the schematic's title block (`https://github.com/gallicchio/GPiBridge`) and
on the back silkscreen (`github.com/gallicchio/GPiBridge`, above the authors).
- GitHub serves https, so the schematic's link uses it.
- The silkscreen leaves the scheme off, as boards usually do.

The descender of the "g" needed the silkscreen's name blocks re-spaced: 0 silkscreen
problems, DRC 0. The full build passes in 104 s, with sigrok's check at 6 of 6.

If VS Code had the old folder open, open `OpticsPCBs/GPiBridge` instead.

## Prompt 3

Quick question: What are the advantages and disadvantages of USBTMC vs Prologix?

## Response 3 2026-10-06 10:56 - 10:57 Claude Opus 5.5 Max

The short version: **Prologix is easier to use and gives more control; USBTMC is the
standard that VISA-based software expects.**

**Prologix ("++" commands over a serial port)**

Advantages:
- **Works everywhere with no install.** It's just a serial port: a terminal program,
  Python with pyserial, or any language can drive it. Every OS has the driver built in.
- **One port reaches the whole bus.** `++addr` switches between up to 30 instruments on
  one cable.
- **Full bus control.** IFC, REN, local lockout, trigger, device clear, serial poll, the
  SRQ line and secondary addresses are all exposed. On a real Prologix, device mode and
  listen-only are too.
- **Existing software and easy debugging.** PyVISA-py, EZGPIB, KE5FX's tools and your
  `lab-instrument-control` already speak it, and you can read the traffic by eye.

Disadvantages:
- **Not a standard.** NI-VISA, Keysight's and R&S's VISA, LabVIEW and MATLAB don't
  recognise it, so instruments don't appear as `GPIB0::10::INSTR` unless PyVISA-py's
  Prologix layer translates.
- **In-band text framing.** CR, LF, ESC and "+" in data must be escaped, which makes
  binary uploads fiddly.
- **Reads end on EOI, a terminator or a timeout.** That's why `++read_tmo_ms` matters so
  much.
- **Shared global state.** Settings like `++addr`, `++eos` and `++auto` belong to the
  adapter, so two programs sharing it can clash.

**USBTMC/USB488 (USB test-and-measurement class)**

Advantages:
- **Standard.** The instrument looks like a native USB instrument (`USB0::...::INSTR`) to
  any VISA library, LabVIEW, MATLAB, PyVISA and Linux's `usbtmc` driver, with no
  adapter-specific code.
- **Clean messages.** Each message carries its length and an end-of-message bit, so
  binary data is safe without escaping.
- **GPIB functions map to proper USB requests:**
  - serial poll is a status-byte request;
  - SRQ arrives on an interrupt endpoint;
  - device clear, trigger, remote/local and abort are each a defined request.
- **Can carry identity.** UsbGpib enumerates once per instrument, so scripts can find a
  meter by name instead of by GPIB address.

Disadvantages:
- **One interface is one instrument.** A bus with several instruments behind one adapter
  fits USBTMC awkwardly. You need several interfaces, or re-enumeration when instruments
  change.
- **Needs VISA installed on Windows.** Windows has no built-in USBTMC driver; NI-VISA or
  Keysight IO Libraries supply one. On Linux the kernel driver and PyVISA-py's USB backend
  can contend for the device.
- **No raw bus access.** No arbitrary bus commands, multi-instrument addressing,
  listen-only or passing control.
- **Harder to debug and more firmware work.** It's binary, so no terminal sessions. The
  class with its USB488 extension, abort handling and SRQ endpoint is more code, and VISA
  implementations have quirks. Your bench notes show USBTMC flakiness on the Siglent SDG
  and the Agilent 33220A.

**For GPiBridge:** the choice is firmware-only, so the plan is both. Prologix covers
scripts, multi-instrument buses, Linux without VISA, and debugging. USBTMC covers
VISA-based software and plug-and-play identity, for the common case where the adapter
plugs straight into one instrument. TinyUSB already has a USBTMC class, so it's the
natural next firmware personality.

## Prompt 4

By "both", do you mean both at once, in that a single GPiBridge presents itself and can
be talked to over either protocol? Or "both" in the sense of you'll develop two versions
of the firmware in parallel and someone can choose to load either?

<!-- typo fixed: "chose to load" -> "choose to load" -->

## Response 4 2026-10-06 11:54 - 11:55 Claude Opus 5.5 Max

I meant both at once: one firmware, and one GPiBridge that offers both interfaces at the
same time. That's what `PLAN.md` §3 describes. The adapter would show up as a composite
USB device:
- the Prologix serial port, which drives any address on the bus, as now;
- a USBTMC/USB488 interface, which VISA sees as an instrument, `USB0::0x1209::…::INSTR`;
- the reset interface, as now.

Whatever software you run uses its own side. TinyUSB can combine USBTMC with serial
ports, and the RP2350 has endpoints to spare.

The details that make this work:
- **Which instrument the USBTMC side talks to.** USBTMC has no notion of a GPIB address.
  The firmware would find the instrument it's plugged into, the usual case for this
  adapter, as UsbGpib does. A saved `++t` setting would override that when several
  instruments share a cable.
- **One transaction at a time.** Both sides share one bus engine, so each transaction
  finishes before the next starts, and the bus returns to idle in between. USB callbacks
  would only queue requests. What can't be fixed in firmware: two programs driving the
  *same* instrument at once can still take each other's replies. That's true of any
  shared instrument.
- **Windows without VISA.** Windows has no built-in USBTMC driver; NI-VISA or Keysight IO
  Libraries install one. Without them, the USBTMC interface shows as an unknown device in
  Device Manager. Prologix software still works fine; the warning is only cosmetic. I'd
  make the interface a saved setting like the console port (`++t usbtmc 0/1`), on by
  default so VISA users get plug-and-play.

Why not two firmware versions to choose between? Switching would mean reflashing, and
there would be two images to test and release. A saved setting gives the same choice
without either.

## Prompt 5

Before you compact, log all my prompts and your replies in a new CLAUDE_CODE_CHAT.md as a
permanent record of our design conversation. There are versions of this file in
ECP5-2ADC-2DAC, with lines like:

```
## Prompt 1
## Response 1 2026-10-01 23:12 - 2026-10-02 06:26 Claude Fable 5.1 Max
```

I have no GPIB connectors to measure for you. If you give me a list of datasheets to
download or, at a minimum, part numbers, I can get some of that information for you.

I'm thinking that this one, with the transceivers and a non-generic connector, can be the
standard version of the GPiBridge. There can also be a cheaper GPiBridgeLite version
without the transceivers and with a cheap Chinese connector. If they can be made to run
the same firmware, that would be nice. For a lower price, you'd give up the ability to
drive a full bus of equipment (you'd need one per instrument), and maybe you'd give up
some protection circuitry. Don't design a whole Lite version, but if this is possible,
let me know what it would take, along with advantages and disadvantages.

<!-- typo fixed: "some of that information for." -> "some of that information for you." -->

## Response 5 2026-10-06 16:15 - 16:22 Claude Opus 5.5 Max

### This log

Every prompt and reply is now here, with headers as in ECP5-2ADC-2DAC's log (time range,
model). Prompts 3 and 4 and their replies had been only in the terminal.

### The plug: what to get

**Nothing about the plug holds up the board order.** Its pin pattern is set by the
standard and matches UsbGpib V2's working board (`tools/check_plug.py`). Only the
**housing** depends on the plug's body behind the flange, which I scaled from NorComp's
drawing because the drawing doesn't dimension it. Two ways to settle it:

1. **Order the plugs now.** You need them for assembly anyway: **NorComp
   111-024-113L001**, Digi-Key, $4.22 each. When they arrive, four caliper measurements
   finish the housing:
   - the plastic body below the flange, length and width (I assumed 34.0 × 14.2 mm);
   - from the flange's back face to the bottom of that body, where it sits on the board
     (assumed 3.47 mm);
   - the pins' length below that (5.5 mm on the drawing);
   - the pins' thickness.
2. **Sooner, NorComp's 3D model of the same part** (a STEP file): on the part's page at
   norcomp.net, or through Digi-Key's "EDA/CAD Models" link. With it, the housing's
   interference check runs against the real shape instead of my estimate.

For a Lite (below), get one or two of the AliExpress "IEEE-488 24P male solder type"
plugs that UsbGpib V2 uses, about $1 each, with the seller's drawing if there is one.

### GPiBridge Lite

It's possible, and it can run the same firmware.

**What changes on the board:**
- No SN75160B or SN75161B, no 5 V switch (Q1, Q2 and their parts), no BUS LED.
- GPIO0-15 go straight to the plug, through 100 Ω each, for current limiting and some
  ESD margin.
- GP26 is tied to ground, as a board-ID strap that the firmware reads at start-up. On
  the full board GP26 is unconnected and reads 1, so rev A needs no change. I've marked
  GP26 as reserved for this in `gen/pins.py`.
- A cheap plug, and probably a UsbGpib-sized board (about 54 × 15 mm) and housing,
  perhaps on two layers.

**What changes in the firmware:** one file, the pin layer.
- The full board's pin layer drives the transceivers.
- The Lite's emulates open-collector: a line is asserted by driving it low and released
  by letting go (making it an input), and never driven high.

Everything above that layer is shared: the bus engine, the Prologix commands, USBTMC when
it comes, the capture, USB and the tests. The capture is even better on the Lite, because
its pins are the bus itself.

**Advantages:**
- **About half the price:** roughly $15 against $30, from no transceivers (about $6) and
  their setup fees, a $1 plug instead of $4.22, and a smaller board.
- **Smaller:** the size of a GPIB cable's hood, like UsbGpib V2.
- **Low power:** about 40 mA instead of up to 270 mA. That fits USB's 100 mA before
  configuration, so it works on bus-powered hubs and can drive the bus from power-up.
- **A true bus analyser:** the built-in capture sees the actual wires.
- **Ahead of UsbGpib V2, a board in the same class:** Prologix and USBTMC in one,
  the capture, and the RP2350's unbrickable ROM bootloader.

**Disadvantages:**
- **Not IEEE-488.1.** The RP2350 sinks 12 mA, not 48 mA, and the Lite adds no bus
  terminations.
  - One instrument is easy: about 1.6 mA per line.
  - A few on a short cable probably work.
  - A full bus of 15 devices on 20 m does not.
- **Unpowered on a live bus.** With its USB unplugged, the instrument's terminations
  hold the lines at about 3.4 V on unpowered RP2350 pins. The RP2350 is 5 V-tolerant only
  while powered, and 3.3 V-failsafe while not, so that is marginal; old instruments that
  pull up to 5 V exceed it. The rule would be: unplug it when its USB is unplugged, as for
  UsbGpib and the Prologix. The full version needs no such rule, because its transceivers
  go high-impedance without power.
- **Less protection.** ESD and wiring faults at the contacts reach the RP2350 through
  100 Ω, instead of through TI's bus drivers.
- **Cheap connectors vary** in plating, D-shell fit and body dimensions, so the housing
  has to fit the exact part.
- **Two pin layers to test.** The wire-level test would get a second model, checking
  that no pin is ever driven high onto the bus.

**What it would take:**
- A second variant of the generators, reusing most of the pipeline: about a day or two
  for the board, release and housing.
- Half a day for the second pin layer and its test.

I'd build it after the full board has been brought up, so the firmware is proven first on
the board with the safer bus drivers.

## Prompt 6

You should have the NorComp 111-024-113L001 from Digi-Key datasheet and 3D model. I'd
want you to design the Lite version at the same time so I can order them at the same
time (5 boards each, 2 assembled each -- the JLCPCB minimum.) We'd certainly build and
test the regular version first, but I'd save on time and shipping at the cost of a
potentially wasted $30.

How bad is to leave the Lite version and the UsbGpib and the Prologix plugged into the
instrument with the USB unplugged. I feel like this happens all the time in the lab.

<!-- the drawing (111-YYY-113L001.pdf, rev 15) and the 3D model (111-024-113L001.STEP)
     arrived in GPiBridge/reference/ at 16:34-16:35 -->

## Response 6 2026-10-06 16:36 - 18:05 Claude Opus 5.5 Max

Both boards are ready to order, 5 boards with 2 assembled each. The full GPiBridge
now uses NorComp's measured plug, and the Lite is designed alongside it. Every check
passes on both: ERC 0, DRC 0 at every severity with schematic parity, no overlaps in
the housing, and the firmware tests. Nothing is committed: `GPiBridge/` is still
untracked.

| | GPiBridge | GPiBridge Lite |
|---|---|---|
| release | `mfg/release/` | `mfg/release-lite/` |
| JLCPCB, 5 boards with 2 assembled | about $78 | about $58 |
| a finished adapter, in a run of 5 | about $30 | about $21 |
| housing | base + `gpibridge_lid` | the same base + `gpibridge_lite_lid` |

![GPiBridge Lite in its housing](docs/images/lite_housing_closed.png)

### NorComp's files

I sliced NorComp's 3D model in FreeCAD. It is from 2020; your drawing is rev 15, from
2025. The model changed four things:

- **The pins grip the holes.** They are 0.6 × 0.3 mm, but 1.0 mm wide for their first
  0.5 mm below the body. In NorComp's recommended 1.00 mm hole (also UsbGpib V2's) that
  shoulder is a press fit. So assembly is: plug through the base, then press the board
  down onto it until it rests on the plug's standoff, then solder. The handbook, the
  housing README and BRINGUP now say so. I kept the 1.00 mm hole: it is NorComp's
  recommendation, and the grip holds the plug square while you solder.
- **The base's front plate is now 3.5 mm** (it was 3.3). The flange's back face is
  3.50 mm above the board.
  - With 3.3 mm, the plug would have held the board 0.2 mm up. The lid's screws would
    then have pressed the board down, bending it over the plug, and left the flange off
    the plate after all.
  - At 3.5 mm the board, the plug's standoff and the flange all meet at once.
- **A flare under the flange.** In its last 0.1 mm the insulator flares out, to within
  0.13 mm of the old opening. The opening now has 0.3 mm of clearance all round,
  plus a 0.4 mm step at the front face.
- **The housing check now uses NorComp's own model.** When `reference/` holds the STEP
  (it stays uncommitted), `enclosure/build.py` puts the plug in place too: no overlap,
  and 0.30 mm at the closest point.

Rev 15 of the drawing differs from the 2020 model in a few dimensions: B 46.70, C
36.20, 3.20 mm flange holes, and pins 5.00 ± 0.38 mm long against the model's 5.50.
None of these touches the board or the housing.

### GPiBridge Lite

- **What's shared:** everything except the SN75160B, the SN75161B and their 5 V switch.
  - It has the same outline, four layers, RP2354A core, USB-C, debug connectors,
    LEDs, BOOT and plug.
  - The shared parts sit in the same places, so the same base fits it. Its own lid is
    engraved "GPiBridge Lite".
- **The bus:** each of the 16 lines goes from its pin through 100 Ω (R30-R45; the
  number is R30 + the GPIO). The firmware drives the lines open-drain, and the pads'
  output value is forced low in hardware (OUTOVER). No software path can drive a line
  high.
- **One firmware image** (v0.3.0) runs both boards.
  - R21 sits on DC on both boards: 10 k to 3.3 V on GPiBridge, 1 k to ground on the
    Lite. The firmware reads DC at start-up, before it drives anything.
  - I had reserved GP26 for this, but GP26-29 are walled in by the decoupling
    capacitors' copper, so DC's existing resistor slot does the job instead.
  - `++ver`, `++t status` (`"board"`) and the USB product string say which board it is.
    The serial port's name is the same on both.
  - The green BUS LED hangs on BUS_PWR_EN, so BUS means "on the bus" on both boards.
- **The layout:** the RP2354A's pins come out in the reverse of the plug's contact
  order, so every line has to change layer once.
  - GPiBridge's ribbon runs unchanged and rises into a row of resistors where the
    transceivers' pins were.
  - A via above each resistor takes its line to the bottom layer, straight down to its
    contact.
  - REN crosses between contacts 9 and 10. DIO5-8 go round the end of the upper row.
  - As on GPiBridge, all the copper is planned except the supply fan-outs and the
    crystal's two traces, which the maze router lays.
- **Tests:** `test_wire lite` checks the Lite's pin layer after every one of 10 748 pin
  changes:
  - no bus pin ever drives its line high;
  - no output comes on before the pad's low override is set;
  - nothing is asserted while the firmware is off the bus.

  Its first run caught a real ordering bug: the BUS LED went off a moment before NRFD
  and NDAC were released. It is fixed. sigrok's IEEE-488 decoder reads 12 of 12
  recordings exactly, six from each board.
- **Its limits:** the pins sink 12 mA, against the standard's 48 mA. A line held low
  sits at about 0.22 V with one instrument on the bus, 0.59 V with three and 0.74 V
  with four, against TTL's 0.8 V limit. So it is for one instrument, or up to three on
  a short cable (`DESIGN_NOTES.md` §7).
- **The price gap is smaller than I said in Response 5.** Most of the cost is shared:
  JLCPCB's fees, the RP2354A, USB-C, crystal, inductor, debug connectors, four layers
  and the plug. Getting near half GPiBridge's cost would take a smaller two-layer Lite
  with a $1 plug, after this one has been proven.

### Left plugged in with the USB unplugged

A powered instrument holds every GPIB line at about 3.4 V through about 2 kΩ (its
terminations: 3 k to 5 V and 6.2 k to ground). An unpowered adapter therefore sees
3.4 V on all 16 of its bus pins.

- **GPiBridge: nothing happens.** Its pins reach the bus only through TI's transceivers.
  TI's datasheets say their outputs "do not load the bus when VCC = 0" (at most 40 µA
  per line).
- **GPiBridge Lite: within the chip's ratings on a standard bus.**
  - The RP2350's bus pins are fault-tolerant. Unpowered, "very little current flows
    into the pin whilst it is below 3.63 V".
  - A standard bus idles at 3.37 V. The worst corner of the standard's tolerances
    reaches 3.65 V.
  - Only an instrument with non-standard terminations, pulling nearer 5 V, would exceed
    the limit, and then only by about 0.4 mA per line.
- **UsbGpib and the Prologix: back-powered, but probably unharmed.** Both drive the bus
  straight from a 5 V AVR (an ATmega32U4 in UsbGpib; an ATmega164P with an FT245RL in
  the Prologix, by an EEVblog teardown). Neither has transceivers or series resistors.
  - Unpowered, each pin's clamp diode feeds up to about 1.4 mA into the dead 5 V rail,
    about 20 mA in all. The rail floats up to perhaps 2-3 V, and every bus line is
    pulled down towards it.
  - The instrument usually still reads the lines as high. 1.4 mA is far below the AVR's
    40 mA per-pin rating, so nothing should be damaged.
  - But the adapter now sits half-powered and outside its specification. If its
    microcontroller wakes and its firmware drives a line, a bus that something else is
    using will see it.

So in your lab: on an instrument nobody is using, all three are fine. On a bus where
other devices are talking, GPiBridge is clean and the Lite almost certainly is. Unplug
a Prologix or UsbGpib, or give it its USB.

A one-minute check you could do: plug the Prologix into a powered instrument, leave
its USB cable unplugged, and measure across VBUS and GND at its USB connector. More
than a volt means the bus is powering it. `DESIGN_NOTES.md` §8 has the numbers.

### Also

- **The board files now get IDs per part.** Each footprint's internal IDs come from its
  own reference, so changing one part no longer rewrites the IDs of every part after it
  in the file. Both boards still rebuild byte for byte.
- **`build.py` builds both boards** in about 3 minutes. `GPIBRIDGE_VARIANT=lite`
  selects the Lite in any single generator or check.
- **The lessons file** (`../CLAUDE_PCB.md`) has five new ones:
  - slice vendor 3D models, and check housings against them;
  - follow the force through a housing's screws;
  - when a chip's pin order is the reverse of a connector's, plan the layer change;
  - board IDs from existing resistor slots;
  - per-part ID seeding.

### What I need from you

1. **Order both releases.** In each preview, read that release's
   `PLACEMENT_CHECKS.txt` against JLCPCB's placement. The SN75161B was still at 90 in
   JLCPCB stock at 18:02 today; this order needs 2.
2. **Plugs:** four NorComp 111-024-113L001 (Digi-Key, $4.22). If you want, add one cheap
   "24P male solder type" plug to try in the Lite: its pins would fit, but its body may
   not fit the housing.
3. **Housing, from JLC3DP:** four bases, two `gpibridge_lid`, two `gpibridge_lite_lid`.
4. **Optional:** the Prologix VBUS measurement above.

Sources: [EEVblog, "Prologix GPIB-USB controller" (its chips)](https://eevblog.com/forum/chat/prologix-gpib-usb-controller),
[time-nuts, 2007: the Prologix's FT245R](https://febo.com/pipermail/time-nuts/2007-April/025452.html),
[CNX Software on xyphro's UsbGpib (ATmega32U4, 5 V I/O)](https://www.cnx-software.com/?p=162532);
TI's SN75160B and SN75161B and Raspberry Pi's RP2350 datasheets are in `datasheets/`.

## Prompt 7

For the standard release, all of the rotations were correct. The USB-C connector had to
be moved because it was sticking too far off the board and its traces were not on the
pads. This has been true for every USB-C connector that you've placed for JLCPCB. If you
know why and can fix this, add that information to CLAUDE_PCB.md. For this board, 5 PCBs
with 2 assembled came to $24.80+60.56~$85 before shipping. For the lite board, it's
$25.85+$40.18 for PCB and assembly. ENIG probably made the PCB expensive. The bords are in
my JLCPCB cart, but have not been ordered yet.

## Response 7 2026-10-06 20:58 - 21:10 Claude Opus 5.5 Max

I know why, and it's fixed. JLCPCB places **their** drawing's origin at the CPL's
coordinates, and their drawing of the HRO USB-C (C165948) has its origin 1.572 mm
nearer the pad row than KiCad's. So the connector landed 1.57 mm outward: over the board
edge, with its pads beside ours.

- **I had the evidence and misread it.** `mfg/footprint_check.py` has measured this
  offset on every board ("datum", 1.305 mm on ECP5's USB-C), but its report called it
  harmless. On the Lorenz board I told you nothing in a CPL could fix it. That was
  wrong: the JLCPCB CPL is read by JLCPCB alone, so it should say where their origin
  goes.
- **The fix.**
  - `mfg/make_release.py` now runs the footprint check before writing the CPLs.
  - It moves each part by its datum, turned with the part, in the JLCPCB CPL only. The
    native CPL is unchanged.
  - J1 now sits at 4.022 mm instead of 2.450 mm in both releases. No other part has an
    offset over 0.1 mm.
  - `PLACEMENT_CHECKS.txt` lists the move.
- **`../CLAUDE_PCB.md`.** The old lesson ("model offsets cannot be fixed from the CPL")
  is replaced with the cause, the fix and the history.

**Your rotation readings** are in `mfg/jlc_rotation.py`: all 11 predictions are now
"read", including the SN75160B's 270 beside the SN75161B's 0 on the same footprint, and
the LEDs and inductor read by polarity mark. The Lite uses only part numbers from that
list, so neither release has anything left to check.

**For your cart:**
- **GPiBridge:** you already moved J1 by hand, so nothing is needed. If you re-upload
  `mfg/release/GPiBridge_cpl.csv` instead, J1 should sit on its pads without a move.
- **The Lite:** same part, same place. Unless you've already moved its USB-C, re-upload
  `mfg/release-lite/GPiBridgeLite_cpl.csv`, or move it 1.57 mm towards the board as on
  the other.

**Costs.** Your quotes are recorded in the release notes, `DESIGN_NOTES.md` and the
README. My estimate was about $5 low on assembly for both boards. It had left out the
through-hole fee the USB-C's soldered shell legs bring, which the lessons file already
listed (about $3.58 an order). With that added, the model is within $2 of each of your
quotes.

**ENIG.** It is about $15 of each roughly $25 PCB price, so lead-free HASL would save
about $30 across both orders. I'd keep ENIG. The RP2354A is a 0.4 mm-pitch QFN with a
large centre pad, which wants a flat finish, and with only two assembled boards of each,
one bad joint there costs more than $15.

## Prompt 8

If I already have to pay for JLCPCB's through-hole labor charge, are you sure they have
no stock on any GPIB connectors, so that I don't need to order them and solder them
myself?

## Response 8 2026-10-06 21:12 - 21:17 Claude Opus 5.5 Max

Yes. I checked JLCPCB's parts library again just now, with 27 searches ("GPIB",
"IEEE 488", "Centronics", "57-30240", "micro ribbon", NorComp's part numbers and more).
**Not one GPIB plug is in stock.**

- **NorComp's 111-024-113L001** is listed as C5470282, with zero stock. They would have
  to pre-order it, at $9.96 each (minimum 1) against Digi-Key's $4.22, and it would have
  to reach their warehouse before they could assemble the boards.
- **The other "GPIB" entries** (C99... codes, brand "JLCPCB Assembly") are placeholders
  other customers made for their own parts, all with zero stock.

**Even with a plug in stock, I'd keep soldering it yourself, because of the housing.**
- The base's front plate sits between the plug's flange and the board. So the plug has
  to go through the base before it is soldered; that is what makes the flange, not the
  24 joints, take the push when you plug the adapter in. A factory-soldered plug could
  not be fitted into this base.
- To change that, the opening would have to pass the whole flange, which reaches within
  0.35 mm of the board's bottom edge. The base would become a thin frame, and the push
  would go through the board and the lid's screws instead. That is a redesign I'd rather
  not rush into this order.
- It would also be the only part on the underside, and its pin grid is symmetric, so an
  operator could fit it turned round. The meter check in the handbook is how you catch
  that when you solder it.

The extra cost of doing it at JLCPCB would have been small: the through-hole fee is per
order, which you are already paying, plus about $0.80 of joints. The plug's price and the
housing are what decide it.

So for this order: four NorComp plugs from Digi-Key ($4.22 each), and about 15 minutes
per adapter at the bench, in the housing's base, with the meter check after two pins
(`HANDBOOK.md` step 5). If a later run should come with the plugs fitted, I'll redesign
the base for it.

`PLAN.md` and the release's `hand_solder.csv` now say this.

## Prompt 9

When you are done, I have created a new github repo and cloned it at
~/mudd/other/GPiBridge/ and you should move everything in GPiBridge. Add a link to this
CLAUDE_CHAT.md to the README.md, say that it's by Jason Gallicchio <jason@hmc.edu> and
Claude, and say that assembled boards have been ordered but not received.

Make a copy of CLAUDE_PCB.md that is sanitized for public viewing (if there is anything
really OpticsPCBs specific and would not be useful for someone pulling only this project
without access to the private OpticsPCBs). However, for future-you and future-me, add a
big note right at the top of the sanitized file that the authoritative source for this
type of information when you are working on it with access to ~/OpticsPCBs should be the
one in there, which will get updated as I have you make and fix more PCBs.

Then commit all relevant files, making sure that they can all be shared publicly.

*Added while the work was under way:*

In general, *all* paths should be relative. Add that as a rule to the main CLAUDE_PCB.md
and check all of the other OpticsPCBs projects for relative paths.

Are the enclosures designed to be CNCed or 3D printed? If I have access to something
like a Bambu Lab 3D printer, would it make much difference if I printed them myself as
opposed to ordering them?

## Response 9 2026-10-06 21:22 - 21:50 Claude Opus 5.5 Max

GPiBridge now lives in its own repository, github.com/gallicchio/GPiBridge, as one
commit on `main`, not pushed. It builds there from scratch with every check passing,
and `OpticsPCBs/GPiBridge/` is gone.

### The move

- **Everything came across**, including the ignored datasheets, NorComp's files and the
  fetched Pico SDK. A full `build.py` in the new place passes: ERC 0 and DRC 0 for both
  boards, no overlaps in the housing, the firmware tests, and sigrok 12 of 12. The board
  and schematic files came out byte for byte as before the move.
- **The README** now says it is by Jason Gallicchio <jason@hmc.edu> and Claude, links
  this log near the top, and says both boards are ordered but not yet received. PLAN,
  BRINGUP and DESIGN_NOTES say so too. BRINGUP's first step when they arrive is to look
  at J1, the USB-C.
- **What stays out of git:**
  - the datasheets, and NorComp's drawing and 3D model;
  - JLCPCB's cached parts data and EasyEDA's land patterns (theirs, not ours to
    publish; the tools fetch them again);
  - the compiled host tests, their recordings, and build products.
- **`CLAUDE_PCB.md` here is a public snapshot.**
  - A box at the top says the working copy is in OpticsPCBs, and that it is the one to
    read and update whenever OpticsPCBs is at hand.
  - It keeps every lesson. It leaves out the other boards' file paths, the prompt
    numbers, the private scripts and the paths on Jason's machines.

### All paths relative

- **The rule** is in both lessons files now, with how to keep it:
  - paths relative to the file or the project (`__file__`, `${KIPRJMOD}`,
    `${workspaceFolder}`);
  - tools found on `PATH` or through an environment variable;
  - scratch files in a build directory;
  - a grep before every commit.
- **In GPiBridge, three files broke it.**
  - KiCad wrote the schematic's absolute path into both netlists. `tools/sch_check.py`
    now rewrites it, relative to the netlist, on every build.
  - The VS Code setting now uses `${workspaceFolder}`.
  - One hit remains, and it is upstream's: KiCad's own crystal model names its author's
    folder in its STEP header. Vendored files stay as KiCad ships them.
- **Jason's other projects break it in about 100 committed files:**
  - KiCad library tables and 3D-model paths that point into other people's home
    directories;
  - netlists, and a plot directory inherited from an upstream project;
  - scripts that read data from outside their repository;
  - caches committed by mistake.

  I listed them for Jason, project by project, and changed none of them.

### The housing: 3D printed, and a Bambu will do

It is drawn for 3D printing, not machining: JLC3DP's MJF, in PA12 nylon. Printing it
yourself makes little difference to how it works, and gets you a test fit before the
boards arrive.
- **Print it in PETG or ASA, not PLA.** PLA softens at about 55 °C and creeps under the
  screws, and the back of a working instrument can run warm.
- **No supports.** Print the base on its front face and the lid on its top face. The
  only overhangs are then a 0.4 mm step and a 1 mm ring under each screw boss.
- **About 10 g of filament a set** (4.7 cm³ for the base, 2.9 cm³ for a lid).
- **The small labels come out soft** from a 0.4 mm nozzle; use a 0.2 mm one.
- **Inside edges print about 0.1 mm small,** and the board has only 0.15 mm all round in
  the base. If it does not drop in, print again with +0.1 mm of X-Y hole compensation.

I'd print one base and lid in PETG now, and try a NorComp plug in it the day the plugs
arrive. `enclosure/README.md` now has all of this.

### Found while checking: the screws were too long

- **The housing called for M2 x 10 screws.** With its head in the lid's counterbore, an
  M2 x 10 reaches 0.7 mm past the bottom of the base's 3 mm pilot hole. Its head would
  never seat, or it would break through the front face.
- **Buy M2 x 8:** 1.7 mm of thread in the base, with 1.3 mm to spare.
- **The build now checks it** and fails on a bad length.
- **The counterbores went from 4.0 to 4.3 mm,** so an M2 pan head (up to 4.0 mm across)
  fits as printed. Nothing else in the housing changed.
- **The small engraved labels' strokes are 0.35-0.42 mm,** under JLC3DP's 0.5 mm
  guideline. The README said they met it; it no longer does. They may print faint
  either way.

### For you

1. `git push -u origin main` when you are happy with the commit.
2. M2 x 8 thread-forming screws, not M2 x 10 (`BRINGUP.md` §1 is corrected).
3. Whether I should fix the other projects' paths.
4. The authoritative `CLAUDE_PCB.md` is not in OpticsPCBs' git yet. Commit it there when
   you can.

## Prompt 10

CPL names: The two files should be named _cpl_jlcpcb_upload.csv and _cpl_kicad_native.csv
if they haven't already been renamed.

## Response 10 2026-10-08 21:04 - 21:06 Claude Opus 5.5 Max

They hadn't been renamed. They are now, in both releases:

| was | now |
|---|---|
| `GPiBridge_cpl.csv` | `GPiBridge_cpl_jlcpcb_upload.csv` |
| `GPiBridge_cpl_native.csv` | `GPiBridge_cpl_kicad_native.csv` |
| `GPiBridgeLite_cpl.csv` | `GPiBridgeLite_cpl_jlcpcb_upload.csv` |
| `GPiBridgeLite_cpl_native.csv` | `GPiBridgeLite_cpl_kicad_native.csv` |

- `mfg/make_release.py` writes the new names, and `FABRICATION_NOTES.txt` and
  `PLACEMENT_CHECKS.txt` name them. The notes now say not to upload the native one.
- I regenerated both releases. The four CPLs are byte for byte what was ordered, under
  their new names.
- Files whose only change was the run's timestamp (Gerbers, drill files, assembly PDFs,
  the DRC reports) are left as committed.
- The cost estimates re-fetched JLCPCB's stock and prices, because the cached answers
  were two days old. The Lite's parts for 2 boards went from $6.73 to $6.74, and the
  SN75161B is down from 90 to 82 in stock.
- `CLAUDE_PCB.md` has the naming rule now.

The changes are staged in git, not committed.

## Prompt 11

"Oh no, recent email: ... Due to insufficient stock of C42411119, we have enabled the "Replace Parts"
function for your order SMT026100760574 ..." (JLCPCB, 2026-10-18), then: "I went with C2042572. But
keep the design itself the same, noting that we may have to change it at the last minute next time."

## Response 11 2026-10-18 08:20 - 08:50 Claude Fable 5.1

C42411119 is L1, the Abracon AOTA 3.3 µH inductor of the RP2354A's core regulator, on both GPiBridge
boards (not on the Costas board, which the email first looked like).  JLCPCB's shelf had 3 on the morning
of the email for the 4 assembled boards; 347 when the release was costed on 2026-10-08.  Unpopulated is
not an option (no 1.1 V core supply), so a replacement: Raspberry Pi's design guide specifies only 3.3 µH
in the 2016 size, and the AOTA exists because they had Abracon add a polarity dot (a wrong-way coil's
stray field upsets the output capacitor and the regulation under load); DESIGN_NOTES risk 8 already
accepted the wrong-way case.  tools/jlc_api.py listed the shelf's 3.3 µH 2016 parts; the pick was the TDK
VLS201612HBX-3R3M-1, C2042572 (1.57 A, 174 mΩ against the AOTA's 2.4 A, 115 mΩ; the same land; 1.2 mm
tall; no polarity mark), and Jason chose it in the Replace Parts dialog.

The design is unchanged: gen/parts.py still names the AOTA, with a note that rev A was built with
C2042572 and that the next order should expect to substitute again; DESIGN_NOTES §2.8 and risk 8 record
it, and risk 8 says what the bring-up measures (TP3's ripple under load); BRINGUP.md stage 0 says there
is no dot to look for on rev A and stage 1 names the measurement; README's status says so; the rotation
table carries a comment (the TDK has no correction to read).  The lesson (a line can run out after the
order; Replace Parts is in Order History; the API lists the shelf in a minute; keep the design's part and
record the substitution) is in CLAUDE_PCB.md section 3, here and in OpticsPCBs.  The second GPiBridge order
(the Lite shares L1) may get the same email: the same answer.  Response 10's staged renames were
committed first.

## Prompt 12

Read CLAUDE_CODE_CHAT.md and come up with a bring up and test plan for PCBs that came in.
All prompts (including this and following ones) along with your responses should go into
that document. The limiting factor will be my time in the lab. To this end, write the
bring up plan to use ~/mudd/lab-instrument-control/ and modify lab-instrument-control
repository if bugs are discovered or new features should be added. If there is any
firmware for this project, write it and simulate it as best you can before connecting any
hardware. This includes one-off things just for the bringup process. Install any tools
you need to install in ~/.local/ kicad is there. Various versions of Vivado are in
~/Downloads/Xilinx/ and you can use whichever if appropriate. If you need to look at
other pcb projects in ~/pcbs/ or ~/OpticsPCBs/ you should feel free to look. You should
also modify ~/OpticsPCBs/CLAUDE_PCB.md with any lessons learned that should be applied to
future PCB work. In the next day or in the next few days, I'll hook up appropriate
instruments to this computer to debug this PCB. Any problems should go into a REVB.md or
REVC.md list that you'll maintain as you discover problems with the current revision that
we will test. Again, any lessons learned should go into ~/OpticsPCBs/CLAUDE_PCB.md for
future PCB designs. When you are done with the plan, print it here in the chat, with very
explicit instructions on which channels of which instruments should connect to which
places on the PCB. I'll be juggling several of these PCB bringups at once, and it'll be
easy for me to get confused when I pop in and change some physical configuration, so
you'll need to always remind me of where we're at so that I can sit down and *correctly*
do what needs doing in the brief windows that I have before I need to run to my next
meeting.

*Added while the work was under way:*

The instruments plugged in are being used for something else. Assume that I can attach
any of the lab-instrument-control instruments that would be helpful. I will probably do
one board bringup at a time, but I want to plan them in parallel.

<!-- typo fixed in the prompt above: "lesions learned" -> "lessons learned" -->

## Response 12 2026-11-15 21:38 - 22:40 Claude Fable 5.2

*Nothing is committed, here or in lab-instrument-control or OpticsPCBs. No board has had
power and no instrument was touched: the ones on `bell` tonight belong to other work.*

**Where we are:** no board plugged in yet. **Next at the bench, 1 minute:** one assembled
GPiBridge (two big chips), its USB-C into `bell`, nothing else, and the words "a
GPiBridge is plugged in". `bringup/STATUS.md` holds this from now on, and every step
rewrites it.

![the places a step names](docs/images/bringup_map.png)

### The plan

`BRINGUP.md` is rewritten around it. Each stage is a short visit; Claude does the rest
from `bell`, one step a call (`python3 bringup/run.py <step>`), with nothing waiting
for a keyboard.

| stage | you, at the bench | time | Claude | needs |
|---|---|---|---|---|
| 0 | look at J1 (the USB-C), the chips' pin-1 dots | 2 min | | eyes |
| 1 | board's **J1** to `bell` by USB-C. Write the name Claude gives it (A1) on the board | 1 min | `flash`, `bare A1`: firmware, 3.3 V rail (by the chip's temperature sensor), crystal, the 5 V switch, all 16 receive paths and joints (self-test), flash settings, reboot, capture, BOOTSEL and back | a USB-C data cable |
| 1b | scope **channel 1**, x10 probe: ground clip on **J1's metal shell**; touch **TP3, TP2, TP1, TP4** in any order, each until the scope beeps | 3 min | `rails A1`: the four rails, the core supply's ripple (rev A's substituted L1), +5V_GPIB under load | an SDS1104X-E or the SDS2104X Plus |
| 2 | solder the plug: two pins (the hole marked **1**, the hole under **12**), meter **contact 24 to TP5: 0 ohms**, then the other 22 | 15 min | `plug A1`: the self-test with the plug's joints on the lines | plug, housing base, iron, meter |
| 2b, optional | two boards with plugs, both green LEDs off, into the two ends of a GPIB cable | 2 min | `pair A1 A2`: each of 16 lines alone, both ways; names an open joint, a bridge, a turned plug | a GPIB cable |
| 3, optional | board and the bench Prologix on one GPIB cable, both USBs to `bell` | 2 min | `prologix A1`: every byte value both ways, SRQ, timeouts | Prologix PXAESUX9 |
| 4 | board into the **HP 33120A**'s rear GPIB socket (address 10, on); nothing on its Output BNC | 2 min | `gen A1`: lab-instrument-control's own driver through the adapter, a 16,000-point upload, a capture read by sigrok | an HP 33120A |
| 5 | the dearer instruments, one at a time | | speed; PIO if it is needed | |
| 6 | the Lite (L1): stages 0 to 4 again | | the same firmware image | |

`BRINGUP.md` has each stage's pass conditions and what a failure means, one table of
every connection ("which instrument, which channel, which place"), and a table from
each way rev A could be dead on arrival to the stage that answers it.

**The bench rules** it sets:
- **Green LED off means off the bus.** Every step leaves the board parked, so a cable
  can be changed at any time; a lit green LED means "tell Claude first".
- **Say what is cabled, each visit.** Claude then claims the instrument in
  lab-instrument-control's `bench_claims.py` (written tonight by the op-amp board's
  session; four bring-ups share the bench) and only then touches it.
- **Nothing is soldered but the plug**, and no probe is held longer than a beep.

### What was done to get there

1. **Firmware 0.4.0**, with the bring-up's own commands:
   - `++t selftest`: with nothing on the GPIB side, every receive path, the 5 V switch
     and every joint from the transceivers to the RP2354A, by reading each pin on a
     pull-up and a pull-down with the 5 V on and off;
   - `++t raw`: the sixteen lines by hand, in each of the transceivers' four roles;
   - `++t info` (the chip's stepping, reset cause, and the 3.3 V rail by the temperature
     sensor), `++t lines`, `++t identify` (flash this board's LEDs), `++t autostart`.
2. **A board that is not there**: `firmware/test/sim_board` runs the firmware above the
   SDK behind a pseudo-terminal, on a model of the transceivers from their function
   tables. Several share one simulated cable; faults can be planted (no 5 V, a switch
   stuck, an open joint, a bridge, the plug turned round).
3. **The bring-up scripts** (`bringup/`), each step run against it: 28 tests. Good
   boards pass; each fault fails the step meant to catch it, and is named.
4. **lab-instrument-control**: `Link(gpib=10)` finds a GPiBridge when no Prologix is
   there, `prologix='gpibridge'` asks for it, and `identify` never probes one. Its
   33120A driver runs through the simulated adapter unchanged.
5. **Tools on `bell`**, under `~/.local`: `sigrok-cli` and `pulseview` (nightly
   AppImages), `openocd-xpack` (an OpenOCD that knows the RP2350). `picotool` and
   `probe-rs` were there. Vivado is not needed: there is no FPGA here.
6. **Documents**: `BRINGUP.md`, `bringup/REVB.md`, `bringup/STATUS.md`,
   `bringup/BRINGUP_LOG.md`, a numbered map of the board
   (`docs/images/bringup_map.png`, made by `tools/bringup_map.py` from the placement
   table), `HANDBOOK.md`, `AGENTS.md`, both READMEs.
7. **Lessons** into `~/OpticsPCBs/CLAUDE_PCB.md` section 9 and section 11.

### Found before any board had power

Seven firmware faults, each now with a test that fails without its fix
(`bringup/REVB.md` section 2):

| fault | how it was found |
|---|---|
| a data line over 8192 bytes was dropped: a 16,000-point waveform for the 33120A is 32 kB | reading the code against the lab library's notes; then the library's driver against the simulator |
| `++spoll` with the bus off drove the unpowered transceivers (and on the Lite asserted ATN off the bus) | reading; planted back, the test counts 376 breaches |
| two adapters on one cable both took the bus and fought over IFC | the simulated two-board walk counted a fight before it began |
| NRFD, NDAC and SRQ could blip as the transceivers' 5 V came up | the new check "asserted nothing while looking" |
| sigrok 0.6 could not read the captures (0 of 12): it names scoped VCD channels `gpib.DIO1` | installing sigrok-cli on `bell`; the check had been skipping itself there |
| "no listener" counted twice for one failed write | the first simulated `bare` |
| `++t power 1` while on the bus reinitialised driven pins | reading |

The firmware now **looks before it takes a bus**: powered up as a listening device, it
reads ATN, REN and IFC for a millisecond, and if another controller holds one it powers
down again having asserted nothing, and says `"bus":"busy"`.

And for rev B's hardware (`bringup/REVB.md` section 1): the test points are bare 1 mm
pads where the rule is now a jack; and the RP2354A's four ADC pins are unconnected, so
the board cannot report its own rails.

### What I need from you

1. **The udev rule**, once, since it needs sudo:
   `sudo cp tools/60-gpibridge.rules /etc/udev/rules.d/ && sudo udevadm control --reload`.
   Without it everything works but `picotool reboot -f -u`.
2. **What is at hand:** the NorComp plugs? A printed housing base? (A board whose plug
   is soldered without the base can never go into it, so with no base A1 stays a bare
   bench board.) A GPIB cable? The Debug Probe?
3. **Then stage 1:** a GPiBridge into `bell`.

### Checks, 2026-11-15 22:30

| check | result |
|---|---|
| firmware 0.4.0 for the RP2354A | builds, no warnings, 60.4 kB |
| "++" protocol (`test_prologix`) | 70 of 70 |
| pin layer (`test_wire`) | 31,577 pin changes, 0 contention, 0 back-power; the Lite 50,189, 0 driven high |
| sigrok's decoder on the simulated bus | 12 of 12 (sigrok-cli 0.8.0-git) |
| the bring-up's steps on simulated boards (`pytest bringup/`) | 28 of 28 |
| lab-instrument-control `test_scpi_link.py` | 18 of 18 |
| paths | nothing committed or new names a place on one machine |

Not done: the hardware generators were not touched or rebuilt (nothing in `hardware/`
changed); stage 3's script has not been simulated (there is no Prologix to simulate);
nothing has run on a board.

## Prompt 13

I just plugged in a GPiBridge (not the lite version) into USB on a hub. Do what you can now.

## Response 13 2026-11-16 08:41 - 09:25 Claude Opus 5.5

*Nothing is committed. No instrument was touched.*

**Where we are:** A1 has passed stage 1 and the failsafe test, and is parked (green LED
off). **Next at the bench:** write **A1** on the board with a marker. Then, when you have
3 minutes and a scope, stage 1b (one probe on four test points); when you have 15
minutes, stage 2 (the plug, in the housing's base).

### What A1 is

The board came up as `RP2350 Boot` on the first try: USB-C, the crystal and both rails
good. It is an RP2350 **A4** (so erratum E9 does not apply), serial 9F9D542A93F67D76, now
**A1**. It runs firmware **0.4.2** and has passed:

| check | A1 |
|---|---|
| the firmware, and which board it found | 0.4.2, "GPiBridge rev A" (R21 read high) |
| 3.3 V rail, by the temperature sensor | about 3.24 V (863 counts; die assumed at 40 C) |
| crystal against `bell`'s clock | +1.4 to +1.8 ppm |
| reset to USB configured | 940 ms, through a hub three levels deep (I expected 150-300 ms) |
| the 5 V switch, all 16 receive paths through both transceivers, their joints to the RP2354A | self-test passes |
| the bus on and off; a write to an empty bus counted as "no listener" | yes |
| the capture on core 1; IFC's length | 151 µs |
| a setting across a reboot, from a fresh start | kept |
| the second serial port on and off; BOOTSEL by software and back | yes |
| three deliberate reboots in 10 s | stays in the firmware |
| three hangs in a row (`++t crash`) | each caught at 2.03 s; the third start goes to BOOTSEL; picotool brings it back |

### Two firmware bugs, found and fixed this morning

`bare` failed its first four runs, each ending in the ROM bootloader. Neither bug was
in code the simulator runs: both are in `main.c`'s watchdog and flash handling.

1. **The failsafe counted deliberate reboots as crashes.** On the RP2350
   `watchdog_caused_reboot()` is also true after `++rst` or `++t console`, so three of
   those within 10 s sent the board to BOOTSEL. It now counts only real watchdog
   timeouts (`watchdog_enable_caused_reboot()`).
2. **Settings were saved only after a bus capture had run in that power-up.** The SDK's
   flash-safe write refuses unless core 1 is started and registered, and only the capture
   started it. So `++t console 1` came back with one port, and "stay off the bus" was not
   kept at first. Core 1 now starts at boot, and `++t status` counts refused writes
   (`settings_errors`).

It took longer than it should have because the step's message ("did not come back
after a reboot") meant the third reboot, and I chased the first. Logging every byte the
step sent and diffing it against a hand replay found it. The step now says which reboot
it waited for and what it saw.

### Also

- `++t crash` (a hang on purpose) and `bringup/run.py failsafe`, so the recovery path
  every future firmware depends on is tested on the board, not assumed.
- `++t info` now reports the watchdog's load and rate and why the chip last started.
  That settled a false alarm from my own stopwatch: closing the serial port blocks for
  the 2 s a hung board takes to reset.
- `bringup/REVB.md` 2.8-2.10, `BRINGUP_LOG.md`, `BRINGUP.md` stage 1, `HANDBOOK.md`,
  `firmware/README.md`; lessons in `~/OpticsPCBs/CLAUDE_PCB.md` section 9.

### Still open from yesterday

- **The udev rule**, which needs sudo:
  `sudo cp tools/60-gpibridge.rules /etc/udev/rules.d/ && sudo udevadm control --reload`.
- **What is at hand:** the NorComp plugs, a printed housing base, a GPIB cable, the Debug
  Probe.

### Checks, 2026-11-16 09:20

| check | result |
|---|---|
| firmware 0.4.2 for the RP2354A | builds, no warnings |
| "++" protocol (`test_prologix`) | 71 of 71 |
| pin layer (`test_wire`) | 31,577 and 50,189 pin changes, no rule broken |
| sigrok's decoder | 12 of 12 |
| the bring-up's steps on simulated boards | 28 of 28 |
| A1 on the bench: `flash`, `bare`, `failsafe` | pass |

## Prompt 14

What is the STL file to print the housing? I want to print both for this one and for the
"lite" one. If they are different files, give me both paths.

## Response 14 2026-11-16 12:36 Claude Opus 5.5

*Nothing changed but this log. Nothing is committed.*

**Where we are:** A1 has passed stage 1 and is parked. The next step at the bench is
stage 2, soldering the plug, and it needs a printed base first.

There are three files: one base fits both boards, and each board has its own lid.

| print | GPiBridge (A1, A2) | GPiBridge Lite (L1, L2) |
|---|---|---|
| base | `enclosure/out/gpibridge_base.stl` | `enclosure/out/gpibridge_base.stl` (the same file) |
| lid | `enclosure/out/gpibridge_lid.stl` | `enclosure/out/gpibridge_lite_lid.stl` |

For four boards (A1, A2, L1, L2) print four bases, two GPiBridge lids and two Lite lids.
The STLs are current: nothing in `gen/`, `hardware/` or `enclosure/` has changed since
they were built for the order on 2026-10-06, and `enclosure/out/CHECK.txt` still says no
overlap for either board.

How to print them on an FDM printer (`enclosure/README.md`):
- **PETG or ASA, not PLA.** PLA softens on a warm instrument.
- **The base on its front face, the lids on their top faces.** No supports are needed.
- **0.12-0.16 mm layers.**
- **Print one base first** and check that a plug passes its opening and a board drops
  in. If either is tight, reprint with the slicer's X-Y hole compensation at +0.1 mm.
- **Screws:** two M2 x 8 thread-forming per housing. An M2 x 10 is too long.

Only the base is needed for stage 2; the lid can wait.

## Prompt 15

I will come in and do the printing and scope work tomorrow. I copied a new CLAUDE_PCB.md
here. Check in that and everything relevant that you've worked on today. I'll push.

## Response 15 2026-11-16 22:30 Claude Opus 5.5

*Committed, not pushed. No instrument was touched.*

**Where we are:** A1 has passed stage 1 and is parked. **Tomorrow:** print one housing
base (`enclosure/out/gpibridge_base.stl`) and check the fit; do stage 1b (one x10 probe on
channel 1, ground clip on J1's shell, then TP3, TP2, TP1 and TP4, each until the scope
beeps); then stage 2, the plug in the base.

Before committing: `make -C firmware/test` (71 of 71, both pin models clean, sigrok 12 of
12), `pytest bringup/` (28 of 28), lab-instrument-control's `test_scpi_link.py` (18 of 18).
The path and email scans found nothing new.

Commits in this repository:
1. **The rev A bring-up (Prompts 12-15):** the plan, firmware 0.4.2 and its `++t`
   bring-up commands, the simulated bench, `bringup/`, A1's results, and this log.
2. **`CLAUDE_PCB.md`:** Jason's copy from OpticsPCBs, as he placed it.
3. **`PIN_AUDIT.md`:** the pin audit another session wrote on 2026-11-16 (no BLOCKER or
   HIGH). It is in its own commit, so it can be dropped before pushing. Its one open
   question, whether R21 back-powers +5V_GPIB with the bus off, is answered by stage 1b,
   which records TP4 with the bus switched off.

In lab-instrument-control, one commit holds only this project's files (`scpi_link.py`,
`test_scpi_link.py`, `gpib/gpib.md`), which teach `Link` to use a GPiBridge.
`bench_claims.py` and the other sessions' changes there are left as they were.

## Prompt 16

I cannot clip the scope on easily. With a multimeter, though, I get the following with
respect to the USB connector's shell: Vbus = 5.202, 1V1 = 1.097, 5V = 0 (why? I did this
several times), 3V3 = 3.308

## Response 16 2026-11-18 Claude Opus 5.5

*No instrument was touched. A1's bus was switched on for the reading.*

**Where we are:** A1's bus is on (green LED lit), so TP4 has its 5 V. Read **TP4** with
the meter's black lead on J1's shell (4.75-5.25 V expected), then **TP1** again, and send
both. Leaving it on with nothing in the plug does no harm.

**Why TP4 read 0 V:** A1 is parked, and parking switches the bus off, which opens Q1 and
cuts the transceivers' 5 V. That is the design working, and it also settles
`PIN_AUDIT.md`'s one open question: R21 does not feed +5V_GPIB through the SN75161B
while the bus is off.

| test point | read | allowed |
|---|---|---|
| TP3 "1V1" | 1.097 V | 1.05-1.15 V |
| TP2 "3V3" | 3.308 V | 3.20-3.40 V |
| TP1 "VBUS" | 5.202 V | 4.40-5.30 V |
| TP4 "5V", bus off | 0 V | under 1 V |

Stage 1's 3.24 V from the temperature sensor assumed a 40 °C die; 3.308 V means it was
about 32 °C. A meter cannot see the +1V1 ripple, the one check for the substituted L1.

## Prompt 17

A green LED came on. Now 5V reads 5.144 V on the multimeter. VBUS is 5.159 V. A few
seconds after I hit enter, I'll hold channel 1 of the SDS2104X scope on 1V1. Check that
it's set to 10x and that the 50 ohm terminators are off. If you need to "take" it from
another agent, do that. No other agents are using the scope. Let me know in **bold** when
I can let go.

## Response 17 2026-11-18 11:36 Claude Opus 5.5

*SDS2104X:1 claimed, used, released. Channel 4 (claimed by ECP5-2ADC-2DAC) untouched.*

**You can let go now.**

**Where we are:** A1's rails all pass, by meter and by scope; its bus is off again
(parked). Next for A1 is stage 2, the plug.

+1V1 on channel 1 (x10, 1 MΩ), one record at each setting:

| | bus on | bus off | limit |
|---|---|---|---|
| DC | 1.107 V | 1.100 V | 1.05-1.15 V |
| ripple, 200 ns/div | 14.8 mV pp | 12.5 mV pp | 60 mV pp |
| ripple, 20 µs/div | 44.3 mV pp, 2.5 mV rms | 45.3 mV pp, 2.5 mV rms | 60 mV pp |
| ripple, 1 ms/div | 48.3 mV pp, 2.6 mV rms | 46.3 mV pp, 2.5 mV rms | 60 mV pp |

The ripple is the same with the transceivers on or off: the substituted inductor does its
job. The meter's bus-on readings pass too: TP4 5.144 V (4.75-5.25), VBUS 5.159 V, so Q1
drops 15 mV and this hub leaves about 0.4 V of margin.

The scope: channel 1 was at **50 Ω** when I found it. My script restored it to 50 Ω
afterwards, which was wrong given what you asked; I then set it to **1 MΩ** (x10, the rest
as found). The trigger was on C4 and stayed on C1: the scope would not take C4 back while
C4 is off. Channel 2 is on at 50 Ω and x1, left alone in case someone's coax is on it.

## Prompt 18

Record them and commit. Why do I need the case to solder and test the connector? Give me
instructions for that.

## Response 18 2026-11-18 11:50 Claude Opus 5.5

*Committed, not pushed. No instrument was touched.*

**Where we are:** A1 has passed stages 1 and 1b and is parked. Next is stage 2, the plug.
Decide first whether A1 is to be housed or to stay bare as the bench board.

**Why the base:** not for the plug's height. The plug sets that itself: its flange is
3.50 mm above its standoff plate, exactly the base's plate. The reason is that the base's
plate goes *between* the plug's flange and the board, and the flange (54.7 x 15.3 mm) is
far bigger than the plate's opening (33.3 x 14.9 mm). Once the plug is soldered, a base
can never be fitted. Testing needs no base at all. A1 kept bare is the better bench board
anyway (test points, SWD and UART in reach); A2 and the Lites would go in housings.
(Partway through checking this I wrote that the base was not needed; that was wrong.)

The instructions, now `BRINGUP.md` stage 2 (and `HANDBOOK.md` step 5,
`enclosure/README.md`):
1. Unplug A1's USB-C.
2. Board top side up, USB-C to your left, LEDs toward you. The plug goes underneath, D
   pointing down, **its wide side away from you**: under the row with "1" at its end.
3. Push the pins up through the holes and press the board down until the plug's flat
   standoff plate is tight against its underside the whole length.
4. Solder two pins: the hole marked **1**, and in the row nearer the LEDs the **second
   hole from the USB-C end** (contact 23; ground, so more heat). 13 and 14 in
   `docs/images/bringup_map.png`.
5. Meter on beep, one lead on J1's shell (it is GND directly). At the plug's face, at the
   D's USB-C end: the second contact in along the **narrow** side must **beep**; the
   second along the **wide** side must **not**. The other way round, the plug is turned:
   unsolder both now. This needs no moulded numbers: turned round, the joint in the
   ground hole is on the wide side's contact.
6. Solder the other 22. The eight ground pins need more heat: in the near row the seven
   from the USB-C end; in the far row the one marked "12". Look for bridges (2.16 mm).
7. USB-C back into `bell`; say "A1 has its plug". Claude runs `run.py plug A1`. The real
   test of every joint is stage 4, the 33120A.

The old check ("contact 24 where the numbers are moulded") assumed numbers nobody had
seen on the plug; by position alone it could not tell, because contact 12's hole is
ground too.

Recorded: `run.py meter` (new: typed meter readings checked against `rails`' limits)
wrote `results/2026-11-18/114540_rails_A1.json`, with the scope's numbers in
`113626_scope_1V1_A1.json`; `BRINGUP_LOG.md`, `STATUS.md`, `REVB.md` (open questions
answered; 1.3, new 1.6 and 2.11). `bench.Probe` now always sets 1 MΩ. Lessons in
`~/OpticsPCBs/CLAUDE_PCB.md` section 9 (not committed there).

## Prompt 19

A1 has its plug

## Response 19 2026-11-18 13:40 Claude Opus 5.5

*Nothing committed. No instrument touched.*

**Where we are:** A1 has passed stage 2: `run.py plug A1` (`results/2026-11-18/133650_plug_A1.json`).
The self-test read every line exactly as it did bare on 11-16, in all five roles, so no
plug joint bridges to ground or to a driven neighbour. A1 is parked again (green LED off).

What this step cannot see is an open joint, two data lines bridged, or a plug turned
round (the meter check at step 5 covers that). Stage 4 sees all three.

**Next, stage 4 (2 minutes):** the HP 33120A on, at GPIB address 10, nothing on its
Output BNC. A1's plug straight into its rear GPIB socket, A1's USB-C into `bell`, and
say "A1 is on the 33120A". No Prologix is on `bell` now, so the run through the Prologix
for comparison waits until one is.
Stage 2b (two boards on one cable) waits for a second board with a plug; stage 3 (the
Prologix as a device) for the Prologix and a GPIB cable.

## Prompt 20

Slight change of plans. I plugged the GBiBridge into the E3646 which has a broken output 1.
I set it to GPIB and it defaulted to address 02. See ~/lab-instrument-control for more
details on this unit. It has a 5W 1.5 ohm resistor on channel 2. Try to control the
voltage and current limit to safe levels. Read back the current.

## Response 20 2026-11-18 13:55 Claude Opus 5.5

*Nothing committed. The E3646A was claimed (`E3646A@GPIB2`) and is still held.*

**Where we are:** A1 drove the E3646A through its own plug, and it all worked. A1 is
parked; the supply is as found, output off. Next is still stage 4, the 33120A, when you
choose.

- It is the first E3646A (`CAL:COUNt?` +21, the faulty output 1), in its power-on state.
- Output 2 into the resistor, current limited first, never above 1 V or 0.65 W:

  | asked | read back | mode |
  |---|---|---|
  | 0.2 V, 0.5 A limit | 0.1939 V, 0.1285 A | CV |
  | 0.5 V, 0.5 A limit | 0.4953 V, 0.3228 A | CV |
  | 1.0 V, 0.8 A limit | 0.9960 V, 0.6456 A | CV |
  | 1.0 V, 0.3 A limit | 0.4629 V, 0.3018 A | CC |

  Within 1 % of the same supply and resistor over RS-232 on 10-15. Output 1 read −0.203 V
  and −10.6 mA throughout, as broken as before.
- A1: 5999 bytes out, 1540 in, no timeout, no "no listener". The plug is the right way
  round, and the data and handshake lines work through it; SRQ, IFC and REN are not shown
  by this.
- New: `run.py park A1` puts a board back the way a step leaves it after a session by hand.
- Recorded in `bringup/results/2026-11-18/134503_e3646a_A1.json`, `BRINGUP_LOG.md`,
  `REVB.md` section 3; lab-instrument-control's `hp/hp.md`, `AGENTS.md` and the driver's
  docstring (uncommitted there, beside another session's uncommitted edits).

## Prompt 21

When you are done, ramp the supply up and down in steps of 0.1 V twice a second. I'll take
a triumphant video. Keep going with that until I tell you to stop.

## Response 21 2026-11-18 13:49 Claude Opus 5.5

Ramping: output 2 from 0 to 1.0 V and back in 0.1 V steps, one every 0.5 s, 0.8 A limit
(at most 0.65 W), in the background until told to stop, with a 60-minute cap. The supply
read 0.257 A at 0.4 V and 0.580 A at 0.9 V. On stopping: output off, settings as found,
A1 parked.

## Prompt 22

The screen often only shows the limit rather than the current. Don't set the limit each
time. As it ramps, I want to see the voltage and live current.

## Response 22 2026-11-18 13:52 Claude Opus 5.5

The ramp only ever sent `VOLTage x`; the limit was set once. The guide has the display
leave its limit mode "after about 5 seconds", and a step every 0.5 s never gives it that.
Stopped the first ramp (248 steps, none late, no timeouts) and restarted it through the
trigger subsystem (`VOLTage:TRIGgered x;:INITiate`), in case a triggered change keeps the
meter view. Next to try: `DISPlay:MODE VI` with each step.

## Prompt 23

If that's the case, ramp more slowly

## Response 23 2026-11-18 13:55 Claude Opus 5.5

Now 7 s a step: about 5 s of limits, then about 2 s of measured current; 140 s a cycle.
Stopping the trigger ramp went wrong: the stop signal came in the middle of a query, the
clean-up then read each answer one query late, and it quit without restoring the supply
or parking A1. The supply was already in its power-on state when I looked (asked: had it
been switched off and on?). The ramp script now stops on a flag between commands and
runs every clean-up step whatever the one before did; tested by stopping it mid-run.

## Prompt 24

Keep testing. See if you can push the setting and getting functions to the limit of
speed, and make sure that things are handled gracefully.

(During the turn:) I did power cycle it, but I thought you were done with the ramp.

## Response 24 2026-11-18 14:15 Claude Opus 5.5

*Nothing committed. The E3646A is still claimed (`E3646A@GPIB2`); A1 is parked.*

**Where we are:** A1 drove the E3646A as fast as the supply goes, and through every fault
I could make, without a wrong byte. One real bug turned up, in lab-instrument-control,
and is fixed there. Next at the bench is still stage 4, the 33120A.

- The power cycle explains the reset and the 4 timeouts: A1 rode through it. (I had
  said the ramp was restarted; I should have said it plainly that the supply was live.)
- Speed (output off): A1's own round trip 0.24 ms; `*OPC?` 29/s, `VOLT?` 24/s, `*IDN?`
  16/s, a measurement 10/s; set with `*OPC?` 21/s; set then read back 12/s, 500 pairs, no
  mismatch; 200 settings back to back 25/s. A capture of `*IDN?`: A1 takes each byte in
  about 1 µs, the supply needs 90 ms to start its answer. The supply is the limit.
- Output on: a step and a current reading 6.6/s; the current settles within a reading.
- New through the plug: SRQ (serial poll 96) and EOI sent by A1. Only IFC and REN unshown.
- The bug: a query given up after its `++read` (timeout, signal) left its answer in the
  port, and every later answer came one query late, `clear()` included. That is what
  broke the ramp's clean-up. `scpi_link` now notes such a read and, before the next
  command, asks the adapter `++ver` and drops everything before its answer. Tested: a
  fake adapter in lab-instrument-control (the old code fails 3 of 4), `sim_board` here,
  and on the bench, where every fault case now recovers on the next query.
- A timeout at an empty address now says "the GPiBridge found no listener at GPIB 9".
- Recorded: `bringup/results/2026-11-18/140851_e3646a_speed_A1.json` and the capture,
  `BRINGUP_LOG.md`, `REVB.md` (2.12 and section 3); lab-instrument-control's
  `scpi_link.py`, `test_scpi_link.py`, `gpib/gpib.md`, `hp/hp.md`. Tests: 32 here, 30 there.

## Prompt 25

Commit whatever needs committing in the GPiBridge and the lab-instrument-control repos.
Where are we with the PCB? Why do we have a REVB.md? Are there PCB changes that need to
be made for a revB? Check in the speed and fault tests, but make sure they are clearly
marked as such in their comment block. Is it worth moving it over to the 33120A now? I'd
plug the OUTPUT into channel 2 of the SDS 2104X scope. You get your scripts ready to go
and I'll move around the plugs.

(During the turn:) You should be ready to go. It's plugged in. The interface is set to
HPIB. Output goes to scope channel 2. / Do I need to unplug or power cycle anything? /
I rebooted the function generator. / I kept it off longer this time. Try again. / The
function generator's buttons do not work and it says "Rmt" on its screen. I will power
cycle again. Wait 3 minutes from when you get this message before you try anything.

## Response 25 2026-11-18 15:00 Claude Opus 5.5

*Committed: GPiBridge 4fa583c (and a second commit for what follows); lab-instrument-control
2b40f87 (another session's third-E3646A notes) and a98cb1f (scpi_link). Not pushed.*

**Where we are:** A1 passed stage 4 on the 33120A with the scope watching (14:54). The
generator then stopped taking data again after the speed tests sent it a query it could
not answer (my SCPI mistake), and needs one more power cycle, with A1 parked (it is).

- **The PCB:** A1 has passed stages 1, 1b, 2 and 4, and driven two instruments; nothing
  found is a hardware fault. **No rev B change is needed.** `REVB.md` is the one list of
  what the bring-up teaches (AGENTS.md asks for it), so a rev B, if there ever is one,
  starts from it; it is not a plan to make one. Its hardware entries are improvements:
  jacks on the test points, the rails on ADC pins, maybe a witness hole for the plug,
  the SN75162B if it returns, a two-piece housing base. Still to see: the Lite (L1), two
  boards on one cable, IFC and REN at the plug, the board's current.
- **Speed and fault tests:** `bringup/speed_faults.py`, `run.py speed`, headed "SPEED AND
  FAULT TESTS. Not a bring-up stage"; simulated, with a planted open DIO3.
- **Stage 4:** 45 `*IDN?`/s (Prologix 31), 16,000 points in 8.1 s, the scope saw the sine
  and the 16,000 points as sent, no timeout. On the way: lab-instrument-control re-asked
  behind a long upload (fixed there), and firmware 0.4.2 gave up a write on a listener
  busy over 1 s and dropped the rest of the message (0.4.3: 10 s; flashed).
- **Open:** the 33120A stopping (REVB.md 2.13). Next test, from a fresh power-up: reads
  with nothing asked, to see whether that is what wedges it.

## Prompt 26

And when you do try, go slowly and carefully.

## Response 26 2026-11-18 15:05 Claude Opus 5.5

Waited 3 minutes, looked at the lines (normal), sent one `*IDN?`: no answer, the
generator still stuck (not yet power-cycled). Parked A1 and stopped; listed the
step-by-step test for after its power cycle.

## Prompt 27

Is there no way to do something with the HPIB bus to get the function generator
unstuck? Really?

## Response 27 2026-11-18 15:07 Claude Opus 5.5

Tried what had not been: a serial poll (status 0: its GPIB chip answers by itself) and a
universal device clear sent by hand in raw mode: taken, but NDAC never let go, i.e. the
chip waits for the generator's processor, which has stopped (its keys are dead too).
IFC and REN-off had happened many times already. Nothing on the bus restarts a stopped
processor: only its power switch.

## Prompt 28

Before I rebooted, the screen says "+0.000 VDC" and the Rmt and ERROR indicators are
on. I am turning it on. You probably don't need to wait 3 minutes, but give it at least
enough time to go through its self tests.

## Response 28 2026-11-18 15:20 Claude Opus 5.5

One step at a time, `*IDN?` after each: one and five empty reads, `APPLy:APPLy?`, the
exact failing message, five reads, a device clear with errors unread, `APPLy:DC`, go to
local, park and back: none stopped it. Then a speed run's opening `++t power 1` on a live
bus (5 V off and on within 3 ms) and it stopped. Suspected A1's power switching.

## Prompt 29

I cannot clip to the DAV pin. I will need to solder. Let's repeat. If this continues to
be a problem that cannot be fixed in firmware, this is not an acceptable hardware product
to use in lab. If simply turning on the transceivers causes instruments to require a
power cycle, I cannot use this. I hare restarted the function generator.

## Response 29 2026-11-18 16:00 Claude Opus 5.5

20 off/ons 0.5 s apart: 20 of 20; restarts: stopped at the 10th. Firmware 0.4.4: a
restart does not switch the 5 V; a 0.5 s minimum off; unaddress before letting go;
simulated, flashed.

## Prompt 30

generator powered off and on.

## Response 30 2026-11-18 16:05 Claude Opus 5.5

0.4.4: 30 restarts, 30 of 30. Back-to-back off and on (0.51 s off, held by the
firmware): stopped at the first. So the delay was not the cause; recommended watching
the lines on the scope.

## Prompt 31

I will solder the wires on the back to probe with the scope, but give me pin numbers in
addition to things like "2nd from the left". Pins 1, 12, and 13 are labeled, so I can use
that to find a specific number. "2nd from the left" is a nice confirmation.

## Response 31 2026-11-18 16:08 Claude Opus 5.5

From the board file: DAV contact 6 (ground 18 across from it), ATN 11 (ground 23), IFC 9
(ground 21), TP4 for the 5 V; contact k sits across from k+12.

## Prompt 32

I have all 4 of your channels in. DAV (yellow lead) on ch1, ATN (blue lead) on ch3, IFC
(brown lead) on ch2, and the 5V test point (green lead) on Ch4. All probes are 10x. I'm
not sure they are all properly compensated probes, and the leads (including the ground
leads) are each 20cm long in order to be able to set the probes down without pulling on
the solder joints. The function generator is off and the GPiBridge is not plugged into
USB. Start recording on the scope and tell me whether to plug in the USB on the GPiBridge
or turn on the function generator.

(During the turn:) The other project was not using ch4. / I can go back to probing the
function generator on ch2 if that's better, but that does not seem to be as useful at the
moment. / Generator turned on. / USB-C plugged in

## Response 32 2026-11-18 16:41 Claude Opus 5.5

Claimed all four channels (ch4 by force); 1 Mohm, x10. Generator power-up: its own short
blips, then lines released near 3 V. A1 plugged in: nothing. A1's transceivers on: clean
(nothing for 6 ms, then IFC 151 us, ATN, UNT, UNL). Yet the first `*IDN?` got nothing.

## Prompt 33

It shows Rmt but no ERROR. Try again with the 33120A one more time, then we'll switch to
different 33120A units that I have here. I can't do Prologix until tomorrow. The 33120A
was rebooted and has been on for a minute.

## Response 33 2026-11-18 16:46 Claude Opus 5.5

A1's power-up clean again; no answer again (2 of 2 since the wires, 3 of 3 before). No
bridge at the joints (raw mode). Asked for the swap to another 33120A.

## Prompt 34

It's on a different, newer-looking 33120A and all scope probes should be the same. It was
not easy to move, so something might have come loose.

## Response 34 2026-11-18 16:56 Claude Opus 5.5

*Nothing committed since 65436aa.*

Probes all reading. The "top" 33120A (8.0-5.0-1.0) answered at once; 120 of 120 cycles
(back-to-back off/on, off/on, restart, go to local); stage 4 PASS; speed and fault tests
PASS (`*OPC?` 4.4 ms). A1's power-down on the scope: 5 V below 0.2 V in 2.9 ms, lines
clean. **The first 33120A is at fault, not A1.** Corrected REVB 2.14's brownout theory and
0.4.4's comments; noted in lab-instrument-control's `hp/hp.md` and `AGENTS.md` that the
first unit locks up and the "top" unit is on HP-IB address 10 now.

## Prompt 35

Commit everything. Then look at the loast of equipment in lab-instrument-control, filter
on ones that have a GPIB port, and sort them from least expensive to most expensive. We'll
test a few until we're satisfied that the A1 hardware works. Let me know if it can desolder
the wires now connected to the scope. If you want them, that's fine, but they are a
shorting hazzard.

## Response 35 2026-11-18 18:30 Claude Opus 5.5

Put the SDS2104X back as found, but with channel 2 at 1 MΩ while a probe is still soldered
to A1. The read-back showed the hidden channels' scale and offset had not come back: the
scope ignores both on a channel that is off. lab-instrument-control's `channel()` now
switches the channel on for them (checked on channel 1); noted in `siglent.md`. Committed
GPiBridge, lab-instrument-control and OpticsPCBs' `CLAUDE_PCB.md`. Listed the inventory's
GPIB instruments by rough used price (my estimates, not looked up). The four wires can come
off now. Suggested the order: the bench's E3632A, the 33220A (GPIB and LAN, so a stall can
be told from a hang), then stage 5's Keithley 2000 and SR830.

## Prompt 36

If you need manuals for any of these, try to get them and put them in the untracked
manuals directory. If you can't find what you need, make a list of items and links that you
cannot access. I'll try to get them tomorrow.

## Response 36 2026-11-18 20:16 Claude Opus 5.5

Most were already in lab-instrument-control's `manuals_untracked/`, 13 of them under their
bare download names from 2026-10-05: identified and renamed by its convention (3325B,
5316B, 8656B service, 8662A, 8665B, 8590E guides, 8970B, TC200, 500B, LDX-3500B).
Downloaded from Keysight: the 8970B operating manual (the folder had only its viewer page)
and two 8656B operation manuals. Every GPIB instrument on the list now has a manual with its
commands, except an original (non-B) LDX-3525, whose older guide is not downloadable
(manuals.online refuses scripts). Removing four duplicate copies was refused by the
permission check: listed in `MANUALS.md` for Jason. `MANUALS.md` and `MANUALS_WANTED.md`
updated, not committed.

## Prompt 37

The "The only copy I found is on manuals.online" link gives me a 404 error. I added more
manuals. Check for byte-identical duplicates. Delete what you need to delete to keep only
one copy.

## Response 37 2026-11-19 08:38 Claude Opus 5.5

Five of the new files were byte-identical to ones filed yesterday: deleted, each after a
fresh `cmp`. Also deleted the two same-content copies and the 8970B viewer page listed
yesterday. No two files in the folder are the same now. Filed the six new ones (the 8656B
quick reference; 8970B supplements, a GPIB example, the security note, the Y-factor note).
The old LDX-3500 guide is on ManualsLib, and its contents have no remote chapter: the
original LDX-3525 probably has no GPIB at all (inventory row changed to "?"). Not committed.

## Prompt 38

The GPiBridge is now plugged into the "bottom" 33120A (the third one on my desk here). I set
the interface to HPIB. Check everything you can with that one. The 4 wires are still on the
scope. If that checks out, I'll desolder the leads and try other instruments.

(While I worked:) Keep going, but when you're done, while I'm desoldering the leads, I want
you to make sure there is a clean separation between the things in GPiBridge and the things
in lab-instrument-control. GPiBridge should contain the PCB, firmware, udev rules, and
enough information for someone to get up and running with this under Linux, Mac, or
Windows. Python examples for the two instruments we've tested so far are good. The code
here should be independent of lab-instrument-control and be at a much lower level. There
could and should be a link to the public lab-instrument-control repo, though, for people
who want to work at that higher level. The lab-instrument-control repo should also be
standalone in the sense that someone with a working GPiBridge should not need to also
download or look at the GPiBridge repo to use it. The lab-instrument-control repo should
also have the udev rule and installation instructions. The code here should treat the
GPiBridge as one of several drop-in hardware USB-to-GPIB interfaces to these instruments.
The others being the Prologix, the interface that I first used to talk to the 6 GHz VNA
over the summer, the other open source GPIB USB interface with that we used as inspiration
for the GPiBridge (I believe it used STM32), and perhaps any more official GPIB to USB
interfaces.

(Then:) Are you done with the device? Can I pull it off and start desoldering? I will
assume yes.

## Response 38 2026-11-19 09:04 Claude Opus 5.5

The bottom 33120A (7.0-5.0-1.0): power-up clean on the scope; 150 of 150 cycles; stage 4
and the speed and fault tests PASS; power-down clean. Its firmware differs from the bad
unit's only in the I/O processor's number (5.0 against 2.0). `tools/gpibridge.py` fixed: it
inherited `++eot_enable 1` from `bringup/adapter.py` (a 0x04 at the head of a capture), and
on a parked board waited 70 s for nothing; two simulated tests. Released the scope and the
33120A. Separation:
- **GPiBridge:** `examples/` (pyserial only: `gpib_port.py`, `hp_33120a.py`,
  `agilent_e3646a.py`, tested on the simulated board; the E3646A one not yet on the
  supply); README "Getting started" per OS with the udev rule and a link to
  lab-instrument-control; AGENTS.md says which code may use what.
- **lab-instrument-control:** `60-gpibridge.rules` (identical to GPiBridge's), the NI
  rule, an Installing section, `gpib/gpib.md` comparing Prologix, GPiBridge, UsbGpib (an
  ATmega32U4, not an STM32), the NI HS/HS+ (the summer's three fixes) and Keysight's; no
  more pointers into GPiBridge or `~/DroneSDR`.
- **Left for Jason:** whether `bringup/` stage 4 and the speed tests move off
  lab-instrument-control. Nothing committed.

## Prompt 39

I am soldering the connector onto a second GPiBridge and also a GPiBridgeLite unit. Is the
firmware the same for the two units, with the transceiver chip either auto detected in
some way or irrelevant to the firmware? If not, in revB, it would be good to make that
happen so that only one version of the firmware needs to be maintained. Also, revB and
its cases should have holes goin all the way through where the GPIB connector has its
screw holes. This would allow a captive screw with a hand tightened back to securely
attach the unit to the instrument if someone wanted to.

## Response 39 2026-11-19 09:10 Claude Opus 5.5

Reminded first: a board meant for a housing needs the base on before its plug is soldered
(REVB 1.6), and the two-pin orientation check. One firmware image already runs both
boards: it reads R21 on DC before driving anything. Weak point: a Lite with R21 missing may
read as a GPiBridge; proposed a firmware read with each pull to catch it, and for rev B an
ID on a spare ADC pin carrying board and revision (REVB 1.8). The screw holes (REVB 1.7):
the flange's holes fall at (8.65, 17.5) and (55.35, 17.5), on R3, R4, C1, the USB pair and
inner tracks on the left, J4, R11 and R12 on the right; NorComp's flange holes are 3.2 mm,
for #4-40, while GPIB lock screws are M3.5 (or 6-32), so rev B needs another plug as well.
PLAN.md and DESIGN_NOTES.md now point to it.

## Prompt 40

Do the firmware fix for rev A. I plugged in our first GPiBridgeLite into USB. Flash it.
Then I'll plug it into one of the two working function generators.

(Then:) L1 is on now. (And:) I see the yellow and red LEDs alternating

## Response 40 2026-11-19 09:33 Claude Opus 5.5

Firmware 0.4.5: R21 read with the pad's pull-down, then its pull-up (the pull-down first,
its input buffer off: RP2350-E9); a pin that follows the pull means no R21: the Lite's pin
layer, no bus, no raw mode or self-test, ERR steady, "unknown (R21 not read)". Tests: a
third wire run with R21 missing (the old read fails it, bus pins driven high), a sim_board
fault and a bring-up test; 39 of 39. L1 was not on USB at first (it had come and gone at
09:17); flashed the moment it came back (09:30): it read R21 as the Lite. bare and plug
PASS. The alternating LEDs: the flash step's two-minute identify. Corrected the times of
Responses 37-39 (they were guessed; now from the transcript).

## Prompt 41

Change of plans. It's plugged into the E3646. Test that instead.

The 3D printed plastic housing made it *just* big enough to not fit in with the power plug
plugged into the function generator. This is, in general, going to be a problem with these
units. The circuit board needs to sit almost flush with the back of the instrument. On the
scale of the backs of these instruments, it's pretty big. There is a lot of stuff back
there that can get in the way. I don't know what good revB options are. If there is a
90-degree GPIB solder plug, that might work to have the board stick out back rather than
along the instrument. A more expensive option would be to buy an extender that would plug
into the back of the instrument and just copy the port a centimeter or two further back. I
don't know if these are sold or how expensive they are. The National Instruments and
Prologix and other adapters mostly stick out back. (They also have the captive thumb screws
that I talked about.) I don't know what their PCBs look like. Do you think that the GPIB
plug has solder pins that are soldered on either side of a thick PCB? Do they use a 90
degree adapter? I'm torn on whether revB should depart this radically or not.

(While I worked: photos of the Keysight 82357B, NI GPIB-USB-HS/HS+, ines GPIB-USB-2,
ADLINK USB-3488A and Prologix; then of XyphroLabs' UsbGpib V2 and GPIBee, and Galvant's
bare GPIBUSB board on a right-angle plug: "Here are some other adapters, including a
"bare" one with a connector that takes a 90 degree bend.")

## Response 41 2026-11-19 09:55 Claude Opus 5.5

L1 on the first E3646A (GPIB 2, claimed): `speed` PASS (22 checks);
`examples/agilent_e3646a.py`'s first hardware run: 0.494 V, 0.322 A into 1.5 ohm, put
back, no error. `failsafe L1` failed twice on timing (5.2 s a hang); with the port left
open the board left USB in 2.02 s (kernel: 2.00 s): closing the port at once had held the
disconnect up to a kernel timeout. Step fixed, PASS. Rev B form: REVB.md 1.9 with the
options (straight out on a right-angle plug, which exist; a straddle-mounted solder-cup
plug; slimmer along the panel; rev A with a short GPIB cable or Keysight's 10834A, which
moves the connector 2.3 cm out); recommended straight out, the electronics unchanged.
Then (Jason: the L-com CIB24SRA at $25, L-com's extenders, NorComp's 111-024 at $7.31;
"Would one of these 90 degree connectors be a drop-in option with the same boards?"): the
CIB24SRA is a receptacle, the instrument's side, so it cannot plug into an instrument;
right-angle plugs exist from Chinese makers, not on DigiKey; none is a drop-in on rev A's
boards, but a 90-degree build could be a third variant from the same generators. Softened
1.7's claim that GPIB screws are M3.5: the CIB24SRA has 4-40.

## Prompt 42

I'm fine buying from Chinese makers. Give me some links or names to search for.

## Response 42 2026-11-19 09:57 Claude Opus 5.5

Dongguan Fuyconn Electronics: FUY57142 (male, right-angle PCB, "big hole"), FUY57109A
(right-angle PCB, bail locks), FUY57018C-24P (male, black screws; vertical or right-angle,
its page says both); MOQ 10, 7-10 days, prices on request, no drawings online. An Alibaba
listing of a right-angle male with big screw holes. Nothing on LCSC or AliExpress. Search
terms, and what to ask for (a drawing, the screw thread, the plating, samples). In REVB.md
1.9.

## Prompt 43

Unit A2 (with transceivers and a 3D printed case) is now plugged in to USB but not to an
instrument. Flash add test it. I will set up the three instruments that were in the physics
stock room, so also write test code for those.

## Response 43 2026-11-19 10:35 Claude Opus 5.5

A2 flashed (0.4.5, read as GPiBridge); `bare A2` lost it on its third restart: on USB port
3-5.3 behind a hub that logged its own errors, the computer could not read its descriptor
again. Asked for A2 on the computer's own port (3-3, where A1 and L1 passed). The three
stock-room GPIB instruments taken to be the HP 3325B, 5316B and 5370B; three agents read
their scanned manuals and wrote `examples/hp_3325b.py`, `hp_5316b.py`, `hp_5370b.py`
(pyserial only, every code with its page). Reviewed: a sign fix in the 3325B parser; the
5316B reads to the line feed (`++read 10`, checked on the simulated board); the 5370B has
no self-check, so its trigger levels are set and read back. None has met its instrument.

## Prompt 44

I have to run, but all 3 instruments are hooked up on 3 different GPiBridges (one lite). I
don't have time to look at the settings, but do what you can with the setup. I took photos
of the backs of the instruments and put them in photos. Don't check photos in yet, but
eventually we'll want nice photos and videos of the devices talking to instruments. I'll
be back in an hour or two.

## Response 44 2026-11-19 11:14 Claude Opus 5.5

From the photos and a serial poll at every address: A2 on the 3325B (17), L1 on the
5370B (3), A1 on the 5316B, which is set to TALK ONLY (it answers a poll at every address
and takes no codes). `hp_3325b.py` PASS through A2; `hp_5370b.py` PASS through L1. Bus
captures: the 3325B ends in CR LF with EOI, the 5370B without EOI, so `gpib_port.read()`
can stop at the line feed now. 120 bus cycles each, 120 of 120. A2 restarted 16 times on
this hub without a fault (the morning's loss was the other hub). A1 flashed to 0.4.5. The
5370B status byte's oven and timebase bits are clear while a service request stands.
Instrument notes added to lab-instrument-control's `gpib/gpib.md`. Photos left untracked.
Nothing committed.

## Prompt 45

Try 5316B again.

(While I worked:) A2 is off of the 3325B. Do that too. / When you say, "A2 on USB: 16
restarts on the hub you're using now", were these planned restarts or unintended
restarts? Is there debugging that needs to happen here, or were you just reporting a good
situation? / On the top-level README.md page of both the GPiBridge and
lab-instrument-control, I want a list or a table of all instruments that have actually
been successfully controlled with each piece of software. Don't list where they are in my
lab, but keep a column for what they are (oscilloscope, power supply, etc), what their
approximate used cost is, and what limitations they might have under GPiBridge control. /
I have flipped those two switches on the back of the unit with ADDRESSABLE/TALK ONLY. I
don't think I flipped either switch when I told you that I had. I needed to unplug and
move things around. Try that one again. / Let me know when I can plug A2 back into the
instrument. / A2 is back on. If you want me to connect anything to anything else, let me
know. It's easy for me to connect the 3 things that you're working with now. If you want
me to connect any of those things with a function generator or oscilloscope, that would
require a longer BNC cable chain.

## Response 45 2026-11-19 13:07 Claude Opus 5.5

The 5316B was still in TALK ONLY. The manual's drawing has both leftmost rear switches
down; Jason's photo had both up. Once Jason set them, it answered at 20 alone, and
`hp_5316b.py` passed through A1 (CHECK read 10,000,000 Hz). It sends no EOI and keeps
sending readings while addressed, so a `++read eoi` from the capture tool never ended and
held A1 until a reboot. `picotool reboot -f -a` can't reboot a running board, because the
firmware keeps feeding the watchdog. Both bugs are in `REVB.md` 2.15, for 0.4.6. A2's
bare, failsafe and plug stages pass; the failsafe step had taken "no GPiBridge on USB" for
"gone", and now follows one board's serial and device number. A2's 16 restarts had been
deliberate. Both READMEs now have a table of the instruments each has driven, with rough
used prices and limitations: five through GPiBridges, 13 through lab-instrument-control.
Asked for a BNC from the 3325B to the 5316B (and the 5370B) for a three-board demo.
Nothing committed.

## Prompt 46

Called as requested, with the tee. Test all of that.

(While I worked:) Some instruments have knobs and buttons, and I don't know which settings
can be overridden through GPIB. Let me know if you need me to do anything to the knobs or
buttons.

## Response 46 2026-11-19 13:31 Claude Opus 5.5

The 3325B (through A2) stepped a 0.5 Vpp sine from 1 kHz to 20 MHz; the 5316B (A1) and the
5370B (L1, the Lite) counted it. The 3325B read back every frequency exactly. The 5316B
read +1.24 ppm high at every one, and the 5370B -0.03 ppm from 1 MHz up. The 5370B took
two corrections: it counts frequency on STOP (`IN2`; on START every period carried about
0.7 ns), and a sample size sent after the gate time overrides it. Now
`examples/three_instruments.py`, for the video; the README tables and both repos' notes
updated. No knobs needed; for a quicker video, the 5316B's rear gate control could be
turned toward 1 s (now 12-13 s a reading). Asked whether the 5370B's cable moved to STOP.
Boards parked again. Nothing committed.

## Prompt 47

The 5370B says "Err 02" on its screen. I can restart it or push buttons. Cabe moved to
STOP

(While I worked:) That message about Err 02 is old. / But it's back on the screen now.

## Response 47 2026-11-19 13:36 Claude Opus 5.5

Err 02 is overrange (Table 3-2): with the 3325B left at 1 mVpp, the 5370B starts a
measurement that never ends, in frequency or in time interval. Harmless: no restart, no
buttons. The example now leaves the 5370B in its power-up codes instead of frequency mode;
a 5 MHz run after the change: 5316B +1.240 ppm, 5370B -0.038 ppm. Claim, log and notes
updated: the cable is on STOP. Nothing committed.

## Prompt 48

I have further teed off the output to go into both the start and stop with two
different-length cables. I'd guess 0.5m and 1m. Fix the firmware bugs, upload the new
firmware, and test things with the current setup. The commit.

(While I worked:) When you're done, I will go down to the Advanced Lab and test those
instruments. I will need to do this on a different computer with a different agent
running. That agent will have access to a unison-synchronized copy of this filesystem, so
you should be able to leave explicit instructions for that claude instance to do what
needs doing with the Advanced Lab instruments (and any potential firmware updates that it
needs to do) and writing a report for you to ingest. / Another quick test before I move the
3 GPiBridge units to the Advanced Lab would be to plug one into the 33220A that is here in
my office. Write a test for that, in addition to the Advance Lab instruments for later.

## Response 48 2026-11-19 13:57 Claude Opus 5.5

Firmware 0.4.6, on all three boards:
- **A read the host has given up on now ends** when the host sends anything more. Input
  already waiting when the read began (several commands in one write) still gets a
  Prologix's read. `++ver` was answered 60 ms after it was sent, in the middle of a read
  the 5316B never ends.
- **Reboot-from-flash now reboots**, in 0.08-0.17 s, and isn't counted as a crash.
- **picotool needs our USB IDs** (`--vid 0x1209 --pid 0x0001`, plus `--ser` with several
  boards plugged in). Without them it finds no board at all; the docs are corrected.
- **Tests:** 85 host checks and 39 bring-up tests pass.

On this setup, `examples/cable_delay.py` timed the two cables through the 5370B: STOP's
is shorter by 2.85 ns, about 0.56 m. The three-instrument sweep passes on 0.4.6.

Written for later:
- `examples/agilent_33220a.py`, which keeps the output off.
- A brief for the Advanced Lab agent, untracked in `bringup/handoff/`, because it names
  rooms.
- Three scripts for the Keithley 2000, SR830 and PAR 5210, being written from their
  manuals.
- Two lessons in CLAUDE_PCB.md.

## Prompt 49

Before I move things, write a demo that cycles through, showing fun numbers on the
frequency counter like 123456789, 1000....0000, etc. If you don't this every second or so,
I can take a video.

(While I worked:) Ok, my colleague is here. Make the cool demo that cycles through numbers
like 123456789 and other round or interesting number on the big screen. / stop the fun
number demo. I will shut off those instruments.

## Response 49 2026-11-19 14:11 Claude Opus 5.5

`examples/fun_numbers.py` ran in a loop, 2 s per number:
- **The numbers:** 12,345,678.9 Hz, π MHz, e MHz, the golden ratio, the caesium second,
  the hydrogen line, the speed of light, Avogadro's number, 2^24, 867-5309, all ones and
  all nines.
- **The displays:** the 3325B showed each number exactly. The 5370B agreed to about eight
  digits. The 5316B read +1.3 ppm high.
- **The fix it needed:** a reset to the 5316B, sent once the 3325B had answered its new
  frequency, so the counter's gate didn't straddle the change. Without it, every other
  reading was a blend of two numbers.

Stopped on Jason's word. The 3325B was left at 1 mVpp and all three instruments on their
front panels. The boards are parked and the claims released.

The scripts for the Advanced Lab are written from their manuals, and checked against fakes
of each instrument:
- `keithley_2000.py`;
- `srs_sr830.py`;
- `par_5210.py`, whose manual gives no factory address.

The brief in `bringup/handoff/` now carries each script's open questions.

A second commit of these was blocked by the permission check; it waits for Jason's word.

## Prompt 50

The A1 unit is plugged into the 33220A, and its output is on channel 2 of the 2104X. Test
that. Because of the size of the current PCB, it covers the ethernet and USB inputs, so
those cannot be used simultaneously with the GPiBridge.

(While I worked:) When that's all done and debugged and marked as "tested" in both repos,
look at 20261119_135948.mp4, which is a video of the fun number demo. Shrink it to be able
to be pushed to github. Make a gif thumbnail, and add it to the front page of the GPiBridge
README.md. / The Advanced Lab instruments will need to wait until tomorrow or next week,
but make sure that a test is written up and ready to go.

## Response 50 2026-11-19 14:22 Claude Opus 5.5

The 33220A through A1 at GPIB 10:
- **The output-off example:** mismatches none. The 1000-point waveform took 0.02 s to
  upload.
- **The signal test,** with the output on the scope's channel 2:
  - 200 alternating queries, 758 a second, every answer right.
  - 1 kHz at 0.2 Vpp: the scope read 999.8 Hz and 0.403 Vpp.
  - 12.345 kHz: 12,345.87 Hz, counted from the scope's record.
  - The uploaded waveform's shape correlated 0.99998 with the points sent.
  - Output off: 6 mV.
- **It took four runs.** The scope's own frequency readout scatters by 0.1%, and my first
  crossing count doubled on noise; hysteresis fixed it.
- **Marked tested in both repositories.** REVB 1.9: the board covers the 33220A's USB and
  Ethernet sockets.

The video went to `docs/video/fun_numbers.mp4`: 540x960, about 4 MB. I first cut the
sound track in case it held voices; Jason asked to keep it, so it is back (AAC, 64 kb/s).
`docs/images/fun_numbers.gif` is 2.0 MB and links to it, near the top of the README.

The Advanced Lab is ready: the brief, plus the three scripts.

## Prompt 51

On the main README.md page, include a still from the video from around 15 seconds in. Pick
one that's in focus and shows all 3 GPiBridge devices controlling the 3 instruments.

## Response 51 2026-11-19 14:26 Claude Opus 5.5

From 11 to 19 s, a frame every 0.25 s, ranked by sharpness (Laplacian variance). 15.50 s
was the sharpest of the backs (327, against 14-260 around it), with all three boards' green
LEDs in view. It is `docs/images/three_gpibridges.jpg` (540x960, 143 kB), beside the GIF in
a two-column table near the top of the README, both at 270 px. The commit waits for
Jason's word: the permission check stopped it.
