# GPiBridge rev A: the bring-up log

One entry a step, newest last, written by `bringup/run.py`; the full record of each is
the JSON file it names. `STATUS.md` is where things stand now.

## 2026-11-15  before the first board: on a PC only

No board has had power. What was run, on the bench PC `bell`:
- the firmware (0.4.0) builds for the RP2354A with no warnings, 60.4 kB;
- `make -C firmware/test`: 70 protocol checks; the pin layer under 31,577 pin changes
  (GPiBridge) and 50,189 (the Lite), no rule broken; sigrok's decoder reads 12 of 12
  recordings exactly;
- `pytest bringup/`: 28 tests, every step against simulated boards, good ones and
  faulty ones;
- lab-instrument-control's `test_scpi_link.py`: 18, with the GPiBridge found as a GPIB
  adapter.

Seven firmware faults were found and fixed on the way (`REVB.md` section 2).

## 2026-11-16 08:41-09:16  A1, the first board: what the entries below do not say

Jason plugged one assembled GPiBridge into `bell` through a hub at 08:41. It came up as
`RP2350 Boot` (2e8a:000f): USB-C, the crystal and both rails good enough for the ROM.
picotool: RP2350 stepping **A4**, QFN60, blank flash. It was named **A1**
(serial 9F9D542A93F67D76).

- **08:42 `flash`: firmware 0.4.0 loaded and answered.**
- **08:42-08:57: `bare` failed four times** with "did not come back within 15 s after a
  reboot", each time ending in BOOTSEL. No record was written (the step raised before
  saving; it now names the reboot and what it saw). Bisected by replaying `bare`'s
  commands; the cause turned out to be two firmware bugs and a misleading message.
  - **Deliberate reboots counted as crashes.** `++rst`, `++t console 1`, `++t console 0`
    within 10 s made three "crashes", and the failsafe sent the board to BOOTSEL. On the
    RP2350, `watchdog_caused_reboot()` is true after `watchdog_reboot()`.
  - **No setting was ever saved unless a capture had run in that power-up**:
    `flash_safe_execute()` refuses (`PICO_ERROR_NOT_PERMITTED`) while core 1 is not a
    lockout victim, and only `++t capture start` started core 1. So `++t console 1`
    came back with one port, and `park`'s "stay off the bus" was not kept the first
    time. `bare`'s own "a setting survives a reboot" check had passed only because it
    ran after the capture.
  - The step's message said "after a reboot" but meant the third one; the reboot after
    `++rst` had worked. A byte-for-byte log of what `bare` and the replay sent showed it.

  Both fixed in 0.4.1 (`REVB.md` 2.8, 2.9); `bare` now saves a setting before any
  capture and checks `settings_errors`.
- **09:08: `failsafe` failed twice, the board right both times.** Three deliberate hangs
  (`++t crash`, new) went: firmware, firmware, BOOTSEL, as designed. The step's first
  `picotool reboot` came the instant BOOTSEL appeared and was not answered (it retries
  now). Its stopwatch started after closing the port, and closing blocks for the
  2 s the board is hung, so it read 0.06 s for a 2.03 s hang. `++t info` now reports the
  watchdog's load (2,000,000), its rate (1000 a ms) and why the chip last started (reason
  1, timer), which settled it.
- **09:14 0.4.2** (0.4.1 plus `++t crash` and the watchdog fields): `flash`, `bare` and
  `failsafe` all pass.

**A1's numbers:**
- crystal +1.4 to +1.8 ppm against `bell`'s clock;
- temperature sensor 860-866 counts, so the 3.3 V rail is about 3.24 V if the die is
  at 40 C;
- reset to USB configured 940 ms through this hub (three hub levels deep: 1-6.4.4.2);
- a reboot back to answering in 1.12 s, BOOTSEL and back in 1.7 s;
- IFC 151 µs;
- the self-test reads every receive path of both transceivers as designed, and the
  5 V switch opens and closes.

## 2026-11-16 08:42:10  `flash` A1: PASS

Record: `results/2026-11-16/084210_flash_A1.json`

- ok   an RP2354A is waiting in its ROM bootloader (2e8a:000f)
- ok   picotool load and verify, USB 1-6.4.4.2
- ok   A1 (9F9D542A93F67D76) runs the new firmware

## 2026-11-16 09:01:23  `flash` A1: PASS

Record: `results/2026-11-16/090123_flash_A1.json`

- ok   an RP2354A is waiting in its ROM bootloader (2e8a:000f)
- ok   picotool load and verify, USB 1-6.4.4.2
- ok   A1 (9F9D542A93F67D76) runs the new firmware

## 2026-11-16 09:01:49  `bare` A1: PASS

Record: `results/2026-11-16/090149_bare_A1.json`

- ok   ++ver names the firmware
- ok   the firmware read the board it is on (R21 on DC)
- ok   the 3.3 V rail, by the temperature sensor against it
- ok   the system clock
- ok   not restarted by the watchdog
- ok   reset to USB configured
- ok   the 12 MHz crystal against this PC
- ok   the self-test (5 V switch, receive paths, joints)
- ok   ++t power 1, then 0
- ok   a write to an empty bus is counted as "no listener"
- ok   the capture saw the bus start: IFC asserted for the time the firmware holds it
- ok   a setting survives a reboot (flash)
- ok   ++t console 1: a second serial port, which answers "status" in JSON
- ok   ++t console 0: one port again, as a Prologix
- ok   ++t bootsel: the RP2354A appears in its ROM bootloader
- ok   picotool reboot: back into the firmware
- ok   parked: off the bus, and told to stay off it

## 2026-11-16 09:05:03  `flash` A1: PASS

Record: `results/2026-11-16/090503_flash_A1.json`

- ok   an RP2354A is waiting in its ROM bootloader (2e8a:000f)
- ok   picotool load and verify, USB 1-6.4.4.2
- ok   A1 (9F9D542A93F67D76) runs the new firmware

## 2026-11-16 09:05:12  `bare` A1: PASS

Record: `results/2026-11-16/090512_bare_A1.json`

- ok   ++ver names the firmware
- ok   the firmware read the board it is on (R21 on DC)
- ok   the 3.3 V rail, by the temperature sensor against it
- ok   the system clock
- ok   not restarted by the watchdog
- ok   reset to USB configured
- ok   the 12 MHz crystal against this PC
- ok   the self-test (5 V switch, receive paths, joints)
- ok   ++t power 1, then 0
- ok   a write to an empty bus is counted as "no listener"
- ok   a setting survives a reboot (flash)
- ok   no settings write refused by the flash
- ok   the capture saw the bus start: IFC asserted for the time the firmware holds it
- ok   ++t console 1: a second serial port, which answers "status" in JSON
- ok   ++t console 0: one port again, as a Prologix
- ok   three deliberate reboots within 10 s (++rst, console on, off) are not taken for crashes
- ok   ++t bootsel: the RP2354A appears in its ROM bootloader
- ok   picotool reboot: back into the firmware
- ok   parked: off the bus, and told to stay off it

## 2026-11-16 09:08:17  `failsafe` A1: FAIL

Record: `results/2026-11-16/090817_failsafe_A1.json`

- FAIL hang 1: the watchdog restarts the board into the firmware, which says why (got {"crash": 1, "gone_after_s": 0.05, "then": "running", "watchdog_reset": 1}, wanted "running, after 2 s")
- FAIL hang 2: the watchdog restarts the board into the firmware, which says why (got {"crash": 2, "gone_after_s": 0.05, "then": "running", "watchdog_reset": 1}, wanted "running, after 2 s")
- FAIL hang 3: the watchdog restarts the board into the ROM bootloader (got {"crash": 3, "gone_after_s": 0.05, "then": "BOOTSEL", "watchdog_reset": null}, wanted "BOOTSEL, after 2 s")
- ok   picotool reboot answered
- ok   picotool boots the image again, and that is not counted as a crash
- note: picotool reboot answered at try 2

## 2026-11-16 09:08:41  `failsafe` A1: FAIL

Record: `results/2026-11-16/090841_failsafe_A1.json`

- FAIL hang 1: the watchdog restarts the board into the firmware, which says why (got {"crash": 1, "gone_after_s": 0.06, "then": "running", "watchdog_reset": 1}, wanted "running, after 2 s")
- FAIL hang 2: the watchdog restarts the board into the firmware, which says why (got {"crash": 2, "gone_after_s": 0.06, "then": "running", "watchdog_reset": 1}, wanted "running, after 2 s")
- FAIL hang 3: the watchdog restarts the board into the ROM bootloader (got {"crash": 3, "gone_after_s": 0.06, "then": "BOOTSEL", "watchdog_reset": null}, wanted "BOOTSEL, after 2 s")
- ok   picotool reboot answered
- ok   picotool boots the image again, and that is not counted as a crash
- note: picotool reboot answered at try 2

## 2026-11-16 09:10:51  `flash` A1: PASS

Record: `results/2026-11-16/091051_flash_A1.json`

- ok   an RP2354A is waiting in its ROM bootloader (2e8a:000f)
- ok   picotool load and verify, USB 1-6.4.4.2
- ok   A1 (9F9D542A93F67D76) runs the new firmware

## 2026-11-16 09:11:51  `flash` A1: PASS

Record: `results/2026-11-16/091151_flash_A1.json`

- ok   an RP2354A is waiting in its ROM bootloader (2e8a:000f)
- ok   picotool load and verify, USB 1-6.4.4.2
- ok   A1 (9F9D542A93F67D76) runs the new firmware

## 2026-11-16 09:14:08  `flash` A1: PASS

Record: `results/2026-11-16/091408_flash_A1.json`

- ok   an RP2354A is waiting in its ROM bootloader (2e8a:000f)
- ok   picotool load and verify, USB 1-6.4.4.2
- ok   A1 (9F9D542A93F67D76) runs the new firmware

## 2026-11-16 09:14:17  `bare` A1: PASS

Record: `results/2026-11-16/091417_bare_A1.json`

- ok   ++ver names the firmware
- ok   the firmware read the board it is on (R21 on DC)
- ok   the 3.3 V rail, by the temperature sensor against it
- ok   the system clock
- ok   not restarted by the watchdog
- ok   reset to USB configured
- ok   the 12 MHz crystal against this PC
- ok   the self-test (5 V switch, receive paths, joints)
- ok   ++t power 1, then 0
- ok   a write to an empty bus is counted as "no listener"
- ok   a setting survives a reboot (flash)
- ok   no settings write refused by the flash
- ok   the capture saw the bus start: IFC asserted for the time the firmware holds it
- ok   ++t console 1: a second serial port, which answers "status" in JSON
- ok   ++t console 0: one port again, as a Prologix
- ok   three deliberate reboots within 10 s (++rst, console on, off) are not taken for crashes
- ok   ++t bootsel: the RP2354A appears in its ROM bootloader
- ok   picotool reboot: back into the firmware
- ok   parked: off the bus, and told to stay off it

## 2026-11-16 09:15:10  `failsafe` A1: PASS

Record: `results/2026-11-16/091510_failsafe_A1.json`

- ok   hang 1: the watchdog restarts the board into the firmware, which says why
- ok   hang 2: the watchdog restarts the board into the firmware, which says why
- ok   hang 3: the watchdog restarts the board into the ROM bootloader
- ok   picotool reboot answered
- ok   picotool boots the image again, and that is not counted as a crash
- note: picotool reboot answered at try 2

## 2026-11-18 11:45:40  `rails` A1: PASS

Record: `results/2026-11-18/114540_rails_A1.json`

- ok   VBUS at TP1
- ok   +3V3 at TP2
- ok   +1V1 at TP3
- ok   +5V_GPIB at TP4, bus on
- ok   +5V_GPIB falls when the bus is switched off (Q1 opens)
- ok   +1V1 ripple (a scope's figure, rev A's substituted L1)
- note: Hand meter, black lead on J1's shell (Jason, 2026-11-18). TP1-TP4 first with A1 parked (bus off), then TP4 and TP1 with the bus on (green LED lit).
- note: VBUS fell 43 mV when the transceivers came on (5.202 to 5.159 V, through a hub three levels deep); Q1 drops 15 mV (5.159 to 5.144 V).
- note: TP4 at 0 V with the bus off: R21 (the SN75161B's DC pull-up) does not back-power +5V_GPIB (PIN_AUDIT.md's uncertain item).
- note: +1V1 by scope (results/2026-11-18/113626_scope_1V1_A1.json): 1.107 V bus on, 1.100 V off. Ripple bus on / off: 14.8 / 12.5 mV pp at 200 ns/div; 44.3 / 45.3 mV pp, 2.5 mV rms at 20 us/div; 48.3 / 46.3 mV pp at 1 ms/div. The same with the transceivers on or off; the pp is mostly spikes picked up by a hand-held probe at full bandwidth.
- note: The 3.3 V rail by meter, 3.308 V, against stage 1's 3.24 V from the temperature sensor at an assumed 40 C die: the die was nearer 32 C.

## 2026-11-18 13:36:50  `plug` A1: PASS

Record: `results/2026-11-18/133650_plug_A1.json`

- ok   the self-test (5 V switch, receive paths, joints)
- note: not seen from here: an open joint at the plug, two DIO lines bridged, the plug turned round

## 2026-11-18 13:45:03  the E3646A by hand, A1 (not a step)

Record: `results/2026-11-18/134503_e3646a_A1.json`

- A1's plug straight into the first E3646A's GPIB socket (`CAL:COUNt?` +21: output 1 faulty), set to GPIB at address 2 by Jason; a 1.5 Ω 5 W resistor on output 2. Bench claim `E3646A@GPIB2`.
- `++t power 1` by hand, then lab-instrument-control's `AgilentE36xxA(address=2, prologix=A1's port)`. Found in the power-on state (0 V, 3 A, P8V, OVP 22 V, output off); put back so, output off.
- Output 2, each setting read back right: 0.2 V asked, 0.1939 V at 0.1285 A; 0.5 V, 0.4953 V at 0.3228 A; 1.0 V with 0.8 A limit, 0.9960 V at 0.6456 A (CV, 0.64 W); 1.0 V with 0.3 A limit, 0.3018 A at 0.4629 V (CC). Within 1 % of the RS-232 run of 2026-10-15 (lab-instrument-control `hp/hp.md`).
- A1 after: 5999 bytes out, 1540 in, 0 timeouts, 0 "no listener". Parked with `run.py park A1` (new).

## 2026-11-18 13:49-14:09  the E3646A ramped, then pushed for speed, A1 (not a step)

Record: `results/2026-11-18/140851_e3646a_speed_A1.json`, capture `135830_capture_idn_e3646a_A1.vcd`

- Ramps of output 2, 0 to 1 V in 0.1 V steps (0.8 A limit), for a video: every 0.5 s (248 steps, none late), through the trigger subsystem, then every 7 s. Jason power-cycled the supply during the second: 4 timeouts, no hang. That ramp's stop came in mid-query and its clean-up read every answer one late; fixed in lab-instrument-control (below).
- Speed, output off: A1's own `++ver` 0.24 ms; `*OPC?` 29/s, `VOLT?` 24/s, `*IDN?` 16/s, `MEAS` 10/s; `VOLT x;*OPC?` 21/s; `VOLT x` then `VOLT?` 12/s, 500 pairs, no mismatch; 200 `VOLT` back to back, 25/s. The capture: A1 takes a byte in about 1 µs; the supply takes 90 ms to start answering `*IDN?`.
- Through the plug, now also: SRQ (serial poll 96) and EOI sent by A1.
- Faults: an empty address, a read with nothing asked, refused commands, an answer left unread, a timeout mid-measurement, a signal mid-query, 80 commands in one message, 5000 bytes of junk. Before the fix in lab-instrument-control's `scpi_link`, an answer left unread shifted every later answer by one, `clear()` included; after it, every case recovers on the next query.
- Output on: a step and a current reading 6.6/s. Left as found each time (0 V, 3 A, output off, `*SRE`/`*ESE` 0); A1 parked.

## 2026-11-18 14:24:50  `gen` A1: FAIL

Record: `results/2026-11-18/142450_gen_A1.json`

- ok   on the bus as the controller
- ok   *IDN? through lab-instrument-control
- ok   a sine set and read back
- ok   a triangle set and read back
- ok   20 MHz refused, with the generator's own error
- ok   the error queue is empty afterwards
- ok   1000 points uploaded in one binary line (2000 bytes): the count and the average the generator computed
- ok   16000 points uploaded in one binary line (32000 bytes): the count and the average the generator computed
- ok   a serial poll answers with a status byte
- ok   sigrok's IEEE-488 decoder reads the capture as the query and its answer
- FAIL no timeout and no "no listener" in the whole step (got [31, 2], wanted [28, 2])
- note: through the Prologix the same loop runs at about 31 a second (lab-instrument-control, gpib/gpib.md)

## 2026-11-18 14:39:54  `gen` A1: FAIL

Record: `results/2026-11-18/143954_gen_A1.json`

- ok   on the bus as the controller
- ok   *IDN? through lab-instrument-control
- ok   a sine set and read back
- ok   on the scope: the sine
- ok   a triangle set and read back
- ok   20 MHz refused, with the generator's own error
- ok   the error queue is empty afterwards
- ok   1000 points uploaded in one binary line (2000 bytes): the count and the average the generator computed
- ok   16000 points uploaded in one binary line (32000 bytes): the count and the average the generator computed
- ok   on the scope: the 16000 points played
- ok   a serial poll answers with a status byte
- FAIL sigrok's IEEE-488 decoder reads the capture as the query and its answer (got "*", wanted "*IDN?\\n\\n")
- FAIL no timeout and no "no listener" in the whole step (got [86, 3], wanted [84, 3])
- note: through the Prologix the same loop runs at about 31 a second (lab-instrument-control, gpib/gpib.md)

## 2026-11-18 14:45:16  `flash` A1: PASS

Record: `results/2026-11-18/144516_flash_A1.json`

- ok   an RP2354A is waiting in its ROM bootloader (2e8a:000f)
- ok   picotool load and verify, USB 3-3
- ok   A1 (9F9D542A93F67D76) runs the new firmware

## 2026-11-18 14:53:07  `gen` A1: FAIL

Record: `results/2026-11-18/145307_gen_A1.json`

- ok   on the bus as the controller
- ok   *IDN? through lab-instrument-control
- ok   a sine set and read back
- ok   on the scope: the sine
- ok   a triangle set and read back
- ok   20 MHz refused, with the generator's own error
- ok   the error queue is empty afterwards
- ok   1000 points uploaded in one binary line (2000 bytes): the count and the average the generator computed
- ok   16000 points uploaded in one binary line (32000 bytes): the count and the average the generator computed
- FAIL on the scope: the 16000 points played (got {"correlation": 0.9363455941581127, "gain": 0.4483221049944027, "start_s": -0.0008174000000000011}, wanted {"correlation": "1.0 +- 0.1", "gain": "0.5 +- 0.05"})
- ok   a serial poll answers with a status byte
- ok   sigrok's IEEE-488 decoder reads the capture as the query and its answer
- ok   no timeout and no "no listener" in the whole step
- note: through the Prologix the same loop runs at about 31 a second (lab-instrument-control, gpib/gpib.md)

## 2026-11-18 14:54:15  `gen` A1: PASS

Record: `results/2026-11-18/145415_gen_A1.json`

- ok   on the bus as the controller
- ok   *IDN? through lab-instrument-control
- ok   a sine set and read back
- ok   on the scope: the sine
- ok   a triangle set and read back
- ok   20 MHz refused, with the generator's own error
- ok   the error queue is empty afterwards
- ok   1000 points uploaded in one binary line (2000 bytes): the count and the average the generator computed
- ok   16000 points uploaded in one binary line (32000 bytes): the count and the average the generator computed
- ok   on the scope: the 16000 points played
- ok   a serial poll answers with a status byte
- ok   sigrok's IEEE-488 decoder reads the capture as the query and its answer
- ok   no timeout and no "no listener" in the whole step
- note: through the Prologix the same loop runs at about 31 a second (lab-instrument-control, gpib/gpib.md)

## 2026-11-18 14:24-14:58  the 33120A between the stage 4 runs (by hand)

- 14:24 `gen` FAIL only on 3 timeouts: lab-instrument-control re-asking for `*OPC?` behind the 32 kB upload (fixed there: a read waits for the adapter after a long write).
- 14:27 the 33120A stopped taking data (held NRFD after addressing; device clear and IFC did not free it; "Rmt", keys dead). Jason switched it off and on.
- 14:39 `gen` with the scope: every check but two: the last `*IDN?` lost after its first byte (0.4.2 gave up on a listener busy over 1 s) and 2 timeouts. Firmware 0.4.3 (writes wait 10 s) built, simulated, flashed (14:45).
- 14:47 nothing answered within seconds of a power-up; 14:52, after 3 minutes with A1 parked, it answered.
- 14:53 `gen`: no timeout at all; the scope's amplitude check was too strict (fixed: alignment to a tenth of a sample, amplitude by RMS). 14:54 `gen`: PASS.
- 14:56 `run.py speed`: its `APPLy:...;APPLy?` was read as `APPLy:APPLy?` (fixed: `;:`); no answer, re-reads for 5 s, device clear, and the 33120A stopped taking data again. A1 parked; waiting for a power cycle (`REVB.md` 2.13).

## 2026-11-18 15:59:32  `flash` A1: PASS

Record: `results/2026-11-18/155932_flash_A1.json`

- ok   an RP2354A is waiting in its ROM bootloader (2e8a:000f)
- ok   picotool load and verify, USB 3-3
- ok   A1 (9F9D542A93F67D76) runs the new firmware

## 2026-11-18 16:51:36  `gen` A1: PASS

Record: `results/2026-11-18/165136_gen_A1.json`

- ok   on the bus as the controller
- ok   *IDN? through lab-instrument-control
- ok   a sine set and read back
- ok   a triangle set and read back
- ok   20 MHz refused, with the generator's own error
- ok   the error queue is empty afterwards
- ok   1000 points uploaded in one binary line (2000 bytes): the count and the average the generator computed
- ok   16000 points uploaded in one binary line (32000 bytes): the count and the average the generator computed
- ok   a serial poll answers with a status byte
- ok   sigrok's IEEE-488 decoder reads the capture as the query and its answer
- ok   no timeout and no "no listener" in the whole step
- note: through the Prologix the same loop runs at about 31 a second (lab-instrument-control, gpib/gpib.md)

## 2026-11-18 16:51:58  `speed` A1: PASS

Record: `results/2026-11-18/165158_speed_A1.json`

- ok   queries: no timeout and no "no listener"
- ok   settings back to back: *OPC? answers and the last one holds
- ok   every setting read back as written
- ok   every setting read back in the same message
- ok   the instrument logged no error for any of it
- ok   a message ended by the board's EOI alone is understood
- ok   SRQ: raised by the instrument, read in the serial poll (RQS and ESB), let go after it
- ok   nobody at GPIB 30: an error that says so
- ok   nobody at GPIB 30: counted by the board
- ok   nobody: the next query gets its own answer
- ok   read_nothing: the next query gets its own answer
- ok   refused: the next query gets its own answer
- ok   answer_left_in_the_port: the next query gets its own answer
- ok   timeout_mid_answer: the next query gets its own answer
- ok   signal_mid_query: the next query gets its own answer
- ok   the board answers its own query after all that
- ok   unread_query_then_clear: the next query gets its own answer
- ok   chain_of_80: the next query gets its own answer
- ok   junk_5000: the next query gets its own answer
- ok   the capture holds the query and its answer
- ok   the 33120A left as it was found
- note: speed and fault tests: not a bring-up stage

## 2026-11-18 15:01-16:54  the 33120A's lock-ups traced (by hand; REVB.md 2.13-2.14)

- 15:06 stuck: serial poll status 0; a universal device clear sent by hand in `++t raw ctrl_talk` taken but NDAC never let go: its processor, not its GPIB chip, has stopped. Only its power switch frees it.
- 15:16-15:19 one piece at a time, `*IDN?` after each: empty reads, `APPLy:APPLy?`, the exact failing message, device clear, `APPLy:DC`, go to local, park and back: none stopped it.
- 15:53 20 bus off/on cycles 0.5 s apart: 20 of 20; 20 restarts of a live bus (0.4.3: 5 V off and on within 3 ms): stopped at the 10th. Firmware 0.4.4 (a restart does not switch the 5 V; 0.5 s minimum off; unaddress before letting go), simulated, flashed 15:59. 16:01 30 restarts: 30 of 30; 16:03 back-to-back off and on: stopped at the first.
- 16:35 Jason's wires on DAV (6), IFC (9), ATN (11), TP4; SDS2104X Plus channels 1-4. Generator power-up, A1 plug-in (bus off), A1's power-up: lines clean at 10 ns; still the first `*IDN?` after the generator's fresh power-up got nothing, twice. No bridge at the new joints (raw test).
- 16:49 the "top" 33120A (8.0-5.0-1.0, set to HP-IB 10): answered at once; 30 back-to-back off/ons, 30 off/ons, 30 restarts, 30 go-to-locals: 120 of 120; `gen` PASS (16:51); `speed` PASS, every fault (16:51). A1's power-down on the scope: 5 V below 0.2 V in 2.9 ms, lines clean. The first unit is at fault.
