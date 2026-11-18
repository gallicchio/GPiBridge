"""SPEED AND FAULT TESTS.  Not a bring-up stage: nothing here is needed to pass the bring-up.

How fast a GPiBridge drives a real instrument, and whether what can go wrong on the way
is handled.  Run it on a board that has passed stage 2 and is plugged into an instrument
this project holds on the bench (bench_claims).  It records nothing in state.json and
moves no stage on STATUS.md: its record goes to results/<day>/<time>_speed_<board>.json,
with a line in BRINGUP_LOG.md.

    python3 bringup/run.py speed A1 --address 2               # the E3646A: every section but live
    python3 bringup/run.py speed A1 --address 10 --only query set
    python3 bringup/run.py speed A1 --address 2 --live        # adds the output-on section (E364xA)
    python3 bringup/run.py --sim speed                        # against sim_board's simulated 33120A

First a scratch script, run on 2026-11-18 with A1 on the bench's E3646A (`REVB.md` 2.12):
it found the late-answer bug in lab-instrument-control's scpi_link, fixed there the same
day.  Instruments it knows: an E364xA power supply with two outputs (E3646A-E3649A) and
the HP 33120A.  Sections, in order:

  adapter   the board's own round trip (++ver, ++t status): no bus traffic at all
  query     queries per second and their spread
  set       one setting: written back to back (the bus handshake the only brake), with
            *OPC?, written then read back (every value compared), and both in one message
  lines     SRQ (*OPC with *ESE 1 and *SRE 32: SRQ asserted, the serial poll reads RQS and
            ESB, SRQ let go) and a message ended by the board's EOI alone.  Not with --sim:
            the simulated instrument raises no SRQ of its own
  faults    nobody at an address, a read with nothing asked, a refused and an unknown
            command, an answer left unread in the port, a timeout mid-answer, a query cut
            short by a signal, an unread query then a device clear, 80 commands in one
            message, 5000 bytes of junk.  After each, the next query must get its own answer
  capture   one *IDN? recorded on the bus by the board, timed handshake by handshake: who
            waits for whom
  live      (--live, E364xA only) the output switched on into what is on it, at most 1 V
            with a 0.8 A limit on the output named by --supply-output (2): a voltage step
            and a current reading as fast as they go, then how soon the current follows

What it changes, and puts back as found at the end: on an E364xA, both outputs'
voltage and current settings (the output stays off except in live), *SRE and *ESE; on a
33120A, its waveform (a 0.1 Vpp sine while it runs), *SRE and *ESE.  The board is parked.
"""
import json
import random
import re
import signal
import statistics
import time

import bench
import steps as S

SECTIONS = ['adapter', 'query', 'set', 'lines', 'faults', 'capture', 'live']


# ---- the instruments -----------------------------------------------------------------------------------
class E364x:
    """A two-output E364xA: the voltage of `out` is the setting pushed around."""
    lo, hi, tol = 0.0, 1.0, 1e-4
    refuse = 'VOLTage 50'                       # above both ranges: -222
    slow = 'MEASure:VOLTage?'                   # about 100 ms

    def __init__(self, model, out=2):
        self.model, self.out = model, out
        self.queries = [('*OPC?', 200), ('VOLTage?', 200), ('*IDN?', 50), ('MEASure:VOLTage?', 20),
                        ('MEASure:CURRent?', 20)]

    def value(self, rng):
        return round(rng.uniform(self.lo, self.hi), 3)

    def set_cmd(self, v):
        return f'VOLTage {v:.3f}'

    get_query = 'VOLTage?'

    def parse(self, reply):
        return float(reply)

    def save(self, L):
        if L.query('OUTPut?') != '0':
            raise S.StepFailed(f'the {self.model} was found with its output on: not touching it')
        found = {'nsel': L.query('INSTrument:NSELect?')}
        for n in (1, 2):
            L.write(f'INSTrument:NSELect {n}')
            found[n] = L.query('APPLy?')
        L.write(f'INSTrument:NSELect {self.out}')
        return found

    def restore(self, L, found):
        L.query('OUTPut OFF;*OPC?')
        for n in (1, 2):
            v, i = (float(x) for x in found[n].strip('"').split(','))
            L.write(f'INSTrument:NSELect {n}')
            L.query(f'APPLy {v},{i};*OPC?')
        L.write(f'INSTrument:NSELect {int(found["nsel"])}')
        now = {}
        for n in (1, 2):
            L.write(f'INSTrument:NSELect {n}')
            now[n] = L.query('APPLy?')
        L.write(f'INSTrument:NSELect {int(found["nsel"])}')
        return all(now[n] == found[n] for n in (1, 2)) and L.query('OUTPut?') == '0', now


class HP33120A:
    """The 33120A: the frequency of a 0.1 Vpp sine is the setting pushed around."""
    tol = 1e-6
    refuse = 'APPLy:SINusoid 2.0E7,0.1,0'      # 20 MHz, above its 15: -222
    slow = None
    SCPI = {'SIN': 'SINusoid', 'SQU': 'SQUare', 'TRI': 'TRIangle', 'RAMP': 'RAMP', 'NOIS': 'NOISe',
            'DC': 'DC', 'USER': 'USER'}

    def __init__(self, model='33120A', out=None):
        self.model = model
        self.queries = [('*OPC?', 200), ('APPLy?', 200), ('*IDN?', 50), ('VOLT?', 50)]

    def value(self, rng):
        return round(rng.uniform(100.0, 10000.0), 1)

    def set_cmd(self, f):
        return f'APPLy:SINusoid {f:.1f},0.1,0'

    get_query = 'APPLy?'

    def parse(self, reply):
        m = re.match(r'"?\w+\s+([^,]+),', reply)
        return float(m.group(1)) if m else float('nan')

    def save(self, L):
        return {'appl': L.query('APPLy?')}

    def restore(self, L, found):
        m = re.match(r'"?(\w+)\s+([^,]+),([^,]+),([^,"]+)', found['appl'])
        if m:
            shape, f, a, o = m.groups()
            f = 'DEF' if shape in ('NOIS', 'DC') else f
            a = 'DEF' if shape == 'DC' else a
            L.write(f'APPLy:{self.SCPI.get(shape, shape)} {f},{a},{o}')
        now = L.query('APPLy?')
        return now == found['appl'], now


def profile_for(idn, out=2):
    model = idn.split(',')[1].strip() if idn.count(',') >= 3 else idn
    if model.startswith('E364'):
        return E364x(model, out)
    if model == '33120A':
        return HP33120A(model)
    raise S.StepFailed(f'no speed and fault tests for {model!r} yet: an E364xA or the 33120A')


# ---- helpers --------------------------------------------------------------------------------------------
def spread(ts):
    ts = sorted(ts)
    return {'n': len(ts), 'per_s': round(len(ts) / sum(ts), 1), 'median_ms': round(1e3 * statistics.median(ts), 2),
            'p95_ms': round(1e3 * ts[int(0.95 * (len(ts) - 1))], 2), 'max_ms': round(1e3 * ts[-1], 2)}


def timed(f, n):
    ts = []
    for k in range(n):
        t = time.perf_counter()
        f(k)
        ts.append(time.perf_counter() - t)
    return spread(ts)


def counters(g):
    s = json.loads(g.ask('++t status'))
    return {k: s[k] for k in ('bus', 'bytes_out', 'bytes_in', 'timeouts', 'no_listener')}


def error_queue(L):
    out = []
    for _ in range(25):
        e = L.query('SYSTem:ERRor?')
        if e.startswith('+0') or e.startswith('0,'):
            break
        out.append(e)
    return out


def handshake_timing(vcd):
    """From a board's capture (VCD text, low = asserted): every byte's handshake, and
    who waited for whom.  For each DAV: since NRFD was let go (the talker's delay), and
    until NDAC was let go (the listener's).  Bytes are the controller's while ATN is
    asserted or the board's data drivers are on (TE_DATA high), else the device's."""
    names, t, ev, state = {}, 0.0, [], {}
    for line in vcd.splitlines():
        line = line.strip()
        if line.startswith('$var'):
            p = line.split()
            names[p[3]] = p[4]
        elif line.startswith('#'):
            t = int(line[1:]) * 10e-9
        elif len(line) > 1 and line[0] in '01' and line[1:] in names:
            n, v = names[line[1:]], int(line[0])
            if state.get(n) != v:
                state[n] = v
                ev.append((t, n, v))
    level = {}
    rows = []
    last = {'NRFD_up': None}
    for t, n, v in ev:
        level[n] = v
        if n == 'NRFD' and v == 1:
            last['NRFD_up'] = t
        if n == 'DAV' and v == 0:
            board_talks = level.get('TE_DATA', 0) == 1 or level.get('ATN', 1) == 0
            rows.append({'t': t, 'board_talks': board_talks, 'ready_to_dav': t - last['NRFD_up']
                         if last['NRFD_up'] is not None else None, 'accepted': None})
        if n == 'NDAC' and v == 1 and rows and rows[-1]['accepted'] is None:
            rows[-1]['accepted'] = t - rows[-1]['t']

    def ms(xs):
        xs = [x for x in xs if x is not None]
        return {'n': len(xs), 'median_us': round(1e6 * statistics.median(xs), 1),
                'max_us': round(1e6 * max(xs), 1)} if xs else None
    dev = [r for r in rows if not r['board_talks']]
    gaps = [b['t'] - a['t'] for a, b in zip(rows, rows[1:])]
    return {'bytes': len(rows), 'span_ms': round(1e3 * (rows[-1]['t'] - rows[0]['t']), 2) if rows else None,
            'board_accepts_a_byte': ms([r['accepted'] for r in dev]),
            'device_accepts_a_byte': ms([r['accepted'] for r in rows if r['board_talks']]),
            'device_talker_delay': ms([r['ready_to_dav'] for r in dev[1:]]),
            'longest_wait_ms': round(1e3 * max(gaps), 2) if gaps else None}


class Guard:
    """One section: an I/O error (a timeout, a garbled answer) in it is a failed check, the
    instrument is sent a device clear, and the next section still runs."""

    def __init__(self, name, rec, L):
        self.name, self.rec, self.L = name, rec, L

    def __enter__(self):
        return self

    def __exit__(self, et, e, tb):
        if et is None or not issubclass(et, (IOError, ValueError, KeyError)):
            return False
        self.rec.check(f'{self.name}: ran to the end', False, f'{et.__name__}: {e}'[:300], 'no error')
        try:
            self.L.clear()
        except IOError:
            pass
        return True


# ---- the run --------------------------------------------------------------------------------------------
def run(ctx, label, address, sections=None, live=False, supply_output=2, nobody=30, claim=None):
    """The sections asked for (all but live by default), as one record."""
    sections = [s for s in (sections or SECTIONS) if s != 'live' or live]
    label, b = ctx.pick(label)
    rec = S.Rec('speed', label, bool(ctx.sim))
    rec.update(address=address, sections=sections)
    rec.note('speed and fault tests: not a bring-up stage')
    small = 10 if ctx.sim else 1                   # the simulation runs the same, with fewer of each
    rng = random.Random(1)
    with ctx.open(label) as a:
        a.cmd('++t power 1')
        if a.json('++t status')['bus'] != 'controller':
            raise S.StepFailed(f'{label} could not take the bus')
    bench.lic()
    from scpi_link import Link
    try:
        L = Link(gpib=address, prologix=b['port'], timeout=5)
    except Exception:
        with ctx.open(label) as a:                 # nothing answered: the board still goes back off the bus
            S.park(a)
        raise
    g = L.gpib
    found = None
    try:
        p = profile_for(L.idn, supply_output)
        rec.update(idn=L.idn, adapter=g.version, model=p.model)
        if not ctx.sim:
            bench.held([claim or f'{p.model}@GPIB{address}'])
        rec['counters_start'] = counters(g)
        found = rec['found'] = p.save(L)
        rec['errors_found'] = error_queue(L)

        if 'adapter' in sections:
            with Guard('adapter', rec, L):
                rec['adapter_ver'] = timed(lambda k: g.ask('++ver'), 200 // small)
                rec['adapter_status'] = timed(lambda k: g.ask('++t status'), 100 // small)

        if 'query' in sections:
            with Guard('query', rec, L):
                before = counters(g)
                rec['queries'] = {q: timed(lambda k, q=q: L.query(q), max(5, n // small)) for q, n in p.queries}
                after = counters(g)
                rec.check('queries: no timeout and no "no listener"', (after['timeouts'], after['no_listener']) ==
                          (before['timeouts'], before['no_listener']), after, before)

        if 'set' in sections:
            with Guard('set', rec, L):
                vals = [p.value(rng) for _ in range(300)]
                n = 200 // small
                t = time.perf_counter()
                for v in vals[:n]:
                    L.write(p.set_cmd(v))
                t_writes = time.perf_counter() - t
                opc = L.query('*OPC?')
                t_all = time.perf_counter() - t
                last = p.parse(L.query(p.get_query))
                rec['set_back_to_back'] = {'n': n, 'writes_s': round(t_writes, 3), 'until_opc_s': round(t_all, 3),
                                           'per_s': round(n / t_all, 1)}
                rec.check('settings back to back: *OPC? answers and the last one holds',
                          opc == '1' and abs(last - vals[n - 1]) <= p.tol * max(1, abs(vals[n - 1])), last, vals[n - 1])
                rec['set_with_opc'] = timed(lambda k: L.query(p.set_cmd(vals[k]) + ';*OPC?'), n)
                bad = []

                def set_get(k):
                    v = vals[k % 300]
                    L.write(p.set_cmd(v))
                    r = p.parse(L.query(p.get_query))
                    if not abs(r - v) <= p.tol * max(1, abs(v)):
                        bad.append((k, v, r))
                rec['set_then_get'] = timed(set_get, 500 // small)
                rec.check('every setting read back as written', not bad, bad[:5], [])
                bad1 = []

                def one_message(k):
                    v = vals[k % 300]
                    r = p.parse(L.query(p.set_cmd(v) + ';:' + p.get_query))
                    if not abs(r - v) <= p.tol * max(1, abs(v)):
                        bad1.append((k, v, r))
                rec['set_get_one_message'] = timed(one_message, 300 // small)
                rec.check('every setting read back in the same message', not bad1, bad1[:5], [])
                errs = error_queue(L)
                rec.check('the instrument logged no error for any of it', errs == [], errs, [])
                rec['counters_after_set'] = counters(g)

        if 'lines' in sections:
            with Guard('lines', rec, L):
                if ctx.sim:
                    rec.note('lines: not simulated (the simulated instrument raises no SRQ of its own)')
                else:
                    g.command('++eos 3')               # nothing appended: EOI alone ends the message
                    try:
                        r = L.query('*IDN?')
                    finally:
                        g.command('++eos 2')
                    rec.check('a message ended by the board\'s EOI alone is understood', r == L.idn, r, L.idn)
                    sre, ese = L.query('*SRE?'), L.query('*ESE?')
                    L.write('*CLS')
                    L.write('*ESE 1')
                    L.write('*SRE 32')
                    s0 = g.ask('++srq')
                    L.write('*OPC')
                    time.sleep(0.2)
                    s1 = g.ask('++srq')
                    poll = g.ask(f'++spoll {address}', 2.0)
                    s2 = g.ask('++srq')
                    L.write('*CLS')
                    L.write(f'*SRE {int(float(sre))}')
                    L.write(f'*ESE {int(float(ese))}')
                    rec['srq'] = {'before': s0, 'after_opc': s1, 'spoll': poll, 'after_spoll': s2}
                    rec.check('SRQ: raised by the instrument, read in the serial poll (RQS and ESB), let go after it',
                              (s0, s1, s2) == ('0', '1', '0') and poll.isdigit() and int(poll) & 0x60 == 0x60,
                              rec['srq'], {'before': '0', 'after_opc': '1', 'spoll': '96 or more', 'after_spoll': '0'})

        if 'faults' in sections:
            with Guard('faults', rec, L):
                F = rec['faults'] = {}

                def then_ok(name):
                    r = L.query('*IDN?')
                    F[name]['next_query'] = r[:60]
                    rec.check(f'{name}: the next query gets its own answer', r == L.idn, r[:60], L.idn)

                before = counters(g)
                t = time.perf_counter()
                try:
                    Link(gpib=nobody, prologix=b['port'], timeout=1.5)
                    F['nobody'] = {'error': None}
                except IOError as e:
                    F['nobody'] = {'error': str(e)[:200]}
                F['nobody']['s'] = round(time.perf_counter() - t, 2)
                rec.check(f'nobody at GPIB {nobody}: an error that says so', 'no listener' in (F['nobody']['error'] or ''),
                          F['nobody']['error'], 'the GPiBridge found no listener ...')
                rec.check(f'nobody at GPIB {nobody}: counted by the board',
                          counters(g)['no_listener'] > before['no_listener'], None, None)
                then_ok('nobody')

                L.timeout = 1.0
                try:
                    F['read_nothing'] = {'got': L.read_raw().decode(errors='replace')[:60]}
                except IOError as e:
                    F['read_nothing'] = {'error': str(e)[:120]}
                L.timeout = 5
                then_ok('read_nothing')

                L.write(p.refuse)
                L.write('BOGUS:COMMand 1')
                F['refused'] = {'errors': error_queue(L)}
                then_ok('refused')

                L.write(p.get_query)                  # an answer the board reads and nobody takes
                g.command('++read eoi')
                time.sleep(0.3)
                F['answer_left_in_the_port'] = {}
                then_ok('answer_left_in_the_port')

                L.timeout = 0.001 if p.slow is None else 0.05
                try:
                    L.query(p.slow or '*IDN?')
                    F['timeout_mid_answer'] = {'timed_out': False}
                except IOError:
                    F['timeout_mid_answer'] = {'timed_out': True}
                L.timeout = 5
                then_ok('timeout_mid_answer')

                class Cut(Exception):
                    pass

                def cut(*_):
                    raise Cut()
                old = signal.signal(signal.SIGALRM, cut)
                try:
                    signal.setitimer(signal.ITIMER_REAL, 0.03 if p.slow else 0.005)
                    try:
                        L.query(p.slow or '*IDN?')
                        F['signal_mid_query'] = {'cut': False}
                    except Cut:
                        F['signal_mid_query'] = {'cut': True}
                finally:
                    signal.setitimer(signal.ITIMER_REAL, 0)
                    signal.signal(signal.SIGALRM, old)
                then_ok('signal_mid_query')
                rec.check('the board answers its own query after all that', g.ask('++ver') == g.version, None, None)

                L.write('*IDN?')
                L.clear()
                time.sleep(0.2)
                F['unread_query_then_clear'] = {}
                then_ok('unread_query_then_clear')

                chain = ';:'.join([p.set_cmd(p.value(rng))] * 80) + ';:' + p.get_query
                t = time.perf_counter()
                r = L.query(chain)
                F['chain_of_80'] = {'bytes': len(chain), 's': round(time.perf_counter() - t, 3), 'reply': r[:60]}
                then_ok('chain_of_80')

                t = time.perf_counter()
                L.write('X' * 5000)
                F['junk_5000'] = {'s': round(time.perf_counter() - t, 3)}
                then_ok('junk_5000')
                F['errors_left'] = error_queue(L)       # the instrument's view of the abuse: kept, not judged
                rec['counters_after_faults'] = counters(g)

        if 'capture' in sections:
            with Guard('capture', rec, L):
                g.ask('++t capture start', 2.0)
                idn = L.query('*IDN?')
                g.command('++t capture dump')
                buf, t_end = b'', time.time() + 10
                while b'$comment end $end' not in buf and time.time() < t_end:
                    buf += g.recv(0.5)
                vcd = buf.decode(errors='replace')
                vcd = vcd[:vcd.find('$comment end $end') + len('$comment end $end')] + '\n'
                path = ctx.home / 'results' / rec['at'][:10] / \
                    f"{rec['at'][11:].replace(':', '')}_speed_{label}_idn{'_sim' if ctx.sim else ''}.vcd"
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(vcd)
                rec['capture'] = str(path.relative_to(ctx.home))
                rec['handshake'] = handshake_timing(vcd)
                rec.check('the capture holds the query and its answer', rec['handshake']['bytes'] >= len(idn) + 5,
                          rec['handshake']['bytes'], f'at least {len(idn) + 5}')

        if 'live' in sections:
            with Guard('live', rec, L):
                if not isinstance(p, E364x):
                    raise S.StepFailed('live: for an E364xA power supply only')
                other = 3 - supply_output
                L.write(f'INSTrument:NSELect {other}')
                L.query('APPLy 0,0.02;*OPC?')          # the other output: 0 V, the least current
                L.write(f'INSTrument:NSELect {supply_output}')
                L.query('APPLy 0,0.8;*OPC?')
                L.query('OUTPut ON;*OPC?')
                try:
                    rows, t0, k = [], time.perf_counter(), 0
                    while time.perf_counter() - t0 < (2 if ctx.sim else 15):
                        v = round(rng.uniform(0, 1.0), 3)
                        L.write(f'VOLTage {v:.3f}')
                        rows.append((round(time.perf_counter() - t0, 3), v, float(L.query('MEASure:CURRent?'))))
                        k += 1
                    rec['live'] = {'steps': k, 'per_s': round(k / (time.perf_counter() - t0), 2), 'first': rows[:5]}
                    L.query('VOLTage 0.2;*OPC?')
                    time.sleep(1)
                    L.write('VOLTage 0.8')
                    t = time.perf_counter()
                    rec['live']['after_a_step'] = [(round(time.perf_counter() - t, 3), float(L.query('MEASure:CURRent?')))
                                                   for _ in range(8)]
                finally:
                    L.query('OUTPut OFF;*OPC?')
    finally:
        try:
            if found is not None:
                L.timeout = 5
                L.clear()
                ok, now = p.restore(L, found)
                rec.check(f'the {p.model} left as it was found', ok, now, found)
                rec['counters_end'] = counters(g)
        finally:
            L.close()
            with ctx.open(label) as a:
                S.park(a)
    return ctx.save(rec)
