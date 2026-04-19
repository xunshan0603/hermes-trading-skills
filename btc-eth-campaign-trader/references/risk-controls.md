# Risk Controls

Use these as hard limits for an aggressive 400-500 USDT account unless deployment config overrides them downward.

## Account Limits

- Per-campaign initial risk: 1.5%-2.0% of account equity.
- Max total open risk: 4.0% of account equity.
- Daily loss stop: 4.0%.
- Weekly de-risk threshold: 10.0%.
- Monthly campaign halt: 20.0%.
- Hard kill drawdown: 25.0%.
- Max leverage: 5x.
- Margin mode: isolated.

If equity drops below the configured minimum, stop live trading and require human review.

## Correlation Limits

BTC and ETH are correlated. Same-direction BTC+ETH positions count as one correlated book.

- BTC risk budget weight: 70%.
- ETH risk budget weight: 30%.
- Total same-direction risk must not exceed max total open risk.

## MAE Circuit Breaker

Measure adverse movement from campaign entry on the underlying price:

- -5% adverse: stop adding.
- -8% adverse: cut at least half.
- -12% adverse: exit campaign.

Do not explain away MAE breaches with narratives.

## Time Stop

Campaign age:

- Day 3 not profitable: halve.
- Day 7 no continuation: exit 70%.
- Day 14 not working: close campaign.

Exception: a strongly profitable aligned campaign with stop already in profit may continue.

## Loss Streak

- 2 consecutive losing campaigns: reduce next risk by 50%.
- 3 consecutive losing campaigns: enter cooldown for at least 24 hours.
- 5 consecutive losing campaigns in a week: stop automated trading until human review.

## Data Quality

No trade if:

- Market data stale.
- Account state stale.
- Open orders unknown.
- Existing position unknown.
- Exchange adapter returns ambiguous status.
- Clock skew exceeds deployment tolerance.
- Validator is unavailable.

## Live Trading Gate

Live trading requires:

- `mode = live`.
- `allow_live = true` in execution config or validator CLI.
- `validator.status = PASS`.
- Dry-run/testnet forward-testing completed by the operator.
