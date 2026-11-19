#!/usr/bin/env python3
"""Fun numbers on frequency counters, for a video: an HP 3325B steps through frequencies
such as 12,345,678.9 Hz, pi MHz and the caesium second, and an HP 5316B and an HP 5370B
count each live on their displays, while the terminal prints what all three say. Each
instrument on its own GPiBridge (or all on one bus). Ctrl-C stops it.

    python3 fun_numbers.py --gen-port E9D119818C2ADDD2 --c16-port 9F9D542A93F67D76 --c70-port 5F4293C74E3358D8
    python3 fun_numbers.py --port COM5 --dwell 3 --once

**Cabling** as for three_instruments.py: the 3325B's MAIN SIGNAL, through a BNC tee, to the
5316B's INPUT A and the 5370B's STOP. **It puts 0.5 Vpp on the 3325B's output** (a sine,
0 V offset), and at the end leaves it at 1 mVpp and all three on their front panels.

**Set the 5316B's front GATE TIME knob** (not at HOLD) for its display: about 1 s gives
8 digits and a new reading each second; it gates on the front knob's long range here (GA0,
60 ms to 10 s). The 5370B gates for 0.1 s (GT3) and updates about ten times a second.

Each instrument keeps its own time, so each counter shows the number as its own timebase
sees it: on the bench of 2026-11-19 the 5370B agreed with the 3325B to 0.03 ppm (eight
digits or so of the fun number), the 5316B read 1.27 ppm high (its last two digits off).
"""
import argparse
import re
import sys
import time

from gpib_port import GpibPort, find_port

# (Hz, what it is). The 3325B: 0.001 Hz to 20.999999999 MHz for a sine; steps of 1 uHz
# below 100 kHz and 1 mHz above, so three decimals are what it shows.
NUMBERS = [
    (10000000.000, '10 MHz: the round one'),
    (12345678.900, '1 2 3 4 5 6 7 8 9'),
    (3141592.654, 'pi MHz'),
    (2718281.828, 'e MHz'),
    (1618033.989, 'the golden ratio, MHz'),
    (9192631.770, 'the caesium second: 9 192 631 770 Hz, over 1000'),
    (1420405.752, 'the hydrogen line, 1420.405752 MHz, over 1000'),
    (2997924.580, 'the speed of light, 299 792 458 m/s, over 100'),
    (6022140.760, "Avogadro's number, 6.02214076E23, over 1E17"),
    (16777216.000, '2 to the 24th'),
    (8675309.000, '867-5309'),
    (11111111.111, 'all ones'),
    (19999999.999, 'all nines, near the top of its range'),
    (123456.789, '123456.789 Hz'),
    (1000000.000, '1 MHz'),
]
NUMBER = re.compile(r'[-+]?\s*\d*\.?\d+(?:\s*[eE]\s*[-+]?\s*\d+)?')


def number(text):
    m = NUMBER.search(text)
    return float(re.sub(r'\s', '', m.group())) if m else None


def port_name(p):
    return find_port(p) if p and re.fullmatch(r'[0-9A-Fa-f]{16}', p) else p


def reading(bus, a, prefix):
    """The counter's next reading, to its line feed (neither sends EOI), or None."""
    try:
        r = bus.read(a, end='\n')
    except IOError:
        return None
    return number(r[len(prefix):] if r.startswith(prefix) else r) if r else None


def main():
    ap = argparse.ArgumentParser(description=__doc__.split('\n\n')[0])
    ap.add_argument('--port', help='one GPiBridge for all three')
    ap.add_argument('--gen-port', help="the 3325B's GPiBridge: a port or a serial number")
    ap.add_argument('--c16-port', help="the 5316B's")
    ap.add_argument('--c70-port', help="the 5370B's")
    ap.add_argument('--gen', type=int, default=17, help='3325B address (17)')
    ap.add_argument('--c16', type=int, default=20, help='5316B address (20)')
    ap.add_argument('--c70', type=int, default=3, help='5370B address (3)')
    ap.add_argument('--dwell', type=float, default=2.0, help='seconds on each number (2)')
    ap.add_argument('--once', action='store_true', help='through the list once, not round and round')
    o = ap.parse_args()

    names = {k: port_name(getattr(o, k + '_port') or o.port) for k in ('gen', 'c16', 'c70')}
    opened = {}
    for p in names.values():
        if p not in opened:
            opened[p] = GpibPort(p)
    gen, c16, c70 = (opened[names[k]] for k in ('gen', 'c16', 'c70'))
    G, A, B = o.gen, o.c16, o.c70
    try:
        for c in ('FU 1', 'OF 0 VO', 'AM 0.5 VO'):           # sine, 0 V, 0.5 Vpp
            gen.write(G, c)
        # 5316B: FREQ A, trigger at 0 V by its DAC, the front knob's long gate, gating
        # continuously (WA0), no service requests: its display runs by itself
        c16.clear(A)
        time.sleep(0.3)
        for c in ('IN', 'FN1TR1', 'AT0', 'GA0WA0SR0'):
            c16.write(A, c)
        c16.cmd('++read_tmo_ms 3000')                        # its next reading: up to a gate away
        # 5370B: frequency on STOP, 0.1 s gate (last: it and SS are alternatives), the
        # display at its fastest (MD3), trigger levels and slopes by HP-IB
        c70.clear(B)
        time.sleep(0.5)
        for c in ('ST1ST6', 'FN3', 'MD3', 'IN2', 'SR', 'SA1', 'SO1', 'TR', 'TA0.00', 'TO0.00', 'ST1', 'GT3'):
            c70.write(B, c)
            time.sleep(0.02)
        c70.cmd('++read_tmo_ms 1000')

        print('%-48s %18s %16s %16s' % ('', '3325B (set)', '5316B', '5370B'))
        while True:
            for f, what in NUMBERS:
                t0 = time.time()
                gen.write(G, 'FR %.3f HZ' % f)
                gen.query(G, 'IFR')                           # answered once it has taken it;
                time.sleep(0.1)                               # then it settles. Then a new
                c16.write(A, 'RE')                            # 5316B measurement: no gate
                time.sleep(max(0.0, o.dwell - 1.2))           # straddles the change (p. 3-34)
                v16 = reading(c16, A, 'F')
                v70 = reading(c70, B, 'FRQ=')
                print('%-48s %18s %16s %16s' % (what, '{:,.3f}'.format(f),
                      '{:,.0f}'.format(v16) if v16 else '-', '{:,.2f}'.format(v70) if v70 else '-'))
                time.sleep(max(0.0, t0 + o.dwell - time.time()))
            if o.once:
                break
    except KeyboardInterrupt:
        print()
    finally:
        gen.write(G, 'AM 0.001 VO')                          # 1 mVpp: as near to off as it goes
        gen.local(G)
        c16.write(A, 'WA0SR0')
        c16.write(A, 'IN')
        c16.local(A)
        c70.write(B, 'FN1GT1ST1SS1MD1IN1SA1SO1AR1')          # its start-up codes (Table 3-4)
        c70.write(B, 'TLSL')
        c70.local(B)
        for bus in opened.values():
            bus.close()
        print('left: the 3325B at 1 mVpp; all three on their front panels')
    return 0


if __name__ == '__main__':
    sys.exit(main())
