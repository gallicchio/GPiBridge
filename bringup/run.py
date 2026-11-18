#!/usr/bin/env python3
"""The bring-up of GPiBridge and GPiBridge Lite rev A, one step a call.  BRINGUP.md is the plan.

    python3 bringup/run.py                  where we are, and the next thing to do at the bench
    python3 bringup/run.py build            the firmware for the board, the host tests, the simulator
    python3 bringup/run.py usb              what is on USB that this bring-up cares about
    python3 bringup/run.py flash [BOARD]    the firmware into every board waiting in BOOTSEL (or the one named)
    python3 bringup/run.py bare [BOARD]     stage 1: a board with only its USB cable
    python3 bringup/run.py failsafe [BOARD] stage 1: three hangs in a row must land in BOOTSEL (not simulated)
    python3 bringup/run.py rails BOARD --scope sds1104 [--channel 1]
                                            stage 1b: one scope probe touched to TP1-TP4 in any order
    python3 bringup/run.py meter BOARD TP1=5.159 TP2=3.308 TP3=1.097 TP4=5.144 TP4off=0 [ripple=48.3]
                                            stage 1b with a hand meter: the numbers typed in, checked
                                            (TPn: bus on, green LED lit; TPnoff: bus off; ripple: mV pp
                                            on +1V1 from a scope, if one was used; --note TEXT)
    python3 bringup/run.py plug [BOARD]     stage 2: the plug soldered, nothing plugged into it
    python3 bringup/run.py pair X Y         stage 2b: two boards on one GPIB cable, every line both ways
    python3 bringup/run.py prologix [BOARD] stage 3: the bench Prologix as a device on the same cable (not simulated)
    python3 bringup/run.py gen [BOARD] [--address 10] [--scope sds2104 --channel 2]
                                            stage 4: the HP 33120A, through lab-instrument-control
                                            (--scope: its OUTPUT on that scope channel by coax: the
                                            scope also checks the sine and the 16,000 points played)
    python3 bringup/run.py speed BOARD --address N [--only SECTION ...] [--live]
                                            SPEED AND FAULT TESTS, not a stage (bringup/speed_faults.py):
                                            how fast, and how gracefully, against an E364xA or a 33120A
    python3 bringup/run.py identify BOARD   flash its yellow and red LEDs for a minute
    python3 bringup/run.py unpark BOARD     the bring-up over: take the bus at plug-in again, as shipped
    python3 bringup/run.py park BOARD       off the bus, the settings a Prologix program expects saved, autostart 0:
                                            as every step leaves it (after a session by hand, such as
                                            lab-instrument-control through the board)
    python3 bringup/run.py ask BOARD "++t status"     one command, its answer

BOARD is the label the bring-up gave the board when it first saw it (A1, A2: GPiBridge;
L1, L2: the Lite), written on the board with a marker.

--sim runs a step against simulated boards (firmware/test/sim_board), with nothing
written outside a scratch folder:
    python3 bringup/run.py --sim bare
    python3 bringup/run.py --sim pair A1 A2 --fault A2:open=DAV
    python3 bringup/run.py --sim gen
--quick shortens the crystal measurement of `bare` to 2 s.

Exit status: 0 a step passed, 1 a check failed, 2 the step could not run.
"""
import argparse
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(HERE))

import adapter as A            # noqa: E402
import steps as S              # noqa: E402


def build():
    """The firmware (into firmware/build-<this computer>), the host tests and sim_board."""
    host = os.uname().nodename.split('.')[0]
    out = ROOT / 'firmware' / f'build-{host}'
    env = dict(os.environ)
    # a compiler and a CMake that a PATH full of other toolchains may hide: the system's first
    env['PATH'] = '/usr/bin:/bin:' + env.get('PATH', '')
    pkg = Path.home() / '.local/lib/cmake/picotool'
    cfg = ['cmake', '-S', str(ROOT / 'firmware'), '-B', str(out), '-DPICO_TOOLCHAIN_PATH=/usr']
    if pkg.exists():
        cfg.append(f'-Dpicotool_DIR={pkg}')          # else the SDK fetches and builds its own
    for cmd in (cfg, ['cmake', '--build', str(out), '-j', '8'], ['make', '-C', str(ROOT / 'firmware/test')]):
        print('$', ' '.join(cmd), flush=True)
        r = subprocess.run(cmd, env=env, capture_output=True, text=True)
        tail = [x for x in (r.stdout + r.stderr).splitlines() if 'warning' in x or 'error' in x or 'checks' in x
                or 'checked' in x or 'sigrok' in x or 'Built target' in x]
        print('\n'.join('  ' + x for x in tail[-12:]))
        if r.returncode:
            print((r.stdout + r.stderr)[-2000:])
            return 1
    print(f'firmware: {(out / "gpibridge.uf2").relative_to(ROOT)}')
    return 0


def usb():
    here = A.gpibridges()
    for serial, d in sorted(here.items()):
        print(f'GPiBridge   {d["product"]:26s} serial {serial}  gpib {d["gpib"]}  console {d["console"] or "off"}')
    for dev in A.usb_devices(A.BOOT_VID, A.BOOT_PID):
        print(f'RP2350 Boot (2e8a:000f) at USB {dev.split("/")[-1]}: a blank board, or one sent to BOOTSEL; `flash` loads it')
    for dev in A.usb_devices(0x2E8A, 0x000C):
        print(f'Debug Probe (2e8a:000c) at USB {dev.split("/")[-1]}')
    for p in A.prologix_ports():
        print(f'Prologix    {p}')
    if not (here or A.usb_devices(A.BOOT_VID, A.BOOT_PID)):
        print('no GPiBridge on USB, neither running (1209:0001) nor in BOOTSEL (2e8a:000f)')
    return 0


def report(rec):
    for c in rec['checks']:
        line = f"  {'ok  ' if c['ok'] else 'FAIL'} {c['what']}"
        if not c['ok']:
            line += f"\n         got {json.dumps(c['got'])[:300]}\n         wanted {json.dumps(c['want'])[:200]}"
        print(line)
    for n in rec['notes']:
        print('  note:', n)
    for k in ('crystal_ppm', 'rail_3v3_implied', 'reboot_s', 'ifc_pulse_us', 'queries_per_s', 'arb_1000_s',
              'arb_16000_s', 'diagnosis', 'rails'):
        if rec.get(k) not in (None, [], {}):
            print(f'  {k}: {json.dumps(rec[k])}')
    print(f"{rec['step']} {rec['board']}: {'PASS' if rec['ok'] else 'FAIL'}   ({rec.get('file', '')})")
    return 0 if rec['ok'] else 1


def main(argv):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('step', nargs='?', default='where')
    ap.add_argument('args', nargs='*')
    ap.add_argument('--sim', action='store_true')
    ap.add_argument('--quick', action='store_true')
    ap.add_argument('--fault', action='append', default=[], metavar='BOARD:WHAT',
                    help='--sim only: no5v, stuck5v, turned, open=LINE, short=LINE,LINE')
    ap.add_argument('--lite', action='append', default=[], metavar='BOARD', help='--sim only: this board is a Lite')
    ap.add_argument('--scope', default=None, help='rails: sds1104[:usb|:SERIAL|:IP] (the default) or '
                    'sds2104[:IP|:usb]; gen: sds2104, the generator\'s OUTPUT on it by coax')
    ap.add_argument('--channel', type=int, default=None, help='rails: the probe\'s channel (1); gen: the coax\'s (2)')
    ap.add_argument('--address', type=int, default=10, help='gen, speed: the instrument\'s GPIB address')
    ap.add_argument('--only', nargs='+', default=None, metavar='SECTION',
                    help='speed: adapter query set lines faults capture live')
    ap.add_argument('--live', action='store_true', help='speed: also the output-on section (E364xA)')
    ap.add_argument('--supply-output', type=int, default=2, help='speed --live: the output with the load on it')
    ap.add_argument('--note', action='append', default=[], help='meter: a line for the record')
    o = ap.parse_args(argv)

    if o.step == 'build':
        return build()
    if o.step == 'usb':
        return usb()
    sim = None
    try:
        if o.sim:
            import sim as SIM
            labels = [x for x in o.args if len(x) == 2 and x[0] in 'AL' and x[1].isdigit()] or ['A1']
            if o.step == 'pair' and len(labels) < 2:
                labels = ['A1', 'A2']
            faults = {}
            for f in o.fault:
                lab, _, what = f.partition(':')
                faults.setdefault(lab, []).append(what)
            tmp = tempfile.mkdtemp(prefix='gpibridge_sim_')
            sim = SIM.SimBench(tmp, [dict(label=lab, lite=lab in o.lite or lab.startswith('L'),
                                          instrument=o.step in ('gen', 'speed') and i == 0,
                                          faults=faults.get(lab, ()), cabled=o.step in ('pair', 'gen', 'speed'),
                                          manual=o.step == 'pair')     # parked, as every step leaves a real one
                                     for i, lab in enumerate(labels)])
            ctx = S.Ctx(sim=sim, home=tmp, quick=True)
            print(f'simulated bench in {tmp}: {", ".join(labels)}')
        else:
            ctx = S.Ctx(quick=o.quick)
        a = o.args
        if o.step == 'where':
            text = S.status_text(ctx)
            if not o.sim:
                (HERE / 'STATUS.md').write_text(text)
            print(text)
            return 0
        if o.step == 'bare':
            return report(S.step_bare(ctx, a[0] if a else None))
        if o.step == 'failsafe':
            return report(S.step_failsafe(ctx, a[0] if a else None))
        if o.step == 'flash':
            return report(S.step_flash(ctx, a[0] if a else None))
        if o.step == 'plug':
            return report(S.step_plug(ctx, a[0] if a else None))
        if o.step == 'pair':
            x, y = a if len(a) == 2 else sorted(ctx.present())[:2]
            return report(S.step_pair(ctx, x, y))
        if o.step == 'prologix':
            return report(S.step_prologix(ctx, a[0] if a else None))
        if o.step == 'gen':
            coax = None
            if o.scope and not o.sim:
                import bench
                coax = bench.Coax(o.scope, o.channel or 2)
            try:
                return report(S.step_gen(ctx, a[0] if a else None, o.address, coax=coax))
            finally:
                if coax is not None:
                    coax.close()
        if o.step == 'speed':
            import speed_faults
            return report(speed_faults.run(ctx, a[0] if a else None, o.address, o.only, o.live, o.supply_output))
        if o.step == 'rails':
            label = a[0] if a else ctx.pick()[0]
            if o.sim:
                import sim as SIM
                port = ctx.present()[label]['port']

                def powered():
                    with A.Adapter(port) as q:
                        return q.json('++t status')['bus'] != 'off'
                probe = SIM.SimProbe(['+1V1', '+5V_GPIB', 'VBUS', '+3V3'], powered)
            else:
                import bench
                probe = bench.Probe(o.scope or 'sds1104', o.channel or 1)
            try:
                return report(S.step_rails(ctx, label, probe))
            finally:
                probe.close()
        if o.step == 'meter':
            label = next((x for x in a if '=' not in x), None)
            readings, ripple = {}, None
            for x in a:
                if '=' in x:
                    k, _, v = x.partition('=')
                    if k == 'ripple':
                        ripple = float(v)
                    else:
                        readings[k] = float(v)
            return report(S.step_meter(ctx, label, readings, ripple, o.note))
        if o.step in ('identify', 'unpark', 'park', 'ask'):
            label = a[0] if a else None
            with ctx.open(label) as ad:
                if o.step == 'park':
                    S.park(ad)
                    print(ad.ask('++t status'))
                elif o.step == 'identify':
                    ad.cmd('++t identify 60')
                    print(f'{ctx.pick(label)[0]}: its yellow and red LEDs flash for a minute')
                elif o.step == 'unpark':
                    ad.cmd('++savecfg 1')
                    ad.cmd('++t autostart 1')
                    ad.cmd('++t power 1')
                    print(ad.ask('++t status'))
                else:
                    ad.cmd(a[1])
                    line = ad.line(2.0)
                    while line:
                        print(line)
                        line = ad.line(0.3)
            return 0
        print(__doc__)
        return 2
    except S.StepFailed as e:
        print('could not run:', e)
        return 2
    finally:
        if sim is not None:
            sim.close()


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
