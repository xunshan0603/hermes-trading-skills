#!/usr/bin/env python3
"""Size a linear USDT perpetual position from account risk."""

from __future__ import annotations

import argparse
import json
import sys


def calculate(equity: float, risk_pct: float, entry: float, stop: float, leverage: float) -> dict:
    if equity <= 0:
        raise ValueError("equity must be positive")
    if not (0 < risk_pct <= 0.05):
        raise ValueError("risk_pct must be between 0 and 0.05")
    if entry <= 0 or stop <= 0:
        raise ValueError("entry and stop must be positive")
    if leverage <= 0:
        raise ValueError("leverage must be positive")
    stop_distance_pct = abs(entry - stop) / entry
    if stop_distance_pct <= 0:
        raise ValueError("stop distance must be positive")
    max_loss_usdt = equity * risk_pct
    notional_usdt = max_loss_usdt / stop_distance_pct
    margin_usdt = notional_usdt / leverage
    size_base = notional_usdt / entry
    return {
        "account_equity_usdt": equity,
        "risk_pct": risk_pct,
        "max_loss_usdt": max_loss_usdt,
        "entry_price": entry,
        "stop_price": stop,
        "stop_distance_pct": stop_distance_pct,
        "leverage": leverage,
        "notional_usdt": notional_usdt,
        "margin_usdt": margin_usdt,
        "size_base": size_base,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Calculate OKX linear swap position size.")
    parser.add_argument("--equity", type=float, required=True)
    parser.add_argument("--risk-pct", type=float, required=True)
    parser.add_argument("--entry", type=float, required=True)
    parser.add_argument("--stop", type=float, required=True)
    parser.add_argument("--leverage", type=float, default=3.0)
    args = parser.parse_args()

    try:
        result = calculate(args.equity, args.risk_pct, args.entry, args.stop, args.leverage)
    except ValueError as exc:
        json.dump({"status": "ERROR", "error": str(exc)}, sys.stdout, indent=2)
        sys.stdout.write("\n")
        return 2

    json.dump({"status": "OK", "sizing": result}, sys.stdout, indent=2)
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
