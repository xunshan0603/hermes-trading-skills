# Replay And Journal

Autonomous trading must leave a replayable trail.

## Journal Every Decision

Append JSONL records with:

- Timestamp.
- Market snapshot hash or path.
- Account snapshot hash or path.
- Decision JSON.
- Validator result.
- Execution result if any.
- Error or rejection reason if any.

## Review Cadence

Daily:

- Count decisions.
- Count trades.
- Check all `REJECTED` reasons.
- Check open risk and drawdown.

Weekly:

- Review all losing campaigns.
- Confirm no averaging down.
- Confirm no mixed-regime campaign.
- Confirm MAE and time-stop compliance.

Monthly:

- Recompute win rate, PF, max drawdown.
- Compare live/paper behavior to strategy assumptions.
- Lower risk after drift or unexplained losses.

## Replay Rule

For every live order, it must be possible to answer:

1. What data did the agent see?
2. What rule allowed the trade?
3. What risk did it take?
4. What validator approved it?
5. What exchange response occurred?
6. What exit rule applies now?
