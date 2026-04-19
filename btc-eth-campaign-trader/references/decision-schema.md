# Decision Schema

Return Chinese explanation plus one JSON object. The JSON must be machine-readable and contain no comments.

## Required JSON Fields

```json
{
  "decision_id": "ISO8601-symbol",
  "timestamp": "2026-04-20T00:00:00Z",
  "mode": "paper|testnet|live",
  "exchange": "OKX",
  "symbol": "BTC-USDT-SWAP",
  "decision": "NO_TRADE|OPEN_PROBE|OPEN_CAMPAIGN|SCALE_IN|SCALE_OUT|HOLD|EXIT|COOLDOWN",
  "side": "long|short|none",
  "state": "NO_TRADE|PROBE|CAMPAIGN|SCALE_IN|SCALE_OUT|EXIT|COOLDOWN",
  "regime": {
    "btc": "bull|bear|mixed|unknown",
    "eth": "bull|bear|mixed|unknown",
    "symbol": "bull|bear|mixed|unknown",
    "basis": "previous close and MA20/MA60"
  },
  "risk": {
    "account_equity_usdt": 500.0,
    "risk_pct": 0.018,
    "max_loss_usdt": 9.0,
    "existing_open_risk_pct": 0.0,
    "total_open_risk_after_pct": 0.018,
    "leverage": 3,
    "margin_mode": "isolated"
  },
  "entry_plan": {
    "entry_type": "limit|market|none",
    "entry_price": 65000.0,
    "stop_price": 64000.0,
    "invalidation": "4H reclaim failed",
    "size_base": 0.001,
    "notional_usdt": 65.0,
    "take_profit_policy": "scale_out_1_5R_3R_trail"
  },
  "guardrails": {
    "no_averaging_down": true,
    "mae_stop_add_pct": -0.05,
    "mae_cut_half_pct": -0.08,
    "mae_exit_pct": -0.12,
    "time_stop_days": [3, 7, 14]
  },
  "validator": {
    "status": "PASS|REJECTED",
    "violations": []
  },
  "rationale": [
    "Short reason 1",
    "Short reason 2"
  ]
}
```

## Rejection Format

Use `NO_TRADE` when data is incomplete or the setup is invalid.

```json
{
  "decision": "NO_TRADE",
  "side": "none",
  "validator": {
    "status": "REJECTED",
    "violations": ["mixed_regime_campaign_forbidden"]
  }
}
```

## Decision IDs

Use deterministic IDs:

`{timestamp}-{exchange}-{symbol}-{decision}`

Example:

`2026-04-20T00:00:00Z-OKX-BTC-USDT-SWAP-OPEN_PROBE`
