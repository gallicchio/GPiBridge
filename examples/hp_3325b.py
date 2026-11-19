#!/usr/bin/env python3
"""An HP 3325B (or 3325A) synthesizer/function generator through a GPiBridge: a sine set
and read back, then its error code and its status byte.

    python3 hp_3325b.py                          # GPIB address 17 (the factory setting)
    python3 hp_3325b.py --address 9 --port COM5

**Its MAIN SIGNAL output carries a 1 kHz sine of 0.1 Vpp at 0 V offset** from the
amplitude setting until near the end, when the amplitude goes to 1 mVpp, the least the
3325B allows (table 2-9 on p. 2-22, specifications on 3-2; it is also the preset value).
The generator has no output switch, so that 1 kHz, 1 mVpp sine stays on. Amplitudes are
into 50 ohm (3-2): expect twice that into 1 Mohm. The signal comes out of the front or rear
BNC, whichever the RF command last chose (front after a preset).

Page numbers are those printed in the 3325B Operating Manual (03325-90014, March 1990);
"3325A 3-25" means the 3325A manual. Never send it Device Clear: the 3325B takes that as
Preset (2-7). HP-IB address 31 makes it listen-only (2-7): it would never answer.
"""
import argparse
import math
import re
import sys

from gpib_port import GpibPort

SCALE = {'': 1, 'HZ': 1, 'KH': 1e3, 'MH': 1e6, 'VO': 1, 'MV': 1e-3}
# The status byte: 3325B table 2-3 on 2-10 (3325A 3-24). Bit 4 (16) is always 0.
BITS = ((1, 'ERR: program or entry error'), (2, 'STOP: sweep stopped'), (4, 'START: sweep started'),
        (8, 'FAIL: hardware failure'), (32, 'SWEEP: sweep in progress'),
        (64, 'RQS: it asked for service'), (128, 'BUSY: executing a command'))
# The 3325B error codes this script could cause; table 2-51 (2-65, 2-66) has them all.
ERRORS = {100: 'entry parameter out of bounds', 200: 'invalid units suffix', 500: 'amplitude/offset incompatible',
          503: 'amplitude too small', 700: 'unknown command', 701: 'illegal query', 800: 'illegal character'}


def identify(bus, a):
    """'3325B', '3325A' or None. ID? answers 'HP3325B' (2-38) in either data transfer mode
    (*IDN? breaks in mode 2, where '*' ends a command). The 3325A has no identity query
    (table 2-52 on 2-67): when nothing answers ID?, an IFR reply of 'FR', digits and 'HZ'
    (3325A 3-25) says it is one."""
    try:
        r = bus.query(a, 'ID?')                                   # 2-38
    except IOError:
        r = ''
    print('ID?:', r or '(no answer)')
    if r:
        return '3325B' if '3325B' in r else None
    try:
        r = bus.query(a, 'IFR')                                   # 3325A 3-25; 3325B 2-34
    except IOError:
        return None
    print('IFR:', r)
    return '3325A' if re.match(r'FR\s*[\d.]+\s*HZ$', r) else None


def interrogate(bus, a, mnemonic):
    """I<mnemonic>: the setting as a number (Hz, Vpp, V, or the function's digit), and the
    reply. With HEAD on, e.g. 'FR00001000.000HZ', 'AM00000.100000VO', 'FU1' (FR 2-34, AM
    2-22, OF 2-49, FU 2-35; 3325A 3-25, 3-26); with HEAD off (3325B only, 2-36) the number
    alone. Every reply ends in CR LF, with EOI on the LF (2-19)."""
    r = bus.query(a, 'I' + mnemonic).replace(' ', '')
    m = re.match(r'(?:%s)?([-+]?[\d.]+)([A-Z]*)$' % mnemonic, r)
    if not m or m.group(2) not in SCALE:
        raise ValueError('I%s: unexpected reply %r' % (mnemonic, r))
    return float(m.group(1)) * SCALE[m.group(2)], r


def check(bus, a, mnemonic, want, what):
    """One setting read back and compared with what was set: True when it matches."""
    got, r = interrogate(bus, a, mnemonic)
    ok = math.isclose(got, want, rel_tol=1e-4, abs_tol=1e-6)
    print('I%s: %-18s = %g %s  %s' % (mnemonic, r, got, what, 'ok' if ok else 'MISMATCH: set %g' % want))
    return ok


def error(bus, a, model):
    """The latest error code, 0 for none; asking clears it. 3325B: ERR?, 'ERR###' (2-31).
    3325A: IER, 'ER#' (3325A 3-25; its codes 1-9 on 3-24)."""
    r = bus.query(a, 'ERR?' if model == '3325B' else 'IER').replace(' ', '')
    m = re.match(r'(?:ERR|ER)?(\d+)$', r)
    if not m:
        raise ValueError('error query: unexpected reply %r' % r)
    return int(m.group(1))


def main():
    ap = argparse.ArgumentParser(description=__doc__.split('\n\n')[0])
    ap.add_argument('--address', type=int, default=17, help='GPIB address (17, the factory setting)')
    ap.add_argument('--port', help='the serial port (found by itself if one GPiBridge is plugged in)')
    o = ap.parse_args()
    a = o.address

    with GpibPort(o.port) as bus:
        print('adapter:', bus.version)
        model = None
        try:
            model = identify(bus, a)
            if not model:
                print('not a 3325A or 3325B at GPIB %d: nothing else sent to it' % a)
                return 1
            print('instrument: HP', model)
            # What an earlier program (or ID? on a 3325A) left, cleared: the error code by
            # asking, the status byte's ERR, STOP, START, FAIL and RQS by the poll (2-10).
            print('before: error %d, status byte %d: cleared' % (error(bus, a, model), bus.serial_poll(a)))

            bus.write(a, 'OF 0 VO')            # DC offset 0 V (2-49)
            bus.write(a, 'FU 1')               # function 1, sine (table 2-19 on 2-35)
            bus.write(a, 'FR 1000 HZ')         # 1 kHz (2-34)
            bus.write(a, 'AM 0.1 VO')          # 0.1 Vpp (2-21; units in table 2-9 on 2-22)
            bad = ['I' + c[0] for c in (('FR', 1000, 'Hz'), ('AM', 0.1, 'Vpp'), ('OF', 0, 'V'), ('FU', 1, '(sine)'))
                   if not check(bus, a, *c)]
            bus.write(a, 'AM 0.001 VO')        # 1 mVpp, the least it allows (table 2-9 on 2-22)
            if not check(bus, a, 'AM', 0.001, 'Vpp, the least'):
                bad.append('IAM')

            e = error(bus, a, model)
            print('error: %d%s' % (e, ' (%s)' % ERRORS.get(e, 'see table 2-51 on 2-65; 3325A: 3-24')
                                   if e else ', none'))
            if e:
                bad.append('error %d' % e)
            sb = bus.serial_poll(a)            # status byte: table 2-3 on 2-10
            print('status byte: %d: %s' % (sb, '; '.join(n for b, n in BITS if sb & b) or 'no bits set'))
            if sb & 9:                         # ERR (1) or FAIL (8)
                bad.append('status byte %d' % sb)
            print('result:', 'FAILED: ' + ', '.join(bad) if bad else 'all as set')
            return 1 if bad else 0
        except (IOError, ValueError) as x:
            print('FAILED:', x)
            return 1
        finally:
            if model:
                bus.write(a, 'AM 0.001 VO')    # (again, also after a failure) 1 mVpp: 2-22
            bus.local(a)                       # Go To Local: its front panel works again (2-8)


if __name__ == '__main__':
    sys.exit(main())
