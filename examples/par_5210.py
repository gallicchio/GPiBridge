#!/usr/bin/env python3
"""An EG&G Princeton Applied Research (Signal Recovery) Model 5210 dual-phase lock-in
amplifier through a GPiBridge: its identity, every setting it reports, its outputs and
status byte, two harmless settings stepped and put back, and 50 readings timed.

    python3 par_5210.py                          # GPIB address 12 (a guess: see below)
    python3 par_5210.py --address 7 --port COM5

**It changes nothing an experiment can feel, and assumes nothing on its inputs.** It
reads. The only settings it writes are what DISPLAY 1 shows (D1) and the output time
constant (TC), each one step and back, then read back; whatever is still changed after
a failure is put back too. The time constant moves only while it is below 10 s: shorter
ones are analog filters, from 10 s up the filter is digital (p. 6-20), and a change could
restart its average. From 1 ms to 1 s it goes one step longer, from 3 s one step
shorter; CH1 and CH2 follow that filter for those few milliseconds. It never sends an
oscillator, reference, sensitivity, offset or DAC setting (OA, OF, IE, F2F, SEN, XOF,
DAC), an auto-function (AS, ASM, AQN, ANR, ATS, AXO, ADCAL), OUTFF, the "*" transfer
mode, or DM (a toggle). OSC OUT is left as it was found.

The address is set on the front panel, not by switches: CONFIG, then DYN RES/GPIB.
DISPLAY 1 shows 0 and DISPLAY 2 the address (0 to 31), which the VALUE keys change;
CONFIG again goes back (p. 5-27). The 5210 keeps it with the power off (p. 3-24). The
manual gives no factory address: 12 here is a guess, so read it there first. With
DISPLAY 1 at 1, DISPLAY 2 shows the terminator: 0 or 1 CR, 2 or 3 CR LF. Codes 1 and 3
also echo the bus to the RS232 port, which slows it (p. 5-28).

The 5210 expects its terminator after each command and ends each answer with it, with
EOI on the last byte "in all cases" (pp. 6-5, 6-6, 6-18; "always sent", C-3). A command
is its name, then integers separated by spaces (p. 6-6). A setting command sent without
its argument answers with the setting. Two numbers in one answer are separated by the
character the DD command sets (pp. 6-6, 6-18). This script sends CR, as the manual's own
GPIB program does (GPCOM.BAS, C-3), with EOI on it (with EOI, C-3 says, no terminator is
needed). If ID brings no answer, it sends the LF that makes CR LF. Then it reads GP and
keeps to the 5210's terminator. Answers
are read to EOI (++read eoi), whichever terminator is set. gpib_port reads lines to a LF,
so while the 5210 ends answers in CR alone, the adapter adds a LF after the EOI byte
(++eot_enable 1, ++eot_char 10). ID must answer 5210 (p. 6-19), or the script stops.

Page numbers are those printed in the Model 5210 Instruction Manual, 219874-A-MNL-G
(Signal Recovery, 2002).
"""
import argparse
import math
import re
import sys
import time

from gpib_port import GpibPort

# The status byte (serial poll, or ST) and the overload byte (N), bits 0 to 7: p. 6-8
# (also 6-18, 6-19). Bit 0 is set when a command is done; bits 1 and 2 report a bad one.
STATUS = ('command complete', 'invalid command', 'command parameter error', 'reference unlock',
          'overload', 'new outputs after an external trigger, or an auto-function running',
          'SRQ asserted', 'data available')
OVERLOAD = ('bit 0 (not used)', 'current input at 10^8 V/A', 'current input at 10^6 V/A',
            'Y output overload', 'X output overload', 'PSD overload', 'input overload',
            'reference unlock')
DONE, INVALID, PARAMETER, READY = 1, 2, 4, 128
DIGITAL_TC = 8      # TC 8 is 10 s: from there up the output filter is digital (p. 6-20)
ON = {0: 'off', 1: 'on'}


def sensitivity(n):
    """Full scale in volts for SEN n: 100 nV (0) to 3 V (15), 1-3-10 (table p. 6-9, formula 6-21)."""
    return (1 + 2 * (n % 2)) * 10.0 ** (n // 2 - 7)


def time_constant(n):
    """Seconds for TC n: 1 ms (0) to 3 ks (13), 1-3-10 (table p. 6-12)."""
    return (1 + 2 * (n % 2)) * 10.0 ** (n // 2 - 3)


def osc_hz(n):
    """OF n1 n2 in Hz: n1 from 2000 to 20000 within band n2, 0.5-2 Hz (0) to 20-120 kHz (5),
    p. 6-15. That makes n1 x 10^(n2-4) Hz, as the example on p. 6-23 has it (OF 10000 2 is
    100 Hz). The example on p. 6-15, "OF 1000 3" for 1 kHz, is outside its own range."""
    return n[0] * 10.0 ** (n[1] - 4)


def eng(x, unit):
    """1e-07, 'V' -> '100 nV'."""
    for f, p in ((1e3, 'k'), (1, ''), (1e-3, 'm'), (1e-6, 'u'), (1e-9, 'n'), (1e-12, 'p'), (1e-15, 'f')):
        if abs(x) >= 0.9995 * f:
            return '%.4g %s%s' % (x / f, p, unit)
    return '%.4g %s' % (x, unit)


def pick(table):
    return lambda n: table.get(n[0], 'not in the manual\'s table')


# Step 2: command, how many numbers it answers, page, what they mean. Each one reads.
SETTINGS = (
    ('SEN', 1, '6-9', lambda n: 'full scale %s (a current input divides it by its V/A: N)'
     % eng(sensitivity(n[0]), 'V')),
    ('G', 2, '6-9', lambda n: 'gain vernier %s, at %d of 0-255' % (ON.get(n[0], '?'), n[1])),
    ('IE', 1, '6-11', pick({0: 'EXT reference: front REF IN or rear TTL REF IN',
                            1: 'INT reference: the internal oscillator'})),
    ('F2F', 1, '6-11', pick({0: 'F: detects at the reference frequency', 1: '2F: at twice it'})),
    ('P', 2, '6-11', lambda n: 'reference phase %.3f deg (quadrant %d, then %.3f deg)'
     % (90 * n[0] + n[1] / 1e3, n[0], n[1] / 1e3)),
    ('FRQ', 1, '6-12', lambda n: 'reference frequency %.3f Hz%s'
     % (n[0] / 1e3, ' (0: an external reference not locked)' if n[0] == 0 else '')),
    ('OA', 1, '6-15', lambda n: 'oscillator %s rms at OSC OUT' % eng(n[0] / 1e3, 'V')),
    ('OF', 2, '6-15', lambda n: 'oscillator %s (band %d)' % (eng(osc_hz(n), 'Hz'), n[1])),
    ('FLT', 1, '6-10', pick({0: 'FLAT: no signal filter', 1: 'NOTCH', 2: 'LP: low-pass', 3: 'BP: band-pass'})),
    ('ATC', 1, '6-10', pick({0: 'filter frequency set by hand (FF)', 1: 'filter tracks the reference'})),
    ('FF', 2, '6-10', lambda n: 'signal filter at %s (band %d)' % (eng(n[0] * 10.0 ** (n[1] - 2), 'Hz'), n[1])),
    ('LF', 1, '6-10', pick({0: 'line rejection off', 1: '100/120 Hz notch', 2: '50/60 Hz notch',
                            3: 'both notches'})),
    ('DR', 1, '6-12', pick({0: 'dynamic reserve HI STAB', 1: 'dynamic reserve NORM', 2: 'dynamic reserve HI RES'})),
    ('TC', 1, '6-12', lambda n: 'time constant %s' % eng(time_constant(n[0]), 's')),
    ('XDB', 1, '6-12', pick({0: 'output slope 6 dB/octave', 1: 'output slope 12 dB/octave'})),
    ('XOF', 2, '6-13', lambda n: 'X offset %s, %+.1f %% of full scale' % (ON.get(n[0], '?'), n[1] / 10.0)),
    ('YOF', 2, '6-13', lambda n: 'Y offset %s, %+.1f %% of full scale' % (ON.get(n[0], '?'), n[1] / 10.0)),
    ('EX', 1, '6-13', pick({0: 'X expand off', 1: 'X expanded x10'})),
    ('TRIG', 1, '6-16', pick({0: 'ADC triggered by the reference', 1: 'ADC triggered at rear ADC EXT TRIG IN',
                              2: 'ADC free-running at 100 Hz', 4: 'ADC in ratio mode', 8: 'ADC in 8F mode'})),
    ('D1', 1, '6-19', pick({0: 'DISPLAY 1 shows SET REF PH', 1: 'DISPLAY 1 shows SET OSC LVL',
                            2: 'DISPLAY 1 shows SET OSC F', 3: 'DISPLAY 1 shows FIL FRQ',
                            4: 'DISPLAY 1 shows REF F', 5: 'DISPLAY 1 shows DISP, as DISPLAY 2'})),
    ('D2', 1, '6-19', pick({0: 'XY %: CH1 X, CH2 Y', 1: 'XY V: CH1 X, CH2 Y', 2: 'R theta: CH1 magnitude, CH2 phase',
                            3: 'OFFSET: CH1 X, CH2 Y', 4: 'NOISE: CH1 noise, CH2 magnitude', 5: 'SPEC'})),
    ('MSK', 1, '6-19', lambda n: 'SRQ mask %d%s' % (n[0], ' (never asks for service)' if n[0] == 0 else '')),
    ('REMOTE', 1, '6-19', pick({0: 'front panel keys work', 1: 'front panel locked out, but for LOCAL'})),
    ('DAC', 1, '6-15', lambda n: 'rear DAC AUX OUT at %+.3f V' % (n[0] / 1e3)),
)


def bits(byte, names):
    on = [names[i] for i in range(8) if byte >> i & 1]
    return '%d (0x%02X): %s' % (byte, byte, '; '.join(on) if on else 'no bit set')


def numbers(line):
    """The integers in an answer: one, or two with the DD delimiter between (p. 6-6)."""
    return [int(n) for n in re.findall(r'[-+]?\d+', line)]


def ask(bus, a, cmd):
    """The answer to `cmd`, read to the EOI on its last byte (pp. 6-5, 6-6)."""
    bus.write(a, cmd)
    return bus.read(a)


def drop_late(bus, a):
    """A serial poll; if it says an answer is waiting (bit 7, p. 6-8), the answer is read and
    dropped, or the next query would read it. Returns the status byte, in words."""
    sb = bus.serial_poll(a)
    if sb & READY:
        try:
            print('   a late answer, read and dropped: %r' % bus.read(a))
        except IOError:
            pass
    return bits(sb, STATUS)


def get(bus, a, cmd, count, bad):
    """(the integers in the answer to `cmd`, the answer); (None, ...) if there are not `count`
    of them, or no answer, the reason added to `bad`. count None: any answer will do."""
    try:
        line = ask(bus, a, cmd)
    except IOError:
        try:
            why = 'status byte ' + drop_late(bus, a)
        except (IOError, ValueError):
            why = 'no answer to a serial poll either'
        bad.append('%s: no answer (%s)' % (cmd, why))
        return None, '(no answer)'
    n = numbers(line)
    if count is not None and len(n) != count:
        bad.append('%s answered %r: %d numbers, not %d' % (cmd, line, len(n), count))
        return None, line
    return n, line


def show(cmd, line, meaning, page):
    print('   %-7s %-16s %s (p. %s)' % (cmd, "'%s'" % line, meaning, page))


def settle(bus, a, timeout=2.0):
    """The status byte once the 5210 has carried out a command. The manual's own loop
    (p. 6-7): bit 0 clears while it works and is set again when it is done; a quick command
    may be done before the first poll, so bit 0 has 10 ms to clear."""
    t0 = time.time()
    sb = bus.serial_poll(a)
    while sb & DONE and time.time() - t0 < 0.01:
        sb = bus.serial_poll(a)
    while not sb & DONE and time.time() - t0 < timeout:
        sb = bus.serial_poll(a)
    return sb


def put(bus, a, cmd, value, bad, step):
    """`cmd value` (p. 6-6), and the setting read back: True if it reads back as sent, the
    command done, and neither invalid command nor parameter error set (p. 6-8)."""
    bus.write(a, '%s %d' % (cmd, value))
    sb = settle(bus, a)
    if sb & READY:                       # a setting has no answer: one waiting is unexpected
        drop_late(bus, a)
    n, line = get(bus, a, cmd, 1, bad)
    ok = n == [value] and sb & DONE and not sb & (INVALID | PARAMETER)
    print('%s %s %d: status byte %s; reads back %r: %s'
          % (step, cmd, value, bits(sb, STATUS), line, 'ok' if ok else 'MISMATCH'))
    if not ok:
        bad.append('%s %d: status byte %d, read back %r' % (cmd, value, sb, line))
    return ok


def identify(bus, a):
    """(ID's answer or None, whether the LF of CR LF was needed). ID goes with CR, EOI on it
    (++eos 1, as GPCOM.BAS, p. C-3). With no answer the 5210 may be set to CR LF and waiting
    for the LF (p. 5-28): the LF alone follows (++eos 3, nothing added; gpib_port escapes
    it, so it goes as data, with EOI), and the answer is read again."""
    bus.write(a, 'ID')                   # identification: answers 5210 (p. 6-19)
    try:
        return bus.read(a), False
    except IOError:
        pass
    print('   no answer to ID with CR: sending the LF of CR LF')
    bus.cmd('++eos 3')
    bus.write(a, '\n')
    bus.cmd('++eos 0')                   # CR LF from now on, until GP says otherwise
    try:
        return bus.read(a), True
    except IOError:
        return None, True


def main():
    ap = argparse.ArgumentParser(description=__doc__.split('\n\n')[0])
    ap.add_argument('--address', type=int, default=12,
                    help='GPIB address (12, a guess: CONFIG then DYN RES/GPIB shows it, p. 5-27)')
    ap.add_argument('--port', help='the serial port (found by itself if one GPiBridge is plugged in)')
    o = ap.parse_args()
    a = o.address
    bad = []
    changed = {}                         # setting: the value it was found at, while it is not

    with GpibPort(o.port, read_timeout=2.0) as bus:
        print('adapter:', bus.version)
        # CR after each command, with EOI (p. C-3); a LF after the EOI byte of each answer,
        # for gpib_port's readline, while answers may end in CR alone (p. 6-5).
        for c in ('++eos 1', '++eot_char 10', '++eot_enable 1'):
            bus.cmd(c)
        try:
            sb = bus.serial_poll(a)
        except (IOError, ValueError):
            sys.exit('nothing answers a serial poll at GPIB %d: nothing sent to it' % a)
        print('0. status byte', bits(sb, STATUS))
        if sb & READY:                   # an answer somebody left unread would answer ID
            try:
                print('   an answer was waiting, read and dropped: %r' % bus.read(a))
            except IOError:
                pass

        # 1. Its identity (p. 6-19), before anything else is sent
        ident, lf_needed = identify(bus, a)
        if ident != '5210':
            for c in ('++eos 2', '++eot_enable 0'):     # the adapter as gpib_port sets it
                bus.cmd(c)
            sys.exit('GPIB %d: %s, not 5210: nothing more sent'
                     % (a, 'no answer to ID' if ident is None else 'ID answered %r' % ident))
        print('1. ID: %r, a 5210%s' % (ident, ' (terminator CR LF)' if lf_needed else ''))
        failed = False
        try:
            n, line = get(bus, a, 'VER', None, bad)
            show('VER', line, 'firmware version', '6-19')
            n, line = get(bus, a, 'DD', 1, bad)
            if n:
                delim = chr(n[0])
                show('DD', line, 'delimiter %r between two numbers in an answer' % delim, '6-18')
                if delim in '0123456789+-':
                    bad.append('DD %d: the delimiter %r cannot be told from the numbers' % (n[0], delim))
            gp, line = get(bus, a, 'GP', 2, bad)
            crlf = gp[1] >= 2 if gp else lf_needed
            if gp:
                show('GP', line, 'address %d, terminator %s, test echo to RS232 %s'
                     % (gp[0], 'CR LF' if crlf else 'CR',
                        'on (it slows the bus, p. 5-28)' if gp[1] & 1 else 'off'), '6-18')
                if gp[0] != a:
                    bad.append('GP says address %d, but it answered at %d' % (gp[0], a))
            # From here on, its own terminator; the adapter's LF only while answers end in CR.
            bus.cmd('++eos 0' if crlf else '++eos 1')
            bus.cmd('++eot_enable %d' % (0 if crlf else 1))

            # 2. Every setting it reports: a setting command without its argument reads it (p. 6-6)
            print('2. settings')
            s = {}
            for cmd, count, page, meaning in SETTINGS:
                n, line = get(bus, a, cmd, count, bad)
                s[cmd] = n
                show(cmd, line, meaning(n) if n else '?', page)
            # With the internal reference, FRQ counts the oscillator (p. 6-12), to 0.1 %, and
            # the oscillator is set to 1 % (p. 3-7): a check of how OF is read (osc_hz).
            if s['IE'] == [1] and s['F2F'] == [0] and s['OF'] and s['FRQ'] and s['FRQ'][0] > 0:
                set_hz, counted = osc_hz(s['OF']), s['FRQ'][0] / 1e3
                agree = abs(counted / set_hz - 1) < 0.05
                print('   internal reference: OF reads as %s, FRQ counts %s: %s'
                      % (eng(set_hz, 'Hz'), eng(counted, 'Hz'), 'they agree' if agree else 'THEY DISAGREE'))
                if not agree:
                    bad.append('OF %r read as %g Hz, FRQ %g Hz' % (s['OF'], set_hz, counted))

            # 3. The outputs: X, Y and MAG in 1/10000 of full scale, to 150 % (+-15000); PHA in
            #    millidegrees (pp. 6-13, 6-14, 6-21). In volts: that fraction of SEN's full scale
            #    (table p. 6-9). The formula on p. 6-22 multiplies by 10^-5, which would make
            #    full scale a tenth of the table's: taken for a misprint.
            print('3. outputs')
            ov, line = get(bus, a, 'N', 1, bad)
            show('N', line, 'overload byte ' + bits(ov[0], OVERLOAD) if ov else '?', '6-18, 6-19')
            gain = None if not ov else 1e8 if ov[0] & 2 else 1e6 if ov[0] & 4 else None
            full = s['SEN'] and sensitivity(s['SEN'][0]) / (gain or 1)
            unit = 'A' if gain else 'V'
            out = {}
            for cmd, lo, page in (('X', -15000, '6-13'), ('Y', -15000, '6-13'), ('MAG', 0, '6-14')):
                n, line = get(bus, a, cmd, 1, bad)
                if n:
                    out[cmd] = v = n[0]
                    ok = lo <= v <= 15000
                    show(cmd, line, '%+.2f %% of full scale%s%s' % (
                        v / 100.0, ', %s' % eng(v / 1e4 * full, unit) if full else '',
                        '' if ok else ': OUTSIDE %d to 15000' % lo), page)
                    if not ok:
                        bad.append('%s %d outside %d to 15000' % (cmd, v, lo))
            n, line = get(bus, a, 'PHA', 1, bad)
            if n:
                out['PHA'] = n[0] / 1e3
                ok = abs(n[0]) <= 180000
                show('PHA', line, 'phase %+.3f deg%s' % (n[0] / 1e3, '' if ok else ': OUTSIDE +-180'), '6-14')
                if not ok:
                    bad.append('PHA %d outside +-180000' % n[0])
            for cmd, what, page in (('XY', 'X and Y together', '6-13'), ('MP', 'MAG and PHA together', '6-14')):
                n, line = get(bus, a, cmd, 2, bad)
                show(cmd, line, what if n else '? (two numbers expected, p. 6-6)', page)
            if all(k in out for k in ('X', 'Y', 'MAG', 'PHA')):
                # MAG is |X + jY| and PHA its angle (pp. 3-16, 3-17); read one after another,
                # they agree only as well as the signal holds still: shown, not judged.
                print('   from X and Y: magnitude %.0f (MAG %d), phase %+.1f deg (PHA %+.1f)'
                      % (math.hypot(out['X'], out['Y']), out['MAG'],
                         math.degrees(math.atan2(out['Y'], out['X'])), out['PHA']))
            n, line = get(bus, a, 'NN', 1, bad)
            show('NN', line, 'noise %.2f %% of full scale' % (n[0] / 100.0) if n else '?', '6-14')
            for ch in (1, 2, 3, 4):
                n, line = get(bus, a, 'ADC %d' % ch, 1, bad)
                show('ADC %d' % ch, line,
                     'rear AUX ADC INPUT CH%d %+.3f V' % (ch, n[0] / 1e3) if n else '?', '6-16')
            n, line = get(bus, a, 'ST', 1, bad)
            show('ST', line, 'status byte ' + bits(n[0], STATUS) if n else '?', '6-18')
            sb = bus.serial_poll(a)
            print('   serial poll: status byte', bits(sb, STATUS))
            if sb & (INVALID | PARAMETER):
                bad.append('status byte %d after the reads: a command not taken' % sb)

            # 4. Two settings one step and back, each read back. D1 only picks what DISPLAY 1
            #    shows (p. 6-19); TC moves only within the analog filter (below 10 s, p. 6-20).
            tests = []
            if s['D1'] and 0 <= s['D1'][0] <= 5:
                tests.append(('D1', s['D1'][0], (s['D1'][0] + 1) % 6))
            if s['TC'] and 0 <= s['TC'][0] < DIGITAL_TC:
                tc = s['TC'][0]
                tests.append(('TC', tc, tc + 1 if tc + 1 < DIGITAL_TC else tc - 1))
            for cmd, was, new in tests:
                changed[cmd] = was           # before the write: whatever happens, it is put back
                put(bus, a, cmd, new, bad, '4.')
                if put(bus, a, cmd, was, bad, '4.'):
                    del changed[cmd]
            if s['TC'] and s['TC'][0] >= DIGITAL_TC:
                tc = s['TC'][0]
                print('4. TC %d (%s): a digital filter, left alone' % (tc, eng(time_constant(tc), 's')))

            # 5. Speed: 50 X readings, each a write and a read to EOI
            times, lines = [], []
            for i in range(50):
                t0 = time.perf_counter()
                lines.append(ask(bus, a, 'X'))
                times.append(1e3 * (time.perf_counter() - t0))
            print('5. 50 X readings, ms each:')
            for i in range(0, 50, 10):
                print('   ' + ' '.join('%6.1f' % t for t in times[i:i + 10]))
            srt = sorted(times)
            print('   min %.1f, median %.1f, max %.1f ms: %.0f readings a second'
                  % (srt[0], (srt[24] + srt[25]) / 2, srt[-1], 50e3 / sum(times)))
            vals = [numbers(line) for line in lines]
            good = [v[0] for v in vals if len(v) == 1 and abs(v[0]) <= 15000]
            if good:
                print('   X from %d to %d (full scale 10000)' % (min(good), max(good)))
            if len(good) < 50:
                bad.append('%d of 50 X answers not one number within +-15000' % (50 - len(good)))
            if srt[-1] > 450:
                bad.append('an X reading took %.0f ms: ended by the adapter\'s 500 ms timeout, '
                           'not by EOI?' % srt[-1])
        except (IOError, ValueError) as e:  # ValueError: a serial poll unanswered
            failed = isinstance(e, IOError)
            why = str(e) if failed else 'no answer to a serial poll (%s)' % e
            print('   failed:', why)
            bad.append(why)
        finally:
            # 6. Whatever is still changed put back, then Go To Local. The 5210's own front
            #    panel lockout is the REMOTE command and the LOCAL key (pp. 5-25, 6-19), never
            #    sent here; Go To Local is for the bus's remote state.
            try:
                if failed:               # Selected Device Clear: drops a half-read answer and
                    bus.clear(a)         # changes no setting (p. 5-25)
                    time.sleep(0.1)
                for cmd, was in list(changed.items()):
                    if put(bus, a, cmd, was, bad, '6.'):
                        del changed[cmd]
            except (IOError, ValueError) as e:
                bad.append('putting settings back: %s' % e)
            for cmd, was in changed.items():
                print('6. %s IS NOT BACK at %d: set it on the front panel' % (cmd, was))
            bus.local(a)
            for c in ('++eos 2', '++eot_enable 0'):     # the adapter as gpib_port sets it
                bus.cmd(c)
            print('6. back to local')
    print('mismatches:', '; '.join(bad) if bad else 'none')
    return 1 if bad else 0


if __name__ == '__main__':
    sys.exit(main())
