#!/usr/bin/env python3
"""An HP 5316B universal counter through a GPiBridge: its CHECK function (the counter
counting its own 10 MHz reference) read and checked, FREQ A selected, the status byte read
and explained, and the counter handed back to its front panel.

    python3 hp_5316b.py                          # HP-IB address 20 (the 5316B's factory setting)
    python3 hp_5316b.py --address 7 --port COM5

**It needs nothing on INPUT A, B or C**, and puts nothing out. The rear REF switch must be
at INT (or at EXT with 10, 5 or 1 MHz into REF IN/OUT), or CHECK reads as an error (E3,
page 3-12). Keep the front GATE TIME knob out of HOLD, which stops the bus on a read
(3-36): the script gates on the rear PRESET GATE TIME, wherever it is (500 us to 30 ms).

The address is set by the five right-hand rear-panel switches, A5 (most significant) to
A1: 20, or 10100, from the factory (pages 3-32, 3-33). The two switches left of them go
down, as the manual's drawing (3-33) shows them: ADDRESSABLE, not TALK ONLY. Leaving TALK
ONLY also takes the front RESET key (3-30). With no identity query, whatever is at the
address gets the codes.
"""
import argparse
import json
import sys
import time

from gpib_port import GpibPort

RQS = 64    # status byte bit 6: service requested, a reading is ready (3-31, 3-34, 3-35)


def read_line(bus, a):
    """One reading, to its line feed. A reading ends in CR LF (3-36), with no EOI on any byte
    (seen on the bus, 2026-11-19). '++read 10' stops at the LF. '++read eoi' never ends: a
    5316B still addressed to talk sends its next reading, and the next (3-30)."""
    return bus.read(a, end='\n')              # '++read 10'


def release(bus, a):
    """Codes sent while a reading is held (WA1) wait until it is read (3-38, item 5): if the
    status byte says one is ready, read it. Returns the status byte after."""
    if bus.serial_poll(a) & RQS:
        print('   a reading was held; read to let the codes in:', read_line(bus, a))
    return bus.serial_poll(a)


def parse(r):
    """'F+    1.00000E+07' (Table 3-5, page 3-37): F frequency, T time, O overflow, X error,
    a space otherwise; then a sign, spaces, digits with a point, E, a sign and two digits.
    The letter, the value, and the weight of its last digit."""
    kind, number = r[:1], r[1:].replace(' ', '')
    mantissa, exponent = number.upper().split('E')
    decimals = len(mantissa.split('.')[1]) if '.' in mantissa else 0
    return kind, float(number), 10.0 ** (int(exponent) - decimals)


def faults(bus):
    """A GPiBridge's count of transfers that timed out or found no listener; None on a Prologix."""
    if not bus.version.startswith('GPiBridge'):
        return None
    st = json.loads(bus.ask('++t status'))
    return st.get('timeouts', 0) + st.get('no_listener', 0)


def main():
    ap = argparse.ArgumentParser(description=__doc__.split('\n\n')[0])
    ap.add_argument('--address', type=int, default=20, help='HP-IB address (20)')
    ap.add_argument('--port', help='the serial port (found by itself if one GPiBridge is plugged in)')
    o = ap.parse_args()
    a = o.address
    bad = []

    with GpibPort(o.port) as bus:
        print('adapter:', bus.version)
        try:
            # 1. Device Clear, a reset (3-30 f; Table 3-3, 3-31). IN: FN1 AS0 BS0 TR0 WA0 SR0 GA0 (3-34, 3-39)
            bus.clear(a)
            bus.write(a, 'IN')
            print('1. clear, IN')
            print('   status byte %d' % release(bus, a))

            # 2. FN9: CHECK, the 10 MHz reference into the counter (3-6, 3-35). GA3: the short
            #    gate range, 500 us to 30 ms, on the rear control, which has no HOLD (3-36).
            #    WA1: gate once, hold the reading for a talk address. SR1: request service
            #    when it is ready; it needs WA1 (3-34, 3-38 item 8; the manual's own test, 4-14).
            bus.write(a, 'FN9GA3WA1SR1')
            t0 = time.time()
            status = bus.serial_poll(a)
            while not status & RQS and time.time() - t0 < 3:
                time.sleep(0.05)
                status = bus.serial_poll(a)
            print('2. FN9 GA3 WA1 SR1: status byte %d after %.2f s' % (status, time.time() - t0))
            if not status & RQS:
                bad.append('CHECK: no service request within 3 s')
            r = read_line(bus, a)
            try:
                kind, f, lsd = parse(r)
            except ValueError:
                kind, f, lsd = r[:1], float('nan'), 0.0
            # A count of the reference by itself: 10 MHz to within 2 counts of the last digit
            # (page 1-2), with at least 3 digits even on the shortest gate.
            if kind == 'F' and lsd <= 1e5 and abs(f - 10e6) <= 2 * lsd:
                print('   reading %r: %.0f Hz, 10 MHz to within 2 x %g Hz' % (r, f, lsd))
            else:
                hint = ' (X: an error; is the rear REF switch at INT? 3-12)' if kind == 'X' else ''
                print('   reading %r: expected F and 10 MHz%s' % (r, hint))
                bad.append('CHECK read %r' % r)

            # 3. FN1: FREQ A (3-35). WA0: gate continuously, send only when addressed; SR0: no
            #    service requests (3-34). With nothing on INPUT A no reading comes: none is
            #    asked for. A GPiBridge counts a write the counter did not take.
            before = faults(bus)
            bus.write(a, 'WA0SR0FN1')
            after = faults(bus)
            took = ('sent (a Prologix cannot tell whether it was taken)' if before is None else
                    'taken, every byte handshaken' if before == after else 'NOT taken: the write timed out')
            print('3. WA0 SR0 FN1:', took)
            if before != after:
                bad.append('FN1 not taken')
            release(bus, a)

            # 4. The status byte (Table 3-3, 3-31): only bit 6 (64) is defined, set while SR1 and
            #    WA1 hold a reading, cleared when it is read (3-34, 3-35). There is no error bit:
            #    an error is an X before a reading (3-37) and the ERROR light (3-12).
            status = bus.serial_poll(a)
            print('4. status byte %d: bit 6 (64, a reading ready) %s; bits 0-5 and 7, none defined, %s'
                  % (status, 'SET' if status & RQS else 'clear', 'SET' if status & ~RQS else 'clear'))
            if status:
                bad.append('status byte %d in FREQ A with WA0 SR0' % status)
        except (IOError, ValueError) as e:      # ValueError: a serial poll or ++t status unanswered
            why = str(e) if isinstance(e, IOError) else 'no answer to a serial poll (%s)' % e
            print('   failed:', why)
            bad.append(why)
        finally:
            # 5. No reading or SRQ left held (WA0 SR0), then Go To Local (Table 3-3, 3-31).
            try:
                bus.write(a, 'WA0SR0')
                release(bus, a)
            except (IOError, ValueError):
                pass
            bus.local(a)
            print('5. back to local')
    print('mismatches:', '; '.join(bad) if bad else 'none')
    return 1 if bad else 0


if __name__ == '__main__':
    sys.exit(main())
