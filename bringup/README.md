# bringup/: running the bring-up

[`../BRINGUP.md`](../BRINGUP.md) is the plan. This folder is what runs it and what it
leaves behind.

| file | what |
|---|---|
| `run.py` | the command line: one step a call, no keyboard input, `--sim` for a simulated board. With no step it prints where we are |
| `STATUS.md` | **where we are, and the next thing to do at the bench.** Rewritten by every step |
| `BRINGUP_LOG.md` | what happened: one entry a step, appended by `run.py` |
| `REVB.md` | what rev B should change, what the firmware already changed, and the questions still open |
| `state.json` | each board's serial number, its name (A1, L1, ...) and the stages it has passed |
| `results/<day>/` | each step's full record (JSON), and captures (VCD) |
| `steps.py` | the steps: `bare`, `flash`, `rails`, `plug`, `pair`, `prologix`, `gen` |
| `adapter.py` | one "++" adapter on a serial port (a GPiBridge, the simulator, or a Prologix); finding them on USB |
| `bench.py` | the instruments, through lab-instrument-control's drivers, each checked against its `bench_claims.py` first |
| `expect.py` | every number a board is compared against, with where it comes from |
| `sim.py`, `test_bringup.py` | the simulated bench (`firmware/test/sim_board` processes on one simulated cable, a scope probe that is not there) and the tests that run every step against it: `pytest bringup/` |

```sh
python3 bringup/run.py                  # where we are
python3 bringup/run.py build            # firmware, host tests, simulator
python3 bringup/run.py --sim bare       # any step against a simulated board
python3 bringup/run.py --sim pair A1 A2 --fault A2:open=DAV
pytest bringup/                         # every step, good boards and planted faults
```

lab-instrument-control is looked for two folders above this repository's root (where it
lives on Jason's machines), one above, in the home folder, or where
`$LAB_INSTRUMENT_CONTROL` says. Only stage 1b's scope and stage 4's generator need it.
