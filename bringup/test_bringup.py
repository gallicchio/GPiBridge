"""The bring-up steps against simulated boards: `pytest bringup/` (after `make -C firmware/test`).

Each simulated board is firmware/test/sim_board: the firmware's own protocol code, bus
engine and pin layer on this PC, behind a pseudo-terminal, with the transceivers
modelled from their function tables.  What these tests show:
- a good board passes every step, GPiBridge and the Lite;
- each planted fault fails the step that is there to catch it, and is named;
- two boards on one cable never drive a line against each other while a step runs;
- a board plugged into a bus that already has a controller stands back;
- lab-instrument-control's own HP 33120A driver runs through the adapter, 16,000-point
  upload included (skipped if lab-instrument-control is not beside this repository).
"""
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))

import adapter as A                     # noqa: E402
import bench                            # noqa: E402
import sim as SIM                       # noqa: E402
import steps as S                       # noqa: E402

pytestmark = pytest.mark.skipif(not SIM.SIM_BOARD.exists(), reason='make -C firmware/test sim_board')


def make(tmp_path, boards):
    b = SIM.SimBench(tmp_path / 'bench', boards)
    return b, S.Ctx(sim=b, home=tmp_path / 'home', quick=True, quiet=True)


def failed(rec):
    return [c['what'] for c in rec['checks'] if not c['ok']]


# ---- stage 1 ---------------------------------------------------------------------------------------------
@pytest.mark.parametrize('label', ['A1', 'L1'])
def test_bare_good_board(tmp_path, label):
    b, ctx = make(tmp_path, [dict(label=label, lite=label[0] == 'L', cabled=False)])
    with b:
        rec = S.step_bare(ctx, label)
        assert rec['ok'], failed(rec)
        assert abs(rec['crystal_ppm']) < 400            # both clocks are this PC's
        assert len(rec['ifc_pulse_us']) == 2 and 140 <= rec['ifc_pulse_us'][-1] <= 400
        with ctx.open(label) as a:                       # left parked, with the defaults a Prologix program expects
            st = a.json('++t status')
            assert (st['bus'], st['autostart']) == ('off', 0)
            assert a.ask('++eos') == '0' and a.ask('++eot_enable') == '0' and a.ask('++addr') == '1'
        assert ctx.state['boards'][f'SIM{label}']['stages']['bare']['ok']
        assert '"event":"boot"' in b.uart(label)


@pytest.mark.parametrize('lite, fault, names', [
    (False, 'no5v', ['follow the pad']),
    (False, 'stuck5v', ['stayed high']),
    (False, 'open=DAV', ['DAV']),
    (False, 'open=SRQ', ['SRQ']),
    (False, 'open=DIO5', ['DIO5']),
    (True, 'short=DAV,NRFD', ['DAV', 'NRFD']),
])
def test_bare_faults_fail_the_self_test(tmp_path, lite, fault, names):
    label = 'L1' if lite else 'A1'
    b, ctx = make(tmp_path, [dict(label=label, lite=lite, faults=[fault], cabled=False)])
    with b:
        rec = S.step_bare(ctx, label)
        assert not rec['ok']
        assert any('self-test' in w for w in failed(rec))
        text = ' '.join(rec['selftest_trouble'])
        assert all(n in text for n in names), text
        assert not ctx.state['boards'][f'SIM{label}']['stages']['bare']['ok']


def test_plug_step(tmp_path):
    b, ctx = make(tmp_path, [dict(label='A1', cabled=False)])
    with b:
        assert S.step_plug(ctx, 'A1')['ok']


# ---- stage 1b ----------------------------------------------------------------------------------------------
def probe_for(ctx, label, script, **kw):
    port = ctx.present()[label]['port']

    def powered():
        with A.Adapter(port) as q:
            return q.json('++t status')['bus'] != 'off'
    return SIM.SimProbe(script, powered, **kw)


def test_rails_in_any_order(tmp_path):
    b, ctx = make(tmp_path, [dict(label='A1', cabled=False)])
    with b:
        p = probe_for(ctx, 'A1', ['+5V_GPIB', '+3V3', 'VBUS', '+1V1'])
        rec = S.step_rails(ctx, 'A1', p, patience=20)
        assert rec['ok'], failed(rec)
        assert set(rec['rails']) == {'+1V1', '+3V3', 'VBUS', '+5V_GPIB'}
        assert rec['rails']['+5V_GPIB']['off_V'] < 0.1 and 'off_V' not in rec['rails']['VBUS']
        assert p.beeps == 5                              # one a rail, two for the last


def test_rails_lite_has_three(tmp_path):
    b, ctx = make(tmp_path, [dict(label='L1', lite=True, cabled=False)])
    with b:
        rec = S.step_rails(ctx, 'L1', probe_for(ctx, 'L1', ['VBUS', '+1V1', '+3V3']), patience=20)
        assert rec['ok'] and set(rec['rails']) == {'+1V1', '+3V3', 'VBUS'}


def test_rails_ripple_and_a_missing_rail_fail(tmp_path):
    b, ctx = make(tmp_path, [dict(label='A1', cabled=False)])
    with b:
        rec = S.step_rails(ctx, 'A1', probe_for(ctx, 'A1', ['+1V1', '+3V3', 'VBUS'], ripple_mv=90.0), patience=3)
        bad = failed(rec)
        assert any('+5V_GPIB' in w for w in bad) and any('ripple' in w for w in bad)


GOOD_METER = dict(TP1=5.159, TP1off=5.202, TP2=3.308, TP3=1.097, TP4=5.144, TP4off=0.0)    # A1, 2026-11-18


def test_meter_readings(tmp_path):
    b, ctx = make(tmp_path, [dict(label='A1', cabled=False), dict(label='L1', lite=True, cabled=False)])
    with b:
        rec = S.step_meter(ctx, 'A1', GOOD_METER, ripple_mvpp=48.3)
        assert rec['ok'], failed(rec)
        assert rec['rails']['+5V_GPIB'] == {'V': 5.144, 'off_V': 0.0} and rec['rails']['VBUS']['V'] == 5.159
        assert ctx.state['boards']['SIMA1']['stages']['rails']['ok']
        rec = S.step_meter(ctx, 'L1', dict(TP1=5.1, TP2=3.3, TP3off=1.1))      # the Lite has no TP4
        assert rec['ok'], failed(rec)
        assert any('ripple not measured' in n for n in rec['notes'])
        with pytest.raises(S.StepFailed, match='TP4'):
            S.step_meter(ctx, 'L1', dict(TP1=5.1, TP2=3.3, TP3=1.1, TP4=5.1))


def test_meter_catches_q1_a_rail_and_a_missing_reading(tmp_path):
    b, ctx = make(tmp_path, [dict(label='A1', cabled=False)])
    with b:
        rec = S.step_meter(ctx, 'A1', dict(GOOD_METER, TP4off=4.9, TP2=3.05), ripple_mvpp=75.0)
        bad = failed(rec)
        assert any('falls' in w for w in bad) and any('+3V3' in w for w in bad) and any('ripple' in w for w in bad)
        rec = S.step_meter(ctx, 'A1', {k: v for k, v in GOOD_METER.items() if k != 'TP4'})   # only bus off
        assert any('+5V_GPIB at TP4' in w for w in failed(rec))
        assert not ctx.state['boards']['SIMA1']['stages']['rails']['ok']


# ---- stage 2b ----------------------------------------------------------------------------------------------
PARKED = dict(manual=True)


@pytest.mark.parametrize('x, y', [('A1', 'A2'), ('A1', 'L1'), ('L1', 'A1'), ('L1', 'L2')])
def test_pair_good_boards(tmp_path, x, y):
    b, ctx = make(tmp_path, [dict(label=l, lite=l[0] == 'L', **PARKED) for l in (x, y)])
    with b:
        rec = S.step_pair(ctx, x, y)
        assert rec['ok'], (failed(rec), rec['faults'][:4])
        assert rec['walked'] == 32
        assert all(v == {'fights': 0, 'breaches': 0} for v in b.stats().values()), b.stats()
        for l in (x, y):
            with ctx.open(l) as a:
                assert a.json('++t status')['bus'] == 'off'


@pytest.mark.parametrize('boards, words', [
    ([dict(label='A1'), dict(label='A2', faults=['open=DAV'])], ['DAV', 'contact 6']),
    ([dict(label='A1'), dict(label='L1', lite=True, faults=['open=NDAC'])], ['NDAC', 'contact 8']),
    ([dict(label='A1'), dict(label='A2', faults=['short=DIO1,DIO2'])], ['bridge', 'DIO1', 'DIO2']),
    ([dict(label='L1', lite=True), dict(label='L2', lite=True, faults=['short=ATN,SRQ'])], ['bridge', 'ATN', 'SRQ']),
    ([dict(label='A1'), dict(label='A2', faults=['turned'])], ['TURNED ROUND']),
    ([dict(label='A1'), dict(label='L1', lite=True, faults=['turned'])], ['TURNED ROUND']),
])
def test_pair_names_the_fault(tmp_path, boards, words):
    b, ctx = make(tmp_path, [dict(d, **PARKED) for d in boards])
    with b:
        rec = S.step_pair(ctx, boards[0]['label'], boards[1]['label'])
        assert not rec['ok']
        text = ' '.join(rec['diagnosis'])
        assert all(w in text for w in words), text


# ---- two controllers ---------------------------------------------------------------------------------------
def test_a_second_controller_stands_back(tmp_path):
    b, ctx = make(tmp_path, [dict(label='A1')])              # A1 takes the bus as its USB comes up
    with b:
        with ctx.open('A1') as a1:
            assert a1.json('++t status')['bus'] == 'controller'
        b.add(1, 'A2')                                        # a second adapter is plugged into the same cable
        with ctx.open('A2') as a2:
            st = a2.json('++t status')
            assert (st['bus'], st['bus_power']) == ('busy', 0)
            a2.write(10, b'*IDN?')                            # and a program that tries to use it is told why
        assert 'another controller' in b.uart('A2')
        assert all(v['fights'] == 0 for v in b.stats().values()), b.stats()
        with ctx.open('A1') as a1:                            # A1 never noticed
            st = a1.json('++t status')
            assert st['bus'] == 'controller' and st['timeouts'] == 0


# ---- stage 4 -----------------------------------------------------------------------------------------------
def have_lic():
    try:
        bench.lic()
        return True
    except FileNotFoundError:
        return False


@pytest.mark.skipif(not have_lic(), reason='lab-instrument-control is not beside this repository')
@pytest.mark.parametrize('label', ['A1', 'L1'])
def test_gen_through_lab_instrument_control(tmp_path, label):
    b, ctx = make(tmp_path, [dict(label=label, lite=label[0] == 'L', instrument=True)])
    with b:
        rec = S.step_gen(ctx, label, 10, points=16000)
        assert rec['ok'], failed(rec)
        assert '33120A' in rec['idn'] and rec['queries_per_s'] > 20
        assert b.stats()[label] == {'fights': 0, 'breaches': 0}


@pytest.mark.skipif(not have_lic(), reason='lab-instrument-control is not beside this repository')
def test_gen_with_nobody_at_the_address(tmp_path):
    b, ctx = make(tmp_path, [dict(label='A1')])               # no instrument on the bus
    with b:
        with pytest.raises(IOError):
            S.step_gen(ctx, 'A1', 10)


# ---- the status page ---------------------------------------------------------------------------------------
def test_status_says_what_is_next(tmp_path):
    b, ctx = make(tmp_path, [dict(label='A1', cabled=False)])
    with b:
        assert 'USB-C' in S.status_text(S.Ctx(home=tmp_path / 'empty', quiet=True, sim=SIM.SimBench(tmp_path / 'e', [])))
        S.step_bare(ctx, 'A1')
        assert 'failsafe A1' in S.status_text(ctx)
        ctx.state['boards']['SIMA1']['stages']['failsafe'] = {'ok': True, 'at': 'x' * 19, 'file': ''}
        text = S.status_text(ctx)
        assert '**A1**' in text and 'solder the plug' in text
        S.step_plug(ctx, 'A1')
        assert '33120A' in S.status_text(ctx)


def test_vcd_pulses():
    vcd = '$timescale 10 ns $end\n$var wire 1 - IFC $end\n$enddefinitions $end\n#0\n$dumpvars\n1-\n$end\n' \
          '#1000\n0-\n#16000\n1-\n#20000\n0-\n'
    assert S.vcd_low_pulses(vcd, 'IFC') == [150.0]
    assert S.vcd_low_pulses(vcd.replace(' IFC ', ' gpib.IFC '), 'IFC') == [150.0]     # sigrok-style scoped names too
