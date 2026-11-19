#!/usr/bin/env python3
"""One signal, two counters: an HP 3325B synthesizer sets a sine, and an HP 5316B and an
HP 5370B count it, each instrument on its own GPiBridge (or all three on one GPIB cable).

    python3 three_instruments.py --port COM5                 # all three on one bus
    python3 three_instruments.py --gen-port /dev/ttyACM1 --c16-port /dev/ttyACM2 --c70-port /dev/ttyACM0
    python3 three_instruments.py --gen-port E9D119818C2ADDD2 ...   # or by GPiBridge serial number
    python3 three_instruments.py --freqs 1e3 1e6 12345678.9

**Cabling:** the 3325B's MAIN SIGNAL output, through a BNC tee, to the 5316B's INPUT A and
the 5370B's **STOP** input: the 5370B counts frequency on STOP (IN2, "normal input
selection for frequency or period", its manual p. 3-23). Measured on START instead (IN3),
each period carries the fixed delay between its START and STOP event paths, about 0.7 ns:
-0.7 % at 10 MHz (2026-11-19).

**It puts 0.5 Vpp on the 3325B's output** (into 50 ohm; about 1 Vpp into the counters'
1 Mohm inputs), a sine at 0 V offset; both counters trigger at 0 V, set by HP-IB. At the
end, also after a failure, the 3325B goes to 1 mVpp (it has no output switch) and all three
are handed back to their front panels.

Each counter has its own timebase, and so has the 3325B: the parts-per-million columns are
the differences between them, the same at every frequency if all is well. The 5316B gates
on the time set by its rear GATE TIME control (long range, 60 ms to 10 s; GA2, manual
p. 3-36): each reading takes that long. The 5370B averages over a 0.1 s gate (GT3).
Neither counter sends EOI: both are read to the line feed (`++read 10`).
"""
import argparse
import re
import sys
import time

from gpib_port import GpibPort, find_port

NUMBER = re.compile(r'[-+]?\s*\d*\.?\d+(?:\s*[eE]\s*[-+]?\s*\d+)?')
RQS = 64


def number(text):
    m = NUMBER.search(text)
    return float(re.sub(r'\s', '', m.group())) if m else None


def port_name(p):
    """A port as given, or the port of the GPiBridge with this USB serial number."""
    return find_port(p) if p and re.fullmatch(r'[0-9A-Fa-f]{16}', p) else p


def ppm(measured, f):
    return '%+9.3f' % ((measured / f - 1) * 1e6) if measured else '        ?'


def main():
    ap = argparse.ArgumentParser(description=__doc__.split('\n\n')[0])
    ap.add_argument('--port', help='one GPiBridge for all three (found by itself if one is plugged in)')
    ap.add_argument('--gen-port', help="the 3325B's GPiBridge: a port or a serial number")
    ap.add_argument('--c16-port', help="the 5316B's")
    ap.add_argument('--c70-port', help="the 5370B's")
    ap.add_argument('--gen', type=int, default=17, help='3325B address (17)')
    ap.add_argument('--c16', type=int, default=20, help='5316B address (20)')
    ap.add_argument('--c70', type=int, default=3, help='5370B address (3)')
    ap.add_argument('--freqs', type=float, nargs='+',
                    default=[1e3, 1e4, 1e5, 1e6, 1e7, 2e7, 12345678.9], help='Hz, 0.001 Hz to 20 MHz')
    o = ap.parse_args()

    names = {k: port_name(getattr(o, k + '_port') or o.port) for k in ('gen', 'c16', 'c70')}
    opened = {}                                      # one GpibPort per distinct port
    for k, p in names.items():
        if p not in opened:
            opened[p] = GpibPort(p)
            print('%s: %s' % (p or 'the GPiBridge', opened[p].version))
    gen, c16, c70 = (opened[names[k]] for k in ('gen', 'c16', 'c70'))
    G, A, B = o.gen, o.c16, o.c70
    bad = []
    try:
        # The 3325B: sine, 0 V offset, 0.5 Vpp (its manual 2-34 to 2-49; examples/hp_3325b.py)
        for c in ('FU 1', 'OF 0 VO', 'AM 0.5 VO'):
            gen.write(G, c)
        e = gen.query(G, 'ERR?').replace(' ', '')
        print('3325B: %s, %s, %s; %s' % (gen.query(G, 'IFU'), gen.query(G, 'IAM'), gen.query(G, 'IOF'), e))
        if e != 'ERR000':
            bad.append('3325B set-up: ' + e)

        # The 5316B (pp. 3-34 to 3-36): FREQ A; trigger level by its DAC (TR1), 0 V; the long
        # gate on the rear control (GA2); one reading held per measurement (WA1) and a
        # service request when it is ready (SR1)
        c16.clear(A)
        time.sleep(0.3)
        for c in ('IN', 'FN1TR1', 'AT0', 'GA2WA1SR1'):
            c16.write(A, c)

        # The 5370B (Table 3-4, pp. 3-22 to 3-24): frequency on STOP (IN2), mean, one
        # measurement per MR (MD2), slopes and trigger levels by HP-IB, positive, 0 V. The
        # gate last: GT (gate time) and SS (sample size) are alternatives, the last one sent
        # wins, and GT3 followed by SS1 measured a single period.
        c70.clear(B)
        time.sleep(0.5)
        for c in ('ST1ST6', 'FN3', 'MD2', 'IN2', 'SR', 'SA1', 'SO1', 'TR', 'TA0.00', 'TO0.00', 'ST1', 'GT3'):
            c70.write(B, c)
            time.sleep(0.02)                         # MR and codes 10 ms apart (p. 3-24)
        sb = c70.serial_poll(B)
        if sb & RQS and sb & 15:
            bad.append('5370B set-up: error %d' % (sb & 15))
        c70.cmd('++read_tmo_ms 2000')                # a measurement can take a moment to begin
        c70.write(B, 'MR')                           # the first after a change of function
        time.sleep(0.3)                              # may be old (MD2, p. 3-22): read, unused;
        try:                                         # once (2026-11-19) none came at all
            c70.read(B, end='\n')
        except IOError:
            pass

        print('\n%15s %16s %22s %9s %22s %9s %9s' % ('set (Hz)', '3325B says', '5316B', 'ppm',
                                                   '5370B', 'ppm', '5316-5370'))
        for f in o.freqs:
            gen.write(G, 'FR %.3f HZ' % f)
            said = gen.query(G, 'IFR').replace(' ', '')
            time.sleep(0.1)                          # the synthesizer settles
            c16.write(A, 'RE')                       # a new 5316B measurement (p. 3-34)
            c70.write(B, 'MR')                       # and one of the 5370B's
            t0, sb = time.time(), c16.serial_poll(A)
            while not sb & RQS and time.time() - t0 < 15:
                time.sleep(0.05)
                sb = c16.serial_poll(A)
            r16 = c16.read(A, end='\n') if sb & RQS else '(none in 15 s)'
            r70 = c70.read(B, end='\n')
            v16 = number(r16[1:]) if r16[:1] == 'F' else None    # 'F' a frequency; 'X' an error
            v70 = number(r70) if r70.startswith('FRQ') else None
            v70 = v70 if v70 and v70 < 1e15 else None           # 9.99999999999E+62: no measurement
            both = '%+9.3f' % ((v16 / v70 - 1) * 1e6) if v16 and v70 else '        ?'
            print('%15.3f %16s %22s %s %22s %s %s' % (f, said, r16, ppm(v16, f), r70, ppm(v70, f), both))
            if not (v16 and v70 and abs(v16 / f - 1) < 1e-4 and abs(v70 / f - 1) < 1e-4):
                bad.append('%g Hz: 5316B %r, 5370B %r' % (f, r16, r70))
        e = gen.query(G, 'ERR?').replace(' ', '')
        if e != 'ERR000':
            bad.append('3325B: ' + e)
    finally:
        gen.write(G, 'AM 0.001 VO')                  # 1 mVpp: as near to off as it goes
        gen.local(G)
        c16.write(A, 'WA0SR0')
        c16.write(A, 'IN')                           # its defaults: front-panel trigger levels
        c16.local(A)
        # Its start-up codes (bold in Table 3-4), as after switching it on; then the knobs:
        # display rate, trigger levels, slopes. With nothing to measure (the 3325B at
        # 1 mVpp) it shows "Err 02", overrange: a measurement that never ends, in either
        # function. Harmless; it clears once it has a signal (2026-11-19).
        c70.write(B, 'FN1GT1ST1SS1MD1IN1SA1SO1')
        c70.write(B, 'TLSL')
        c70.local(B)
        for bus in opened.values():
            bus.close()
        print('\nleft: the 3325B at 1 mVpp; all three on their front panels')
    print('mismatches (beyond 100 ppm, or no reading):', '; '.join(bad) if bad else 'none')
    return 1 if bad else 0


if __name__ == '__main__':
    sys.exit(main())
