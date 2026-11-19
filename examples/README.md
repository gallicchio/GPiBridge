# Examples: instruments through a GPiBridge, in plain Python

Python 3 and pyserial (`pip install pyserial`), on Linux, macOS or Windows. Nothing
else: no VISA, no driver to install.

| file | what it does |
|---|---|
| [`gpib_port.py`](gpib_port.py) | The whole layer: find the GPiBridge's port, then `write`, `read`, `query`, `serial_poll`, `clear` and `local` to an instrument by its GPIB address. Each is one or two of the Prologix "++" commands, so it also works with a Prologix (name its port). |
| [`hp_33120a.py`](hp_33120a.py) | HP 33120A function generator: a sine, an arbitrary waveform uploaded as a binary block, each read back, and its error queue. **It puts 0.1 Vpp on the generator's output.** |
| [`agilent_e3646a.py`](agilent_e3646a.py) | Agilent E3646A power supply: one output's voltage and current limit, the output on for a few seconds while it reads what it measures, then off, and its settings put back. **It switches the supply's outputs on.** |
| [`hp_3325b.py`](hp_3325b.py) | HP 3325B (or 3325A) synthesizer, from before SCPI: `ID?`, a 1 kHz sine set and read back with its interrogate codes, its error code and status byte. **It puts 0.1 Vpp on its output, then leaves 1 mVpp** (it has no output switch). Address 17 from the factory, set on the front panel. |
| [`hp_5316b.py`](hp_5316b.py) | HP 5316B counter: its CHECK function (it counts its own 10 MHz reference) read and checked, FREQ A selected, the status byte. Nothing on its inputs. Address 20 from the factory, on rear switches (the two leftmost down, ADDRESSABLE, not TALK ONLY); the rear REF switch at INT. |
| [`hp_5370b.py`](hp_5370b.py) | HP 5370B time interval counter: no self-check mode, so its trigger levels are set and read back (FN2); time interval selected; the status byte. Nothing on its inputs. Address on rear switches (ADDRESSABLE, not TALK ONLY); 3 in the manual's examples. |
| [`three_instruments.py`](three_instruments.py) | One signal, two counters: the 3325B steps a sine from 1 kHz to 20 MHz, and the 5316B and the 5370B count it, each instrument on its own GPiBridge (or all on one bus). Cabling: the 3325B's MAIN SIGNAL, through a BNC tee, to the 5316B's INPUT A and the 5370B's STOP. **It puts 0.5 Vpp on the 3325B's output**, then leaves 1 mVpp. |
| [`cable_delay.py`](cable_delay.py) | Time a BNC cable: the 3325B's square wave reaches the 5370B's START by one cable and its STOP by another, and the 5370B averages 1000 START-to-STOP intervals (to a few picoseconds). Swap the cables and give `--swapped` the first reading: the counter's own skew cancels. **It puts 0.5 Vpp on the 3325B's output**, then leaves 1 mVpp. |
| [`agilent_33220a.py`](agilent_33220a.py) | Agilent 33220A function generator, its **output kept off** throughout (it refuses to start if the output is on): a sine set and read back setting by setting (APPLy would switch the output on), a 1000-point 14-bit waveform uploaded as a binary block and read back, the error queue, queries a second; its waveform put back. |
| [`fun_numbers.py`](fun_numbers.py) | For a video: the 3325B steps through fun frequencies (12,345,678.9 Hz, pi MHz, the caesium second, 867-5309...) every 2 s, and the 5316B and the 5370B count each live on their displays while the terminal prints all three. Cabling as for `three_instruments.py`. **0.5 Vpp on the 3325B's output** until Ctrl-C, then 1 mVpp. |
| [`keithley_2000.py`](keithley_2000.py) | Keithley 2000 multimeter: DC volts only, a few readings and 50 timed ones, `*TST?`, the error queue; every setting it changes put back and compared. Sources nothing; refuses if the meter is on a current function, scanning or storing. Address 16 from the factory. |
| [`srs_sr830.py`](srs_sr830.py) | SRS SR830 lock-in: its whole setup read and explained, the outputs (`SNAP?`) and status bytes, the time constant one step and back, 50 timed `SNAP?`. Never touches the reference, sine output, sensitivity or inputs (`--read-only`: touches nothing). Address 8 from the factory. |
| [`par_5210.py`](par_5210.py) | EG&G PAR 5210 analog lock-in: `ID`, its whole setup read and decoded, X, Y, magnitude and phase in % and volts, the status and overload bytes, a display setting and the time constant one step and back, 50 timed `X`. Never writes the oscillator, sensitivity, input or offsets. Ends its answers in CR (or CR LF) with EOI: it reads to EOI. **The manual gives no factory address**: read it on the panel (CONFIG, DYN RES/GPIB). |

The three older HP instruments' scripts were written from their scanned manuals (every code
has its page number beside it) on 2026-11-19. Run that day:
- `hp_3325b.py` through GPiBridge A2 on a 3325B (address 17): everything read back as
  set, no error. Its answers end in CR LF, with EOI on the LF (seen on the bus).
- `hp_5370b.py` through GPiBridge Lite L1 on its 5370B (address 3): both pairs of
  trigger levels read back exactly. **The 5370B sends no EOI**: its answers end in CR LF
  alone (seen on the bus), so the script reads to the line feed (`read(..., end='\n')`,
  which is `++read 10`); waiting for EOI, each read ended only on the adapter's 500 ms
  timeout. With a service request standing, its status byte leaves the oven and timebase
  bits clear.
- `hp_5316b.py` through GPiBridge A1 on a 5316B (address 20), once its rear switches had
  left TALK ONLY (in which it answered a serial poll at every address): CHECK read
  10,000,000 Hz, every code taken. **The 5316B sends no EOI either**, and while it is
  addressed to talk it sends reading after reading. Read to the line feed: a
  `++read eoi` never ends, and GPiBridge firmware 0.4.5 took no other command until it
  did (only a reboot ended one). From 0.4.6 anything the host sends ends it: `++ver`
  answered 60 ms after it was sent, in the middle of such a read.

The 3325B and the 5370B also went through 120 bus cycles each (off and on, restart, IFC,
go to local), the instrument answering after every one.

- `three_instruments.py`, the same day, through A2 (3325B), A1 (5316B) and L1 (5370B),
  at 1 kHz, 10 kHz, 100 kHz, 1 MHz, 10 MHz, 20 MHz and 12,345,678.9 Hz: the 3325B read
  back each exactly; the 5316B read +1.23 to +1.24 ppm high at every one (its timebase
  against the 3325B's); the 5370B -0.03 ppm from 1 MHz up, and within 3 ppm below (a
  0.1 s gate on slow sine edges). The 5316B takes 12-13 s a reading, which is where that
  unit's rear GATE TIME control was set.
  Two 5370B lessons on the way: it counts frequency on its STOP input (`IN2`); counted on
  START (`IN3`) each period carried about 0.7 ns of delay, -0.7 % at 10 MHz. And a gate
  time (`GT`) and a sample size (`SS`) are alternatives, the last one sent winning:
  `GT3` then `SS1` measured single periods.
- `cable_delay.py`, the same day, through A2 and L1 on firmware 0.4.6, with Jason's two
  cables of about 0.5 m and 1 m: START to STOP -2.864 ns, then -2.847 ns (98 and 62 ps
  for one edge; the mean of 1000 to about 3 ps): STOP's cable the shorter, by about
  0.56 m of RG-58, give or take the 5370B's own skew. The 3325B's units are two letters
  (HZ, KH, MH): `FR 1 MHZ` set 1 MHz, then the stray `Z` raised error 700.
- `three_instruments.py` again on 0.4.6: the same within 0.04 ppm, mismatches none.
- `agilent_33220a.py` through A1 on a 33220A (address 10, firmware 2.07-2.06-22-2), the same
  day: mismatches none; the 1000-point waveform (2000 bytes) in 0.02 s; 758 queries a
  second, answers checked by alternating two. With its output on a scope (a separate
  test): 1 kHz at 0.2 Vpp read 999.8 Hz and 0.403 Vpp at 1 Mohm, 12.345 kHz counted
  from the scope's record as 12,345.87 Hz, the uploaded waveform's shape correlated
  0.99998 with the points sent, and the output off read 6 mV. The board covers the
  33220A's USB and Ethernet sockets.
- `fun_numbers.py`, the same day: each number on all three displays; the terminal showed
  the 5316B +1.3 ppm (12,345,694 for 12,345,678.9) and the 5370B to about eight digits
  (12,345,678.52). Resetting the 5316B (`RE`) once the 3325B has answered its new
  frequency keeps its gate from straddling the change; without that wait, every other
  reading was a blend of two numbers.
- `keithley_2000.py`, `srs_sr830.py`, `par_5210.py`: written from their manuals on
  2026-11-19 and checked against fakes of the instruments; not yet run on one.

```sh
cd examples
python3 hp_33120a.py --address 10
python3 agilent_e3646a.py --address 2 --output 2 --volts 0.5 --amps 0.4
```

The port is found by itself when one GPiBridge is plugged in; `--port` names it:
`/dev/ttyACM0` on Linux, `/dev/cu.usbmodem<serial>1` on macOS, `COM5` on Windows. On
Linux, install the udev rule first (`../tools/60-gpibridge.rules`; the file says how),
and be in the `dialout` group.

The instrument's interface must be set to GPIB (HP-IB) on its front panel, at the address
you give. A GPiBridge set to stay off the bus (`++t autostart 0`, as bring-up leaves
boards) is switched on by `gpib_port.py`, which says so.

`agilent_e3646a.py` has run on a real E3646A, through GPiBridge Lite L1 (2026-11-19).
`hp_33120a.py` has not met a real 33120A yet. Both run against the firmware's simulated bus and 33120A
(`firmware/test/sim_board --instrument`, then `--port` its pseudo-terminal), where the
E3646A one finds a 33120A and refuses. The protocol is the Prologix's: its manual has
every "++" command, and `../HANDBOOK.md` §2 lists them with GPiBridge's own (`++t ...`).

**For more than this**, such as drivers for whole instruments, queries that recover after a
timeout, and LAN and USB instruments beside GPIB ones, use
[lab-instrument-control](https://github.com/QuantumQuasars/lab-instrument-control). It
treats a GPiBridge as one of several USB-GPIB adapters, and needs nothing from this
repository.
