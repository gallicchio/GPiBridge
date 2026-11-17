"""The simulated bench: firmware/test/sim_board processes, each a GPiBridge that is not
there, joined by one simulated GPIB cable.  `make -C firmware/test` builds sim_board.

    with SimBench(tmp, [dict(label='A1'), dict(label='L1', lite=True)]) as bench:
        bench.port('A1')          # the pseudo-terminal that stands for its USB serial port
        bench.stats()             # {'A1': {'fights': 0, 'breaches': 0}, ...}

A board may carry the simulated HP 33120A on its plug (instrument=True) and planted
faults (faults=['open=DAV'], ['short=DAV,NRFD'], ['no5v'], ['stuck5v'], ['turned']).
cabled=False keeps a board off the shared cable, alone on its own bus.
"""
import json
import os
import struct
import subprocess
import time
from pathlib import Path

SIM_BOARD = Path(__file__).resolve().parent.parent / 'firmware' / 'test' / 'sim_board'
SLOTS = 8
# shared_bus in sim_board.c: low[8] and high[8] (uint16), terminates[8] and present[8]
# (uint8), fights[8] and breaches[8] (uint32)
BUS_STRUCT = struct.Struct(f'<{SLOTS}H{SLOTS}H{SLOTS}B{SLOTS}B{SLOTS}I{SLOTS}I')


class SimBench:
    def __init__(self, tmp, boards):
        self.tmp = Path(tmp)
        self.tmp.mkdir(parents=True, exist_ok=True)
        self.bus = self.tmp / 'gpib_cable.bin'
        self.bus.write_bytes(bytes(BUS_STRUCT.size))
        self.procs, self.info = {}, {}
        if not SIM_BOARD.exists():
            raise FileNotFoundError(f'{SIM_BOARD}: build it with `make -C firmware/test sim_board`')
        for slot, b in enumerate(boards):
            self.add(slot, **b)

    def add(self, slot, label, lite=False, instrument=False, faults=(), manual=False, cabled=True):
        link = self.tmp / f'port_{label}'
        cmd = [str(SIM_BOARD)] + (['lite'] if lite else []) + ['--link', str(link), '--serial', f'SIM{label}']
        if cabled:
            cmd += ['--bus', str(self.bus), '--slot', str(slot)]
        if instrument:
            cmd += ['--instrument']
        if manual:
            cmd += ['--manual']
        for f in faults:
            cmd += ['--fault', f]
        log = open(self.tmp / f'uart_{label}.log', 'w')
        p = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=log, text=True)
        ready = p.stdout.readline()                # one JSON line once its port is there
        if not ready:
            raise RuntimeError(f'sim_board for {label} did not start: {" ".join(cmd)}')
        self.procs[label] = p
        self.info[label] = dict(json.loads(ready), link=str(link), slot=slot, log=log, cabled=cabled)

    def port(self, label):
        return self.info[label]['link']

    def serial(self, label):
        return self.info[label]['serial']

    def labels(self):
        return list(self.procs)

    def uart(self, label):
        """What the board's UART has printed so far (its JSON log)."""
        self.info[label]['log'].flush()
        return (self.tmp / f'uart_{label}.log').read_text()

    def stats(self):
        """Per board: bus fights it started (two drivers opposed on one line) and breaches
        of its own pin rules (firmware/test/wire_model.h)."""
        v = BUS_STRUCT.unpack(self.bus.read_bytes()[:BUS_STRUCT.size])
        fights, breaches = v[4 * SLOTS:5 * SLOTS], v[5 * SLOTS:6 * SLOTS]
        return {label: {'fights': fights[i['slot']], 'breaches': breaches[i['slot']]}
                for label, i in self.info.items() if i['cabled']}

    def close(self):
        for p in self.procs.values():              # each by its own handle, never by name
            p.terminate()
        for p in self.procs.values():
            try:
                p.wait(timeout=2)
            except subprocess.TimeoutExpired:
                p.kill()
        for i in self.info.values():
            i['log'].close()
        self.procs = {}

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        self.close()


class SimProbe:
    """A scope probe that is not there, for the `rails` step: script is the list of rails
    the hand touches, each held for `hold` readings, with nothing (0 V) between them."""

    def __init__(self, script, powered, hold=4, ripple_mv=12.0):
        self.script, self.powered, self.hold, self.ripple_mv = list(script), powered, hold, ripple_mv
        self.reads = 0
        self.beeps = 0

    def _on(self):
        i, phase = divmod(self.reads, self.hold + 2)
        return self.script[i] if i < len(self.script) and phase < self.hold else None

    def dc(self):
        rail = self._on()
        self.reads += 1
        level = {'+1V1': 1.102, '+3V3': 3.296, 'VBUS': 4.93, '+5V_GPIB': 4.88 if self.powered() else 0.01}
        return level.get(rail, 0.003)

    def ripple(self, tdiv):
        import math
        n = 1400
        t = [k * tdiv * 14 / n for k in range(n)]
        v = [self.ripple_mv / 2000 * math.sin(2 * math.pi * 3.1e6 * x) for x in t]
        return t, v

    def beep(self, n=1):
        self.beeps += n

    def close(self):
        pass
