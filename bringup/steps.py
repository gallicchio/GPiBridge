"""The bring-up steps.  `run.py` calls one at a time; BRINGUP.md says what is plugged in for each.

Every step returns a record: what was asked, what the board said, and a list of
checks with their verdicts.  Nothing here waits for a keyboard, so a step can be run
from a chat while the person at the bench is elsewhere.  Each step leaves the board
PARKED: off the GPIB bus (green BUS LED off) and told to stay off it when it is next
plugged in (`++t autostart 0`), so cables can be changed at any time between steps
and two adapters on one cable never both act as the controller.
"""
import json
import os
import re
import subprocess
import time
from datetime import datetime
from pathlib import Path

import adapter as A
import expect as E

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
STAGES = ['flash', 'bare', 'failsafe', 'rails', 'plug', 'pair', 'prologix', 'gen']
# what each stage is, in the words STATUS.md uses
STAGE_WORDS = {
    'flash': 'firmware loaded',
    'bare': 'stage 1: the bare board on USB',
    'failsafe': 'stage 1: three hangs in a row land in the ROM bootloader',
    'rails': 'stage 1b: the four rails with a scope probe',
    'plug': 'stage 2: the plug soldered, checked alone',
    'pair': 'stage 2b: every line against a second board',
    'prologix': 'stage 3: against the bench Prologix as a device',
    'gen': 'stage 4: the HP 33120A',
}


class StepFailed(Exception):
    """A step could not run at all (no board, no port); a check that fails is in the record instead."""


# ---- the record of one step -----------------------------------------------------------------------------
class Rec(dict):
    def __init__(self, step, board, sim=False):
        super().__init__(step=step, board=board, at=datetime.now().strftime('%Y-%m-%d %H:%M:%S'), sim=sim,
                         ok=True, checks=[], notes=[])

    def check(self, what, ok, got=None, want=None):
        self['checks'].append({'what': what, 'ok': bool(ok), 'got': got, 'want': want})
        if not ok:
            self['ok'] = False
        return bool(ok)

    def note(self, text):
        self['notes'].append(text)

    def failed(self):
        return [c for c in self['checks'] if not c['ok']]


# ---- where things are -----------------------------------------------------------------------------------
class Ctx:
    """The boards a step can reach, and where its records go.

    sim: a sim.SimBench (then the "boards" are its sim_board processes, and nothing is
    written outside `home`).  home: where state.json, results/, STATUS.md and
    BRINGUP_LOG.md live: this folder for the real bench, a scratch one for a simulation.
    """

    def __init__(self, sim=None, home=None, quick=False, quiet=False):
        self.sim, self.quick, self.quiet = sim, quick, quiet
        self.home = Path(home) if home else HERE
        self.home.mkdir(parents=True, exist_ok=True)
        self.state_path = self.home / 'state.json'
        self.state = json.loads(self.state_path.read_text()) if self.state_path.exists() else {'boards': {}}

    def say(self, *a):
        if not self.quiet:
            print(*a, flush=True)

    # -- the boards plugged in now: {label: {'serial', 'port', 'kind', 'console'}}
    def present(self):
        out = {}
        if self.sim:
            for label in self.sim.labels():
                i = self.sim.info[label]
                self._known(i['serial'], i['board'], label)
                out[label] = {'serial': i['serial'], 'port': i['link'], 'kind': i['board'], 'console': None}
            return out
        for serial, d in A.gpibridges().items():
            if not d['gpib']:
                continue
            kind = 'GPiBridge Lite rev A' if 'Lite' in d['product'] else 'GPiBridge rev A'
            label = self._known(serial, kind)
            out[label] = {'serial': serial, 'port': d['gpib'], 'kind': kind, 'console': d['console']}
        return out

    def _known(self, serial, kind, label=None):
        """The label of this serial number; a board seen for the first time gets the next
        free one: A1, A2 for GPiBridge, L1, L2 for the Lite."""
        b = self.state['boards'].get(serial)
        if b is None:
            if label is None:
                letter = 'L' if 'Lite' in kind else 'A'
                taken = {x['label'] for x in self.state['boards'].values()}
                label = next(f'{letter}{n}' for n in range(1, 99) if f'{letter}{n}' not in taken)
            b = self.state['boards'][serial] = {'label': label, 'kind': kind, 'stages': {}, 'new': True,
                                               'first_seen': datetime.now().strftime('%Y-%m-%d %H:%M')}
            self.write_state()
        return b['label']

    def pick(self, label=None):
        """(label, entry) of the board a step works on: the one named, or the only one there."""
        here = self.present()
        if label is None:
            if len(here) != 1:
                raise StepFailed(f'{len(here)} GPiBridges are plugged in ({", ".join(sorted(here)) or "none"}): '
                                 'name one')
            label = next(iter(here))
        if label not in here:
            raise StepFailed(f'board {label} is not plugged in (plugged in: {", ".join(sorted(here)) or "none"})')
        return label, here[label]

    def open(self, label, timeout=2.0):
        label, b = self.pick(label)
        return A.Adapter(b['port'], timeout=timeout)

    def reopen(self, label, old=None, wait=15.0, why='a reboot'):
        """After a reboot: close, wait for the port to come back and answer ++ver."""
        if old is not None:
            old.close()
        t0, last, seen = time.time(), None, []
        time.sleep(0.05 if self.sim else 0.5)
        while time.time() - t0 < wait:
            where = 'gone'
            try:
                if not self.sim and A.usb_devices(A.BOOT_VID, A.BOOT_PID):
                    where = 'BOOTSEL'
                b = self.present().get(label)
                if b:
                    where = 'port'
                    a = A.Adapter(b['port'], timeout=1.0)
                    reply = a.ask('++ver', 0.5)
                    if reply:
                        return a, time.time() - t0
                    where = 'port, silent'
                    a.close()
            except OSError as e:
                last, where = e, f'error: {e}'
            if not seen or seen[-1][1] != where:
                seen.append((round(time.time() - t0, 2), where))
            time.sleep(0.05 if self.sim else 0.2)
        self.reopen_log = seen
        raise StepFailed(f'board {label} did not come back within {wait:.0f} s after {why} ({last}); '
                         f'what it saw: {seen}')

    # -- records
    def write_state(self):
        self.state_path.write_text(json.dumps(self.state, indent=1, sort_keys=True) + '\n')

    def save(self, rec, stage=None):
        day = self.home / 'results' / rec['at'][:10]
        day.mkdir(parents=True, exist_ok=True)
        name = f"{rec['at'][11:].replace(':', '')}_{rec['step']}_{rec['board'].replace('+', '_')}" \
               f"{'_sim' if rec['sim'] else ''}.json"
        (day / name).write_text(json.dumps(rec, indent=1) + '\n')
        rec['file'] = str((day / name).relative_to(self.home))
        if stage:
            for label in rec['board'].split('+'):
                for b in self.state['boards'].values():
                    if b['label'] == label:
                        b['stages'][stage] = {'ok': rec['ok'], 'at': rec['at'], 'file': rec['file']}
                        b.pop('new', None)
            self.write_state()
        if not self.sim:
            log_entry(self, rec)
            (self.home / 'STATUS.md').write_text(status_text(self))
        return rec


def park(a):
    """Off the bus, and stay off it at the next plug-in, until a step says otherwise.
    The settings a step used for itself go back to the firmware's defaults first: what
    is saved in the board must be what a Prologix program expects to find."""
    for c in ('++savecfg 0', '++addr 1', '++auto 0', '++eoi 1', '++eos 0', '++eot_enable 0', '++eot_char 10',
              '++read_tmo_ms 500', '++savecfg 1', '++t autostart 0'):
        a.cmd(c)
    a.ask('++t raw off', 1.0)


def hexmask(s):
    return int(s, 16)


# ---- stage 1: the bare board on USB ---------------------------------------------------------------------
def step_bare(ctx, label=None):
    """A board with nothing on it but the USB cable (the plug need not be soldered yet).

    What it settles: the firmware runs and says which board it is on; the 3.3 V rail, by
    the chip's own temperature sensor; the crystal, against this PC's clock; the 5 V
    switch, both transceivers' receive paths and every joint between them and the
    RP2354A, by the self-test; settings in flash; a reboot; the bus capture on core 1.
    """
    label, b = ctx.pick(label)
    rec = Rec('bare', label, bool(ctx.sim))
    rec['serial'], rec['kind'] = b['serial'], b['kind']
    a = ctx.open(label)
    try:
        # which firmware, on which board
        ver = a.ask('++ver')
        rec['ver'] = ver
        lite = 'Lite' in b['kind']
        rec.check('++ver names the firmware', ver.endswith(E.VERSION) and ver.startswith('GPiBridge'), ver,
                  f'GPiBridge ... version {E.VERSION}')
        rec.check('the firmware read the board it is on (R21 on DC)', ('Lite' in ver) == lite, ver, b['kind'])
        info = rec['info'] = a.json('++t info')
        lo, hi = E.temp_raw_window()
        raw = info.get('temp_raw', 0)
        rec['rail_3v3_implied'] = round(E.rail_from_temp_raw(raw), 3) if raw else None
        rec.check('the 3.3 V rail, by the temperature sensor against it', lo <= raw <= hi, raw,
                  f'{lo}..{hi} (3.3 V within 3 %, die at {E.DIE_C[0]:.0f}-{E.DIE_C[1]:.0f} C)')
        rec.check('the system clock', info.get('sys_khz') == E.SYS_KHZ, info.get('sys_khz'), E.SYS_KHZ)
        rec.check('not restarted by the watchdog', info.get('watchdog_reset') == 0, info.get('watchdog_reset'), 0)
        if info.get('chip_rev') == 2:
            rec.note('RP2350 stepping A2: erratum E9 applies (the firmware carries the workaround)')
        st = rec['status'] = a.json('++t status')
        rec.check('reset to USB configured', E.USB_READY_MS[0] <= st['usb_ready_ms'] <= E.USB_READY_MS[1],
                  st['usb_ready_ms'], f'{E.USB_READY_MS[0]}..{E.USB_READY_MS[1]} ms')

        # the crystal: the board's microseconds against this PC's, a straight line through many readings
        span = 2.0 if (ctx.quick or ctx.sim) else 40.0
        xs, ys, t0 = [], [], time.time()
        while time.time() - t0 < span:
            t1 = time.monotonic()
            us = a.json('++t status')['us']
            t2 = time.monotonic()
            if t2 - t1 < 0.02:                     # a reading the USB did not hold up
                xs.append((t1 + t2) / 2)
                ys.append(us / 1e6)
            time.sleep(span / 60)
        mx, my = sum(xs) / len(xs), sum(ys) / len(ys)
        slope = sum((x - mx) * (y - my) for x, y in zip(xs, ys)) / sum((x - mx) ** 2 for x in xs)
        rec['crystal_ppm'] = round((slope - 1) * 1e6, 1)
        rec['crystal_readings'], rec['crystal_seconds'] = len(xs), round(xs[-1] - xs[0], 1)
        rec.check('the 12 MHz crystal against this PC', abs(rec['crystal_ppm']) < E.CRYSTAL_PPM
                  + (300 if ctx.quick or ctx.sim else 0), rec['crystal_ppm'], f'within {E.CRYSTAL_PPM:.0f} ppm')

        # the self-test: nothing must be plugged into the GPIB side
        self_test(a, rec, lite)

        # the bus on and off (the green BUS LED follows; on GPiBridge it is lit by the 5 V itself)
        a.cmd('++t power 1')
        on = a.json('++t status')
        a.cmd('++t power 0')
        off = a.json('++t status')
        rec.check('++t power 1, then 0', (on['bus'], off['bus']) == ('controller', 'off'), [on['bus'], off['bus']],
                  ['controller', 'off'])

        # nobody is there: a write must say so (and the red ERR LED lights for a second)
        a.cmd('++t power 1')
        before = a.json('++t status')['no_listener']
        a.write(30, b'*IDN?')
        time.sleep(0.05)
        after = a.json('++t status')['no_listener']
        rec.check('a write to an empty bus is counted as "no listener"', after == before + 1, after - before, 1)

        # a setting kept in flash through a reboot: before the capture runs, since until 0.4.1 only a capture
        # made the flash writable (it started core 1; bringup/REVB.md 2.9)
        a.cmd('++savecfg 1')
        a.cmd('++addr 7')
        time.sleep(0.1 if ctx.sim else 2.6)        # the firmware writes 2 s after the last change
        a.cmd('++rst')
        a, back = ctx.reopen(label, a, why='++rst')
        rec['reboot_s'] = round(back, 2)
        kept = a.ask('++addr')
        rec.check('a setting survives a reboot (flash)', kept == '7', kept, '7')
        a.cmd('++addr 1')
        st = a.json('++t status')
        rec['usb_ready_ms_after_reboot'] = st['usb_ready_ms']
        rec.check('no settings write refused by the flash', st.get('settings_errors', 0) == 0,
                  st.get('settings_errors'), 0)
        # the capture: core 1 records the bus while it restarts; IFC's pulse says the timer is right
        a.cmd('++t power 0')
        a.ask('++t capture start', 1.0)
        a.cmd('++t power 1')
        a.cmd('++t capture dump')
        vcd = []
        t_end = time.time() + 5
        while time.time() < t_end:
            line = a.line(1.0)
            vcd.append(line)
            if line.strip() == '$comment end $end':
                break
        pulses = vcd_low_pulses('\n'.join(vcd), 'IFC')
        rec['capture_changes'] = sum(1 for x in vcd if x.startswith('#'))
        rec['ifc_pulse_us'] = [round(p, 1) for p in pulses]
        # (the first low is the bus still unpowered when the capture began; the last is the pulse)
        rec.check('the capture saw the bus start: IFC asserted for the time the firmware holds it',
                  len(pulses) == 2 and E.IFC_US[0] <= pulses[-1] <= E.IFC_US[1], rec['ifc_pulse_us'],
                  f'unpowered, then one pulse of {E.IFC_US[0]:.0f}..{E.IFC_US[1]:.0f} us')


        if not ctx.sim:
            console_port(ctx, label, a, rec)
            a = ctx.open(label)
            a = bootsel_round_trip(ctx, label, a, rec)
        a.cmd('++t identify 0')
        park(a)
        time.sleep(0.1 if ctx.sim else 2.6)
        parked = a.json('++t status')
        rec.check('parked: off the bus, and told to stay off it', (parked['bus'], parked['autostart']) == ('off', 0),
                  [parked['bus'], parked['autostart']], ['off', 0])
    finally:
        a.close()
    return ctx.save(rec, 'bare')


def self_test(a, rec, lite):
    """++t selftest, read against what a good board says, line by line."""
    lines = a.json_until('++t selftest', 'selftest', 'done', timeout=15)
    rec['selftest'] = lines
    done = lines[-1]
    trouble = []
    for d in lines[:-1]:
        if lite:
            if d['selftest'] == 'float':
                if hexmask(d['up']):
                    trouble.append(f"held low with nothing on the bus: {' '.join(A.names(hexmask(d['up'])))}")
                if hexmask(d['down']) != 0xffff:
                    rec.note('some lines stay high against the pads\' pull-downs ('
                             + ' '.join(A.names(0xffff ^ hexmask(d['down'])))
                             + '): something with terminations is on the bus')
            elif d['selftest'] == 'walk' and 'line' in d:
                trouble.append(f"asserting {d['line']} gave {' '.join(A.names(hexmask(d['read']))) or 'nothing'}")
        elif d['selftest'] == 'off':
            high = 0xffff ^ hexmask(d['down'])
            if high:
                trouble.append('with the 5 V switched off these pins stayed high (the switch Q1 did not open, or '
                               f"something drives them): {' '.join(A.names(high))}")
        else:
            reads = hexmask(d['reads'])
            follows = hexmask(d['down']) & ~hexmask(d['up']) & reads      # low only on the pull-down
            low = hexmask(d['up']) & reads                                 # low whatever the pull
            if follows:
                trouble.append(f"{d['selftest']}: pins that follow the pad's pull, so nothing drives them (an open "
                               f"joint, a dead channel, or no 5 V): {' '.join(A.names(follows))}")
            if low:
                trouble.append(f"{d['selftest']}: lines read asserted with nothing on the bus (a short to ground, "
                               f"a bridge, or something plugged in): {' '.join(A.names(low))}")
    rec['selftest_trouble'] = trouble
    rec.check('the self-test (5 V switch, receive paths, joints' + ('' if not lite else ': the Lite, pin against pin')
              + ')', done.get('ok') is True and not trouble, trouble or 'ok', 'ok')


def vcd_low_pulses(vcd, name):
    """The widths, in microseconds, of the low pulses of one signal in a VCD."""
    ident, scale_ns, t, level, since, out = None, 10.0, 0, None, None, []
    for line in vcd.splitlines():
        line = line.strip()
        m = re.match(r'\$timescale\s+(\d+)\s*(ns|us|ps)', line)
        if m:
            scale_ns = int(m.group(1)) * {'ps': 1e-3, 'ns': 1.0, 'us': 1e3}[m.group(2)]
        m = re.match(r'\$var wire 1 (\S+) (\S+) \$end', line)
        if m and m.group(2).split('.')[-1] == name:
            ident = m.group(1)
        if line.startswith('#') and line[1:].isdigit():
            t = int(line[1:])
        elif ident and len(line) >= 2 and line[0] in '01' and line[1:] == ident:
            if line[0] == '0' and level != '0':
                since = t
            elif line[0] == '1' and level == '0' and since is not None:
                out.append((t - since) * scale_ns / 1000.0)
            level = line[0]
    return out


def console_port(ctx, label, a, rec):
    """The second serial port: the device reconnects with two, then with one again."""
    serial = ctx.pick(label)[1]['serial']
    a.cmd('++t console 1')
    a, _ = ctx.reopen(label, a, why='++t console 1')
    two = A.gpibridges().get(serial, {})
    line = ''
    if two.get('console'):
        with A.Adapter(two['console'], timeout=2.0) as c:
            line = c.ask('status')
    rec.check('++t console 1: a second serial port, which answers "status" in JSON',
              bool(two.get('console')) and line.startswith('{') and '"version"' in line, line[:80] or two, 'a JSON line')
    a.cmd('++t console 0')
    a, _ = ctx.reopen(label, a, why='++t console 0')
    one = A.gpibridges().get(serial, {})
    rec.check('++t console 0: one port again, as a Prologix', not one.get('console'), one.get('console'), None)
    rec.check('three deliberate reboots within 10 s (++rst, console on, off) are not taken for crashes',
              not A.usb_devices(A.BOOT_VID, A.BOOT_PID), 'in BOOTSEL' if A.usb_devices(A.BOOT_VID, A.BOOT_PID)
              else 'running', 'running')
    a.close()


def picotool():
    import shutil
    return shutil.which('picotool')


def picotool_reboot(tool, rec=None, tries=20):
    """picotool reboot into the firmware, to the one RP2350 in BOOTSEL.  The ROM's USB device
    shows in sysfs a moment before it answers (A1, 2026-11-16: the first call failed when made
    the instant it appeared), so this tries for a few seconds."""
    r = None
    for k in range(tries):
        devs = A.usb_devices(A.BOOT_VID, A.BOOT_PID)
        if devs:
            dev = devs[0]
            r = subprocess.run([tool, 'reboot', '--bus', open(f'{dev}/busnum').read().strip(), '--address',
                                open(f'{dev}/devnum').read().strip()], capture_output=True, text=True)
            if r.returncode == 0:
                if rec is not None and k:
                    rec.note(f'picotool reboot answered at try {k + 1}')
                return r
        time.sleep(0.25)
    return r or subprocess.CompletedProcess([tool], 1, '', 'no RP2350 in BOOTSEL')


def bootsel_round_trip(ctx, label, a, rec):
    """Into the ROM bootloader by software and back: how every later firmware gets in."""
    tool = picotool()
    if not tool:
        rec.note('no picotool on the PATH: the BOOTSEL round trip was skipped')
        return a
    before = set(A.usb_devices(A.BOOT_VID, A.BOOT_PID))
    a.cmd('++t bootsel')
    a.close()
    t0, new = time.time(), set()
    while time.time() - t0 < 10 and not new:
        time.sleep(0.2)
        new = set(A.usb_devices(A.BOOT_VID, A.BOOT_PID)) - before
    rec.check('++t bootsel: the RP2354A appears in its ROM bootloader', bool(new), sorted(new), 'one RP2350 Boot device')
    if not new:
        raise StepFailed(f'board {label} did not appear in BOOTSEL; it may need its USB cable replugged')
    dev = new.pop()
    where = ['--bus', open(f'{dev}/busnum').read().strip(), '--address', open(f'{dev}/devnum').read().strip()]
    time.sleep(0.5)                                # the ROM answers a moment after it appears
    r = subprocess.run([tool, 'info', '-a'] + where, capture_output=True, text=True)
    rec['picotool_info'] = (r.stdout + r.stderr).strip().splitlines()
    r = picotool_reboot(tool, rec)
    rec.check('picotool reboot: back into the firmware', r.returncode == 0, (r.stdout + r.stderr).strip()[-120:], 'ok')
    a, back = ctx.reopen(label, why='picotool reboot')
    rec['bootsel_back_s'] = round(back, 2)
    return a


# ---- the watchdog's failsafe ---------------------------------------------------------------------------------
def step_failsafe(ctx, label=None):
    """The way every bad firmware image gets replaced with nobody at the bench: a hang is
    caught by the watchdog (2 s), and the third timeout in a row starts the ROM bootloader.
    `++t crash` hangs on purpose.  Then picotool boots the image again, and a deliberate
    reboot must not count (bringup/REVB.md 2.8).  The board's own; not simulated."""
    if ctx.sim:
        raise StepFailed("the watchdog is the board's own: this step is not simulated")
    tool = picotool()
    if not tool:
        raise StepFailed('picotool is not on the PATH')
    label, b = ctx.pick(label)
    rec = Rec('failsafe', label, False)
    a = ctx.open(label)
    up = a.json('++t info')['uptime_ms']
    if up < 11000:                                 # the count of timeouts clears 10 s after a start
        time.sleep((11000 - up) / 1000)
    rounds = rec['rounds'] = []
    for n in (1, 2, 3):
        a.cmd('++t crash')
        t0, t_gone, where = time.time(), None, None
        a.close()                                  # blocks until the board is gone: the kernel waits on it
        while time.time() - t0 < 12:
            boot = A.usb_devices(A.BOOT_VID, A.BOOT_PID)
            running = ctx.present().get(label)
            # gone: the USB device itself (its serial port's link comes and goes with udev's work)
            if t_gone is None and not A.usb_devices(A.VID, A.PID) and not boot:
                t_gone = time.time() - t0
            if boot and t_gone is not None:
                where = 'BOOTSEL'
                break
            if running and t_gone is not None:
                try:
                    a = A.Adapter(running['port'], timeout=1.0)
                    info = a.json('++t info', 1.0)
                    where = 'running'
                    break
                except (OSError, ValueError):
                    pass
            time.sleep(0.05)
        rounds.append({'crash': n, 'gone_after_s': None if t_gone is None else round(t_gone, 2), 'then': where,
                       'watchdog_reset': info.get('watchdog_reset') if where == 'running' else None})
        want = 'BOOTSEL' if n == 3 else 'running'
        rec.check(f'hang {n}: the watchdog restarts the board ' + ('into the ROM bootloader' if n == 3 else
                  'into the firmware, which says why'),
                  where == want and t_gone is not None and 1.5 <= t_gone <= 4.0
                  and (n == 3 or info.get('watchdog_reset') == 1), rounds[-1], f'{want}, after 2 s')
        if where != 'running':
            break
    if A.usb_devices(A.BOOT_VID, A.BOOT_PID):
        r = picotool_reboot(tool, rec)
        rec.check('picotool reboot answered', r.returncode == 0, (r.stdout + r.stderr).strip()[-160:], 'ok')
        a, back = ctx.reopen(label, why='picotool reboot')
        info = a.json('++t info')
        rec.check('picotool boots the image again, and that is not counted as a crash',
                  info['watchdog_reset'] == 0, info['watchdog_reset'], 0)
    park(a)
    a.close()
    return ctx.save(rec, 'failsafe')


# ---- loading the firmware -------------------------------------------------------------------------------
def firmware_uf2():
    builds = sorted(ROOT.glob('firmware/build*/gpibridge.uf2'), key=lambda p: p.stat().st_mtime)
    if not builds:
        raise StepFailed('no firmware/build*/gpibridge.uf2: run `python3 bringup/run.py build`')
    return builds[-1]


def step_flash(ctx, label=None):
    """The newest firmware build into every RP2354A waiting in its ROM bootloader (a blank
    board starts there), or into the running board named."""
    if ctx.sim:
        raise StepFailed('a simulated board has no flash to load')
    tool = picotool()
    if not tool:
        raise StepFailed('picotool is not on the PATH')
    uf2 = firmware_uf2()
    rec = Rec('flash', label or 'new', False)
    rec['uf2'] = str(uf2.relative_to(ROOT))
    rec['uf2_built'] = datetime.fromtimestamp(uf2.stat().st_mtime).strftime('%Y-%m-%d %H:%M:%S')
    if label:
        a = ctx.open(label)
        rec['was'] = a.ask('++ver')
        a.cmd('++t bootsel')
        a.close()
        time.sleep(2.0)
    before = set(A.gpibridges())
    boots = A.usb_devices(A.BOOT_VID, A.BOOT_PID)
    rec.check('an RP2354A is waiting in its ROM bootloader (2e8a:000f)', bool(boots), len(boots), 'one or more')
    loaded = []
    for dev in boots:
        where = ['--bus', open(f'{dev}/busnum').read().strip(), '--address', open(f'{dev}/devnum').read().strip()]
        i = subprocess.run([tool, 'info', '-d'] + where, capture_output=True, text=True)
        r = subprocess.run([tool, 'load', '-v', '-x', str(uf2)] + where, capture_output=True, text=True)
        loaded.append({'at': dev.split('/')[-1], 'device': (i.stdout + i.stderr).strip().splitlines(),
                       'load': (r.stdout + r.stderr).strip().splitlines()[-4:], 'ok': r.returncode == 0})
        rec.check(f'picotool load and verify, USB {dev.split("/")[-1]}', r.returncode == 0,
                  (r.stdout + r.stderr).strip()[-160:], 'ok')
    rec['loaded'] = loaded
    time.sleep(3.0)
    here = ctx.present()
    labels = []
    for lab, b in sorted(here.items()):
        if label not in (None, lab) and b['serial'] in before:
            continue
        with A.Adapter(b['port']) as a:
            ver = a.ask('++ver')
            if b['serial'] not in before or lab == label:
                labels.append(lab)
                rec.check(f'{lab} ({b["serial"]}) runs the new firmware', ver.endswith(E.VERSION), ver, E.VERSION)
                a.cmd('++t identify 120')
                park(a)
    rec['boards'] = labels
    rec['board'] = '+'.join(labels) or rec['board']
    return ctx.save(rec, 'flash')


# ---- stage 1b: the rails, with one scope probe touched to each test point --------------------------------
def step_rails(ctx, label, probe, patience=300.0):
    """The hand holds the probe on each test point in turn, in any order; the step says
    which rail it is by its voltage (and tells +5V_GPIB from VBUS by switching the bus
    off for a moment), records it and its ripple, and makes the scope beep.  It ends
    when all four are in (three on the Lite, which has no +5V_GPIB), or after `patience`."""
    label, b = ctx.pick(label)
    lite = 'Lite' in b['kind']
    rec = Rec('rails', label, bool(ctx.sim))
    want = [r for r in E.RAILS if not (lite and r == '+5V_GPIB')]
    got = rec['rails'] = {}
    a = ctx.open(label)
    try:
        a.cmd('++t power 1')                       # the transceivers on: the load the rails must carry
        t_end = time.time() + patience
        while time.time() < t_end and len(got) < len(want):
            v = probe.dc()
            rail = None
            if 0.9 < v < 1.3:
                rail = '+1V1'
            elif 2.9 < v < 3.7:
                rail = '+3V3'
            elif 4.0 < v < 5.6:
                if lite:
                    rail = 'VBUS'
                else:                              # which 5 V: does it follow the bus power?
                    a.cmd('++t power 0')
                    a.json('++t status')
                    time.sleep(0.02 if ctx.sim else 0.3)
                    v_off = probe.dc()
                    a.cmd('++t power 1')
                    a.json('++t status')
                    time.sleep(0.02 if ctx.sim else 0.3)
                    rail = '+5V_GPIB' if v_off < 1.0 else 'VBUS' if v_off > 4.0 else None
                    if rail == '+5V_GPIB':
                        got.setdefault(rail, {})['off_V'] = round(v_off, 3)
            if rail is None or 'V' in got.get(rail, {}):
                continue
            again = probe.dc()                     # still on it, and steady?
            if abs(again - v) > 0.05:
                continue
            entry = got.setdefault(rail, {})
            entry['V'] = round((v + again) / 2, 3)
            for tdiv, key in ((200e-9, 'fast'), (20e-6, 'slow')):
                t, w = probe.ripple(tdiv)
                mean = sum(w) / len(w)
                entry[f'ripple_{key}_mVpp'] = round((max(w) - min(w)) * 1e3, 1)
                entry[f'ripple_{key}_mVrms'] = round((sum((x - mean) ** 2 for x in w) / len(w)) ** 0.5 * 1e3, 2)
            probe.beep(2 if len([r for r in got if 'V' in got[r]]) == len(want) else 1)
            ctx.say(f'  {rail} ({E.RAILS[rail][0]}): {entry["V"]:.3f} V, ripple {entry["ripple_fast_mVpp"]} mV pp')
        for rail in want:
            tp, lo, hi = E.RAILS[rail]
            v = got.get(rail, {}).get('V')
            rec.check(f'{rail} at {tp}', v is not None and lo <= v <= hi, v, f'{lo}..{hi} V')
        if '+1V1' in got and 'V' in got['+1V1']:
            r = max(got['+1V1']['ripple_fast_mVpp'], got['+1V1']['ripple_slow_mVpp'])
            rec.check('+1V1 ripple with the bus on (rev A\'s substituted, unpolarised L1)', r <= E.RIPPLE_1V1_MVPP, r,
                      f'at most {E.RIPPLE_1V1_MVPP:.0f} mV pp')
        if '+5V_GPIB' in got:
            rec.check('+5V_GPIB falls when the bus is switched off (Q1 opens)',
                      got['+5V_GPIB'].get('off_V', 9) < 1.0, got['+5V_GPIB'].get('off_V'), 'under 1 V')
        park(a)
    finally:
        a.close()
    return ctx.save(rec, 'rails')


def step_meter(ctx, label, readings, ripple_mvpp=None, notes=()):
    """Stage 1b with a hand meter instead of a scope: the numbers a person read off it
    (black lead on J1's shell or TP5), checked against the same windows as `rails`.

    readings: {'TP1': 5.159, 'TP4': 5.144, 'TP4off': 0.0, ...}, in volts.  A plain name
    is a reading with the bus on (the green LED lit: `run.py ask A1 "++t power 1"` first,
    since every step leaves a board parked with it off); a name ending in 'off' is one
    with the bus off.  TP1-TP3 hardly move with the bus, so either serves for their
    window; the bus-on one is used when both are there.  TP4 needs both: +5V_GPIB in its
    window with the bus on, and under 1 V with it off (Q1 opens; nothing back-powers it).
    A meter cannot see the ripple on +1V1, which is the question about rev A's
    substituted L1: ripple_mvpp is a scope's figure if one was taken, else the record
    says the question is still open."""
    label, b = ctx.pick(label)
    lite = 'Lite' in b['kind']
    tps = {tp: rail for rail, (tp, _, _) in E.RAILS.items() if not (lite and rail == '+5V_GPIB')}
    bad = [k for k in readings if k.removesuffix('off') not in tps]
    if bad:
        raise StepFailed(f'not a test point of {label}: {", ".join(bad)} (it has {", ".join(sorted(tps))}, '
                         'and each with "off" for a reading with the bus off)')
    rec = Rec('rails', label, bool(ctx.sim))
    rec['method'] = 'hand meter'
    got = rec['rails'] = {}
    for tp, rail in sorted(tps.items()):
        on, off = readings.get(tp), readings.get(tp + 'off')
        entry = got[rail] = {}
        if on is not None:
            entry['V'] = on
        if off is not None:
            entry['off_V'] = off
        _, lo, hi = E.RAILS[rail]
        v = on if (on is not None or rail == '+5V_GPIB') else off
        rec.check(f'{rail} at {tp}' + (', bus on' if rail == '+5V_GPIB' else ''),
                  v is not None and lo <= v <= hi, v, f'{lo}..{hi} V')
    if '+5V_GPIB' in got:
        off = got['+5V_GPIB'].get('off_V')
        rec.check('+5V_GPIB falls when the bus is switched off (Q1 opens)', off is not None and off < 1.0, off,
                  'under 1 V')
    if ripple_mvpp is not None:
        got['+1V1']['ripple_mVpp'] = ripple_mvpp
        rec.check('+1V1 ripple (a scope\'s figure, rev A\'s substituted L1)', ripple_mvpp <= E.RIPPLE_1V1_MVPP,
                  ripple_mvpp, f'at most {E.RIPPLE_1V1_MVPP:.0f} mV pp')
    else:
        rec.note('+1V1 ripple not measured (a meter cannot): the question about the substituted L1 stays open')
    for n in notes:
        rec.note(n)
    return ctx.save(rec, 'rails')


# ---- stage 2: the plug soldered ---------------------------------------------------------------------------
def step_plug(ctx, label=None):
    """After the plug is soldered, with nothing plugged into it: the self-test again.  A
    solder bridge from a contact to ground, or to a neighbour that a transceiver drives,
    shows as a line read asserted.  What it cannot see is the far side of each joint: an
    open joint, two data lines bridged, or the plug turned round.  Stage 2b or 3 sees
    those; the meter check (HANDBOOK.md section 1, step 5) is for the last."""
    label, b = ctx.pick(label)
    rec = Rec('plug', label, bool(ctx.sim))
    with ctx.open(label) as a:
        self_test(a, rec, 'Lite' in b['kind'])
        park(a)
    rec.note('not seen from here: an open joint at the plug, two DIO lines bridged, the plug turned round')
    return ctx.save(rec, 'plug')


# ---- stage 2b: two boards on one GPIB cable, every line both ways ----------------------------------------
def step_pair(ctx, label_x, label_y):
    """Two boards joined by a GPIB cable (or one plugged into the other through a cable's
    stacking connector), nothing else on it.  One board asserts each line alone, the
    other must read exactly that line; then the other way.  That walks every bus
    driver, every receiver and every plug joint of both boards, and it names an open
    joint, a bridge between two contacts, or a plug soldered in turned round."""
    rec = Rec('pair', f'{label_x}+{label_y}', bool(ctx.sim))
    ax, ay = ctx.open(label_x), ctx.open(label_y)
    faults = rec['faults'] = []
    try:
        for a in (ax, ay):
            park(a)                                # both off the bus before either takes a role
        rec['kinds'] = {label_x: ctx.present()[label_x]['kind'], label_y: ctx.present()[label_y]['kind']}
        walked = set()
        for pe in (1, 0):                          # the SN75160B's drivers totem-pole, then open-collector
            for role_x, role_y in (('ctrl_talk', 'dev_listen'), ('dev_listen', 'ctrl_talk')):
                # the one that will be the controller takes its role last, the other is a device already
                first, second = ((ay, role_y), (ax, role_x)) if role_x.startswith('ctrl') else ((ax, role_x), (ay, role_y))
                for a, role in (first, second):
                    a.json('++t raw dev_listen')
                first[0].json(f'++t raw {first[1]}')
                second[0].json(f'++t raw {second[1]}')
                for a in (ax, ay):
                    a.json(f'++t raw pe {pe}')
                sx, sy = ax.json('++t raw get'), ay.json('++t raw get')
                rest_x, rest_y = hexmask(sx['lines']) & hexmask(sx['reads']), hexmask(sy['lines']) & hexmask(sy['reads'])
                if rest_x or rest_y:
                    faults.append({'what': 'asserted at rest', 'roles': [role_x, role_y], 'pe': pe,
                                   label_x: A.names(rest_x), label_y: A.names(rest_y)})
                for (src, s, s_label), (dst, d, d_label) in (((ax, sx, label_x), (ay, sy, label_y)),
                                                              ((ay, sy, label_y), (ax, sx, label_x))):
                    can = hexmask(s['drives']) & hexmask(d['reads'])
                    for bit in range(16):
                        if not can >> bit & 1:
                            continue
                        src.json(f'++t raw set 0x{1 << bit:04x}')
                        got = hexmask(dst.json('++t raw get')['lines']) & hexmask(d['reads'])
                        own = hexmask(src.json('++t raw get')['lines']) & hexmask(s['reads']) & ~(1 << bit)
                        src.json('++t raw set 0x0000')
                        walked.add((s_label, d_label, A.LINES[bit]))
                        if got != 1 << bit or own:
                            faults.append({'what': 'walk', 'from': s_label, 'to': d_label, 'line': A.LINES[bit],
                                           'pe': pe, 'read': A.names(got), 'echo': A.names(own)})
        rec['walked'] = len(walked)
        rec.check('every line walked both ways', len(walked) == 32, len(walked), 32)
        rec['diagnosis'] = diagnose_pair(faults, label_x, label_y)
        rec.check('each line asserted alone is read alone at the other board', not faults,
                  rec['diagnosis'] or 'ok', 'ok')
    finally:
        for a in (ax, ay):
            try:
                park(a)
            finally:
                a.close()
    if ctx.sim:
        rec['sim_stats'] = ctx.sim.stats()
        rec.check('no two drivers ever opposed on a line, and no pin rule broken (simulation)',
                  all(v['fights'] == 0 and v['breaches'] == 0 for v in rec['sim_stats'].values()), rec['sim_stats'],
                  'none')
    return ctx.save(rec, 'pair')


def diagnose_pair(faults, label_x, label_y):
    """What the faults of a two-board walk mean, in words."""
    if not faults:
        return []
    out = []
    rest = [f for f in faults if f['what'] == 'asserted at rest']
    stuck = set()
    for f in rest:
        stuck |= set(f[label_x]) | set(f[label_y])
    # a plug turned round puts a ground pad on each of these contacts' lines, and they read low for ever
    turned = {'DIO1', 'DIO2', 'DIO3', 'DIO4', 'DIO5', 'EOI', 'DAV', 'NRFD'}
    if len(stuck & turned) >= 6:
        out.append('Most of DIO1-5, EOI, DAV and NRFD read asserted with nothing driving them: that is the mark of '
                   'a plug soldered in TURNED ROUND (its ground contacts sit on those lines). On each board, the '
                   'contacts on the D\'s narrow side should be the ones that read 0 ohms to GND, seven of them from '
                   'the USB-C end (HANDBOOK.md section 1, step 5).')
        return out                                 # everything else the walk saw follows from that
    elif stuck:
        out.append(f'Asserted with nothing driving them: {" ".join(sorted(stuck))} (a short to ground at a plug, or '
                   'something else on the cable).')
    walks = [f for f in faults if f['what'] == 'walk']
    dead = {}
    for f in walks:
        if not f['read']:
            dead.setdefault(f['line'], set()).add((f['from'], f['to']))
        elif set(f['read']) != {f['line']}:
            extra = sorted(set(f['read']) - {f['line']})
            missing = f['line'] not in f['read']
            if extra and not missing:
                c = [f"{x} (contact {A.CONTACT[x]})" for x in [f['line']] + extra]
                out.append(f"{f['line']} asserted by {f['from']} also asserted {' '.join(extra)} at {f['to']}: "
                           f"a bridge between {' and '.join(c)}.")
            else:
                out.append(f"{f['line']} asserted by {f['from']} read as {' '.join(f['read'])} at {f['to']}: "
                           "lines crossed (a plug turned round, or the wrong cable).")
    for line, ways in sorted(dead.items()):
        if len(ways) == 2:
            out.append(f'{line} (contact {A.CONTACT[line]}) passes neither way: an open joint at that contact on '
                       'one of the two plugs, or a broken cable wire.')
        else:
            (frm, to), = ways
            out.append(f'{line} (contact {A.CONTACT[line]}) passes from {to} to {frm} but not from {frm} to {to}: '
                       f"{frm}'s driver or {to}'s receiver for that line (or its joint at the transceiver).")
    return list(dict.fromkeys(out))


# ---- stage 3: the bench Prologix as a device: both ends of the bus on this PC ------------------------------
def step_prologix(ctx, label=None, device_address=5, prologix_port=None):
    """The bench Prologix in DEVICE mode on the same cable (its manual, section 6.2: what
    it hears on GPIB it passes to USB unbuffered; one message from USB waits in it until
    it is addressed to talk).  So every byte value can be sent each way and compared, EOI
    and all, and SRQ and the serial poll are under this script's control.

    NOT SIMULATED: there is no Prologix to simulate.  Both ends are on USB, so this step
    is worked out on the day with nobody at the bench."""
    import random
    if ctx.sim:
        raise StepFailed('there is no simulated Prologix: this step needs the real one')
    label, b = ctx.pick(label)
    ports = [prologix_port] if prologix_port else A.prologix_ports()
    if len(ports) != 1:
        raise StepFailed(f'{len(ports)} Prologix adapters on USB: one is wanted')
    rec = Rec('prologix', label, False)
    rec['prologix'] = os.path.basename(ports[0])
    p, g = A.Adapter(ports[0]), ctx.open(label)
    try:
        # the Prologix a device BEFORE this board takes the bus: two controllers would fight
        for c in ('++savecfg 0', '++mode 0', f'++addr {device_address}', '++eoi 1', '++eos 3', '++eot_enable 0',
                  '++lon 0', '++status 0'):
            p.cmd(c)
        rec['prologix_ver'] = p.ask('++ver')
        rec.check('the Prologix is a device', p.ask('++mode') == '0', None, '0')
        g.controller()
        g.cmd('++eos 3')                           # nothing appended: the bytes sent are the bytes that arrive
        g.cmd('++t power 1')
        st = g.json('++t status')
        rec.check('this board took the bus (nobody else holds ATN, REN or IFC)', st['bus'] == 'controller', st['bus'],
                  'controller')
        values = list(range(256))
        random.shuffle(values)
        bad_out, bad_in = [], []
        for i in range(0, 256, 32):
            chunk = bytes(values[i:i + 32])
            p.drain(0.05)
            g.write(device_address, chunk)         # to the device: it must pass on exactly these
            got, t_end = b'', time.time() + 2
            while len(got) < len(chunk) and time.time() < t_end:
                got += p.recv(0.2)
            if got != chunk:
                bad_out.append({'sent': chunk.hex(), 'arrived': got.hex()})
            p.send(A.Adapter.escape(chunk) + b'\n')    # from the device: it waits to be addressed to talk
            time.sleep(0.05)
            got = g.read_eoi(3.0)
            if got != chunk:
                bad_in.append({'sent': chunk.hex(), 'arrived': got.hex()})
        rec['bad_out'], rec['bad_in'] = bad_out[:4], bad_in[:4]
        rec.check('every byte value, to the device, arrives as sent', not bad_out, len(bad_out), 0)
        rec.check('every byte value, from the device, arrives as sent, ended by its EOI', not bad_in, len(bad_in), 0)
        p.cmd('++status 72')                       # RQS set: the device asserts SRQ
        time.sleep(0.1)
        srq = g.ask('++srq')
        poll = g.ask(f'++spoll {device_address}', 3.0)
        after = g.ask('++srq')
        rec.check('SRQ seen, the serial poll reads the status byte, and SRQ is gone after it',
                  (srq, poll, after) == ('1', '72', '0'), [srq, poll, after], ['1', '72', '0'])
        before = g.json('++t status')['timeouts']
        g.cmd('++read_tmo_ms 200')
        t0 = time.time()
        nothing = g.read_eoi(1.5)
        rec['empty_read_s'] = round(time.time() - t0, 2)
        rec.check('a read with nothing to read ends by its timeout, and is counted',
                  nothing == b'' and g.json('++t status')['timeouts'] == before + 1, nothing.hex(), '')
        park(g)
    finally:
        p.cmd('++mode 0')                          # the Prologix stays a device: never a second controller here
        p.close()
        g.close()
    rec.note('the bench Prologix was left in device mode, unsaved: lab-instrument-control sets ++mode 1 when it opens it')
    return ctx.save(rec, 'prologix')


# ---- stage 4: a real instrument, through lab-instrument-control's own driver ------------------------------
def step_gen(ctx, label=None, address=10, points=16000):
    """The HP 33120A at `address`, driven by lab-instrument-control's hp_33120A.py through
    the adapter exactly as it is through the Prologix: identity, settings read back, a
    setting the generator must refuse, a binary arbitrary waveform of 1000 points and one
    of 16,000 (32 kB in one line, ended by EOI), the queries per second, a serial poll
    and a capture of *IDN? read by sigrok's decoder."""
    import random
    import bench
    label, b = ctx.pick(label)
    rec = Rec('gen', label, bool(ctx.sim))
    rec['address'] = address
    with ctx.open(label) as a:
        a.cmd('++savecfg 0')
        a.cmd('++t power 1')
        st = a.json('++t status')
        rec.check('on the bus as the controller', st['bus'] == 'controller', st['bus'], 'controller')
        errors_before = (st['timeouts'], st['no_listener'])
    gen = None
    try:
        gen = bench.hp33120a(b['port'], address, timeout=20.0)
        rec['idn'] = gen.idn
        rec.check('*IDN? through lab-instrument-control', '33120A' in gen.idn, gen.idn, '...33120A...')
        w = gen.sine(1234.5, 0.8, 0.1)
        rec.check('a sine set and read back', (w['function'], w['freq'], w['vpp'], w['offset']) == ('SIN', 1234.5, 0.8, 0.1),
                  w, 'SIN 1234.5 Hz 0.8 Vpp 0.1 V')
        w = gen.triangle(2e3, 1.0)
        rec.check('a triangle set and read back', w['function'] == 'TRI' and w['freq'] == 2e3, w, 'TRI 2 kHz')
        try:
            gen.sine(20e6, 1.0)
            refused = False
        except ValueError as e:
            refused = '-222' in str(e) or 'range' in str(e).lower()
        rec.check('20 MHz refused, with the generator\'s own error', refused, refused, True)
        rec.check('the error queue is empty afterwards', gen.errors() == [], None, [])
        for n in (1000, points):
            x = [random.uniform(-1, 1) for _ in range(n)]      # new samples every run: nothing stale can pass
            t0 = time.time()
            w = gen.arb(x, 100.0, 1.0)
            dt = time.time() - t0
            mean = sum(round(2047 * v) for v in x) / n / 2047
            got = gen.qf('DATA:ATTRibute:AVERage? VOLATILE')
            rec[f'arb_{n}_s'] = round(dt, 2)
            rec.check(f'{n} points uploaded in one binary line ({2 * n} bytes): the count and the average the '
                      'generator computed', w.get('points') == n and abs(got - mean) < 3e-4,
                      {'points': w.get('points'), 'average': got}, {'points': n, 'average': round(mean, 6)})
        t0, k = time.time(), 0
        while time.time() - t0 < (0.5 if ctx.sim else 3.0):
            gen.q('*IDN?')
            k += 1
        rec['queries_per_s'] = round(k / (time.time() - t0), 1)
        rec.note('through the Prologix the same loop runs at about 31 a second (lab-instrument-control, gpib/gpib.md)')
        gen.off()                                  # 0 V DC: the 33120A has no output switch
        gen.output(load=50)
    finally:
        if gen is not None:
            gen.close()
    with ctx.open(label) as a:
        a.controller()
        a.cmd(f'++addr {address}')
        spoll = a.ask(f'++spoll {address}', 3.0)
        rec.check('a serial poll answers with a status byte', spoll.isdigit(), spoll, 'a number')
        a.ask('++t capture start', 1.0)
        idn = a.query(address, '*IDN?', 3.0)
        a.cmd('++t capture dump')
        vcd, t_end = [], time.time() + 10
        while time.time() < t_end:
            line = a.line(1.0)
            vcd.append(line)
            if line.strip() == '$comment end $end':
                break
        path = ctx.home / 'results' / rec['at'][:10] / f"{rec['at'][11:].replace(':', '')}_gen_{label}_idn.vcd"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text('\n'.join(vcd) + '\n')
        rec['capture'] = str(path.relative_to(ctx.home))
        decoded = sigrok_bytes(path)
        if decoded is None:
            rec.note('no sigrok-cli: the capture was saved, not decoded')
        else:
            rec.check('sigrok\'s IEEE-488 decoder reads the capture as the query and its answer',
                      decoded == b'*IDN?\n' + idn.encode() + b'\n', decoded.decode(errors='replace'),
                      '*IDN?\\n' + idn + '\\n')
        a.cmd('++loc')
        st = a.json('++t status')
        rec.check('no timeout and no "no listener" in the whole step',
                  (st['timeouts'], st['no_listener']) == errors_before, [st['timeouts'], st['no_listener']],
                  list(errors_before))
        park(a)
    return ctx.save(rec, 'gen')


def sigrok_bytes(vcd_path):
    """The data bytes sigrok's ieee488 decoder finds in a capture; None without sigrok-cli."""
    import shutil
    sr = os.environ.get('SIGROK_CLI') or shutil.which('sigrok-cli')
    if not sr:
        return None
    show = subprocess.run([sr, '-I', 'vcd', '-i', str(vcd_path), '--show'], capture_output=True, text=True).stdout
    have = {m.split('.')[-1]: m for m in re.findall(r'^- (\S+): logic', show, re.M)}    # 'gpib.DIO1' on some versions
    chans = ':'.join(f'{n.lower()}={have.get(n, n)}' for n in A.LINES)
    r = subprocess.run([sr, '-I', 'vcd', '-i', str(vcd_path), '-P', 'ieee488:' + chans, '-B', 'ieee488=data'],
                       capture_output=True)
    return r.stdout


# ---- the log and the status page ---------------------------------------------------------------------------
def log_entry(ctx, rec):
    log = ctx.home / 'BRINGUP_LOG.md'
    if not log.exists():
        log.write_text('# GPiBridge rev A: the bring-up log\n\nOne entry a step, newest last, written by '
                       '`bringup/run.py`; the full record of each is the JSON file it names.\n')
    lines = [f"\n## {rec['at']}  `{rec['step']}` {rec['board']}: {'PASS' if rec['ok'] else 'FAIL'}\n",
             f"Record: `{rec.get('file', '')}`\n"]
    for c in rec['checks']:
        got = '' if c['ok'] else f" (got {json.dumps(c['got'])[:200]}, wanted {json.dumps(c['want'])[:120]})"
        lines.append(f"- {'ok  ' if c['ok'] else 'FAIL'} {c['what']}{got}")
    lines += [f'- note: {n}' for n in rec['notes']]
    with open(log, 'a') as f:
        f.write('\n'.join(lines) + '\n')


def status_text(ctx):
    """STATUS.md: where the bring-up stands, and the next thing to do at the bench."""
    boards = sorted(ctx.state['boards'].values(), key=lambda b: b['label'])
    present = {}
    try:
        present = ctx.present()
    except OSError:
        pass
    out = ['# GPiBridge bring-up: where we are', '',
           f"Written by `bringup/run.py` at {datetime.now().strftime('%Y-%m-%d %H:%M')}. `BRINGUP.md` is the plan; "
           '`BRINGUP_LOG.md` is what happened.', '']
    if not boards:
        out += ['No board has been plugged in yet.', '']
    else:
        out += ['| board | what it is | serial | plugged in now | ' + ' | '.join(STAGES) + ' |',
                '|---|---|---|---|' + '---|' * len(STAGES)]
        for b in boards:
            serial = next(s for s, x in ctx.state['boards'].items() if x is b)
            cells = []
            for s in STAGES:
                r = b['stages'].get(s)
                cells.append('' if r is None else ('pass ' if r['ok'] else '**FAIL** ') + r['at'][5:16])
            out.append(f"| **{b['label']}** | {b['kind']} | `{serial}` | {'yes' if b['label'] in present else 'no'} | "
                       + ' | '.join(cells) + ' |')
        out.append('')
    out += ['## Next at the bench', ''] + next_steps(ctx, boards, present) + ['']
    return '\n'.join(out)


def next_steps(ctx, boards, present):
    """The next physical thing, for the board that is furthest behind."""
    if not boards:
        return ['1. Take one assembled **GPiBridge** (the board with the two big chips marked SN75161B CONTROL and '
                'SN75160B DATA) out of its bag. Look at J1, the USB-C socket: its face should be flush with the '
                'board\'s short edge and its pins on their pads.',
                '2. Plug it into the bench PC `bell` with a USB-C **data** cable. Nothing else is connected.',
                '3. Tell Claude "A1 is plugged in". Claude runs `flash` and `bare`.']
    out = []
    for b in boards:
        lab, st = b['label'], b['stages']
        ok = lambda s: st.get(s, {}).get('ok')                              # noqa: E731
        lite = 'Lite' in b['kind']
        if any(s in st and not st[s]['ok'] for s in STAGES):
            bad = next(s for s in STAGES if s in st and not st[s]['ok'])
            out.append(f"- **{lab}**: `{bad}` FAILED ({st[bad]['file']}). Nothing to do at the bench until Claude has "
                       'read it; leave the board as it is.')
        elif not ok('bare'):
            out.append(f'- **{lab}**: USB-C to `bell`, nothing else. Claude runs `bare {lab}` (about 2 minutes).')
        elif not ok('failsafe'):
            out.append(f'- **{lab}**: stage 1 passed; Claude runs `failsafe {lab}` (20 s, nothing for you).')
        elif not ok('plug'):
            rails = '' if ok('rails') else ('(optional, 3 minutes) the rails, with a meter or one scope probe, '
                                            '`BRINGUP.md` stage 1b; then ')
            out.append(f'- **{lab}**: stage 1 passed{", and its rails" if ok("rails") else ""}. Next is yours: '
                       f'{rails}solder the plug, `BRINGUP.md` stage 2 (15 minutes): through a printed base if {lab} '
                       'is ever to be housed (once the plug is soldered, the base can no longer go on), bare if it '
                       f'is to be the bench board. Then its USB-C back into `bell`, and tell Claude "{lab} has its '
                       'plug".')
        elif not ok('gen'):
            out.append(f'- **{lab}**: its plug is on and checks alone. Next: plug {lab} into the back of the '
                       'HP 33120A (GPIB address 10, powered on), USB-C to `bell`, and tell Claude '
                       f'"{lab} is on the 33120A". ' + ('' if lite else 'Before that, if a second board with its plug '
                       'and a GPIB cable are at hand: stage 2b (`pair`). '))
        else:
            out.append(f'- **{lab}**: through stage 4. Next: stage 5, the dearer instruments, one at a time.')
    return out
