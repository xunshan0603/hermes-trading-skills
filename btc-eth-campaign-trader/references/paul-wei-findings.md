# Paul Wei Ledger Findings

Use these facts as strategy memory, not as mythology.

## Data Source

The public `bwjoke/BTC-Trading-Since-2020` repository exposes BitMEX orders, executions, wallet history, snapshots, instrument metadata, and a derived XBT-equivalent equity curve.

Validated local research artifacts:

- `tradeHistory`: 173,058 rows.
- `order`: 43,214 rows.
- `walletHistory`: 17,099 rows.
- Period: 2020-05-01 to 2026-04-17.
- Adjusted wealth: 1.83953943 XBT to 96.38685218 XBT, about 52.40x.
- Major account jump occurred in 2020-2021.
- Later behavior became more BTC-concentrated and lower-frequency.

## Core Ledger Lessons

1. The strategy is campaign-based, not single-fill based. Large trades contain many adds, reductions, partial exits, and occasional flips.
2. BTC is the main battlefield. Later years are overwhelmingly BTC-concentrated.
3. The repeatable edge is regime alignment:
   - Bull-regime longs and bear-regime shorts have strong positive expectancy.
   - Bull-regime shorts and mixed-regime longs are clear leakage zones.
4. The strategy is right-tail dominated. Removing the largest winners destroys the result.
5. The biggest losses come from wrong-way campaigns held too long.
6. Deep adverse excursion is destructive. Once underlying adverse movement reaches roughly -8% to -12%, rescue behavior tends to harm expectancy.
7. Profit extraction matters. Large withdrawals were part of survival, not an afterthought.

## Research Numbers To Preserve

XBTUSD campaign reconstruction with BitMEX daily/hourly candles:

- Closed campaigns: 687.
- Estimated net including available funding: about +43.04 XBT.
- Win rate: about 59.7%.
- Profit factor: about 1.36.
- Bull long: about +17.88 XBT, PF about 2.03.
- Bear short: about +20.31 XBT, PF about 2.13.
- Bull short: about -7.43 XBT, PF about 0.70.
- Mixed long: about -5.36 XBT, PF about 0.87.
- Skip mixed + skip bull shorts: about +46.38 XBT, PF about 1.95.
- Aligned regime with MAE better than -8%: about +42.41 XBT, PF about 2.96.

## Interpretation

Do not copy early extreme drawdowns. Distill the mature lesson:

Full risk only when the higher-timeframe BTC regime agrees. Avoid forcing trades in mixed regimes. Cut wrong-way campaigns before they become identity trades.
