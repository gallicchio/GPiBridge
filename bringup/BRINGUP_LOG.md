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

## 2026-11-19 08:46:46  `gen` A1: PASS

Record: `results/2026-11-19/084646_gen_A1.json`

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

## 2026-11-19 08:47:04  `speed` A1: PASS

Record: `results/2026-11-19/084704_speed_A1.json`

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

## 2026-11-19 08:38-08:52  the "bottom" 33120A (by hand; REVB.md 2.14)

- 08:40 the third 33120A (7.0-5.0-1.0, set to HP-IB, address 10), the same A1, wires and probes. Parked: its lines at 2.9 V, A1's 5 V off. A1's power-up on the scope: IFC 151 us at 6.0 ms, then UNT, UNL; `*IDN?` answered at once.
- 08:41 30 each of back-to-back off/on, off/on, restart, go to local and IFC, a `*IDN?` after each: 150 of 150.
- 08:43 `tools/gpibridge.py test 10` on the parked board: 21 empty reads in 70 s and `ok: false`, no reason given; its capture's VCD began with a 0x04 (`++eot_enable 1` left by `bringup/adapter.py`), which sigrok-cli refused. The tool now sets its own options (`++savecfg 0`, `++eot_enable 0`) and says when the bus is off; two simulated tests. With the bus on: 44.9 queries a second, serial poll 0; the capture decodes.
- 08:46 `gen` PASS; 08:47 `speed` PASS. 08:51 A1's power-down through `run.py park`: 5 V below 0.2 V at 2.91 ms, lines no lower than 2.33 V; `*IDN?` answered after it. Parked; scope restored.

## 2026-11-19 09:30:29  `flash` L1: PASS

Record: `results/2026-11-19/093029_flash_L1.json`

- ok   an RP2354A is waiting in its ROM bootloader (2e8a:000f)
- ok   picotool load and verify, USB 1-6.4.4.4
- ok   L1 (5F4293C74E3358D8) runs the new firmware

## 2026-11-19 09:30:42  `bare` L1: PASS

Record: `results/2026-11-19/093042_bare_L1.json`

- ok   ++ver names the firmware
- ok   the firmware read the board it is on (R21 on DC)
- ok   the 3.3 V rail, by the temperature sensor against it
- ok   the system clock
- ok   not restarted by the watchdog
- ok   reset to USB configured
- ok   the 12 MHz crystal against this PC
- ok   the self-test (5 V switch, receive paths, joints: the Lite, pin against pin)
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

## 2026-11-19 09:31:54  `plug` L1: PASS

Record: `results/2026-11-19/093154_plug_L1.json`

- ok   the self-test (5 V switch, receive paths, joints: the Lite, pin against pin)
- note: not seen from here: an open joint at the plug, two DIO lines bridged, the plug turned round

## 2026-11-19 09:46:26  `speed` L1: PASS

Record: `results/2026-11-19/094626_speed_L1.json`

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
- ok   the E3646A left as it was found
- note: speed and fault tests: not a bring-up stage

## 2026-11-19 09:44-09:49  L1 on the E3646A (by hand)

- L1 (firmware 0.4.5) on the first E3646A (1.7-5.0-1.0, CAL:COUNt +21) at GPIB 2: `*IDN?` at once, no timeout. `speed` PASS (above). `examples/agilent_e3646a.py`, its first run on hardware: output 2 at 0.5 V, 0.4 A limit into the 1.5 ohm resistor for 3 s, measured 0.494 V and 0.322 A, the output off and the settings put back, no error. Parked; the E3646A still claimed (cabled).
- Housed, the adapter did not fit the 33120A with its power cord in (REVB.md 1.9).

## 2026-11-19 09:49:44  `failsafe` L1: FAIL

Record: `results/2026-11-19/094944_failsafe_L1.json`

- FAIL hang 1: the watchdog restarts the board into the firmware, which says why (got {"crash": 1, "gone_after_s": 5.19, "then": "running", "watchdog_reset": 1}, wanted "running, after 2 s")
- FAIL hang 2: the watchdog restarts the board into the firmware, which says why (got {"crash": 2, "gone_after_s": 5.41, "then": "running", "watchdog_reset": 1}, wanted "running, after 2 s")
- FAIL hang 3: the watchdog restarts the board into the ROM bootloader (got {"crash": 3, "gone_after_s": 5.41, "then": "BOOTSEL", "watchdog_reset": null}, wanted "BOOTSEL, after 2 s")
- ok   picotool reboot answered
- ok   picotool boots the image again, and that is not counted as a crash
- note: picotool reboot answered at try 2

## 2026-11-19 09:51:42  `failsafe` L1: FAIL

Record: `results/2026-11-19/095142_failsafe_L1.json`

- FAIL hang 1: the watchdog restarts the board into the firmware, which says why (got {"crash": 1, "gone_after_s": 5.16, "then": "running", "watchdog_reset": 1, "close_took_s": 5.15}, wanted "running, after 2 s")
- FAIL hang 2: the watchdog restarts the board into the firmware, which says why (got {"crash": 2, "gone_after_s": 5.36, "then": "running", "watchdog_reset": 1, "close_took_s": 5.35}, wanted "running, after 2 s")
- FAIL hang 3: the watchdog restarts the board into the ROM bootloader (got {"crash": 3, "gone_after_s": 5.41, "then": "BOOTSEL", "watchdog_reset": null, "close_took_s": 5.35}, wanted "BOOTSEL, after 2 s")
- ok   picotool reboot answered
- ok   picotool boots the image again, and that is not counted as a crash
- note: picotool reboot answered at try 2

## 2026-11-19 09:53:25  `failsafe` L1: PASS

Record: `results/2026-11-19/095325_failsafe_L1.json`

- ok   hang 1: the watchdog restarts the board into the firmware, which says why
- ok   hang 2: the watchdog restarts the board into the firmware, which says why
- ok   hang 3: the watchdog restarts the board into the ROM bootloader
- ok   picotool reboot answered
- ok   picotool boots the image again, and that is not counted as a crash

## 2026-11-19 09:49-09:53  L1's failsafe: the step's timing, not the board (by hand; REVB.md 2.10)

- 09:49 and 09:51 `failsafe L1` FAIL: every hang "took" 5.2-5.4 s, though each restarted as it should (running, running, BOOTSEL). 09:53 one `++t crash` with the port left open: gone from USB in 2.02 s, the kernel's disconnect at 2.00 s. Closing the port right after the crash had held the disconnect up to the kernel's request timeout. The step now closes it once the board is gone: PASS at 09:53 (2.03 s three times).

## 2026-11-19 10:21:07  `flash` A2: PASS

Record: `results/2026-11-19/102107_flash_A2.json`

- ok   an RP2354A is waiting in its ROM bootloader (2e8a:000f)
- ok   picotool load and verify, USB 3-5.3
- ok   A2 (E9D119818C2ADDD2) runs the new firmware

## 2026-11-19 10:21-10:23  A2: flashed; lost on USB in `bare` (by hand)

- 10:21 `flash` PASS: A2 (E9D119818C2ADDD2) runs 0.4.5 and read R21 as GPiBridge. It is on USB port 3-5.3, behind a VIA Labs hub (2109:2817); A1 and L1 were on a computer port (3-3).
- 10:22 `bare A2` stopped: after `++t console 0` (its third restart in the step; the first two came back) A2 did not enumerate: "device descriptor read/64, error -110" twice, "device not accepting address, error -71" twice, "unable to enumerate USB device". The hub had logged "clear tt 3 ... error -110" twice before, while A2 still worked. Next: A2 on a computer port, to tell the hub from the board.

## 2026-11-19 11:07:52  `flash` A1: PASS

Record: `results/2026-11-19/110752_flash_A1.json`

- ok   an RP2354A is waiting in its ROM bootloader (2e8a:000f)
- ok   picotool load and verify, USB 3-3.1
- ok   A1 (9F9D542A93F67D76) runs the new firmware

## 2026-11-19 11:00-11:12  the physics stock room's 3325B, 5316B and 5370B (by hand; Jason away)

- Jason's photos (`photos/`, not committed): A2 on the 3325B (Main Signal Out empty), L1 on the 5370B, the third board on the 5316B. All three boards on USB through one hub, ports 3-3.1, 3-3.3, 3-3.4. Claimed HP3325B, HP5316B, HP5370B; released E3646A@GPIB2.
- A serial poll at every address 1-30 on each bus: L1 found address 3 (status 32), A2 address 17 (status 2); on A1 every address answered 0: the 5316B is set to TALK ONLY (a capture of a poll at address 9: SPE, talk 9, then two NUL bytes sent by it). A serial poll at an empty address counts a timeout, as it must (a talker cannot be seen to be absent).
- `examples/hp_3325b.py` through A2: `ID?` HP3325B; 1 kHz, 0.1 Vpp, 0 V, sine read back; 1 mVpp; no error. `examples/hp_5370b.py` through L1: trigger levels read back exactly, FN9 error 1 as it should. Bus captures (`110517_hp3325b_ifr_A2.vcd`, `110536_hp5370b_fn2_L1.vcd`): the 3325B ends in CR LF with EOI; the 5370B in CR LF without EOI. `gpib_port.read(end='\n')` added; the 5370B script reads to the line feed (1.4 s for the whole run).
- 120 bus cycles each (30 off/on, restart, IFC, go to local): A2 with the 3325B, `ID?` after each; L1 with the 5370B, a serial poll after each: 120 of 120 both.
- A2 on the hub at 3-3: 10 `++rst` and 3 console on/off pairs, each back in about 1 s; no kernel error. This morning's loss was on the other hub (3-5, which logged its own errors).
- A1 flashed to 0.4.5 (11:07): all three boards now run it.

## 2026-11-19 12:48:51  `bare` A2: PASS

Record: `results/2026-11-19/124851_bare_A2.json`

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

## 2026-11-19 12:55:48  `failsafe` A2: PASS

Record: `results/2026-11-19/125548_failsafe_A2.json`

- ok   hang 1: the watchdog restarts the board into the firmware, which says why
- ok   hang 2: the watchdog restarts the board into the firmware, which says why
- ok   hang 3: the watchdog restarts the board into the ROM bootloader
- ok   picotool reboot answered
- ok   picotool boots the image again, and that is not counted as a crash
- note: picotool reboot answered at try 2

## 2026-11-19 12:56:03  `plug` A2: PASS

Record: `results/2026-11-19/125603_plug_A2.json`

- ok   the self-test (5 V switch, receive paths, joints)
- note: not seen from here: an open joint at the plug, two DIO lines bridged, the plug turned round

## 2026-11-19 12:44-13:05  A2's stage 1; the 5316B through A1; two firmware bugs (by hand)

- A2 off the 3325B, USB only: `bare`, `failsafe`, `plug` all PASS (records above). The
  first `failsafe` crashed in the step, not the board: it took "no GPiBridge on USB" for
  "gone", never true beside A1 and L1 (A2 was back running in 2 s). Fixed to follow A2's
  serial and USB device number (`REVB.md` 2.10); rerun PASS. Released HP3325B while A2 was
  off it; A2 back on the 3325B at 13:0x (Jason), claimed again.
- 12:44: the 5316B still answered a serial poll at every address, and nothing listened at
  20, 9 or 1: still TALK ONLY. Jason's photo and the manual's drawing (p. 3-33): seven
  switches, the five on the right A5-A1 at 10100 = 20; the two on the left both up, where
  the drawing has them down. Jason set both down (12:5x): a poll at 20 answered, every
  other address timed out.
- `examples/hp_5316b.py --address 20` through A1: CHECK read `F      +1.00000E+07`,
  10,000,000 Hz to within 2 x 100 Hz; FN1 taken; status byte 0; mismatches none.
- `tools/gpibridge.py capture 20 "IN FN9 GA3 WA1"` hung A1: the capture reads with
  `++read eoi`, and the 5316B, addressed to talk, sent a CHECK reading about ten times a
  second with no EOI, so the read never ended and every later command queued behind it
  (`REVB.md` 2.15). `picotool reboot -f -a` could not free it (the second bug in 2.15);
  the reset interface's BOOTSEL request, then `picotool reboot`, did. A1 came back parked.
- Captured instead with `++read 10` (`130417_hp5316b_check_A1.vcd`): the reading ends
  CR LF with EOI on no byte, 92 us a byte, 106 ms after the talk address. Counter left in
  FN1, WA0, SR0 and in local; A1 parked.

## 2026-11-19 13:10-13:30  three GPiBridges, one signal: the 3325B counted by the 5316B and the 5370B (by hand)

- Jason cabled the 3325B's MAIN SIGNAL through a BNC tee to the 5316B's INPUT A and the
  5370B's START. Claims updated (3325B: 1 Vpp, 0 V). A2 on the 3325B (17), A1 on the 5316B
  (20), L1 on the 5370B (3); `gpib_port` switched each parked board on the bus for the
  runs; parked again after (13:30), each instrument back on its front panel.
- 0.5 Vpp sine, 0 V offset. 5316B: FREQ A, trigger by its DAC at 0 V (`TR1`, `AT0`), rear
  long gate (`GA2`), `WA1 SR1`, a reading per `RE`. 5370B: frequency, one per `MR`.
- First try, the 5370B on START with `IN3`: single periods (the `SS1` sent after `GT3` won)
  at -100 ppm to -1.5 %, a fixed ~0.7 ns a period. With the gate last, `IN3` gave no
  measurement (9.99999999999E+62). With `IN2` (STOP, the manual's normal input for
  frequency) and `GT3` last it measured: so the STOP channel had the signal (cable moved,
  or a front-panel common-input setting: asked Jason).
- `examples/three_instruments.py`, 1 kHz to 20 MHz and 12,345,678.9 Hz: 3325B read back
  exactly, `ERR000`; 5316B +1.23 to +1.24 ppm at every frequency (12-13 s a reading, its
  rear gate); 5370B -0.028 to -0.034 ppm from 1 MHz up, +0.0 to +3.0 ppm below (0.1 s gate,
  slow edges); mismatches none. The 3325B left at 1 mVpp.
- 13:3x: Jason had moved the 5370B's cable to STOP (so `IN2` had the signal). The 5370B
  showed "Err 02" afterwards: overrange (Table 3-2: "TI is too long"), its measurement
  never ending with the 3325B at 1 mVpp. It stayed after the example was changed to leave
  it in its start-up codes (time interval), as it must: nothing on START, 1 mVpp on STOP.
  An `MR` in MD2 gave no output within 1 s and no service request. Harmless.

## 2026-11-19 13:44:40  `flash` A1: PASS

Record: `results/2026-11-19/134440_flash_A1.json`

- ok   an RP2354A is waiting in its ROM bootloader (2e8a:000f)
- ok   picotool load and verify, USB 3-3.1
- ok   A1 (9F9D542A93F67D76) runs the new firmware

## 2026-11-19 13:44:46  `flash` A2: PASS

Record: `results/2026-11-19/134446_flash_A2.json`

- ok   an RP2354A is waiting in its ROM bootloader (2e8a:000f)
- ok   picotool load and verify, USB 3-3.3
- ok   A2 (E9D119818C2ADDD2) runs the new firmware

## 2026-11-19 13:44:53  `flash` L1: PASS

Record: `results/2026-11-19/134453_flash_L1.json`

- ok   an RP2354A is waiting in its ROM bootloader (2e8a:000f)
- ok   picotool load and verify, USB 3-3.4
- ok   L1 (5F4293C74E3358D8) runs the new firmware

## 2026-11-19 13:38-14:05  firmware 0.4.6 on all three; the 5370B times two cables (by hand)

- Jason teed the 3325B's signal on to both the 5370B's START and STOP, by cables of about
  0.5 m and 1 m. Claim updated.
- 0.4.6 (`REVB.md` 2.15): a read the host has given up on ends when it sends more; the
  reset interface's reboot-from-flash is honoured. `test_prologix` 85 checks (a talker
  that never stops, CR LF, several commands in one write, a reboot due), `test_wire`,
  sigrok, `pytest bringup/` 39: all pass. `flash` A1, A2, L1: PASS (records above).
- A1 with the 5316B in CHECK: `++ver` sent during a `++read eoi` it never ends was answered
  60 ms later; `++t status` answered after it. Reboot-from-flash (the request picotool
  sends): A1 gone 0.17 s after it idle, 0.08 s in such a read; back, `watchdog_reset` 0.
  `picotool reboot -u -f --vid 0x1209 --pid 0x0001 --ser 9F9D542A93F67D76` put A1 in
  BOOTSEL; `picotool reboot -a -f` with the same rebooted it into the firmware. Without
  `--vid`/`--pid` picotool found no board (it looks for Raspberry Pi's IDs).
- `examples/cable_delay.py` (A2, L1): the 3325B's 1 MHz square to START and STOP; 1000
  intervals: -2.864 ns, then -2.847 ns (one edge 98, 62 ps): STOP's cable the shorter, by
  about 0.56 m of RG-58, give or take the 5370B's skew. `FR 1 MHZ` raised 3325B error 700
  (units are two letters); `FR 1000000 HZ` clean.
- `examples/three_instruments.py` on 0.4.6: once the 5370B's first, discarded reading did
  not come within 0.5 s (by hand right after, each came in 0.2 s); the script now waits 2 s
  and lets it go. Rerun: 5316B +1.27 ppm, 5370B -0.03 ppm from 1 MHz up; mismatches none.
- The examples switch a parked board on the bus; all three parked again at the end (14:05).

## 2026-11-19 13:50-14:15  the fun-numbers demo; the Advanced Lab scripts (by hand)

- `examples/fun_numbers.py` through A2 (3325B), A1 (5316B) and L1 (5370B), filmed by
  Jason with a colleague. The 5316B's terminal readings were a blend every other number
  until it was reset (`RE`) only after the 3325B had answered `IFR`. Stopped at 14:1x on
  Jason's word: 3325B at 1 mVpp, all three local, boards parked, claims HP3325B, HP5316B and
  HP5370B released.
- `examples/keithley_2000.py`, `srs_sr830.py` and `par_5210.py` were written from their
  manuals by three agents. They were checked against fakes of each instrument and against
  `sim_board`, but no hardware. They are for the Advanced Lab, through
  `bringup/handoff/advanced_lab_brief.md` (kept out of git).

## 2026-11-19 14:15-14:35  A1 on the Agilent 33220A, its output on the SDS2104X (by hand)

- A1 in the 33220A's GPIB socket (Jason): the board covers the generator's USB and
  Ethernet sockets (`REVB.md` 1.9). Its OUTPUT by BNC to the SDS2104X's channel 2. Claimed
  33220A (0.2 Vpp into 50 ohm) and SDS2104X:2; released after.
- `*IDN?` at GPIB 10: Agilent Technologies,33220A,MY44054664,2.07-2.06-22-2 (the unit
  lab-instrument-control drives over LAN and USB). Output off, 1 kHz sine 0.1 Vpp, 50 ohm.
- `examples/agilent_33220a.py`: mismatches none; 1000 points (2000 bytes) in 0.02 s; 200
  queries in 0.14 s; put back as found, output off throughout.
- Signal test (scratch `sig_33220a.py`), with the scope's settings saved and put back:
  - 200 alternating `FREQ?`/`VOLT?`: 758 a second, every answer right.
  - Output on, 1 kHz 0.2 Vpp: 999.8-1000.2 Hz, 0.403 Vpp at 1 Mohm.
  - 12.345 kHz 0.1 Vpp: 0.2025 Vpp. The scope's own FREQ read 12,360.8, then 12,331.4
    (it scatters 0.1 %), so the frequency was counted from the record instead.
    - My first count doubled: noise at each falling edge crossed zero upwards too.
    - With 20 mV hysteresis: 12,345.87 Hz (+70 ppm, the scope's clock).
  - The 1000-point waveform: shape correlated 0.99998 with the points sent.
  - Output off: 6 mV. Error queue empty. Mismatches none (the fourth run; the first
    three were the scope readout's scatter and my crossing count).
- A1 parked; the 33220A back to sine 1 kHz 0.1 Vpp, output off, local.
