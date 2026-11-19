# Rev B: what to change, and what is still open

Started 2026-11-15, the evening the bring-up was prepared, before any rev A board had
power. This is the one list to add to: anything found on the bench, in the firmware or
in the documents that rev B of either board should change, and every question a
measurement has not yet answered. `DESIGN_NOTES.md` section 6 has the older rev B
thoughts; they are folded in at the end so nothing has to be chased.

Each entry says how it was **found**, **what** is wrong, the **change**, and its
**state**. Hardware changes wait for rev B and are applied together. Firmware changes
need no board: they are made as they are found and listed in section 2.

## 1. Changes for rev B, hardware

### 1.1 The test points are bare pads
- **Found:** writing stage 1b of `BRINGUP.md`, 2026-11-15.
- **What:** TP1 (VBUS), TP2 (+3V3), TP3 (+1V1), TP4 (+5V_GPIB) and TP5 (GND) are 1 mm
  pads. Nothing clips to them, and TP5 is 2.4 mm from TP4, so a scope's ground lead has
  no place of its own: it goes on the USB-C socket's shell. Jason's rule since
  2026-11-07 (OWLternating Current's bench) is that every test point is a jack.
- **Change:** an MMCX jack on each rail (U.FL where MMCX will not fit), each with its
  own ground, named in silk, left unpopulated in a production run. The board has room
  along its bottom edge, left of the LEDs, once BOOT moves up.
- **State:** rev B. Rev A works round it: one probe held on each pad until the scope
  beeps (`run.py rails`). On A1 (2026-11-18) the ground clip would not stay on J1's
  shell either; a hand meter read the four rails (`run.py meter`), and a probe held on
  TP3 alone gave the ripple.

### 1.2 The board cannot measure itself
- **Found:** the same evening: `bare` can check everything on a board except its rails
  and its current, which need a hand.
- **What:** GP26 to GP29, the RP2354A's four ADC inputs, are unconnected ("walled in by
  the decoupling capacitors' copper", `gen/pins.py`). Rev A's only reading of a supply
  is the temperature sensor against the 3.3 V rail, good to about 5 %.
- **Change:** VBUS and +5V_GPIB each through a 2:1 divider (100 k / 100 k, 10 nF) to an
  ADC pin, and +1V1 direct to a third; `++t info` then gives the three in millivolts on
  every board, for ever, with no probe. A 50 mΩ shunt in the +5V_GPIB feed with its two
  ends on the dividers would give the transceivers' current as well. This is the lesson
  of CostasLink's 192 mΩ input path (`CLAUDE_PCB.md` section 9: "DC levels too").
- **State:** rev B. Needs the RP2354A's left side replanned: the capacitors' copper is
  what walls the pins in.

### 1.3 Nothing stops the plug going in turned round
- **Found:** Response 1; simulated 2026-11-15 (`sim_board --fault turned`).
- **What:** the 2 x 12 grid is symmetric. Turned, the board's ground pads sit on DIO1-4,
  EOI, DAV, NRFD and DIO5, and hold them low; DIO5's pad sits on the shield.
- **Change:** none found for the footprint (the connector is what is symmetric). Rev B
  could add a 1 mm witness hole in the board beside contact 1 that the plug's moulded
  "1" shows through, if NorComp's moulding allows; to be looked at with a real plug.
- **State:** open. Rev A: the meter check after two pins (`BRINGUP.md` stage 2), and
  the two-board walk names it (`run.py pair`). The check first read "contact 24 at the
  plug's face, where the numbers are moulded", but nobody had seen numbers on NorComp's
  plug. Since 2026-11-18 it needs none: tack contacts 1 and 23, then at the D's USB-C
  end the second contact in on the narrow side beeps to ground and the second on the
  wide side does not; turned round, the two swap. (Contact 24 would not do: its hole's
  partner when turned is contact 12's, also ground.)

### 1.6 The housing's base cannot be fitted after the plug is soldered
- **Found:** 2026-11-18, Jason asking why stage 2 needed a printed base.
- **What:** the base's plate lies between the plug's flange and the board, and the
  flange (54.7 x 15.3 mm) is bigger than the plate's opening (33.3 x 14.9 mm). The plug
  sets its own height (flange 3.50 mm above its standoff, the plate's thickness), so the
  base is not needed as a jig; but a board soldered bare can never be housed, and
  soldering waits for a print.
- **Change:** a base in two halves, split across the opening and joined by the lid's
  screws, would go on afterwards. To be weighed against the plate's strength (it
  carries the pull when the adapter is unplugged).
- **State:** rev B idea. Rev A: a board meant for a housing waits for a printed base;
  one kept bare as the bench board (A1, if Jason chooses) can be soldered now.

### 1.4 A second controller cannot be seen by the SN75161B while it is one itself
- **Found:** simulation, 2026-11-15: two boards on one cable, both started by USB, drove
  IFC against each other.
- **What:** as a controller (DC low) the SN75161B transmits ATN, REN and IFC and cannot
  read them back. The firmware now looks while it is still a device, before it takes
  the bus (section 2.4), which covers every case but two controllers starting in the
  same millisecond.
- **Change:** the SN75162B (a separate SC pin: REN and IFC on their own) if it returns
  to stock; it is 22 pins against 20, so a new footprint. Already in `DESIGN_NOTES.md`
  section 6.
- **State:** rev B, if the part exists then.

### 1.5 Carried over, already settled in the generators
- **The USB-C's place in JLCPCB's file** (Response 7): the JLCPCB CPL now carries their
  drawing's 1.572 mm offset. Rev A's boards were moved by hand in the preview: look at
  J1 on each (`BRINGUP.md` stage 0).
- **L1** (Response 11): rev A carries TDK's unpolarised VLS201612HBX-3R3M-1, not the
  Abracon AOTA of the design. On A1 it does not matter: +1V1's ripple is 2.5 mV rms,
  the same with the transceivers on or off (section 3).
- **The housing's screws** are M2 x 8, not M2 x 10 (Response 9).

### 1.7 Holes for captive lock screws, through the board and the housing
- **Asked:** Jason, 2026-11-19: holes all the way through, on the plug's flange holes,
  so that a captive screw with a hand-tightened head can hold the adapter to the
  instrument. Rev A decided against it (`DESIGN_NOTES.md` §2.6, `PLAN.md`): this
  reverses that.
- **Where they fall:** the flange's holes are 46.70 mm apart, on the plug's axis: board
  (8.65, 17.5) and (55.35, 17.5).
  - **Left**, in the USB and supply corner: R4's centre 0.6 mm away, C1 1.7, R3 2.2;
    USB D+ and D- run 1.75-3.25 mm below it on F.Cu, the 5 V fan-out 3 mm left, and
    LED_ERR, LED_USB, TE_DATA and TE_CTRL cross it on In2.
  - **Right**, in the debug corner: R12 1.7 mm, J4 (the UART connector) 2.2, R11 2.7,
    and the UART's vias and tracks.
  - Clearing a circle of about 3 mm radius round each moves those parts and re-routes
    those tracks; J4 (and its opening in the lid) moves the most. The board may need to
    grow along x; the housing (62.6 mm) with it.
- **The screw may not fit the plug's flange as it is.** NorComp's flange holes are
  3.2 mm (its panel cutout calls 0.120"), which passes #4-40. GPIB lock screws are
  usually M3.5 x 0.6 (black, metric) or 6-32 on older instruments, both about 3.5 mm,
  but L-com's right-angle receptacle CIB24SRA has 4-40 screwlocks: the thread varies by
  maker. Measure the studs on the lab's instruments first. A plug sold with GPIB screws
  (some vertical PCB plugs come with black captive screws) would settle it; the standoff
  height (3.50 mm) and the 24-pin pattern must stay as they are, or the generators
  change with it.
- **The stack a screw passes through:** the lid (its top), the board, the base's 3.5 mm
  plate, the flange, into the instrument's lock stud. Captive in the lid (a shoulder
  under the head, or an e-clip), with a knurled head the hand turns. The board's holes
  unplated, with a copper keep-out, so the screw does not tie the instrument's chassis to
  the circuit's ground; clearance 3.8-4.0 mm.
- **For the housing:** `enclosure/build.py` gets the two holes through both parts, and
  its 3D check gets the screw.
- **State:** rev B, asked for.

### 1.9 The housing does not fit beside the 33120A's power plug
- **Found:** Jason, 2026-11-19: housed, the adapter was just too big to go in with the
  generator's power cord plugged in. "On the scale of the backs of these instruments,
  it's pretty big": rev A lies along the panel, 62.6 x 28.2 mm in the housing, against
  the plug flange's 54.7 x 15.3 mm, so it covers about 6.5 mm above and below the
  flange and 4 mm past each end, where instruments put other connectors.
- **What others do** (Jason's photos):
  - Prologix, NI GPIB-USB-HS/HS+, Keysight 82357B, ines, XyphroLabs GPIBee: a body that
    sticks straight out from the panel, about a cable hood's size across, with captive
    thumbscrews; several carry a stacking receptacle on the back.
  - XyphroLabs UsbGpib V2: along the panel, like rev A, but barely taller than the
    flange (no transceivers, like the Lite).
  - Galvant's GPIBUSB (OSHW, 2013): a bare board on a right-angle PCB-mount plug,
    sticking straight out.
- **Options:**
  1. **Straight out, on a right-angle PCB-mount plug** (they exist: Amphenol 57-series
     style; female ones are common, male ones rarer). The board sticks out from the
     panel; across, it need be no bigger than a GPIB cable's hood, so it fits wherever
     a cable fits. Thumbscrews sit in the hood's ears, where cables have them, clear of
     the board (1.7 then needs no rerouting). More board area. It sticks out 50-60 mm.
  2. **Straight out, a solder-cup plug straddling the board's edge** (the two rows of
     cups either side of it): probably how hood-style adapters are built; to be seen by
     opening the bench Prologix.
  3. **Along the panel, slimmer:** the Lite could come close to the flange's height (as
     UsbGpib V2 does); GPiBridge's two SOIC-20W transceivers make that hard. It would
     still not fit everywhere.
  4. **Rev A as it is, with a spacer:** a short GPIB cable (its plug stacks), or
     Keysight's 10834A, a GPIB-to-GPIB adapter that brings the connector out about
     2.3 cm from the panel.
- **The parts compared (DigiKey, 2026-11-19):**
  - NorComp 111-024-113L001, rev A's: a **plug** (male), vertical, through-hole; $7.31
    each, $5.83 at 25; unthreaded flange.
  - L-com CIB24SRA: right-angle, through-hole, but a **receptacle** (female), the
    instrument's own side: it cannot plug into an instrument, only take a cable.
    $26.68, $21.25 at 25; 4-40 screwlocks.
  - Right-angle **plugs** (male) for a PCB: offered by Chinese makers, not found on
    DigiKey, LCSC or AliExpress (2026-11-19). Dongguan Fuyconn Electronics (fuyconn.com;
    MOQ 10, 7-10 days, price on request): FUY57142 (male, right-angle PCB, "big hole",
    rivet board lock), FUY57109A (right-angle PCB, bail locks), FUY57018C-24P (male,
    black screws; its page says both vertical and right-angle). None gives a drawing,
    the row spacing or the screw thread: ask, and get samples before designing.
  - Spacers: L-com's GPIB extenders are $50-120, Keysight's 10834A similar: they defeat
    the point of a cheap adapter.
- **Not a drop-in on rev A's boards:** a right-angle plug's pins leave its body at the
  board's edge, in another pattern, and the board then stands out from the panel. It
  would be a third build variant from the same generators (as the Lite is: `if BI...`
  branches in placement and routing), with the same schematic, parts and firmware, so
  "some flat, some at 90 degrees" is a rev B option, not a rev A rework.
- **To find out before choosing:** whether a GPIB cable plugs into that 33120A with its
  power cord in (if it does, option 1 or 2 within a hood's size fits it); how the
  bench Prologix's plug meets its board.
- **State:** open, Jason's decision. Claude's view: option 1, keeping the electronics,
  the firmware and the pin map as they are (with 1.8's revision ID).

- **The Agilent 33220A (2026-11-19):** A1, plugged into its GPIB socket, covers its USB
  and Ethernet sockets, so it is GPIB alone while a GPiBridge is in. Another case for a
  board that leaves the instrument's back by the shortest way.

### 1.8 One firmware for every board and revision: make the board ID fail-safe, and carry the revision
- **Asked:** Jason, 2026-11-19 (one firmware for GPiBridge and the Lite).
- **Already so on rev A:** one image runs both. `hal_lite()` reads R21 on DC once, before
  any pin is driven: 10 k to 3.3 V is GPiBridge, 1 k to ground is the Lite.
- **What is weak:** a Lite whose R21 is missing or open leaves DC floating. If it reads
  high, the firmware takes it for a GPiBridge and drives its pins as it would the
  transceivers' inputs, high as well as low, into the bus through the 100 R resistors.
  The handbook asks for a look at
  `"board"` in `++t status`, but nothing stops it.
- **Change, firmware (rev A too):** read DC twice, with the RP2350's pull-up and then its
  pull-down (about 50 k). R21 outvotes both (10 k up: 2.8 V against the pull-down; 1 k
  down: 0.07 V against the pull-up), so a pin that follows the pull has no R21: board
  unknown, stay off the bus, light ERR, say so in `++t status`. Simulate with a fault in
  `sim_board` first.
- **Change, rev B hardware:** if rev B moves any signal to another GPIO, the same image
  must also tell rev A from rev B. One spare ADC pin (GP26-29; on rev A they are boxed in
  by the decoupling capacitors' copper) with a two-resistor divider can carry the board
  and the revision together. Keep R21's meaning as it is, so rev A boards still read
  right.
- **State:** firmware done in 0.4.5 (2026-11-19, Jason: "Do the firmware fix for rev A"):
  `hal_rp2350.c` `read_board()`; `test_wire no_r21` (103 pin changes, 0 failures; the old
  single read fails it 8 times, three of them bus pins driven high); `--fault no_r21` in
  `sim_board` and `test_bare_names_a_board_without_r21`; a board read as unknown gets the
  label U1 in the bring-up. First on hardware: L1, read as the Lite (flash, bare and plug
  PASS, 09:30-09:32). Rev B ID pin: asked for.

## 2. Firmware, changed before the first board (0.3.0 to 0.4.0, 2026-11-15)

All found on a PC: by running the lab's real host software against the firmware on a
simulated bus, by new host tests, and by reading. Each has a test that fails without
the fix.

### 2.1 A data line longer than 8192 bytes was dropped
- **Found:** reading `prologix.c` against lab-instrument-control's notes: a 16,000-point
  waveform for the 33120A is one 32 kB line.
- **What:** the line was gathered whole and then sent; a longer one was thrown away with
  one log line. A Prologix passes bytes on as they come.
- **Change:** past the buffer, the instrument is addressed once and the line streams;
  the last byte is held back so the EOI rides whatever ends the line.
- **State:** done. `test_prologix.c` (30,000 bytes; two buffers exactly; nobody
  listening), and `bringup/test_bringup.py` uploads 16,000 points through
  lab-instrument-control's own driver.

### 2.2 A serial poll with the bus off drove the unpowered transceivers
- **Found:** reading `gpib_serial_poll()`; confirmed by planting the bug back: 376 pin
  changes high into the unpowered chips, and on the Lite ATN asserted while off the bus.
- **What:** after `++t power 0`, `++spoll` skipped the transfer but still ran the lines
  that end one.
- **Change:** it returns at once, like every other transfer.
- **State:** done. `test_wire.c`, "bus off".

### 2.3 sigrok 0.6 could not read the board's captures
- **Found:** installing `sigrok-cli` on `bell` for the first time: 0 of 12 recordings
  decoded. The check had "passed" there until then by skipping itself.
- **What:** the VCD named a scope, and libsigrok 0.6 calls a scoped channel `gpib.DIO1`
  where 0.5 said `DIO1`.
- **Change:** no scope in the VCD; the host tools also ask sigrok for the names it
  gives.
- **State:** done. 12 of 12 with sigrok-cli 0.8.0-git; `tools/gpibridge.py capture`
  tried against the simulator.

### 2.4 Two controllers on one bus
- **Found:** the simulated two-board walk counted a bus fight before it had begun.
- **What:** every GPiBridge took the bus as soon as USB configured it. Beside a Prologix
  in controller mode, or a second GPiBridge, both drive ATN, REN and IFC.
- **Change:** on power-up the board is a listening device for a millisecond and reads
  ATN, REN and IFC; if any is held it powers down again, asserts nothing, lights the red
  LED and says `"bus":"busy"`. `++t power 2` takes the bus regardless (for a bus with a
  line stuck low). `++t autostart 0` (saved) keeps a board off the bus until
  `++t power 1`: the bring-up parks every board that way between steps.
- **State:** done in simulation (`test_wire.c`, `test_prologix.c`,
  `test_a_second_controller_stands_back`). **Open for the bench:** that a real idle
  bus, and no bus at all, read as free (stage 1's `++t power 1` says so at once).

### 2.5 NRFD, NDAC and SRQ could blip as the transceivers' 5 V came and went
- **Found:** the new test "asserted a line while looking for another controller".
- **What:** unpowered, the bus pins rest on pull-downs. A listening SN75161B transmits
  NRFD, NDAC and SRQ from its terminal pins, so for the moment between the 5 V arriving
  and the pull-ups being set (and again as it left) those three read "asserted".
- **Change:** the pull-ups go on before the 5 V and stay 3 ms after it is switched off.
- **State:** done in the model. **Open for the bench:** the real fall time of
  +5V_GPIB (the 3 ms is an estimate: 2.6 µF into the chips and the LED). Stage 1b's
  probe on TP4 can time it.

### 2.6 Smaller
- "No listener" was counted twice for one failed write (the write, and the unaddressing
  after it). Once now.
- `++t power 1` on a board already on the bus reinitialised pins that were being
  driven. It lets go first now.
- The self-test's pull-down readings keep each pin's input buffer off until the moment
  it is read, so the RP2350's erratum E9 (A2 stepping) cannot turn an open joint into
  a pass.

### 2.8 Deliberate reboots were counted as crashes (found on A1, 2026-11-16)
- **Found:** A1's first `bare` ended in BOOTSEL four times out of four.
- **What:** the failsafe sends the board to the ROM bootloader after three watchdog
  resets in a row. It asked `watchdog_caused_reboot()`, which on the RP2350 is true after
  a deliberate `watchdog_reboot()` too (`++rst`, `++t console`). Three of those within
  ten seconds looked like three crashes. On the RP2040 it would have been the same.
- **Change (0.4.1):** count only `watchdog_enable_caused_reboot()`: a timeout of the
  watchdog the firmware enabled (the SDK marks it in SCRATCH4).
- **State:** done. On A1: three `++rst` in 4 s stay in the firmware; three `++t crash`
  in a row land in BOOTSEL (`run.py failsafe`).

### 2.9 Settings were saved only after a capture (found on A1, 2026-11-16)
- **Found:** the same morning: `++t console 1` came back with one serial port.
- **What:** `flash_safe_execute()` returns `PICO_ERROR_NOT_PERMITTED`, and writes
  nothing, unless the other core is a "lockout victim". Core 1 became one only when
  `++t capture start` launched it. The firmware logged the refusal to the console port
  and the UART, which nobody was reading.
- **Change (0.4.1):** core 1 is launched at boot, asleep; `++t status` counts
  `settings_errors`; `bare` saves a setting before any capture and requires 0.
- **State:** done, and seen on A1.

### 2.10 Smaller, for the bring-up's own tools (2026-11-16)
- **The reconnect after a reboot** waited for the serial port's udev link and blamed
  "a reboot" without saying which; it now says which, and what it saw (gone, BOOTSEL).
- **picotool reboot** right as BOOTSEL appears is not answered: the steps retry.
- **Closing the port blocks** for as long as the board is hung (the kernel's control
  transfer waits): time from the event, not from after `close()`.
  - **And do not close it until the board has gone** (2026-11-19). L1's first failsafe
    "failed": each hang measured 5.2-5.4 s. Closed at once, the port leaves the kernel a
    request the hung board never answers, and the disconnect waits for its timeout, so
    even watching from another thread saw 5.2 s. With the port left open, L1 left USB
    2.02 s after `++t crash` (the kernel's disconnect: 2.00 s). The step now closes it
    once the board is gone: 2.03 s, three times; PASS. A1 had won the race on 11-16.
  - **And watch this board, not every GPiBridge** (2026-11-19). The step took "no
    GPiBridge on USB" for "gone": true with one board plugged in, never with three. A2,
    beside A1 and L1, restarted in 2 s, but the step waited out its 12 s and crashed
    parking the port it had closed. It now follows the board's serial number (its ROM
    bootloader reports the same one) and USB device number, so a board that leaves and
    comes back between two looks is still seen to have gone; a round it does not see
    end is recorded, and the board reopened to park it. A2: 2.24, 2.09, 2.08 s; PASS.
- **`++t info`** adds the watchdog's load and rate and the reason for the last start
  (`wd_load`, `wd_per_ms`, `boot_reason`, `boot_scratch4`); `++t crash` hangs on purpose.

### 2.11 Stage 1b by hand (2026-11-18)
- **The plan's meter fallback said "read the four points with the green LED lit"**, but
  every step leaves a board parked, LED off. TP4 read 0 V, which looked like a fault
  and was the design. `BRINGUP.md` stage 1b now says what parked reads, and Claude
  lights the LED before the bus-on readings.
- **`run.py meter A1 TP1=... TP4off=...`** records a meter's readings as stage 1b,
  against the same windows as `run.py rails` (tested: a stuck Q1, a low rail, a
  missing bus-on reading).
- **`bench.Probe` never set the scope's input impedance.** The SDS2104X Plus had
  channel 1 at 50 Ω; a x10 probe into 50 Ω reads almost nothing. It now sets 1 MΩ
  every time. The one-off script that took A1's ripple put the 50 Ω back when it
  restored the scope, though Jason had asked for it off; set to 1 MΩ by hand after.

### 2.12 Driving the E3646A as fast as it goes (2026-11-18)
Before stage 4, A1 drove the first E3646A at GPIB 2 through lab-instrument-control
(`results/2026-11-18/134503_e3646a_A1.json`, `140851_e3646a_speed_A1.json`).
- **A1 held up.** 1000 settings read back with no mismatch; 200 `VOLT` commands sent
  back to back (the supply's handshake the only brake, 25 a second); 80 commands
  chained in one 968-byte message; 5000 bytes of junk (the supply said "mnemonic too
  long"); an address with nobody there (counted as "no listener"); the supply switched
  off and on in the middle of a session (4 timeouts, no hang). Not one wrong byte.
- **The fault was in the host library, and it is fixed there.** When a query was
  given up after its `++read` had gone out (a timeout, or a signal stopping a script),
  its answer reached the port late and every later query got the answer before its
  own. A device clear did not help: it cleared the library's buffer, not the port. It
  broke the clean-up of a ramp on the bench. lab-instrument-control's `scpi_link` now
  marks such a read, and before the next command asks the adapter for `++ver` and
  drops everything before that answer (the adapter answers in order: a read still in
  progress finishes first). Tested with a fake adapter there, through `sim_board` here
  (`test_lab_instrument_control_recovers_from_an_answer_left_unread`), and on the bench.
- **A timeout from an empty address now says so.** On a GPiBridge, `scpi_link` reads
  the board's own "no listener" count after a timeout: "the GPiBridge found no listener
  at GPIB 9: is the instrument on, cabled, and at that address?". A Prologix keeps no
  such count.
- **A1 finishes a read before it looks at what the PC sends next** (whether a Prologix
  does the same, its manual does not say). That is why an abandoned read can still
  answer after the next command has gone out. A firmware that abandoned a read when new input came
  would make this simpler for every host program; for rev B's firmware, to weigh against
  Prologix compatibility.
- **`run.py park A1`**: the parked state after a session by hand (`park()` was there,
  with no command of its own).

### 2.13 Stage 4 on the 33120A, and firmware 0.4.3 (2026-11-18)
A1 on the bench's 33120A at GPIB 10, its OUTPUT by coax on the SDS2104X Plus's channel 2
(50 Ω).
- **Everything the step checks passed** on the first run and again with the scope:
  settings read back, 20 MHz refused, 1000 and 16,000 points uploaded (the generator's own
  count and average), the serial poll, 44.7 `*IDN?` a second against the Prologix's 31.
  `run.py gen A1 --scope sds2104 --channel 2` (new) also has the scope see the sine
  (frequency, amplitude, offset) and the 16,000 points played: the record matched the
  samples sent.
- **What failed was "no timeout in the whole step".** First 3, from lab-instrument-control:
  during the upload `os.write` returned 5 s before A1 had passed the 32 kB on, and the
  read of `*OPC?` asked again every 0.8 s; each extra `++read` waited behind the data and
  timed out. `scpi_link` now waits for the adapter's `++ver` after more than 1 kB written
  before it reads (a fake-adapter test there fails on the old code).
- **Then a firmware fault: a write gave up on a busy listener after 1 s**
  (`WRITE_TIMEOUT_US`, "a listener that holds NRFD this long is not coming back"). The
  capture of the step's last `*IDN?`: the generator took the `*` and held NRFD for over
  1 s; A1 dropped the rest of the message. The Prologix manual gives `read_tmo_ms` to
  `++read` and `++spoll` only and says nothing of writes; 0.4.3 waits 10 s (NI-488.2's
  T10s) and still counts and logs a write that hits it. `test_prologix` has a listener
  busy 3 s after a message's first byte (`sim_busy_us`, new in `sim_bus.c`), which 0.4.2
  fails, and one busy 30 s, which must time out and be counted. A1 flashed to 0.4.3.
- **The 33120A then stopped taking data altogether** (settled in 2.14: that unit does it,
  not A1). Three times it answered
  nothing: after the end of a stage 4 run (the 16,000 points, `APPLy:DC`, `++loc`, a serial
  poll), and once straight after Jason switched it off and on. A device clear and an IFC
  did not free it. The capture on 0.4.3: it takes the addressing bytes (UNL, MTA, LAD 10),
  then holds NRFD for the whole 10 s, so not one data byte goes in. Its display says
  "Rmt" and its keys do nothing. Whether a part of A1's behaviour leads it there (the
  dropped half-messages of 0.4.2, the rapid `++loc` and readdressing at the end of the
  step), or this 33120A does it on its own, is the next thing to find, one step at a time
  from a fresh power-up. The same generator ran the whole step cleanly through 0.4.2
  twice.
  - **On 0.4.3, after a power-up with A1 off the bus for 3 minutes, stage 4 passed
    twice in a row with no timeout at all** (`145307_gen_A1.json`, `145415_gen_A1.json`),
    the generator answering to the end. So the stops at the end of the step followed
    0.4.2's half-messages.
  - **The fourth stop followed a query it could not answer**: `run.py speed` sent
    `APPLy:SINusoid f,0.1,0;APPLy?`, which SCPI reads as `APPLy:APPLy?` (after `;` a
    header without `:` stays in the last one's subsystem; now `;:`). No answer; the library
    asked to read again every 0.8 s for 5 s, each time addressing it to talk with nothing
    to say; then a device clear. It has held NRFD since. So the pattern to test next,
    from a fresh power-up: `++read` with nothing asked, once, then a few times, then
    `*IDN?`. If that is it, the library's read-again is what to change (and with the
    Prologix the same would happen; its read-again has run for months on this generator
    after long uploads, though, so something about A1's way of giving up a read may
    differ: compare captures).
  - Its power-up takes time: one attempt within seconds of switching it on got nothing.
    Leave it 3 minutes, A1 parked.
  - **Nothing on the bus frees it** (15:06, stuck): IFC (at every `++t power 1`), REN
    dropped (at every park) and a selected device clear had not; a serial poll answered
    status 0 (no answer waiting); a universal device clear sent by hand in `++t raw
    ctrl_talk` was taken with NRFD but NDAC never let go in 2 s: its GPIB chip holds the
    handshake until the processor deals with a clear, and the processor (keys dead too)
    does not. So it is the generator's firmware that stops; only its power switch helps.
  - **One piece at a time, from a fresh power-up (15:16-15:19), nothing stopped it**, a
    `*IDN?` after each: one read with nothing asked, five 0.8 s apart (no error logged
    for either), `APPLy:APPLy?` (-113 and -420 logged, as SCPI has it), the exact
    `APPLy:SINusoid 1234.5,0.1,0;APPLy?`, five reads, a device clear with the errors
    unread, `APPLy:DC` and `APPLy?`, go to local, park and take the bus again.
  - **Then it stopped with nothing sent to it but A1 restarting the bus**: the check left
    A1 on the bus, and `run.py speed` opens with `++t power 1`, which on a live bus is
    `gpib_stop()` then `gpib_start()`: the transceivers' 5 V off and on within
    milliseconds, IFC, REN. Its first `*IDN?` got nothing (48 bytes out, 0 in). Of the
    four stops not explained by its power-up, three came just after A1's transceivers
    were powered down and up (a park and a new session, or this restart); the fourth was
    0.4.2's half-message. Not every such cycle stops it (one in the careful run did not).
    **Working guess: the lines glitch while A1's 5 V comes and goes, and the 33120A takes
    a glitch for a byte under ATN** (2.5 above: NRFD, NDAC and SRQ blips at the 5 V's
    edges, seen in simulation). To settle on the bench: a scope on DAV and ATN at the
    plug's pins on the board's top side through a park and a `++t power 1`; or twenty
    park/power-up cycles, each followed by `*IDN?`. If it is that, it is a firmware
    order-of-operations fix first (lines held released until the 5 V is up, Q1 switched
    with the transceivers in a known state), and a rev B question if the transceivers
    themselves glitch on their supply's edges.
- **SCPI's `;` in `sim_bus.c`**: a message of several commands answers each, the answers
  joined by `;` (text only: a `DATA:DAC` block or `test_wire`'s every byte value stays
  whole). `run.py speed` sends such messages.

### 2.14 Restarting a live bus stopped the 33120A; firmware 0.4.4 (2026-11-18)
- **Found:** 20 cycles each, a `*IDN?` after every one, from a fresh power-up of the
  generator (`cycles.py` in the session's scratch, 15:53-15:55):
  - bus off (`++t power 0`), 0.5 s, on again: **20 of 20 answered**;
  - `++t power 1` on a live bus: answered 9, then **stopped at the 10th**, the same stop
    as in 2.13 (holding NRFD, only its power switch helps).
- **What:** `++t power 1` on a live bus was `gpib_stop()` then `gpib_start()`: the
  transceivers' 5 V switched off, 3 ms (`RAIL_FALL_US`), on again. I took it for a
  brownout (the rail not yet fallen). **Wrong, as measured later the same day:** the 5 V
  falls below 1 V in 0.36 ms and below 0.2 V in 2.9 ms, so 3 ms was a full power-down;
  and the lines through A1's power-up and power-down are clean (below). The stops were
  that 33120A's own.
- **Change, 0.4.4:**
  - `++t power 1` (or 2) on a live bus takes it again without touching the 5 V: IFC,
    REN, unaddress all.
  - The 5 V is never switched on again within 0.5 s of being switched off, by any path
    (`hal_power`, `MIN_OFF_US`; USB and the watchdog served while it waits).
  - Before letting go of the bus, everyone is unaddressed (UNT, UNL), with a 50 ms limit
    so a stuck instrument cannot hold the stop up.
  - `test_prologix`: `++t power 1` on a live bus switches nothing off, and the
    instrument answers after it; off and on again works.
- **On 0.4.4 (16:01-16:03), after a power-up of the generator:** 30 restarts (now no
  power switching), **30 of 30 answered**. Then `++t power 0` and `++t power 1` back to
  back (the firmware held the 5 V off 0.51 s): **stopped at the first**. So the 3 ms
  was not the whole story. Two theories ruled out on paper: a control pin glitching
  while `hal_init()` re-initialises it right after the power is cut (DC has R21, 10 k to
  3.3 V; TE_DATA and TE_CTRL 10 k to ground); and the 3 ms itself. Taken together
  (0.4.3: 20 of 20 with 0.5 s off timed by the host, 1 in 10 restarts; 0.4.4: 1 of 1),
  the data fit **"each switching of the transceivers off and on has a few per cent
  chance of stopping this 33120A"**, which would be a hardware matter, as well as they
  fit chance. Only the lines on a scope can tell.
- **Settled, 16:35-16:52: it was that 33120A, not A1.** Jason soldered wires to DAV
  (contact 6), IFC (9) and ATN (11), with grounds across from them (18, 21, 23), and a
  fourth to TP4; x10 probes on the SDS2104X Plus, 20 cm leads.
  - The lines, everything off: 0 V. The generator switched on: its own lines blip for
    2-10 us at 7.7 ms (and its power switch's transient shows on every probe for
    0.25 ms), then rest released near 3 V. A1 plugged into USB, bus off: DAV never fell.
  - **A1's transceivers switched on (three times): clean at 10 ns resolution.** The 5 V
    rises to 4.9 V and DAV, IFC and ATN do not move; at 6.0 ms IFC for 151 us, ATN, and
    two DAV pulses (UNT, UNL), as the firmware writes them.
  - Yet the first 33120A (firmware 7.0-2.0-1.0) did not answer the first `*IDN?` after
    a fresh power-up, twice running: it took the addressing and the first byte, then
    held NRFD. No bridge at the soldered pins: in `++t raw ctrl_talk` each of DAV, IFC,
    EOI, REN, DIO1 and DIO5 asserted alone showed alone; ATN brought NDAC, as it must.
  - **A second 33120A (the "top" one, firmware 8.0-5.0-1.0, switched to HP-IB address 10),
    the same A1, wires and probes:** answered at once; then 30 back-to-back offs and
    ons, 30 offs and ons 0.5 s apart, 30 restarts, 30 go-to-locals each followed by a
    query: **120 of 120 answered**; stage 4 PASS (`165136_gen_A1.json`); `run.py speed`
    PASS, every fault section included (`165158_speed_A1.json`): `*OPC?` 4.4 ms (230 a
    second), `*IDN?` 45, `VOLT?` 91 a second; A1 takes a byte in under 1 us.
  - So the first unit stops, now and then and lately more often, on its own: it was
    the last two of its lock-ups after power-ups whose lines were clean. To try it with
    the Prologix (tomorrow) for the record; meanwhile it is not a test instrument.
  - **A third 33120A (the "bottom" one, firmware 7.0-5.0-1.0), 2026-11-19, the same A1,
    wires and probes:** the power-up the same (IFC 151 us at 6.0 ms, then UNT, UNL); 150
    of 150 cycles answered (30 each of back-to-back off/on, off/on, restart, go to local,
    IFC); `tools/gpibridge.py test` 44.9 queries a second; stage 4 PASS
    (`084646_gen_A1.json`); `run.py speed` PASS (`084704_speed_A1.json`); the power-down
    through `run.py park` the same (0.2 V at 2.91 ms, the lines no lower than 2.33 V), and
    it answered after it. Its firmware differs from the first unit's only in the I/O
    processor's number (5.0 against 2.0: the three are the main, I/O and front-panel
    processors'), which fits that unit's I/O firmware, or that unit alone, stopping.
  - 0.4.4's changes stay: a restart that does not switch the 5 V is simply better, and
    the 0.5 s off is harmless.
  - **A1's transceivers switched off (16:53, `++t power 0`):** DAV pulses twice (0.4.4's
    UNT, UNL), ATN is let go, then the 5 V falls: below 1 V in 0.36 ms, 0.5 V in 0.93 ms,
    0.2 V in 2.9 ms. DAV, IFC and ATN do not cross 1.5 V while it does; they sag from
    3.1 to about 2.45 V (the unpowered transceivers' load) and stay there.
- **Still open, for the hardware:** the lines not watched through a power-up or down:
  NRFD, NDAC, REN, EOI, the data. Nothing points at them now. 20 clean cycles passed; the earlier
  stops after a park and a new session (2.13) were on 0.4.2 or followed a restart.
  The fall time of +5V_GPIB (TP4, section 3) and the bus lines through a power-up,
  on a scope, are the measurements that settle it. If a clean power-up glitches, it is
  a rev B matter (an enable on the transceivers' bus side, or their supply held up and
  the outputs gated).

### 2.15 Two firmware bugs found by an HP 5316B (A1, 2026-11-19): fixed in 0.4.6
- **A read that never ends.** `++read eoi` ends only on EOI, and `++read` on a gap longer
  than `++read_tmo_ms` between bytes (`read_until()`, `prologix.c`). A 5316B addressed to
  talk sends reading after reading, ten a second in CHECK, with no EOI. So a read never
  ended, and everything the host sent queued behind it: `++t status` unanswered for
  minutes. Only a reboot ended it. A Prologix may well do the same (its manual gives no
  way to end a read), but the host must always be able to get the adapter back. Fix: a
  read ends when the host sends anything (that line is then carried out as usual), and
  `sim_bus.c` gets a talker that never stops, to test it. `++read 10` was never at risk.
- **`picotool reboot -f -a` never reboots a running board.** The SDK's reset interface
  takes "reboot from flash" (`RESET_REQUEST_FLASH`) as `watchdog_reboot(0, 0, 100)`, and
  the firmware's `usb_poll()` calls `watchdog_update()` every millisecond, which keeps
  reloading those 100 ms. The request was not answered either (the SDK leaves the status
  stage to the reboot), so the host saw a timeout. Unseen until now because the steps
  only ever use `-f -u` (to BOOTSEL), which jumps to the ROM at once; that is how A1 was
  freed (BOOTSEL, then `picotool reboot`). Fix: stop feeding the watchdog once a reboot
  has been asked for, or take that request in our own handler and reboot as `++rst` does.
- **0.4.6 (2026-11-19).**
  - **The read:** if nothing more from the host waits when a read begins, anything it then
    sends ends the read, and is carried out. Bare CR or LF don't count. If more was
    already waiting (several commands in one write), the read is a Prologix's, whole.
    `test_prologix` has a talker that never stops: 85 checks.
    On A1 with the 5316B in CHECK, `++ver` sent during a `++read eoi` was answered in 60 ms.
  - **The reboot:** `usb_poll()` sees a watchdog load under its own 2 s, and the main loop
    reboots as `++rst` does. A read under way ends for it.
    On A1: rebooted 0.17 s after the request when idle, 0.08 s in a never-ending read;
    `watchdog_reset` 0 both times.
    `picotool reboot -a -f --vid 0x1209 --pid 0x0001 --ser SERIAL` did the same.
    Without `--vid`/`--pid`, picotool finds no GPiBridge at all.
  - All three boards flashed (`flash` PASS).

### 2.7 New commands, for the bring-up and after
`++t info`, `++t lines`, `++t selftest`, `++t raw ...`, `++t identify`,
`++t autostart`, `++t power 2`. `HANDBOOK.md` section 2 lists them.

## 3. Open questions, for the first boards to answer

| question | where it is answered | answer |
|---|---|---|
| Which stepping are the RP2354As (A2 has erratum E9)? | stage 1, `chip_rev` | A1: **A4** by picotool (the SDK's `rp2350_chip_version()` reads 3). No E9 |
| What does the temperature sensor's raw count say the 3.3 V rail is? | stage 1 | A1: 860-866, about 3.24 V at an assumed 40 C die. A meter reads 3.308 V, so the die was nearer 32 C |
| How far is the crystal from 12 MHz? | stage 1 | A1: +1.4 to +1.8 ppm against `bell`'s clock |
| How long from reset to USB configured? | stage 1, `usb_ready_ms` | A1: 940 ms through a hub three levels deep (expected 150-300); to measure on a port of the PC itself |
| Does `picotool reboot -f -u` reach the reset interface (the udev rule)? | stage 1 | yes, given our USB IDs: `picotool reboot -u -f --vid 0x1209 --pid 0x0001 --ser SERIAL` put A1 in BOOTSEL, and `-a` (from 0.4.6) rebooted it into the firmware (2026-11-19). Without `--vid`/`--pid` picotool finds no board; with several plugged in it needs `--ser` |
| Does the failsafe work: three hangs land in BOOTSEL? | `run.py failsafe` | A1: yes, each hang caught at 2.03 s |
| Is +5V_GPIB above 4.75 V on this cable and port, bus on? | stage 1b | A1: **yes, 5.144 V**, with VBUS 5.159 V through a hub three levels deep (5.202 V with the bus off). Q1 drops 15 mV |
| The ripple on +1V1 with the substituted L1, bus off and on | stage 1b | A1: 2.5 mV rms on and off; at most 48 mV pp (hand-held probe, full bandwidth), against 60. DC 1.10-1.11 V |
| Does R21 back-power +5V_GPIB through the SN75161B's DC input with the bus off (`PIN_AUDIT.md`)? | stage 1b, TP4 bus off | A1: **no**, 0 V on a meter |
| How fast does +5V_GPIB fall when Q1 opens (firmware waits 3 ms)? | stage 1b, the scope on TP4 | A1: below 1 V in 0.36 ms, 0.5 V in 0.93 ms, 0.2 V in 2.9 ms (on the 33120A's bus, 2026-11-18): 3 ms is enough. Rises to 4.9 V within a millisecond; IFC follows at 6 ms (2.14) |
| The board's current, idle and with the bus on (the descriptor asks for 300 mA) | an inline USB meter, if one is at hand | |
| Does a free bus read as free (section 2.4)? | stages 1, 4 | A1: **yes** on the E3646A's bus (one device, no controller): `++t power 1` took it. Stage 4 again |
| A real instrument through the soldered plug | the E3646A, by hand (2026-11-18), before stage 4 | A1: **yes**. Output 2 stepped into 1.5 Ω and read back within 1 % of the same supply over RS-232; 5999 bytes out, 1540 in, no timeout, no "no listener" (`results/2026-11-18/134503_e3646a_A1.json`). So the plug is the right way round and DIO1-8, DAV, NRFD, NDAC, ATN and the supply's EOI pass. Later that day SRQ (raised by `*OPC` with `*SRE 32`, serial poll 96, released by the poll) and EOI sent by A1 (a `*IDN?` ended by EOI alone was answered) passed too (`140851_e3646a_speed_A1.json`). Not shown: IFC, REN |
| Do the plug's pins, press-fitted, hold the board square in the base? | stage 2 | |
| Queries per second against the Prologix's 31 | stage 4 | **A1 on the 33120A: 44.7 and 44.9 `*IDN?` a second** (2026-11-18, `results/2026-11-18/142450_gen_A1.json`, `143954_gen_A1.json`). On the E3646A: `*OPC?` 29/s, `VOLT?` 24/s, `*IDN?` 16/s, all set by the supply: a capture shows A1 taking each byte in about 1 µs, the supply 90 ms to start answering `*IDN?` and 75 µs to take each byte sent to it. A1's own round trip (`++ver`) is 0.24 ms |
| 16,000 points: how long, against the Prologix's 7 to 9 s? | stage 4 | A1: 9.6 s, then **8.1 s** once lab-instrument-control stopped re-asking during the upload (2.13). The scope saw the 16,000 points played as sent (correlation, `143954_gen_A1.json`) |
| The Lite's low level on a real bus (0.22 V expected with one instrument) | stage 6 | |

## 4. From `DESIGN_NOTES.md` section 6, for the record

A USB PID of our own; an ESD array on USB (USBLC6) if a board dies of it; a smaller,
cheaper Lite on two layers; the SN75162B (1.4 above); and in firmware a PIO bus engine,
USBTMC/USB488 beside the serial port, device mode, and A/B images.
