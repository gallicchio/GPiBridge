#!/usr/bin/env python3
"""An HP (Agilent) 33120A function generator through a GPiBridge: a sine, then an
arbitrary waveform uploaded as a binary block, each read back, and the error queue.

    python3 hp_33120a.py                         # GPIB address 10 (the 33120A's default)
    python3 hp_33120a.py --address 7 --port COM5

**Its OUTPUT carries a signal from the first setting to the end**: a 1 kHz sine of
0.1 Vpp, then a 100-point waveform (a sine with some of its third harmonic) at 1 kHz and
0.1 Vpp. The 33120A has no output switch: it is left at 0 V DC. Into a scope, set the
channel to 50 ohm (or expect twice the amplitude at 1 Mohm).

The generator's interface must be HP-IB (Utility menu, I/O MENU: "HP-IB / 488"), at the
address given.
"""
import argparse
import math
import struct
import sys

from gpib_port import GpibPort


def errors(bus, a):
    """Everything in the error queue, oldest first; empty when there is none."""
    found = []
    while True:
        e = bus.query(a, 'SYSTem:ERRor?')
        if e.startswith(('+0', '0')):
            return found
        found.append(e)
        if len(found) > 20:
            return found


def main():
    ap = argparse.ArgumentParser(description=__doc__.split('\n\n')[0])
    ap.add_argument('--address', type=int, default=10, help='GPIB address (10)')
    ap.add_argument('--port', help='the serial port (found by itself if one GPiBridge is plugged in)')
    o = ap.parse_args()
    a = o.address

    with GpibPort(o.port) as bus:
        print('adapter:', bus.version)
        idn = bus.query(a, '*IDN?')
        print('instrument:', idn)
        if '33120A' not in idn:
            sys.exit('not a 33120A at GPIB %d: nothing sent to it' % a)
        bus.write(a, '*CLS')                                        # an empty error queue

        bus.write(a, 'APPLy:SINusoid 1E3,0.1,0')                    # 1 kHz, 0.1 Vpp, 0 V offset
        print('sine:', bus.query(a, 'APPLy?'))

        # 100 points from -2047 to +2047 (12 bits), one cycle. A binary block: '#', the number
        # of digits of the byte count, the count, then the bytes; FORMat:BORDer SWAPped says
        # each 16-bit point comes least significant byte first, as struct's '<h' packs it.
        n = 100
        points = [round(2047 * (0.8 * math.sin(2 * math.pi * k / n) + 0.2 * math.sin(6 * math.pi * k / n)))
                  for k in range(n)]
        data = struct.pack('<%dh' % n, *points)
        count = str(len(data)).encode()
        bus.write(a, 'FORMat:BORDer SWAPped')
        bus.write(a, b'DATA:DAC VOLATILE, #' + str(len(count)).encode() + count + data)
        bus.write(a, 'FUNCtion:USER VOLATILE')
        bus.write(a, 'APPLy:USER 1E3,0.1,0')
        # (the attribute queries are of the waveform selected: VOLATILE, just above)
        print('waveform:', bus.query(a, 'APPLy?'), '| points', bus.query(a, 'DATA:ATTRibute:POINts?'),
              '| average', bus.query(a, 'DATA:ATTRibute:AVERage?'), '(%.4f sent)' % (sum(points) / n / 2047))

        print('*OPC?', bus.query(a, '*OPC?'), '| serial poll', bus.serial_poll(a))
        bad = errors(bus, a)
        bus.write(a, 'APPLy:DC DEF,DEF,0')                          # 0 V: the nearest thing to off
        bus.local(a)
        print('errors:', bad or 'none')
        return 1 if bad else 0


if __name__ == '__main__':
    sys.exit(main())
