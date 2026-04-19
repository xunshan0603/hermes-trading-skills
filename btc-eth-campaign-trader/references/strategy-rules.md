# Strategy Rules

## Instruments

Primary:

- `BTC-USDT-SWAP`
- `ETH-USDT-SWAP`

Treat BTC as master regime. Treat ETH as a satellite instrument that may trade only when BTC permits the campaign direction.

## Regime

Use the previous completed daily candle:

- `bull`: close > MA20 > MA60
- `bear`: close < MA20 < MA60
- `mixed`: all other states

## Trade Permissions

BTC:

- BTC bull: full-size long campaign allowed.
- BTC bear: full-size short campaign allowed.
- BTC mixed: no campaign; probe only or no trade.

ETH:

- ETH long campaign requires BTC bull and ETH bull or ETH reclaiming MA20 with BTC bull.
- ETH short campaign requires BTC bear and ETH bear or ETH losing MA20 with BTC bear.
- ETH may not fight BTC master regime at full size.
- ETH risk must be smaller than BTC risk because Paul Wei's durable edge was BTC-led.

## Entry Models

Use one of these models only:

1. Trend pullback continuation:
   - Regime agrees.
   - Price pulls back to MA20, prior breakout, VWAP zone, or 4H structure.
   - Lower timeframe reclaims structure.

2. Breakout retest:
   - Regime agrees.
   - Daily or 4H range breaks.
   - Retest holds.
   - Enter probe; add only after continuation.

3. Extreme reversal probe:
   - Use only 25% size.
   - Requires liquidation-style move and fast reclaim.
   - Must not become campaign unless daily regime flips.

## Position Ladder

- 25% probe: initial valid setup.
- 50%: after 1R floating profit and structure holds.
- 75%: after next structural continuation.
- 100%: only when stop can be trailed near breakeven or better.

Never add to a losing campaign. Never increase risk after invalidation.

## Exits

Scale out:

- Take partial profit near 1.5R.
- Take another partial near 3R.
- Trail remainder with 4H structure or daily MA20 depending on campaign maturity.

Forced exit:

- Stop price hit.
- Regime flips against position.
- MAE circuit breaker triggers.
- Time stop triggers.
- Account drawdown guard triggers.
- Validator rejects updated state.

## ETH-Specific Rule

ETH is allowed to outperform, but it is not allowed to overrule BTC. If BTC is mixed, ETH can only probe. If BTC is bull, ETH shorts are tactical only. If BTC is bear, ETH longs are tactical only.
