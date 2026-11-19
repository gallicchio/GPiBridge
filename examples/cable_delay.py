#!/usr/bin/env python3
"""Time a BNC cable with an HP 5370B: one square wave from an HP 3325B reaches the 5370B's
START by one cable and its STOP by another, and the 5370B measures the time between the
two edges, averaged over 1000 of them. Each instrument on its own GPiBridge, or both on one.

    python3 cable_delay.py --gen-port /dev/ttyACM1 --c70-port /dev/ttyACM0
    python3 cable_delay.py --port COM5                      # both on one GPIB cable
    python3 cable_delay.py ... --swapped 2.61               # the cables swapped: the skew cancels

**Cabling:** the 3325B's MAIN SIGNAL, through BNC tees, to the 5370B's START by one cable
and its STOP by another (anything else on the tees may stay). Coaxial cable carries a signal
at about two thirds of the speed of light: some 5 ns a metre for RG-58.

**It puts 0.5 Vpp on the 3325B's output** (a 1 MHz square wave, 0 V offset), then leaves it
at 1 mVpp and every instrument on its front panel.

What the 5370B reads is the difference between the two cables plus its own START-to-STOP
skew (a fraction of a nanosecond). Swap the two cables at the 5370B and measure again: the
skew is the same both times and the cables' difference changes sign, so half the
difference of the two readings is the cables' alone (`--swapped` takes the first reading).

The 5370B codes (its manual, Table 3-4, pp. 3-22 to 3-24): FN1 time interval, IN1 START and
STOP inputs, AR2 +/- time interval arming (so an interval of either sign is measured, not
one period less), slopes and trigger levels by HP-IB (SR, TR), ST1 mean or ST2 standard
deviation, SS3 a sample of 1000, MD2 one sample per MR. It sends no EOI: read to the line
feed.
"""
import argparse
import re
import sys
import time

from gpib_port import GpibPort, find_port

NUMBER = re.compile(r'[-+]?\s*\d*\.?\d+(?:\s*[eE]\s*[-+]?\s*\d+)?')


def port_name(p):
    return find_port(p) if p and re.fullmatch(r'[0-9A-Fa-f]{16}', p) else p


def sample(bus, a, stat):
    """One sample of 1000 time intervals: ST1 mean or ST2 standard deviation, in seconds."""
    bus.write(a, stat)
    time.sleep(0.02)                             # codes and MR 10 ms apart (p. 3-24)
    bus.write(a, 'MR')
    t0 = time.time()
    while True:
        try:
            r = bus.read(a, end='\n')            # 1000 intervals of a 1 MHz wave: well under 1 s
            break
        except IOError:
            if time.time() - t0 > 10:
                raise
    m = NUMBER.search(r.split('=', 1)[-1])
    return (float(re.sub(r'\s', '', m.group())) if m else None), r


def main():
    ap = argparse.ArgumentParser(description=__doc__.split('\n\n')[0])
    ap.add_argument('--port', help='one GPiBridge for both')
    ap.add_argument('--gen-port', help="the 3325B's GPiBridge: a port or a serial number")
    ap.add_argument('--c70-port', help="the 5370B's")
    ap.add_argument('--gen', type=int, default=17, help='3325B address (17)')
    ap.add_argument('--c70', type=int, default=3, help='5370B address (3)')
    ap.add_argument('--swapped', type=float, help='the reading, in ns, with the cables the other way round')
    o = ap.parse_args()

    names = {k: port_name(getattr(o, k + '_port') or o.port) for k in ('gen', 'c70')}
    opened = {}
    for p in names.values():
        if p not in opened:
            opened[p] = GpibPort(p)
            print('%s: %s' % (p or 'the GPiBridge', opened[p].version))
    gen, c70 = opened[names['gen']], opened[names['c70']]
    G, B = o.gen, o.c70
    c70.cmd('++read_tmo_ms 2000')
    ok = True
    try:
        # square, 0 V, 0.5 Vpp, 1 MHz. (Its units are two letters, HZ, KH, MH: "FR 1 MHZ" set
        # 1 MHz, then the stray Z gave error 700 and an extra answer, 2026-11-19.)
        for c in ('FU 2', 'OF 0 VO', 'AM 0.5 VO', 'FR 1000000 HZ'):
            gen.write(G, c)
        e = gen.query(G, 'ERR?').replace(' ', '')
        print('3325B: %s, %s, %s; %s' % (gen.query(G, 'IFU'), gen.query(G, 'IFR'), gen.query(G, 'IAM'), e))
        c70.clear(B)
        time.sleep(0.5)
        for c in ('ST1ST6', 'FN1', 'MD2', 'IN1', 'SR', 'SA1', 'SO1', 'AR2', 'TR', 'TA0.00', 'TO0.00', 'SS3'):
            c70.write(B, c)
            time.sleep(0.02)
        sample(c70, B, 'ST1')                    # the first after a change may be old (MD2, p. 3-22)
        mean, r1 = sample(c70, B, 'ST1')
        sd, r2 = sample(c70, B, 'ST2')
        sb = c70.serial_poll(B)
        print('5370B, 1000 intervals START to STOP: mean %r, standard deviation %r; status %d' % (r1, r2, sb))
        if mean is None or abs(mean) > 1e-6 or sd is None:
            print('no sensible interval: is the signal on both START and STOP?')
            ok = False
        else:
            print('\n  START to STOP: %+.3f ns (+- %.3f ns for one edge; the mean of 1000 to about %.3f ns)'
                  % (mean * 1e9, sd * 1e9, sd * 1e9 / 1000 ** 0.5))
            print('  that is the STOP cable %s than the START cable, by about %.2f m of RG-58 (5.05 ns/m),'
                  % ('longer' if mean > 0 else 'shorter', abs(mean) * 1e9 / 5.05))
            print('  plus the 5370B\'s own START-to-STOP skew: swap the two cables and run with --swapped')
            if o.swapped is not None:
                d, skew = (o.swapped - mean * 1e9) / 2, (o.swapped + mean * 1e9) / 2
                print('  with the other reading, %+.3f ns: the cables differ by %.3f ns (%.2f m), the skew is %+.3f ns'
                      % (o.swapped, abs(d), abs(d) / 5.05, skew))
    finally:
        gen.write(G, 'FU 1')                     # back to a sine
        gen.write(G, 'AM 0.001 VO')              # 1 mVpp: as near to off as it goes
        gen.local(G)
        c70.write(B, 'FN1GT1ST1SS1MD1IN1SA1SO1AR1')   # its start-up codes (Table 3-4)
        c70.write(B, 'TLSL')                     # trigger levels and slopes: the knobs
        c70.local(B)
        for bus in opened.values():
            bus.close()
        print('\nleft: the 3325B at 1 mVpp; both on their front panels')
    return 0 if ok else 1


if __name__ == '__main__':
    sys.exit(main())
