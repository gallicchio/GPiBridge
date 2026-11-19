#!/usr/bin/env python3
"""An Agilent (Keysight) 33220A function generator through a GPiBridge, with its OUTPUT off
throughout: a sine set and read back, a 1000-point arbitrary waveform uploaded as a binary
block and read back, the error queue, and how many queries a second the bus carries.

    python3 agilent_33220a.py                    # GPIB address 10 (the 33220A's default)
    python3 agilent_33220a.py --address 7 --port COM5

**Nothing comes out of it.** The 33220A has an output switch, and this leaves it off: each
setting is made on its own (FUNCtion, FREQuency, VOLTage), never by APPLy, which switches
the output on. If the output is on when it starts, something may be using the generator,
and it stops without changing anything. At the end its waveform settings are put back as
they were and it returns to its front panel.

The generator's GPIB address is set in its Utility menu (I/O). It also has USB and LAN,
usable alongside GPIB, but a GPiBridge rev A plugged into its GPIB socket covers both
(2026-11-19). Run on one through a GPiBridge that day: no mismatches.
"""
import argparse
import math
import struct
import sys
import time

from gpib_port import GpibPort


def errors(bus, a):
    """Everything in the error queue, oldest first; empty when there is none."""
    found = []
    while len(found) < 20:
        e = bus.query(a, 'SYSTem:ERRor?')
        if e.startswith(('+0', '0')):
            break
        found.append(e)
    return found


def close(x, y, rel=1e-6):
    return abs(x - y) <= rel * max(abs(x), abs(y), 1e-12)


def main():
    ap = argparse.ArgumentParser(description=__doc__.split('\n\n')[0])
    ap.add_argument('--address', type=int, default=10, help='GPIB address (10)')
    ap.add_argument('--port', help='the serial port (found by itself if one GPiBridge is plugged in)')
    o = ap.parse_args()
    a = o.address
    bad = []

    with GpibPort(o.port) as bus:
        print('adapter:', bus.version)
        idn = bus.query(a, '*IDN?')
        print('instrument:', idn)
        if '33220A' not in idn:
            sys.exit('not a 33220A at GPIB %d: nothing sent to it' % a)
        if bus.query(a, 'OUTPut?').strip() != '0':
            sys.exit('its OUTPUT is on: something may be using it. Nothing changed')
        was = bus.query(a, 'APPLy?')                   # e.g. "SIN +1.000000000000000E+03,+1.000E-01,+0.00E+00"
        load = bus.query(a, 'OUTPut:LOAD?')
        print('as found: %s, load %s, output off' % (was, load))
        bus.write(a, '*CLS')                           # an empty error queue
        try:
            # 1. A sine, setting by setting (APPLy would switch the output on)
            for c in ('FUNCtion SINusoid', 'FREQuency 1234.5', 'VOLTage 0.1', 'VOLTage:OFFSet 0'):
                bus.write(a, c)
            got = [bus.query(a, q) for q in ('FUNCtion?', 'FREQuency?', 'VOLTage?', 'VOLTage:OFFSet?', 'OUTPut?')]
            print('1. sine set: FUNC %s, FREQ %s, VOLT %s, OFFS %s, OUTP %s' % tuple(got))
            if got[0] != 'SIN' or not close(float(got[1]), 1234.5) or not close(float(got[2]), 0.1) \
                    or abs(float(got[3])) > 1e-6 or got[4] != '0':
                bad.append('sine read back as %s' % got)

            # 2. 1000 points, 14 bits (-8191 to +8191), a sine with some of its third harmonic,
            #    as a binary block: '#', the number of digits of the byte count, the count, the
            #    bytes; FORMat:BORDer SWAPped: least significant byte first, as '<h' packs it
            n = 1000
            pts = [round(8191 * (0.8 * math.sin(2 * math.pi * k / n) + 0.2 * math.sin(6 * math.pi * k / n)))
                   for k in range(n)]
            data = struct.pack('<%dh' % n, *pts)
            count = str(len(data)).encode()
            bus.write(a, 'FORMat:BORDer SWAPped')
            t0 = time.time()
            bus.write(a, b'DATA:DAC VOLATILE, #' + str(len(count)).encode() + count + data)
            points = bus.query(a, 'DATA:ATTRibute:POINts? VOLATILE')      # waits for the upload
            dt = time.time() - t0
            bus.write(a, 'FUNCtion:USER VOLATILE')
            bus.write(a, 'FUNCtion USER')
            avg = bus.query(a, 'DATA:ATTRibute:AVERage? VOLATILE')
            print('2. %d points (%d bytes) in %.2f s: it holds %s points, average %s (%.5f sent); FUNC %s, OUTP %s'
                  % (n, len(data), dt, points, avg, sum(pts) / n / 8191, bus.query(a, 'FUNCtion?'),
                     bus.query(a, 'OUTPut?')))
            if int(float(points)) != n or abs(float(avg) - sum(pts) / n / 8191) > 1e-3:
                bad.append('waveform: %s points, average %s' % (points, avg))

            # 3. The error queue
            e = errors(bus, a)
            print('3. errors:', e or 'none')
            bad += e

            # 4. Queries a second: 200 of FREQuency?
            t0 = time.time()
            for _ in range(200):
                bus.query(a, 'FREQuency?')
            dt = time.time() - t0
            print('4. 200 queries in %.2f s: %.0f a second' % (dt, 200 / dt))
        finally:
            # Its waveform as found (APPLy? gives function, frequency, amplitude, offset), set
            # setting by setting so the output stays off
            fn, rest = was.strip('"').split(' ', 1)
            f, v, off = (x if x not in ('', 'DEF') else None for x in rest.split(','))
            name = {'SIN': 'SINusoid', 'SQU': 'SQUare', 'RAMP': 'RAMP', 'PULS': 'PULSe', 'NOIS': 'NOISe',
                    'DC': 'DC', 'USER': 'USER'}.get(fn, 'SINusoid')
            bus.write(a, 'FUNCtion ' + name)
            for c, x in (('FREQuency', f), ('VOLTage', v), ('VOLTage:OFFSet', off)):
                if x is not None and not (fn == 'DC' and c != 'VOLTage:OFFSet'):
                    bus.write(a, '%s %s' % (c, x))
            print('put back:', bus.query(a, 'APPLy?'), '| output', bus.query(a, 'OUTPut?'))
            bus.local(a)
    print('mismatches:', '; '.join(bad) if bad else 'none')
    return 1 if bad else 0


if __name__ == '__main__':
    sys.exit(main())
