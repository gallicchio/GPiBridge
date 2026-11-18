# GPiBridge bring-up: where we are

Written by `bringup/run.py` at 2026-11-18 11:48. `BRINGUP.md` is the plan; `BRINGUP_LOG.md` is what happened.

| board | what it is | serial | plugged in now | flash | bare | failsafe | rails | plug | pair | prologix | gen |
|---|---|---|---|---|---|---|---|---|---|---|---|
| **A1** | GPiBridge rev A | `9F9D542A93F67D76` | yes | pass 11-16 09:14 | pass 11-16 09:14 | pass 11-16 09:15 | pass 11-18 11:45 |  |  |  |  |

## Next at the bench

- **A1**: stage 1 passed, and its rails. Next is yours: solder the plug, `BRINGUP.md` stage 2 (15 minutes): through a printed base if A1 is ever to be housed (once the plug is soldered, the base can no longer go on), bare if it is to be the bench board. Then its USB-C back into `bell`, and tell Claude "A1 has its plug".
