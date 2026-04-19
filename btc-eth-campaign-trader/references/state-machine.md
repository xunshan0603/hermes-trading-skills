# State Machine

Use this state machine for autonomous operation.

## States

- `NO_TRADE`: default state. No valid campaign.
- `PROBE`: 25% exploratory position with defined stop.
- `CAMPAIGN`: validated aligned position.
- `SCALE_IN`: add only while profitable and regime-aligned.
- `SCALE_OUT`: reduce risk at profit targets or weakening structure.
- `EXIT`: close because stop, invalidation, risk, or time rule triggered.
- `COOLDOWN`: pause after loss streak, drawdown, data anomaly, or execution anomaly.

## Transitions

`NO_TRADE -> PROBE`

- Valid setup.
- Fresh data.
- Stop defined.
- Risk size valid.
- Validator PASS.

`PROBE -> CAMPAIGN`

- Regime aligned.
- Position is profitable or structure confirms.
- Risk after adding remains within limits.

`CAMPAIGN -> SCALE_IN`

- Floating profit at least 1R.
- Structure continues.
- MAE limits not breached.
- Stop can be moved closer to breakeven.

`CAMPAIGN -> SCALE_OUT`

- 1.5R or 3R profit target.
- Momentum weakens.
- Time stop approaches.
- Regime starts degrading.

`ANY_POSITION -> EXIT`

- Stop hit.
- MAE -12%.
- Daily/weekly/monthly risk guard.
- Regime flips against full-size campaign.
- Validator REJECTED.

`ANY -> COOLDOWN`

- Execution anomaly.
- 3 consecutive losing campaigns.
- Account drawdown breach.
- Missing or stale account data.

`COOLDOWN -> NO_TRADE`

- Cooldown elapsed.
- Data is fresh.
- Open orders/positions reconciled.
- Human review if required by config.
