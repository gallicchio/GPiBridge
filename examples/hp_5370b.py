#!/usr/bin/env python3
"""An HP 5370B Universal Time Interval Counter through a GPiBridge: its trigger levels
set by HP-IB and read back, a time interval measurement selected, and its status byte.

    python3 hp_5370b.py                          # GPIB address 3 (the manual's)
    python3 hp_5370b.py --address 5 --port COM5

**It needs nothing on START, STOP, EXT ARM or the rear panel.** The 5370B has no
self-check mode; what it measures without a signal is its own trigger levels (TRIG LVL,
FN2), set by a DAC in 10 mV steps (pp. 3-6, 3-24, 8-35). Two pairs are set and read back.
Then an ordinary time interval (FN1) is selected: with no START signal no reading can
come, so none is asked for. A serial poll shows the codes were taken, and an undefined
code (FN9) shows that the poll would have said so if they had not.

The address is the rear-panel ADDRESS switch A5SW1 (pp. 3-19, 3-20, 4-5): A5..A1 in
binary, 1 = up; the manual's examples and its HP-IB verification use 3 (00011). The
leftmost switch must be down, ADDRESSABLE, not TALK ONLY. The 5370B has no identification
query: the answer to FN2 shows a 5370B is there. At the end, also after a failure, the
knobs set display rate, trigger levels and slopes again, and the counter goes to local.
"""
import argparse
import re
import sys
import time

from gpib_port import GpibPort

# Bits 1-4 of the status byte when bit 7 (service request) is set: Table 3-2 (p. 3-18), p. 3-4
ERRORS = {0: 'measurement complete, ready to output', 1: 'illegal remote command',
          2: 'overrange', 3: 'undefined routine', 4: 'phase-locked loop out of lock',
          5: 'undefined key (hardware)', 6: 'fault in RAM', 7: 'fault in ROM'}
# FN2's answer (p. 3-24): "STA = SD.DD, STO = SD.DD <CR LF>", S the polarity
LEVELS = re.compile(r'STA\s*=\s*([-+ ]*\d*\.?\d+)\s*,?\s*STO\s*=\s*([-+ ]*\d*\.?\d+)')
TOLERANCE = 0.02            # V: two of the DAC's 10 mV steps (p. 8-36)


def describe(sb):
    """The status byte in words (Table 3-2, p. 3-18, numbers its bits 1 to 8)."""
    rqs = 'service requested: error %d, %s' % (sb & 15, ERRORS.get(sb & 15, '?'))  # bits 7, 1-4
    # Bits 6 and 5: oven heater on, external timebase. With a service request this one left
    # both clear (2026-11-19: 32 alone, then 65 with error 1), so they are read only without.
    rest = ('oven heater %s; %s timebase' % ('on' if sb & 0x20 else 'off', 'external' if sb & 0x10 else 'internal')
            if not sb & 0x40 else 'oven and timebase bits not given with a service request')
    return '%d (0x%02X): %s%s; %s' % (sb, sb, 'debug monitor running; ' if sb & 0x80 else '',   # bit 8
                                      rqs if sb & 0x40 else 'no service requested', rest)


def error(bus, a):
    """A serial poll: the error the counter flags, or None (error 0 is a finished measurement)."""
    sb = bus.serial_poll(a)
    return sb & 15 if sb & 0x40 and sb & 15 else None


def said(e):
    return 'error %d, %s' % (e, ERRORS.get(e, '?')) if e else 'no error flagged'


def trigger_levels(bus, a):
    """One FN2 measurement: ([START, STOP] in volts, or None if not as on p. 3-24; the line)."""
    time.sleep(0.02)                          # MR 10 ms or more after a code (p. 3-24)
    bus.write(a, 'MR')                        # take one measurement (p. 3-24)
    try:
        # to the line feed: its answers end in CR LF without EOI (seen on the bus, 2026-11-19)
        line = bus.read(a, end='\n')
    except IOError as x:
        return None, '(%s)' % x
    m = LEVELS.search(line)
    return (m and [float(v.replace(' ', '')) for v in m.groups()]), line


def main():
    ap = argparse.ArgumentParser(description=__doc__.split('\n\n')[0])
    ap.add_argument('--address', type=int, default=3, help='GPIB address (3)')
    ap.add_argument('--port', help='the serial port (found by itself if one GPiBridge is plugged in)')
    o = ap.parse_args()
    a = o.address
    bad = []

    with GpibPort(o.port) as bus:
        print('adapter:', bus.version)
        try:
            print('0. status byte', describe(bus.serial_poll(a)))
        except (IOError, ValueError):
            sys.exit('nothing answers a serial poll at GPIB %d: nothing sent to it' % a)
        try:
            # 1. Device Clear, as the RESET key (p. 3-18), then the start-up codes (bold in
            # Table 3-4). ST1 first: ST9 must be left before anything else changes (p. 3-31).
            bus.clear(a)
            time.sleep(0.5)
            bus.write(a, 'ST1ST6')            # mean; reference to zero (p. 3-22)
            bus.write(a, 'FN1GT1SS1MD1IN1')   # T.I., 1 period, 1 sample, rate knob, inputs (3-22)
            bus.write(a, 'SA1SO1SE1AR1')      # + slopes, + ext arm slope, +T.I. only (p. 3-23)
            bus.write(a, 'EH0EA0TB0SLTL')     # no ext holdoff/arm, ASCII, knob slopes+levels (3-24)
            e = error(bus, a)
            print('1. initialised:', said(e))
            bad += ['initialising: error %d' % e] if e else []

            # 2. Trigger levels (FN2), set by HP-IB (TR) with TA and TO (p. 3-24; Example 7,
            # p. 3-31). MD2: one measurement per MR, held until read (p. 3-22; Example 1,
            # p. 3-25): a free-running counter left talking could send reading after reading,
            # and a read waiting for EOI might never end. After a change of function the first
            # output may be the old measurement (MD2, p. 3-22): a second try.
            bus.write(a, 'FN2MD2TR')          # trigger levels, hold until MR, levels by HP-IB
            for sta, sto in ((0.50, -1.25), (-1.60, 0.80)):
                bus.write(a, 'TA%.2f' % sta)  # START level, -2 to +2 V (p. 3-24)
                bus.write(a, 'TO%.2f' % sto)  # STOP level (p. 3-24)
                e = error(bus, a)             # (the poll also waits until both are sent)
                for attempt in (1, 2):
                    got, line = trigger_levels(bus, a)
                    ok = bool(got) and max(abs(got[0] - sta), abs(got[1] - sto)) <= TOLERANCE
                    last = attempt == 2 or line.startswith('(')
                    print('2. levels set START %+.2f V, STOP %+.2f V: read %r, %s' % (
                        sta, sto, line, 'ok' if ok else 'MISMATCH' if last else 'old? again'))
                    if ok or last:
                        break
                if e or not ok:
                    bad.append('levels %+.2f/%+.2f: %s, read %r' % (sta, sto, said(e), line))
                if line.startswith('('):
                    break                     # no answer: the next pair would wait as long

            # 3. An ordinary time interval: FN1, mean of a sample of 1, START and STOP inputs,
            # slopes set by HP-IB (SR) positive, +T.I. arming, the display rate knob (pp. 3-22
            # to 3-24). Nothing reaches START, so no reading comes, and none is asked for.
            bus.serial_poll(a)                # (a request left from step 2 is cleared)
            bus.write(a, 'FN1ST1SS1MD1IN1SRSA1SO1AR1')
            time.sleep(0.2)
            e = error(bus, a)
            bus.write(a, 'FN9')               # undefined: must be error 1 (pp. 3-4, 3-18)
            time.sleep(0.2)
            e9 = error(bus, a)
            print('3. time interval selected:', said(e), '| the undefined FN9:', said(e9))
            bad += ['time interval codes: error %d' % e] if e else []
            bad += ['FN9 gave error %s, not 1: a clean poll proves nothing' % e9] if e9 != 1 else []

            # 4. The status byte (Table 3-2, p. 3-18). Error 1 may still stand from FN9.
            sb = bus.serial_poll(a)
            print('4. status byte', describe(sb))
            if sb & 0x80 or (sb & 0x40 and (sb & 15) > 1):
                bad.append('status byte %d' % sb)
        finally:
            bus.write(a, 'MD1TLSL')           # display rate, trigger levels, slopes: the knobs
            bus.local(a)                      # Go To Local (p. 3-18)
        print('mismatches:', bad or 'none')
        return 1 if bad else 0


if __name__ == '__main__':
    sys.exit(main())
