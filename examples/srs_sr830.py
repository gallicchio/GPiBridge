#!/usr/bin/env python3
"""A Stanford Research Systems SR830 DSP lock-in amplifier through a GPiBridge: its setup,
outputs and status bytes read, its time constant and key click each set one step away and
back, and how fast SNAP? goes.

    python3 srs_sr830.py                         # GPIB address 8 (the factory setting)
    python3 srs_sr830.py --address 9 --port COM5
    python3 srs_sr830.py --read-only             # nothing at all written to it

**It leaves the SINE OUT as it is: it may be cabled to an experiment.** The reference source
(FMOD), frequency (FREQ), sine amplitude (SLVL), phase and harmonic are only read, as is
every input, gain, offset and output setting, and *RST is never sent (it would set
1.000 Vrms at 1 kHz from the internal oscillator: the defaults on p. 4-4). Two settings are
changed, each put back at once and again at the end: the time constant (OFLT, p. 5-6), one
step, and the key click (KCLK, p. 5-10). For that moment the X, Y, CH1 and CH2 outputs are
filtered with the other time constant, and take a few time constants to settle. Not the
sensitivity: changing it can change the dynamic reserve, and with it the time constant
(p. 4-10), and the current gain (p. 5-5), which stepping it back need not undo. If a data
scan is running or paused (serial poll bit 0, SCN, clear: p. 5-21), something may be
recording, and nothing is changed. Reading the standard event, LIA and error status bytes
clears them (p. 5-20): a program watching them for overloads misses those already latched.
Nothing is assumed about the inputs: X, Y, R and theta are printed, not judged.

The GPIB address is 8 from the factory (pp. 4-4, 5-25), set with the [Setup] key, ADDRESS,
and the knob (p. 4-24): 1 to 30 (p. 5-1; p. 4-24 says 0 to 30). Holding [Setup] at power-on
also gives 8, with every other default, the sine output's included. The SR830 answers on one
interface only, GPIB or RS232: [Setup], GPIB/RS232 (p. 4-24), or OUTX (p. 5-10); GPIB from
the factory (p. 4-4), and kept through power-off. Set to RS232, it takes commands from GPIB
but answers there with silence: --outx then sends OUTX 1 and, at the end, OUTX 0. The manual
puts OUTX first in every program (pp. 5-3, 5-31); here it is sent only if needed, so that
nothing but *IDN? reaches an instrument that may not be an SR830. Commands end in a line
feed or EOI (p. 5-1). Answers end in a line feed (p. 5-2); EOI is promised only on binary
transfers (TRCB?, TRCL?: pp. 5-16, 5-17), so every answer is read to its line feed. Any GPIB
command puts it in REMOTE; with Override Remote on, the factory setting (OVRM, pp. 4-4,
5-19), its front panel still works then. At the end it is sent Go To Local.

Page numbers are those printed in the SR830 manual (revision 2.5, 10/2011).
"""
import argparse
import math
import re
import statistics
import sys
import time

from gpib_port import GpibPort

# Sensitivity (SENS, p. 5-6), full scale rms; the second unit with a current input
SENS = ('2 nV/fA', '5 nV/fA', '10 nV/fA', '20 nV/fA', '50 nV/fA', '100 nV/fA', '200 nV/fA',
        '500 nV/fA', '1 uV/pA', '2 uV/pA', '5 uV/pA', '10 uV/pA', '20 uV/pA', '50 uV/pA',
        '100 uV/pA', '200 uV/pA', '500 uV/pA', '1 mV/nA', '2 mV/nA', '5 mV/nA', '10 mV/nA',
        '20 mV/nA', '50 mV/nA', '100 mV/nA', '200 mV/nA', '500 mV/nA', '1 V/uA')
# Time constant (OFLT, p. 5-6)
TC = ('10 us', '30 us', '100 us', '300 us', '1 ms', '3 ms', '10 ms', '30 ms', '100 ms', '300 ms',
      '1 s', '3 s', '10 s', '30 s', '100 s', '300 s', '1 ks', '3 ks', '10 ks', '30 ks')


def pick(*names):
    return lambda r: names[int(r)]


def unit(u):
    return lambda r: ('%g %s' % (float(r), u)).strip()


def display(names, ratios):
    """DDEF? i answers 'j,k': the display and its ratio (p. 5-8)."""
    return lambda r: '%s, ratio %s' % (names[int(r.split(',')[0])], ratios[int(r.split(',')[1])])


def offset_expand(r):
    """OEXP? i answers 'x,j': the offset in percent, and expand 1, 10 or 100 (p. 5-8)."""
    x, j = r.split(',')
    return 'offset %g %%, expand %s' % (float(x), ('1', '10', '100')[int(j)])


# Step 3: each query, its page, what it is, and its answer in words. Read again at the end,
# every answer must be as found (FREQ? only with the internal reference: with an external
# one it measures the reference's frequency, p. 5-4).
SETUP = (
    ('FMOD?', '5-4', 'reference source', pick('external', 'internal')),
    ('FREQ?', '5-4', 'reference frequency', unit('Hz')),
    ('PHAS?', '5-4', 'phase shift', unit('degrees')),
    ('HARM?', '5-4', 'detection harmonic', unit('')),
    ('RSLP?', '5-4', 'external reference trigger', pick('sine zero crossing', 'TTL rising', 'TTL falling')),
    ('SLVL?', '5-4', 'SINE OUT amplitude', unit('Vrms')),
    ('ISRC?', '5-5', 'input', pick('A', 'A-B', 'I (1 Mohm)', 'I (100 Mohm)')),
    ('IGND?', '5-5', 'input shield', pick('float', 'ground')),
    ('ICPL?', '5-5', 'input coupling', pick('AC', 'DC')),
    ('ILIN?', '5-5', 'line notch filters', pick('out', 'line in', '2x line in', 'both in')),
    ('SENS?', '5-6', 'sensitivity', pick(*SENS)),
    ('RMOD?', '5-6', 'reserve', pick('high reserve', 'normal', 'low noise')),
    ('OFLT?', '5-6', 'time constant', pick(*TC)),
    ('OFSL?', '5-6', 'filter slope', pick('6 dB/oct', '12 dB/oct', '18 dB/oct', '24 dB/oct')),
    ('SYNC?', '5-7', 'synchronous filter', pick('off', 'on below 200 Hz')),
    ('DDEF? 1', '5-8', 'CH1 display', display(('X', 'R', 'X noise', 'Aux In 1', 'Aux In 2'),
                                              ('none', 'Aux In 1', 'Aux In 2'))),
    ('DDEF? 2', '5-8', 'CH2 display', display(('Y', 'theta', 'Y noise', 'Aux In 3', 'Aux In 4'),
                                              ('none', 'Aux In 3', 'Aux In 4'))),
    ('FPOP? 1', '5-8', 'CH1 output', pick('CH1 display', 'X')),
    ('FPOP? 2', '5-8', 'CH2 output', pick('CH2 display', 'Y')),
    ('OEXP? 1', '5-8', 'X', offset_expand),
    ('OEXP? 2', '5-8', 'Y', offset_expand),
    ('OEXP? 3', '5-8', 'R', offset_expand),
    ('OVRM?', '5-19', 'override remote', pick('no: REMOTE locks the front panel',
                                              'yes: the front panel works in REMOTE')),
    ('KCLK?', '5-10', 'key click', pick('off', 'on')),
    ('ALRM?', '5-10', 'alarms', pick('off', 'on')),
)

# The status bytes, bit by bit (pp. 5-21 to 5-23; also 1-9)
SPOLL = ((1, 'SCN: no scan in progress'), (2, 'IFC: no command executing'),
         (4, 'ERR: an enabled error status bit'), (8, 'LIA: an enabled LIA status bit'),
         (16, 'MAV: an answer waits to be read'), (32, 'ESB: an enabled standard event bit'),
         (64, 'SRQ: service requested'))
ESR = ((1, 'INP: input queue overflow'), (4, 'QRY: output queue overflow'),
       (16, 'EXE: a command could not execute, or a parameter out of range'),
       (32, 'CMD: an illegal command'), (64, 'URQ: a key pressed or the knob turned'),
       (128, 'PON: power on'))
LIAS = ((1, 'INPUT/RESRV: input or amplifier overload'), (2, 'FILTR: time constant filter overload'),
        (4, 'OUTPT: output overload'), (8, 'UNLK: reference unlock'),
        (16, 'RANGE: detection frequency crossed 200 Hz'), (32, 'TC: time constant changed indirectly'),
        (64, 'TRIG: data storage triggered'))
ERRS = ((2, 'backup battery failed'), (4, 'RAM error'), (16, 'ROM error'),
        (32, 'GPIB fast data transfer aborted'), (64, 'DSP error'), (128, 'internal math error'))
FAULTS = 1 | 4 | 16 | 32            # in *ESR?: INP, QRY, EXE, CMD (p. 5-22)


def bits(value, table):
    """A status byte in words: each bit set, by its name in the manual."""
    names = [n for b, n in table if value & b]
    return '%d (%s)' % (value, '; '.join(names) if names else 'no bits set')


def identify(bus, a):
    """The answer to *IDN? (p. 5-19), '' if none came, and any answer set aside before it.
    An answer an earlier program left unread comes first: one that does not start with a
    letter ('0.00123') is set aside, and the next one read."""
    bus.write(a, '*IDN?')
    first = None
    for _ in range(2):
        try:
            r = bus.read(a, end='\n')
        except IOError:
            break
        if r[:1].isalpha():
            return r, first
        first = first or r
    return first or '', None


def sync(bus, a):
    """OUTX? (p. 5-10) asked once, and answers read until its '1': anything queued before it
    (an answer left unread, or one queued while answers went to RS232) is set aside, so that
    every later answer is to the question just asked. The answers set aside."""
    bus.write(a, 'OUTX?')
    stale = []
    for _ in range(3):
        r = bus.read(a, end='\n')
        if r == '1':
            return stale
        stale.append(r)
    raise IOError('OUTX? never answered 1: %r' % stale)


def read_setup(bus, a):
    """Every SETUP query's answer, None where none came (after 5 s). After three in a row
    without one, the rest are not asked."""
    got, missed = {}, 0
    for q, _, _, _ in SETUP:
        got[q] = None
        if missed < 3:
            try:
                got[q] = bus.query(a, q, end='\n')
                missed = 0
            except IOError:
                missed += 1
    return got


def floats(answer, n):
    """An answer of n numbers separated by commas (SNAP?, p. 5-15), as floats."""
    v = [float(x) for x in answer.split(',')]
    if len(v) != n:
        raise ValueError('%d numbers, not %d: %r' % (len(v), n, answer))
    return v


def events(bus, a):
    """The standard event status byte, which reading clears (*ESR?, p. 5-20)."""
    return int(bus.query(a, '*ESR?', end='\n'))


def main():
    ap = argparse.ArgumentParser(description=__doc__.split('\n\n')[0])
    ap.add_argument('--address', type=int, default=8, help='GPIB address (8, the factory setting)')
    ap.add_argument('--port', help='the serial port (found by itself if one GPiBridge is plugged in)')
    ap.add_argument('--read-only', action='store_true', help='write no setting (step 5 skipped)')
    ap.add_argument('--outx', action='store_true',
                    help='if *IDN? gets no answer: OUTX 1 (answers to GPIB), *IDN? again, OUTX 0 at the end')
    o = ap.parse_args()
    a = o.address
    bad = []
    found = {}                  # step 3's answers
    put_back = {}               # each setting changed: its value as found
    outx_was = 1                # 0: answers went to RS232, and go there again at the end

    with GpibPort(o.port) as bus:
        print('adapter:', bus.version)
        try:
            # 1. *IDN?: "Stanford_Research_Systems,SR830,s/n00111,ver1.000" (p. 5-19)
            idn, aside = identify(bus, a)
            if not idn and o.outx:
                bus.write(a, 'OUTX 1')                   # answers to GPIB (p. 5-10)
                outx_was = 0
                idn, aside = identify(bus, a)
            print('1. *IDN?: %s%s' % (idn or '(no answer)',
                                      '; before it, set aside: %r, left unread' % aside if aside else ''))
            if not re.search(r',\s*SR830\s*,', idn):
                if idn:
                    outx_was = 1                         # something else answered: nothing more to it
                    print('not an SR830 at GPIB %d: nothing else sent to it' % a)
                    return 1
                try:
                    sb = bus.serial_poll(a)
                    seen = 'something answers a serial poll there (status byte %d), not *IDN?' % sb
                except (IOError, ValueError):
                    seen = 'nothing answers *IDN? or a serial poll there'
                print('no SR830 found at GPIB %d: %s' % (a, seen))
                if not o.outx:
                    print('An SR830 whose answers go to RS232 ([Setup], GPIB/RS232: p. 4-24) is silent on '
                          'GPIB. If one is there, run again with --outx')
                return 1

            # 2. Answers come over GPIB (OUTX? 1, p. 5-10). Then *ESR? (p. 5-20), which reading
            #    clears: what earlier programs left, so that later readings are this one's.
            stale = sync(bus, a)
            print('2. OUTX? 1: answers come over GPIB%s%s' % (
                ' (OUTX 1 sent: they went to RS232, and will again at the end)' if outx_was == 0
                else ', as found: no OUTX needed',
                '; set aside, left from before: %r' % stale if stale else ''))
            print('   *ESR? %s: left from before, now cleared' % bits(events(bus, a), ESR))

            # 3. The setup, only read (pages in SETUP)
            found.update(read_setup(bus, a))
            print('3. as found:')
            for q, page, what, words in SETUP:
                r = found[q]
                try:
                    m = words(r) if r is not None else 'NO ANSWER'
                except (ValueError, IndexError):
                    m = 'NOT AS ON p. %s' % page
                if r is None or m.startswith('NOT AS'):
                    bad.append('%s: %r' % (q, r))
                print('   %-8s %-12s %s: %s (p. %s)' % (q, r, what, m, page))

            # 4. The outputs. OUTP? i (p. 5-15): X, Y, R in volts (amps with a current input),
            #    theta in degrees, one at a time. SNAP? (p. 5-15): X and Y at one instant, R and
            #    theta at another about 10 us later, and the reference frequency. OUTR? i, the
            #    CH1 and CH2 displays (p. 5-15); OAUX? i, Aux In 1 to 4 in volts (p. 5-16).
            u = 'A' if found.get('ISRC?') in ('2', '3') else 'V'
            x, y, r, th = [float(bus.query(a, 'OUTP? %d' % i, end='\n')) for i in (1, 2, 3, 4)]
            print('4. OUTP?: X %+.6g %s, Y %+.6g %s, R %.6g %s, theta %+.2f degrees' % (x, u, y, u, r, u, th))
            sx, sy, sr, sth, sf = floats(bus.query(a, 'SNAP? 1,2,3,4,9', end='\n'), 5)
            print('   SNAP? 1,2,3,4,9: X %+.6g, Y %+.6g, R %.6g (from X and Y: %.6g), theta %+.2f, '
                  'f %.6g Hz' % (sx, sy, sr, math.hypot(sx, sy), sth, sf))
            if min(r, sr) < 0 or max(abs(th), abs(sth)) > 180.01:
                bad.append('R %g, %g; theta %g, %g: outside R >= 0, |theta| <= 180' % (r, sr, th, sth))
            disp = [float(bus.query(a, 'OUTR? %d' % i, end='\n')) for i in (1, 2)]
            aux = [float(bus.query(a, 'OAUX? %d' % i, end='\n')) for i in (1, 2, 3, 4)]
            print('   OUTR?: CH1 %g, CH2 %g | OAUX?: Aux In 1-4 %s V' % (disp[0], disp[1],
                                                                       ', '.join('%g' % v for v in aux)))

            #    The status bytes (pp. 5-21 to 5-23). A serial poll and *STB? read the same byte,
            #    but a poll clears SRQ (p. 5-21). *ESR?, LIAS? and ERRS? clear on reading (p. 5-20).
            #    LIAS? and ERRS? are the inputs' and the instrument's own, printed, not judged.
            sb = bus.serial_poll(a)
            print('   serial poll: %s' % bits(sb, SPOLL))
            print('   *STB?: %s' % bits(int(bus.query(a, '*STB?', end='\n')), SPOLL))
            e = events(bus, a)
            print('   *ESR?: %s' % bits(e, ESR))
            if e & FAULTS:
                bad.append('*ESR? %d after steps 2 to 4' % e)
            print('   LIAS?: %s' % bits(int(bus.query(a, 'LIAS?', end='\n')), LIAS))
            print('   ERRS?: %s' % bits(int(bus.query(a, 'ERRS?', end='\n')), ERRS))

            # 5. Two settings, each a step away and back, read back each time. The time constant
            #    (OFLT, p. 5-6): up a step, to at most 30 s, which every detection frequency
            #    allows; from 30 s and above, down, far above the shortest one allowed (p. 4-9).
            #    The key click (KCLK, p. 5-10). Not while a scan runs or is paused (SCN, p. 5-21).
            if o.read_only:
                print('5. skipped: --read-only')
            elif not sb & 1:
                print('5. skipped: a data scan is running or paused (serial poll bit 0, SCN, clear): '
                      'something may be recording. Nothing changed')
            elif found['OFLT?'] is None or found['KCLK?'] is None:
                print('5. skipped: OFLT? or KCLK? did not answer in step 3')
            else:
                tc, click = int(found['OFLT?']), int(found['KCLK?'])
                for cmd, was, other, names in (('OFLT', tc, tc + 1 if tc <= 12 else tc - 1, TC),
                                               ('KCLK', click, 1 - click, ('off', 'on'))):
                    put_back[cmd] = was
                    for want in (other, was):
                        bus.write(a, '%s %d' % (cmd, want))
                        got = int(bus.query(a, cmd + '?', end='\n'))
                        print('5. %s %d (%s): %s? %d, %s' % (cmd, want, names[want], cmd, got,
                                                             'ok' if got == want else 'MISMATCH'))
                        if got != want:
                            bad.append('%s %d read back %d' % (cmd, want, got))
                e = events(bus, a)
                print('   *ESR?: %s' % bits(e, ESR))
                if e & FAULTS:
                    bad.append('*ESR? %d after step 5' % e)

            # 6. Speed: 50 SNAP? 1,2 (X and Y at one instant, p. 5-15), each timed. The manual
            #    meant SNAP? for coherence, not speed (p. 5-16): this is the bus and the SR830.
            times, odd = [], []
            for _ in range(50):
                t0 = time.perf_counter()
                ans = bus.query(a, 'SNAP? 1,2', end='\n')
                times.append(time.perf_counter() - t0)
                try:
                    floats(ans, 2)
                except ValueError:
                    odd.append(ans)
            ms = [t * 1e3 for t in times]
            print('6. 50 SNAP? 1,2 in %.2f s, %.0f a second: %.1f to %.1f ms each, median %.1f ms%s' % (
                sum(times), len(times) / sum(times), min(ms), max(ms), statistics.median(ms),
                '; %d answers not two numbers' % len(odd) if odd else ''))
            for k in range(0, len(ms), 10):
                print('   ms:', ' '.join('%5.1f' % t for t in ms[k:k + 10]))
            if odd:
                bad.append('%d of 50 SNAP? 1,2 answers not two numbers, e.g. %r' % (len(odd), odd[0]))
        except (IOError, ValueError, IndexError) as x:
            print('FAILED:', x)
            bad.append(str(x))
        finally:
            # 7. Each setting changed, written again as found; every step-3 setting read again
            #    and compared; answers to RS232 again if they went there (OUTX 0, p. 5-10); Go To
            #    Local (as its [LOCAL] key, p. 5-19).
            try:
                for cmd, was in put_back.items():
                    bus.write(a, '%s %d' % (cmd, was))
                if found:
                    now = read_setup(bus, a)
                    moved = ['%s %s, as found %s' % (q, now[q], found[q]) for q, _, _, _ in SETUP
                             if now[q] != found[q] and not (q == 'FREQ?' and found['FMOD?'] == '0')]
                    e = events(bus, a)
                    print('7. put back: %s; every setting read again: %s; *ESR? %s' % (
                        ', '.join('%s %d' % c for c in put_back.items()) or 'nothing changed',
                        'CHANGED: ' + '; '.join(moved) if moved else 'as found', bits(e, ESR)))
                    bad += moved + (['*ESR? %d after steps 6 and 7' % e] if e & FAULTS else [])
            except (IOError, ValueError) as x:
                print('7. FAILED:', x)
                bad.append('putting back: %s' % x)
            if outx_was == 0:
                bus.write(a, 'OUTX 0')                   # answers to RS232, as found (p. 5-10)
            bus.local(a)
    print('mismatches:', '; '.join(bad) if bad else 'none')
    return 1 if bad else 0


if __name__ == '__main__':
    sys.exit(main())
