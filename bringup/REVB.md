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
  beeps (`run.py rails`).

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
  the two-board walk names it (`run.py pair`).

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
  Abracon AOTA of the design. Stage 1b measures whether it matters.
- **The housing's screws** are M2 x 8, not M2 x 10 (Response 9).

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
- **`++t info`** adds the watchdog's load and rate and the reason for the last start
  (`wd_load`, `wd_per_ms`, `boot_reason`, `boot_scratch4`); `++t crash` hangs on purpose.

### 2.7 New commands, for the bring-up and after
`++t info`, `++t lines`, `++t selftest`, `++t raw ...`, `++t identify`,
`++t autostart`, `++t power 2`. `HANDBOOK.md` section 2 lists them.

## 3. Open questions, for the first boards to answer

| question | where it is answered | answer |
|---|---|---|
| Which stepping are the RP2354As (A2 has erratum E9)? | stage 1, `chip_rev` | A1: **A4** by picotool (the SDK's `rp2350_chip_version()` reads 3). No E9 |
| What does the temperature sensor's raw count say the 3.3 V rail is? | stage 1 | A1: 860-866, about 3.24 V at an assumed 40 C die |
| How far is the crystal from 12 MHz? | stage 1 | A1: +1.4 to +1.8 ppm against `bell`'s clock |
| How long from reset to USB configured? | stage 1, `usb_ready_ms` | A1: 940 ms through a hub three levels deep (expected 150-300); to measure on a port of the PC itself |
| Does `picotool reboot -f -u` reach the reset interface (the udev rule)? | stage 1 | not yet: the rule is not installed. BOOTSEL itself works without it (plugdev) |
| Does the failsafe work: three hangs land in BOOTSEL? | `run.py failsafe` | A1: yes, each hang caught at 2.03 s |
| Is +5V_GPIB above 4.75 V on this cable and port, bus on? | stage 1b | |
| The ripple on +1V1 with the substituted L1, bus off and on | stage 1b | |
| How fast does +5V_GPIB fall when Q1 opens (firmware waits 3 ms)? | stage 1b, the scope on TP4 | |
| The board's current, idle and with the bus on (the descriptor asks for 300 mA) | an inline USB meter, if one is at hand | |
| Does a free bus read as free (section 2.4)? | stages 1, 4 | |
| Do the plug's pins, press-fitted, hold the board square in the base? | stage 2 | |
| Queries per second against the Prologix's 31 | stage 4 | |
| 16,000 points: how long, against the Prologix's 7 to 9 s? | stage 4 | |
| The Lite's low level on a real bus (0.22 V expected with one instrument) | stage 6 | |

## 4. From `DESIGN_NOTES.md` section 6, for the record

A USB PID of our own; an ESD array on USB (USBLC6) if a board dies of it; a smaller,
cheaper Lite on two layers; the SN75162B (1.4 above); and in firmware a PIO bus engine,
USBTMC/USB488 beside the serial port, device mode, and A/B images.
