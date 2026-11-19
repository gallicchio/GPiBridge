# GPiBridge bring-up: where we are

Written by `bringup/run.py` at 2026-11-19 13:44. `BRINGUP.md` is the plan; `BRINGUP_LOG.md` is what happened.

| board | what it is | serial | plugged in now | flash | bare | failsafe | rails | plug | pair | prologix | gen |
|---|---|---|---|---|---|---|---|---|---|---|---|
| **A1** | GPiBridge rev A | `9F9D542A93F67D76` | yes | pass 11-19 13:44 | pass 11-16 09:14 | pass 11-16 09:15 | pass 11-18 11:45 | pass 11-18 13:36 |  |  | pass 11-19 08:46 |
| **A2** | GPiBridge rev A | `E9D119818C2ADDD2` | yes | pass 11-19 13:44 | pass 11-19 12:48 | pass 11-19 12:55 |  | pass 11-19 12:56 |  |  |  |
| **L1** | GPiBridge Lite rev A | `5F4293C74E3358D8` | yes | pass 11-19 13:44 | pass 11-19 09:30 | pass 11-19 09:53 |  | pass 11-19 09:31 |  |  |  |

## Next at the bench

- **A1**: through stage 4. Next: stage 5, the dearer instruments, one at a time.
- **A2**: its plug is on and checks alone. Next: plug A2 into the back of the HP 33120A (GPIB address 10, powered on), USB-C to `bell`, and tell Claude "A2 is on the 33120A". Before that, if a second board with its plug and a GPIB cable are at hand: stage 2b (`pair`). 
- **L1**: its plug is on and checks alone. Next: plug L1 into the back of the HP 33120A (GPIB address 10, powered on), USB-C to `bell`, and tell Claude "L1 is on the 33120A". 
