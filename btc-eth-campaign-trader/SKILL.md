---
name: btc-eth-campaign-trader
description: BTC and ETH campaign-trading skill for autonomous or semi-autonomous agents that need to classify market regime, create OKX USDT perpetual trade plans, enforce Paul-Wei-inspired BTC campaign rules, validate risk controls, output Chinese explanation plus machine-readable JSON, and journal decisions for replay. Use for automated trading planning, paper trading, testnet/live gatekeeping, strategy review, and post-trade replay involving BTC-USDT-SWAP or ETH-USDT-SWAP.
---

# BTC ETH Campaign Trader

Use this skill to produce and validate BTC/ETH campaign trade decisions for an automated agent. The strategy is distilled from the public `BTC-Trading-Since-2020` ledger: full-size risk is allowed only when the higher-timeframe BTC regime agrees with the trade.

This skill is a strategy and risk-control layer. It must not bypass exchange adapters, API key policy, account-state checks, or the validator script.

## Operating Mode

Default to `paper` or `testnet`. Use `live` only when the user or deployment config explicitly enables live trading.

Before proposing any order, require:

- Fresh market data for BTC and ETH.
- Fresh account equity, open positions, open orders, and current daily/weekly/monthly drawdown.
- A stop price and invalidation level.
- A position-size calculation.
- A `PASS` from `scripts/validate_trade_plan.py`.

If any required input is stale, missing, inconsistent, or unverifiable, output `NO_TRADE`.

## Core Workflow

1. Classify daily regime for BTC and ETH using `scripts/classify_regime.py` or equivalent logic.
2. Build a trade plan using `references/strategy-rules.md`.
3. Size risk using `scripts/size_position.py`.
4. Validate the full plan using `scripts/validate_trade_plan.py`.
5. Output both:
   - A concise Chinese explanation.
   - A JSON object matching `references/decision-schema.md`.
6. Journal the decision with `scripts/journal_trade_decision.py` when a durable log path is available.

## Strategy Summary

Regime definitions use the previous completed daily candle:

- `bull`: close > MA20 > MA60
- `bear`: close < MA20 < MA60
- `mixed`: all other states

Full-size campaign permission:

- BTC `bull`: BTC long campaign allowed.
- BTC `bear`: BTC short campaign allowed.
- BTC `mixed`: no full campaign; probe only or no trade.
- ETH full campaign must agree with BTC master regime and ETH local regime. ETH is a satellite, not the master signal.

Hard prohibitions:

- Do not open full-size BTC short in BTC bull regime.
- Do not open full-size BTC long in BTC bear regime.
- Do not turn mixed-regime probes into campaigns.
- Do not average down losing positions.
- Do not trade without a stop.
- Do not trade when validator status is not `PASS`.
- Do not exceed configured account risk, leverage, drawdown, or correlated exposure limits.

## Aggressive Small-Account Defaults

These defaults match a 400-500 USDT account using OKX USDT perpetuals with aggressive but bounded risk:

- Instruments: `BTC-USDT-SWAP`, `ETH-USDT-SWAP`.
- Margin mode: isolated.
- Max leverage: 5x.
- Default leverage: 2x-3x.
- Per-campaign initial risk: 1.5%-2.0% of equity.
- Max total open risk: 4.0% of equity.
- Daily loss stop: 4.0%.
- Weekly loss de-risk: 10.0%.
- Monthly campaign halt: 20.0%.
- Hard kill drawdown: 25.0%.
- BTC risk budget weight: 70%.
- ETH risk budget weight: 30%.

Reduce these values when equity is larger, liquidity is poor, execution is unstable, or the agent is not yet forward-tested.

## State Machine

Use the state machine in `references/state-machine.md`:

`NO_TRADE -> PROBE -> CAMPAIGN -> SCALE_IN -> SCALE_OUT -> EXIT -> COOLDOWN`

Any validation failure, stale data, exchange/API anomaly, drawdown breach, or missing stop forces `NO_TRADE`, `EXIT`, or `COOLDOWN` depending on whether a position already exists.

## Resource Map

Read only the references needed for the current task:

- `references/paul-wei-findings.md`: ledger-derived facts behind the strategy.
- `references/strategy-rules.md`: entry, add, reduce, exit, BTC/ETH relationship.
- `references/risk-controls.md`: account, campaign, MAE, time-stop, and kill-switch rules.
- `references/state-machine.md`: autonomous state transitions.
- `references/decision-schema.md`: required JSON output.
- `references/okx-execution-contract.md`: how the strategy should interface with OKX adapters.
- `references/replay-and-journal.md`: logging and replay requirements.

Scripts:

- `scripts/classify_regime.py`: classify BTC/ETH daily regime from OHLC candles.
- `scripts/size_position.py`: calculate linear USDT perpetual size from equity, entry, stop, risk, and leverage.
- `scripts/validate_trade_plan.py`: reject unsafe or schema-invalid plans.
- `scripts/journal_trade_decision.py`: append normalized decision JSONL.
- `scripts/okx_safe_trade_adapter.py`: optional OKX execution adapter; default dry-run, requires validator PASS and explicit live permission.

## Output Contract

Always return:

1. Chinese explanation:
   - Current BTC/ETH regime.
   - Why trade or no trade.
   - Risk budget, stop, invalidation, and exit logic.
   - Validator result.

2. JSON:
   - Valid object, no markdown comments inside JSON.
   - Match `references/decision-schema.md`.
   - Include `validator.status`.

If `decision` is not executable, use `NO_TRADE`, `HOLD`, `EXIT`, or `COOLDOWN`; do not invent an order.

## Hermes Execution

Hermes may call `scripts/okx_safe_trade_adapter.py` to execute a validated plan, but it must not call OKX REST endpoints directly. Use:

```bash
python scripts/okx_safe_trade_adapter.py --plan trade_plan.json --config scripts/okx_adapter_config.example.json
```

For live, the deployment must use a private config with `allow_live=true`, `dry_run=false`, environment-provided OKX keys, and `--execute`. Never store secrets in this skill.

## Final Safety Rule

When in doubt, do not trade. The Paul Wei ledger shows that the edge comes from concentrated aggression in favorable regimes, not from forcing trades in uncertainty.
