#!/usr/bin/env python3
"""A Keithley 2000 6.5-digit multimeter through a GPiBridge: its setup read, DC volts read a
few times and then fifty times against the clock, its error queue and status byte, and its
setup put back as found.

    python3 keithley_2000.py                     # GPIB address 16 (the factory setting)
    python3 keithley_2000.py --address 5 --port COM5

**It puts nothing out and assumes nothing about its inputs.** It reads DC volts on
autorange, in which the meter sources nothing, whatever is on INPUT HI and LO (front or
rear, as its INPUTS button chooses: step 3 says which) or on nothing. Found in a function
that sources current (resistance, continuity, diode), it leaves it for the readings and
goes back to it at the end. It refuses, changing nothing, when it finds the meter measuring
current (something may be wired through the front AMPS jack, 2-5, 2-22, and the manual does
not say whether a change of function opens that path), scanning (5-36: it would switch
scanner channels) or storing readings in its buffer (5-69: they would land there).

For the readings it sets, each read first and put back at the end, last first, then read
again and compared: continuous initiation off, which :READ? needs (5-70); DC volts on
autorange (5-37, 5-42); 1 PLC, 16.7 ms at 60 Hz (5-40); its filter and hold off (5-46, 5-39:
a repeating filter makes up to 100 conversions a reading, hold waits for them to settle,
4-30, 4-31); ASCII, the reading alone (5-28, 5-31); immediate trigger, one trigger, no
delay, one sample (5-71 to 5-73), as the manual's fast example does (C-13). It never sends
*RST or :SYSTem:PRESet (4-48, 5-61): they change far more than this puts back. *CLS clears
its error queue and event registers (4-40): status, not setup. At the end, also after a
failure, it goes to local (GTL, 4-15).

GPIB address 16 from the factory, 0 to 30 (4-3, 4-12): SHIFT then GPIB, the arrow keys to
ADDR and its number, ENTER, EXIT; the address shows at power-up. GPIB or RS-232, one at a
time, is chosen on the front panel only and kept through power off; GPIB from the factory
(4-2). Back from RS-232: SHIFT then GPIB, set GPIB: ON, ENTER (4-3). The language must be
SCPI, also the factory's (SHIFT, GPIB, ENTER twice: LANG; 4-4). Each answer ends in a line
feed sent with EOI (4-38), so a read to the line feed ends where one to EOI would; these
read to the line feed. Commands end in LF, EOI or both (4-37); gpib_port sends both.

Page numbers are those printed in the Model 2000 User's Manual (2000-900-01 Rev. J, August
2010). Written from it on 2026-11-19; it has not met a real 2000 yet.
"""
import argparse
import re
import statistics
import sys
import textwrap
import time

from gpib_port import GpibPort

# What the readings need, as (its query, the value set): each query's answer is kept in
# step 2, the value set in step 4, and the answer sent back at the end, last first. The
# command that sets is the query without its '?' (the tables on 5-8 to 5-18).
CHANGES = (
    (':INITiate:CONTinuous?', 'OFF'),                # 5-70: :READ? needs it off; :ABORt idles it
    (':SENSe:FUNCtion?', '"VOLT:DC"'),               # 5-37
    (':SENSe:VOLTage:DC:RANGe:AUTO?', 'ON'),         # 5-42
    (':SENSe:VOLTage:DC:NPLCycles?', '1'),           # 5-40: 1 power line cycle
    (':SENSe:VOLTage:DC:AVERage:STATe?', 'OFF'),     # 5-46: the filter (4-30)
    (':SENSe:HOLD:STATe?', 'OFF'),                   # 5-39: hold (4-31)
    (':FORMat:DATA?', 'ASCii'),                      # 5-28
    (':FORMat:ELEMents?', 'READing'),                # 5-31: no units, no channel number
    (':TRIGger:SOURce?', 'IMMediate'),               # 5-72
    (':TRIGger:COUNt?', '1'),                        # 5-71
    (':TRIGger:DELay:AUTO?', 'OFF'),                 # table 5-10 (5-18)
    (':TRIGger:DELay?', '0'),                        # 5-72
    (':SAMPle:COUNt?', '1'),                         # 5-73
)
RANGE = ':SENSe:VOLTage:DC:RANGe?'                   # 5-41: the present range's full scale
# Read and shown, never changed
SHOWN = {':ROUTe:SCAN:LSELect?': 'scan: NONE, INT or EXT (5-36)',
         ':TRACe:FEED:CONTrol?': 'buffer storage: NEV or NEXT (5-69)',
         ':SYSTem:AZERo:STATe?': 'autozero (5-64)',
         ':SENSe:VOLTage:DC:REFerence:STATe?': 'DCV rel: readings less a reference (5-44)',
         ':CALCulate:STATe?': 'math, mX+b or percent, on readings (5-21)'}
# The status byte (4-50; figure 4-16 on 4-51). Bit 1 (2) is not used.
BITS = ((1, 'MSB: measurement event'), (4, 'EAV: error available'), (8, 'QSB: questionable, calibration'),
        (16, 'MAV: message available'), (32, 'ESB: standard event'), (64, 'RQS: service requested'),
        (128, 'OSB: operation event'))
OVERFLOW = 9.9e37                                    # an overflowed reading (5-28, 5-31)


def ask(bus, a, q):
    """A query's answer, read to its line feed (4-38). After no answer, Selected Device Clear
    empties its input and output queues, its settings untouched (4-16), so that a late answer
    is not taken for the next one's."""
    try:
        return bus.query(a, q, end='\n')
    except IOError:
        bus.clear(a)
        raise


def timed(bus, a, q):
    """(the answer, None if none came; the seconds it took)"""
    t0 = time.perf_counter()
    try:
        r = ask(bus, a, q)
    except IOError:
        r = None
    return r, time.perf_counter() - t0


def number(r):
    try:
        return float(r)
    except (TypeError, ValueError):
        return None


def said(r):
    """An answer to :READ? or :FETCh?, in words."""
    if r is None:
        return '(no answer)'
    v = number(r)
    if v is None:
        return '%r, NOT A NUMBER' % r
    return '%s (overflow)' % r if v >= OVERFLOW else r


def errors(bus, a):
    """Its error queue, oldest first, until '0,"No error"' (5-63; the numbers in table B-1,
    B-2 to B-6). It holds 10 (5-63)."""
    found = []
    while len(found) < 12:
        try:
            e = ask(bus, a, ':SYSTem:ERRor?')
        except IOError:
            return found + ['(no answer to :SYSTem:ERRor?)']
        if re.match(r'\s*\+?0+\s*(,|$)', e):
            break
        found.append(e)
    return found


def when_ready(bus, a, q, seconds):
    """A query that may take a while: sent, then serial polls until MAV (16) says its answer
    waits in the output queue (4-50), then read, so no read waits on the adapter's timeout."""
    bus.write(a, q)
    t_end = time.time() + seconds
    while time.time() < t_end:
        if bus.serial_poll(a) & 16:
            return bus.read(a, end='\n')
        time.sleep(0.05)
    bus.clear(a)
    raise IOError('%s: no answer in %g s' % (q, seconds))


def setting(q, v, found):
    """The command that sets query q's setting to v, given as the query answers it."""
    if q == ':SENSe:FUNCtion?':
        return ':SENSe:FUNCtion "%s"' % v.strip('"\'')       # 5-37: a quoted name
    if q == ':SENSe:VOLTage:DC:RANGe:AUTO?' and v.strip() in ('0', 'OFF'):
        return ':SENSe:VOLTage:DC:RANGe %s' % found[RANGE]    # 5-42: a range sent ends autorange
    if q == ':TRIGger:COUNt?' and (number(v) or 0) >= OVERFLOW:
        return ':TRIGger:COUNt INF'                            # 5-71: infinite
    return '%s %s' % (q[:-1], v)


def restore(bus, a, found, changed):
    """The settings changed put back, last changed first, then read again: those that are not
    as found. With autorange on the range is the meter's choice, and with auto delay the
    delay (table 3-2 on 3-9): those are not compared."""
    bus.write(a, ':ABORt')                                # 5-70: a reading under way stopped
    for q in reversed(changed):
        bus.write(a, setting(q, found[q], found))
    skip = (RANGE if found[':SENSe:VOLTage:DC:RANGe:AUTO?'] == '1' else None,
            ':TRIGger:DELay?' if found[':TRIGger:DELay:AUTO?'] == '1' else None)
    differ = []
    for q in changed + [RANGE]:
        if q not in skip:
            try:
                now = ask(bus, a, q)
            except IOError:
                now = '(no answer)'
            if now != found[q]:
                differ.append('%s %s, found %s' % (q, now, found[q]))
    return differ


def series(bus, a, q, n):
    """n answers to q, each with its time; it stops when three in a row do not come."""
    out = []
    while len(out) < n and not (len(out) >= 3 and all(r is None for r, _ in out[-3:])):
        out.append(timed(bus, a, q))
    return out


def timing(out):
    s = [t for _, t in out]
    line = '%d in %.2f s: %.1f ms each (least %.1f, median %.1f, most %.1f), %.0f a second' % (
        len(s), sum(s), 1e3 * statistics.mean(s), 1e3 * min(s), 1e3 * statistics.median(s), 1e3 * max(s),
        len(s) / sum(s))
    return line + '\n' + textwrap.fill(' '.join('%.0f' % (1e3 * t) for t in s), 92,
                                       initial_indent='      ms: ', subsequent_indent='          ')


def main():
    ap = argparse.ArgumentParser(description=__doc__.split('\n\n')[0])
    ap.add_argument('--address', type=int, default=16, help='GPIB address (16, the factory setting)')
    ap.add_argument('--port', help='the serial port (found by itself if one GPiBridge is plugged in)')
    o = ap.parse_args()
    a = o.address
    bad = []

    with GpibPort(o.port) as bus:
        print('adapter:', bus.version)
        # The adapter gives up on a read when ++read_tmo_ms passes with no byte, the first
        # one too. A reading here takes tens of ms (1 PLC, filter and hold off, no delay), but
        # autoranging down from 1000 V, or a setting put back, may hold an answer past the
        # 500 ms gpib_port sets: 3000 ms, the most the adapter takes, for this session only
        # (gpib_port sent ++savecfg 0). Back to 500 at the end.
        bus.cmd('++read_tmo_ms 3000')

        # 1. Identity: "KEITHLEY INSTRUMENTS INC.,MODEL 2000,<serial>,<rev>/<rev>" (4-43)
        try:
            idn = bus.query(a, '*IDN?', end='\n')          # (not ask(): no clear after it)
        except IOError:
            sys.exit('nothing answers *IDN? at GPIB %d (a 2000 answers it in SCPI only, 4-4): '
                     'nothing else sent to it' % a)
        print('1. instrument:', idn)
        if not re.search(r'MODEL\s*2000\b', idn.upper()):
            sys.exit('not a Keithley 2000 at GPIB %d: nothing else sent to it' % a)

        # 2. Its setup as found: what step 4 changes, the range, and what is only shown
        found = {}
        for q in [q for q, _ in CHANGES] + [RANGE] + list(SHOWN):
            try:
                found[q] = ask(bus, a, q)
            except IOError:
                bus.local(a)
                sys.exit('2. no answer to %s: nothing changed' % q)
        print('2. as found:')
        for q, r in found.items():
            print(('   %-36s %-14s %s' % (q, r, SHOWN.get(q, ''))).rstrip())
        function = found[':SENSe:FUNCtion?'].strip('"\'').upper()
        refuse = None
        if function.startswith('CURR'):
            refuse = 'it measures current (%s): something may be wired through its AMPS jack (2-22)' % function
        elif 'NONE' not in found[':ROUTe:SCAN:LSELect?'].upper():
            refuse = 'a scan is set up (5-36): it would switch scanner channels'
        elif 'NEXT' in found[':TRACe:FEED:CONTrol?'].upper():
            refuse = 'it is storing readings in its buffer (5-69): these would land there'
        if refuse:
            bus.local(a)
            sys.exit('%s. Nothing changed' % refuse)

        changed = []
        try:
            # 3. The error queue as found (what ran before left it: shown, not counted), then
            # *CLS (4-40), and the queue again: empty. Then the INPUTS button (5-62), the line
            # frequency (5-67), a scanner card (*OPT?, 4-47), and *TST?, its ROM checksum
            # (4-51): the 2000 has no internal temperature or reference to read instead.
            print('3. error queue as found:', errors(bus, a) or 'empty')
            bus.write(a, '*CLS')
            e = errors(bus, a)
            print('   after *CLS:', e or 'empty')
            bad += ['after *CLS: ' + x for x in e]
            info = {}
            for q in (':SYSTem:FRSWitch?', ':SYSTem:LFRequency?', '*OPT?'):
                try:
                    info[q] = ask(bus, a, q)
                except IOError:
                    info[q] = '(no answer)'
                    bad.append('%s: no answer' % q)
            lf = number(info[':SYSTem:LFRequency?'])
            print('   INPUTS %s; line %s Hz; option %s (0: no scanner card)' % (
                {'1': 'FRONT', '0': 'REAR'}.get(info[':SYSTem:FRSWitch?'], info[':SYSTem:FRSWitch?']),
                info[':SYSTem:LFRequency?'], info['*OPT?']))
            try:
                t = when_ready(bus, a, '*TST?', 10)
            except (IOError, ValueError) as x:
                t = '(%s)' % x
            print('   *TST?, ROM checksum: %s (0: passed)' % t)
            if t != '0':
                bad.append('*TST? ' + t)

            # 4. Set for readings (CHANGES), as the manual's fast example does (C-13). Then
            # :READ? five times (5-5: :ABORt, :INITiate, :FETCh?), and once :INITiate with *WAI,
            # which holds what follows until the reading is done (4-52), then :FETCh? (5-4).
            # The values are whatever is on the inputs: only a missing or non-numeric answer
            # counts against it.
            for q, v in CHANGES:
                changed.append(q)
                bus.write(a, setting(q, v, found) + (';:ABORt' if q.startswith(':INIT') else ''))
            print('4. set: DC volts, autorange, 1 PLC%s, filter and hold off, one reading a :READ?, no delay'
                  % (' (%.1f ms)' % (1e3 / lf) if lf else ''))
            for _ in range(5):
                r, dt = timed(bus, a, ':READ?')
                print('   %-24s %-30s %6.1f ms' % (':READ?', said(r), 1e3 * dt))
                bad += [':READ? ' + said(r)] if number(r) is None else []
            t0 = time.perf_counter()
            bus.write(a, ':INITiate;*WAI')
            r, _ = timed(bus, a, ':FETCh?')
            dt = time.perf_counter() - t0
            print('   %-24s %-30s %6.1f ms' % (':INITiate;*WAI :FETCh?', said(r), 1e3 * dt))
            bad += [':FETCh? ' + said(r)] if number(r) is None else []

            # 5. Speed: 50 readings by :READ? (it promises 50 a second at 6.5 digits, 1-2), then
            # 50 *IDN?, each answer timed from the command to its line feed
            out = series(bus, a, ':READ?', 50)
            nums = [number(r) for r, _ in out if number(r) is not None]
            ok = [x for x in nums if x < OVERFLOW]
            print('5. :READ?', timing(out))
            if ok:
                print('      readings: mean %+.7e, least %+.7e, most %+.7e; overflows %d'
                      % (statistics.mean(ok), min(ok), max(ok), len(nums) - len(ok)))
            if len(nums) < 50:
                bad.append('%d of 50 readings missing or not numbers' % (50 - len(nums)))
            out = series(bus, a, '*IDN?', 50)
            print('   *IDN?', timing(out))
            other = sum(r != idn for r, _ in out) + 50 - len(out)
            if other:
                bad.append('%d of 50 *IDN? missing or not as in step 1' % other)

            # 6. The error queue, and the status byte by serial poll (4-50)
            e = errors(bus, a)
            print('6. error queue:', e or 'empty')
            bad += e
            try:
                sb = bus.serial_poll(a)
                print('   status byte %d: %s' % (sb, '; '.join(n for b, n in BITS if sb & b) or 'no bits set'))
                if sb & (4 | 16):                     # an error after the queue was read; an answer unread
                    bad.append('status byte %d' % sb)
            except (IOError, ValueError):
                bad.append('no answer to a serial poll')
        finally:
            if changed:
                differ = restore(bus, a, found, changed)
                print('put back:', '; '.join(differ) if differ else 'all as found')
                bad += ['not put back: ' + d for d in differ]
            bus.cmd('++read_tmo_ms 500')              # the adapter as gpib_port set it
            bus.local(a)                              # Go To Local: its front panel works (4-15)
        print('mismatches:', '; '.join(bad) if bad else 'none')
        return 1 if bad else 0


if __name__ == '__main__':
    sys.exit(main())
