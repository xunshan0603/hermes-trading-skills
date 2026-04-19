#!/usr/bin/env python3
"""Classify BTC/ETH daily regime from OHLC candles.

Input JSON shape:
{
  "symbols": {
    "BTC-USDT-SWAP": {
      "daily": [{"time": "...", "open": 1, "high": 1, "low": 1, "close": 1}, ...]
    }
  }
}
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


def moving_average(values: list[float], window: int) -> float | None:
    if len(values) < window:
        return None
    return sum(values[-window:]) / window


def classify(candles: list[dict]) -> dict:
    closes = [float(c["close"]) for c in candles if c.get("close") is not None]
    if len(closes) < 60:
        return {
            "regime": "unknown",
            "status": "insufficient_data",
            "close": closes[-1] if closes else None,
            "ma20": None,
            "ma60": None,
            "reason": "Need at least 60 completed daily candles.",
        }
    close = closes[-1]
    ma20 = moving_average(closes, 20)
    ma60 = moving_average(closes, 60)
    if close > ma20 > ma60:
        regime = "bull"
    elif close < ma20 < ma60:
        regime = "bear"
    else:
        regime = "mixed"
    return {
        "regime": regime,
        "status": "ok",
        "close": close,
        "ma20": ma20,
        "ma60": ma60,
        "reason": "bull if close > MA20 > MA60; bear if close < MA20 < MA60; otherwise mixed.",
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Classify BTC/ETH campaign regime.")
    parser.add_argument("market_state", help="Path to market-state JSON.")
    parser.add_argument("--symbol", action="append", help="Symbol to classify. Repeatable. Defaults to all symbols.")
    args = parser.parse_args()

    with Path(args.market_state).open(encoding="utf-8") as handle:
        data = json.load(handle)

    symbols = data.get("symbols", {})
    wanted = args.symbol or list(symbols.keys())
    result = {"timestamp": data.get("timestamp"), "symbols": {}}
    for symbol in wanted:
        if symbol not in symbols:
            result["symbols"][symbol] = {"regime": "unknown", "status": "missing_symbol"}
            continue
        result["symbols"][symbol] = classify(symbols[symbol].get("daily", []))

    json.dump(result, sys.stdout, indent=2, ensure_ascii=False)
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
