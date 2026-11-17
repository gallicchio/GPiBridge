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
