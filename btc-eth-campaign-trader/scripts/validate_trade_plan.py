#!/usr/bin/env python3
"""Validate a BTC/ETH campaign trade plan before execution."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


ALLOWED_SYMBOLS = {"BTC-USDT-SWAP", "ETH-USDT-SWAP"}
OPEN_DECISIONS = {"OPEN_PROBE", "OPEN_CAMPAIGN", "SCALE_IN"}
EXECUTABLE_DECISIONS = OPEN_DECISIONS | {"SCALE_OUT", "EXIT"}
ALL_DECISIONS = EXECUTABLE_DECISIONS | {"NO_TRADE", "HOLD", "COOLDOWN"}


def get_nested(data: dict, path: str, default=None):
    cur = data
    for part in path.split("."):
        if not isinstance(cur, dict) or part not in cur:
            return default
        cur = cur[part]
    return cur


def validate(plan: dict, allow_live: bool = False) -> dict:
    violations: list[str] = []

    symbol = plan.get("symbol")
    decision = plan.get("decision")
    side = plan.get("side")
    mode = plan.get("mode")
    exchange = plan.get("exchange")
    btc_regime = get_nested(plan, "regime.btc", "unknown")
    eth_regime = get_nested(plan, "regime.eth", "unknown")
    symbol_regime = get_nested(plan, "regime.symbol", "unknown")
    risk_pct = float(get_nested(plan, "risk.risk_pct", 0) or 0)
    total_open_risk = float(get_nested(plan, "risk.total_open_risk_after_pct", risk_pct) or 0)
    leverage = float(get_nested(plan, "risk.leverage", 0) or 0)
    margin_mode = get_nested(plan, "risk.margin_mode", "")
    entry = float(get_nested(plan, "entry_plan.entry_price", 0) or 0)
    stop = float(get_nested(plan, "entry_plan.stop_price", 0) or 0)
    no_averaging = bool(get_nested(plan, "guardrails.no_averaging_down", False))

    if exchange != "OKX":
        violations.append("exchange_must_be_OKX")
    if symbol not in ALLOWED_SYMBOLS:
        violations.append("unsupported_symbol")
    if decision not in ALL_DECISIONS:
        violations.append("unsupported_decision")
    if side not in {"long", "short", "none"}:
        violations.append("invalid_side")
    if mode == "live" and not allow_live:
        violations.append("live_requires_allow_live")
    if mode not in {"paper", "testnet", "live"}:
        violations.append("invalid_mode")
    if margin_mode != "isolated" and decision in EXECUTABLE_DECISIONS:
        violations.append("isolated_margin_required")
    if leverage <= 0 and decision in EXECUTABLE_DECISIONS:
        violations.append("leverage_required")
    if leverage > 5:
        violations.append("leverage_exceeds_5x")
    if risk_pct > 0.02:
        violations.append("risk_pct_exceeds_2pct")
    if total_open_risk > 0.04:
        violations.append("total_open_risk_exceeds_4pct")
    if not no_averaging and decision in OPEN_DECISIONS:
        violations.append("no_averaging_down_required")

    if decision in EXECUTABLE_DECISIONS:
        if side == "none":
            violations.append("executable_decision_requires_side")
        if entry <= 0:
            violations.append("entry_price_required")
        if stop <= 0:
            violations.append("stop_price_required")
        if side == "long" and stop >= entry:
            violations.append("long_stop_must_be_below_entry")
        if side == "short" and stop <= entry:
            violations.append("short_stop_must_be_above_entry")

    if decision in {"OPEN_CAMPAIGN", "SCALE_IN"}:
        if symbol == "BTC-USDT-SWAP":
            if side == "long" and btc_regime != "bull":
                violations.append("btc_long_campaign_requires_btc_bull")
            if side == "short" and btc_regime != "bear":
                violations.append("btc_short_campaign_requires_btc_bear")
        if symbol == "ETH-USDT-SWAP":
            if side == "long" and not (btc_regime == "bull" and eth_regime in {"bull", "mixed"} and symbol_regime != "bear"):
                violations.append("eth_long_campaign_requires_btc_bull_and_eth_not_bear")
            if side == "short" and not (btc_regime == "bear" and eth_regime in {"bear", "mixed"} and symbol_regime != "bull"):
                violations.append("eth_short_campaign_requires_btc_bear_and_eth_not_bull")

    if decision == "OPEN_PROBE":
        counter_regime = (
            (side == "long" and btc_regime == "bear")
            or (side == "short" and btc_regime == "bull")
            or btc_regime == "mixed"
        )
        if counter_regime and risk_pct > 0.005:
            violations.append("counter_or_mixed_probe_risk_exceeds_0_5pct")

    status = "PASS" if not violations else "REJECTED"
    return {"status": status, "violations": violations}


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate BTC/ETH campaign trade plan.")
    parser.add_argument("plan", help="Path to trade-plan JSON.")
    parser.add_argument("--allow-live", action="store_true", help="Permit mode=live plans.")
    args = parser.parse_args()

    with Path(args.plan).open(encoding="utf-8") as handle:
        plan = json.load(handle)
    result = validate(plan, allow_live=args.allow_live)
    output = {"validator": result, "decision_id": plan.get("decision_id"), "decision": plan.get("decision")}
    json.dump(output, sys.stdout, indent=2, ensure_ascii=False)
    sys.stdout.write("\n")
    return 0 if result["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
