#!/usr/bin/env python3
"""An Agilent (HP, Keysight) E3646A dual-output power supply through a GPiBridge: set
one output's voltage and current limit, switch on, read what it measures, switch off,
and put back the settings it was found with. The E3647A-E3649A take the same commands.

    python3 agilent_e3646a.py --address 2 --output 2 --volts 0.5 --amps 0.4
    python3 agilent_e3646a.py --address 5 --port /dev/ttyACM1 --seconds 10

**This switches the supply's outputs on**, for --seconds (3), then off. The E364xA has
one switch for both outputs, so the other one is set to 0 V first. Know what is
connected to both before running it. The defaults, 0.5 V with a 0.4 A limit, are
gentle on a resistor of an ohm or more; the supply holds whichever limit it meets first.
It refuses a supply found with its outputs on.

The supply's interface must be GPIB (I/O Config: "HPIB / 488"), at the address given
(5 from the factory). Each setting is sent with ";*OPC?" and its "1" read back: a query
sent right after APPLy can lose its answer otherwise.

Run on 2026-11-19 through GPiBridge Lite L1 (firmware 0.4.5), on an E3646A (firmware
1.7-5.0-1.0) at GPIB 2, output 2 into a 1.5 ohm resistor: 0.494 V, 0.322 A measured, the
settings put back, no error.
"""
import argparse
import sys
import time

from gpib_port import GpibPort


def main():
    ap = argparse.ArgumentParser(description=__doc__.split('\n\n')[0])
    ap.add_argument('--address', type=int, default=5, help='GPIB address (5, the factory setting)')
    ap.add_argument('--port', help='the serial port (found by itself if one GPiBridge is plugged in)')
    ap.add_argument('--output', type=int, choices=(1, 2), default=1)
    ap.add_argument('--volts', type=float, default=0.5)
    ap.add_argument('--amps', type=float, default=0.4, help='the current limit')
    ap.add_argument('--seconds', type=float, default=3.0, help='how long the output stays on')
    o = ap.parse_args()
    a, out, other = o.address, o.output, 3 - o.output

    with GpibPort(o.port) as bus:
        def setting(command):                     # a setting, and its completion read back
            if bus.query(a, command + ';*OPC?') != '1':
                raise IOError('%s: not completed' % command)

        def applied(n):                           # (volts, amps limit) of output n
            setting('INSTrument:NSELect %d' % n)
            return tuple(float(x) for x in bus.query(a, 'APPLy?').strip('"').split(','))

        print('adapter:', bus.version)
        idn = bus.query(a, '*IDN?')
        print('instrument:', idn)
        if 'E364' not in idn:
            sys.exit('not an E364xA at GPIB %d: nothing sent to it' % a)
        if bus.query(a, 'OUTPut?') == '1':
            sys.exit('its outputs are on: left alone')
        setting('*CLS')
        found = {n: applied(n) for n in (1, 2)}
        print('found:', {n: '%g V, %g A' % found[n] for n in found})

        try:
            applied(other)
            setting('APPLy 0,%g' % min(0.1, found[other][1]))   # the other output: 0 V
            applied(out)
            setting('APPLy %g,%g' % (o.volts, o.amps))
            print('output %d set to %g V, %g A limit:' % (out, o.volts, o.amps), bus.query(a, 'APPLy?'))
            setting('OUTPut ON')
            t_end = time.time() + o.seconds
            while time.time() < t_end:
                time.sleep(1.0)
                v = float(bus.query(a, 'MEASure:VOLTage?'))
                i = float(bus.query(a, 'MEASure:CURRent?'))
                print('  measured: %.4f V, %.4f A' % (v, i))
        finally:
            setting('OUTPut OFF')
            for n in (1, 2):
                applied(n)
                setting('APPLy %g,%g' % found[n])
            bad = bus.query(a, 'SYSTem:ERRor?')
            bus.local(a)
        print('output off; settings as found; error queue:', bad)
        return 0 if bad.startswith(('+0', '0')) else 1


if __name__ == '__main__':
    sys.exit(main())
