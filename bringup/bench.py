"""The bench instruments, through lab-instrument-control's drivers.

lab-instrument-control is not part of this repository: it is looked for beside the
folder that holds this one (../../lab-instrument-control from the repository's root),
or where $LAB_INSTRUMENT_CONTROL says.  Nothing here runs unless a step asks for an
instrument, and a step asks for one only after the person at the bench has said it is
cabled to this board.  When lab-instrument-control has bench_claims.py (several
projects share the bench), every instrument is checked against its record first.
"""
import os
import sys
from pathlib import Path

PROJECT = 'GPiBridge'                     # the name this project claims instruments under


def lic():
    """lab-instrument-control's folder, put on sys.path with its vendor folders."""
    here = Path(__file__).resolve().parents[1]              # this repository
    places = [os.environ.get('LAB_INSTRUMENT_CONTROL'), here.parent.parent / 'lab-instrument-control',
              here.parent / 'lab-instrument-control', Path.home() / 'lab-instrument-control']
    root = next((Path(p) for p in places if p and (Path(p) / 'scpi_link.py').exists()), None)
    if root is None:
        raise FileNotFoundError('lab-instrument-control not found two folders up, one up, or in the home folder: '
                                'set $LAB_INSTRUMENT_CONTROL')
    for d in (root, root / 'siglent', root / 'hp'):
        if str(d) not in sys.path:
            sys.path.insert(0, str(d))
    return root


def held(resources):
    """Raise unless this project holds `resources` in the bench's record of claims
    (lab-instrument-control/bench_claims.py); nothing to check where there is no record."""
    lic()
    try:
        import bench_claims
    except ImportError:
        return
    bench_claims.require(resources, by=PROJECT, mine=True)


class Probe:
    """One scope channel with a x10 probe on it, used as a voltmeter and a ripple meter.

    spec: 'sds1104' or 'sds1104:usb' (the one SDS1104X-E on USB), 'sds1104:SERIAL',
    'sds1104:IP', 'sds2104' (the bench's SDS2104X Plus at its usual address),
    'sds2104:IP', 'sds2104:usb'.
    """

    def __init__(self, spec, channel=1, attenuation=10):
        import numpy as np
        self.np = np
        lic()
        kind, _, where = spec.partition(':')
        self.ch = int(channel)
        if kind == 'sds1104':
            held([f'SDS1104XE:{self.ch}'])
            from siglent_SDS1104XE import SDS1104XE
            if where in ('', 'usb'):
                self.s = SDS1104XE(usb=True)
            elif where.count('.') == 3:
                self.s = SDS1104XE(where)
            else:
                self.s = SDS1104XE(serial=where)
        elif kind == 'sds2104':
            held([f'SDS2104X:{self.ch}'])
            import siglent_SDS2104X as m
            if where == 'usb':
                from scpi_link import usbtmc_node
                self.s = m.SDS2104X(None, usb=usbtmc_node(m.USB_VENDOR, m.USB_PRODUCT))
            else:
                self.s = m.SDS2104X(where or m.DEFAULT_IP)
        else:
            raise ValueError(f'--scope {spec!r}: sds1104[:usb|:SERIAL|:IP] or sds2104[:IP|:usb]')
        self.att = attenuation
        self.mode = None

    def _set(self, mode, tdiv):
        # 1 MOhm always: a x10 probe into a 50 ohm input reads almost nothing (the bench's
        # SDS2104X Plus had channel 1 at 50 ohm on 2026-11-18)
        if mode != self.mode:
            if mode == 'dc':                       # -1.5 to +6.5 V on the screen: every rail, and ground
                self.s.channel(self.ch, on=True, probe=self.att, impedance='1M', coupling='DC', scale=1.0,
                               offset=-2.5, bwlimit='20M')
            else:                                  # the ripple: +-80 mV about the rail
                self.s.channel(self.ch, on=True, probe=self.att, impedance='1M', coupling='AC', scale=0.02,
                               offset=0.0, bwlimit='FULL')
            self.s.trigger(source=self.ch, level=0.0 if mode == 'ac' else 2.0, slope='rising', mode='auto')
            self.mode = mode
        self.s.timebase(scale=tdiv, delay=0)

    def dc(self):
        """The voltage under the probe now: the mean of one short record."""
        self._set('dc', 200e-6)
        self.s.acquire_now()
        _, v, _ = self.s.waveform(self.ch)
        return float(self.np.mean(v))

    def ripple(self, tdiv):
        """One AC-coupled record at tdiv seconds a division: (t, volts)."""
        self._set('ac', tdiv)
        self.s.acquire_now()
        t, v, _ = self.s.waveform(self.ch)
        return list(map(float, t)), list(map(float, v))

    def beep(self, n=1):
        """A sound from the scope, where it can make one: the hand on the probe looks at the board."""
        import time
        buzzer = getattr(self.s, 'buzzer', None)
        if not buzzer:
            return
        was = buzzer()
        buzzer(True)
        for _ in range(n):                         # the SDS1104X-E beeps at each setting a program changes
            self.s.w(f'C{self.ch}:TRA ON')
            time.sleep(0.25)
        buzzer(was)

    def close(self):
        self._set('dc', 1e-3)                      # leave the channel as a x10 DC probe, 1 V/div
        self.s.run()
        self.s.close()


class Coax:
    """One scope channel with a generator's output on it by 50 ohm coax (stage 4: the
    33120A's OUTPUT on the SDS2104X Plus): it only reads.  Every setting it changes (the
    channel, the timebase, the trigger, the memory depth) goes back as found on close().

    spec: 'sds2104' (the bench's SDS2104X Plus at its usual address), 'sds2104:IP' or
    'sds2104:usb'.  The channel is set to 50 ohm: the 33120A's amplitudes assume a 50 ohm
    load (OUTPut:LOAD 50, which stage 4 leaves set)."""
    DEPTHS = ('200k', '100k', '2M')              # small enough to read in a second over the LAN

    def __init__(self, spec='sds2104', channel=2):
        import numpy as np
        self.np = np
        lic()
        kind, _, where = spec.partition(':')
        if kind != 'sds2104':
            raise ValueError(f'--scope {spec!r} with a generator on it: sds2104[:IP|:usb]')
        self.ch = int(channel)
        held([f'SDS2104X:{self.ch}'])
        import siglent_SDS2104X as m
        if where == 'usb':
            from scpi_link import usbtmc_node
            self.s = m.SDS2104X(None, usb=usbtmc_node(m.USB_VENDOR, m.USB_PRODUCT))
        else:
            self.s = m.SDS2104X(where or m.DEFAULT_IP)
        self.found = {'channel': self.s.channel(self.ch), 'timebase': self.s.timebase(),
                      'trigger': self.s.trigger(), 'mdepth': self.s.q(':ACQuire:MDEPth?')}

    def capture(self, vdiv, tdiv):
        """One forced acquisition at vdiv volts and tdiv seconds a division: (t, volts)."""
        np = self.np
        self.s.channel(self.ch, on=True, scale=vdiv, offset=0.0, coupling='DC', impedance='50', probe=1,
                       bwlimit='20M')
        for depth in self.DEPTHS:
            try:
                self.s.acquire(mdepth=depth)
                break
            except ValueError:
                continue
        self.s.timebase(scale=tdiv, delay=0)
        self.s.trigger(source=self.ch, level=0.0, slope='rising', mode='auto')
        self.s.acquire_now()
        t, v, _ = self.s.waveform(self.ch)
        return np.asarray(t, float), np.asarray(v, float)

    def close(self):
        f = self.found
        try:
            c = f['channel']
            self.s.channel(self.ch, on=c['on'], scale=c['scale'], offset=c['offset'], coupling=c['coupling'],
                           impedance='50' if c['impedance'].upper().startswith('FIF') else '1M', probe=c['probe'],
                           bwlimit=c['bwlimit'])
            try:
                self.s.acquire(mdepth=f['mdepth'])
            except ValueError:
                pass
            self.s.timebase(scale=f['timebase'][0], delay=f['timebase'][1])
            tr = f['trigger']
            src = tr['source']
            self.s.trigger(source=int(src[1:]) if src[:1] == 'C' and src[1:].isdigit() else src, level=tr['level'],
                           slope={'RIS': 'rising', 'FAL': 'falling', 'ALT': 'alternate'}.get(tr['slope'][:3].upper()),
                           mode={'AUTO': 'auto', 'NORM': 'normal', 'SING': 'single'}.get(tr['mode'][:4].upper()))
            if tr['mode'][:4].upper() != 'SING':
                self.s.run()
        finally:
            self.s.close()


def hp33120a(port, address=10, timeout=10.0):
    """lab-instrument-control's own 33120A driver, through the adapter on `port`: a
    GPiBridge is driven as the Prologix is (scpi_link.Link(gpib=..., prologix=port))."""
    lic()
    from hp_33120A import HP33120A
    return HP33120A(address, prologix=port, timeout=timeout)
