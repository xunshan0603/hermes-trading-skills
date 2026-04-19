# OKX Execution Contract

This skill does not require the agent to know OKX API secrets. API keys must live in deployment secrets or a separate adapter.

## Supported Instruments

- `BTC-USDT-SWAP`
- `ETH-USDT-SWAP`

Recommended:

- USDT perpetual swaps.
- Isolated margin.
- One-way mode unless the adapter and account are explicitly configured for hedge mode.

## Adapter Responsibilities

The OKX adapter should provide fresh:

- Server time and local clock skew.
- Best bid/ask and mark/index price.
- Recent OHLCV candles.
- Account equity.
- Open positions.
- Open orders.
- Current margin mode, leverage, and position mode.
- Recent fills and rejected orders.

The adapter should execute only plans with `validator.status = PASS`.

Bundled adapter:

- `scripts/okx_safe_trade_adapter.py`
- Config template: `scripts/okx_adapter_config.example.json`
- Env template: `scripts/.env.example`

Hermes may invoke the bundled adapter, but must not bypass it with raw OKX REST calls.

## Idempotency

Every order request must include an idempotency key derived from `decision_id`.

If exchange status is ambiguous:

1. Do not retry blindly.
2. Query order status.
3. Reconcile position.
4. Enter `COOLDOWN` if uncertain.

## Dry Run

The first adapter version should support:

- `dry_run=true`
- `paper`
- `testnet`
- `live`

Live execution must be disabled unless config explicitly sets `allow_live=true`.

Required live command shape:

```bash
python scripts/okx_safe_trade_adapter.py \
  --plan trade_plan.json \
  --config private_okx_config.json \
  --env .env \
  --allow-live \
  --execute
```

The private config must set `dry_run=false` and `allow_live=true`. The `.env` file must provide `OKX_API_KEY`, `OKX_API_SECRET`, and `OKX_API_PASSPHRASE`. API keys must not have withdrawal permission.

## Execution Rejection

Reject execution if:

- Plan is older than max age.
- Market moved beyond allowed slippage.
- Stop cannot be placed.
- Margin mode is not isolated.
- Leverage exceeds plan.
- Existing position conflicts with the plan.
- Validator output is missing or stale.
