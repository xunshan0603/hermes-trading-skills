#!/usr/bin/env python3
"""Safe OKX adapter for Hermes/OpenClaw trade plans.

This adapter intentionally gates execution behind:
1. validate_trade_plan.py
2. config live/dry-run switches
3. account/market/instrument sanity checks

It uses OKX API v5 request signing. API secrets must be supplied through
environment variables, never through the Skill text.
"""

from __future__ import annotations

import argparse
import base64
import hashlib
import hmac
import json
import math
import os
import re
import subprocess
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


SCRIPT_DIR = Path(__file__).resolve().parent
VALIDATOR = SCRIPT_DIR / "validate_trade_plan.py"


class AdapterError(RuntimeError):
    pass


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")


def parse_iso(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def load_json(path: Path) -> dict[str, Any]:
    with path.open(encoding="utf-8") as handle:
        return json.load(handle)


def write_jsonl(path: Path, record: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(record, ensure_ascii=False, separators=(",", ":")) + "\n")


def load_dotenv(path: Path) -> None:
    if not path.exists():
        return
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


def decimal_places(step: float) -> int:
    text = f"{step:.16f}".rstrip("0")
    if "." not in text:
        return 0
    return len(text.split(".", 1)[1])


def round_down(value: float, step: float) -> float:
    if step <= 0:
        return value
    return math.floor(value / step) * step


class OKXClient:
    def __init__(self, config: dict[str, Any]):
        self.base_url = config.get("base_url", "https://www.okx.com").rstrip("/")
        self.use_testnet = bool(config.get("use_testnet", False))
        self.key = os.environ.get("OKX_API_KEY", "")
        self.secret = os.environ.get("OKX_API_SECRET", "")
        self.passphrase = os.environ.get("OKX_API_PASSPHRASE", "")

    def _headers(self, method: str, path: str, body: str, auth: bool) -> dict[str, str]:
        headers = {"Content-Type": "application/json"}
        if self.use_testnet and auth:
            headers["x-simulated-trading"] = "1"
        if not auth:
            return headers
        if not (self.key and self.secret and self.passphrase):
            raise AdapterError("missing_okx_api_credentials")
        timestamp = utc_now_iso()
        prehash = f"{timestamp}{method.upper()}{path}{body}"
        digest = hmac.new(self.secret.encode(), prehash.encode(), hashlib.sha256).digest()
        headers.update(
            {
                "OK-ACCESS-KEY": self.key,
                "OK-ACCESS-SIGN": base64.b64encode(digest).decode(),
                "OK-ACCESS-TIMESTAMP": timestamp,
                "OK-ACCESS-PASSPHRASE": self.passphrase,
            }
        )
        return headers

    def request(self, method: str, path: str, payload: dict[str, Any] | None = None, auth: bool = False) -> dict[str, Any]:
        body = json.dumps(payload, separators=(",", ":")) if payload else ""
        req = urllib.request.Request(
            self.base_url + path,
            data=body.encode() if body else None,
            headers=self._headers(method, path, body, auth),
            method=method.upper(),
        )
        try:
            with urllib.request.urlopen(req, timeout=20) as response:
                data = json.loads(response.read().decode())
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode(errors="replace")
            raise AdapterError(f"okx_http_error:{exc.code}:{detail}") from exc
        except urllib.error.URLError as exc:
            raise AdapterError(f"okx_network_error:{exc}") from exc
        if data.get("code") not in ("0", 0, None):
            raise AdapterError(f"okx_api_error:{data}")
        return data

    def get_ticker(self, inst_id: str) -> dict[str, Any]:
        q = urllib.parse.urlencode({"instId": inst_id})
        data = self.request("GET", f"/api/v5/market/ticker?{q}")
        rows = data.get("data") or []
        if not rows:
            raise AdapterError("ticker_not_found")
        return rows[0]

    def get_instrument(self, inst_id: str) -> dict[str, Any]:
        q = urllib.parse.urlencode({"instType": "SWAP", "instId": inst_id})
        data = self.request("GET", f"/api/v5/public/instruments?{q}")
        rows = data.get("data") or []
        if not rows:
            raise AdapterError("instrument_not_found")
        return rows[0]

    def get_balance(self) -> dict[str, Any]:
        return self.request("GET", "/api/v5/account/balance", auth=True)

    def get_positions(self, inst_id: str) -> dict[str, Any]:
        q = urllib.parse.urlencode({"instId": inst_id})
        return self.request("GET", f"/api/v5/account/positions?{q}", auth=True)

    def get_open_orders(self, inst_id: str) -> dict[str, Any]:
        q = urllib.parse.urlencode({"instType": "SWAP", "instId": inst_id})
        return self.request("GET", f"/api/v5/trade/orders-pending?{q}", auth=True)

    def set_leverage(self, inst_id: str, leverage: str, margin_mode: str) -> dict[str, Any]:
        payload = {"instId": inst_id, "lever": leverage, "mgnMode": margin_mode}
        return self.request("POST", "/api/v5/account/set-leverage", payload, auth=True)

    def place_order(self, order: dict[str, Any]) -> dict[str, Any]:
        return self.request("POST", "/api/v5/trade/order", order, auth=True)


def run_validator(plan_path: Path, allow_live: bool) -> dict[str, Any]:
    cmd = [sys.executable, str(VALIDATOR), str(plan_path)]
    if allow_live:
        cmd.append("--allow-live")
    proc = subprocess.run(cmd, capture_output=True, text=True)
    try:
        result = json.loads(proc.stdout)
    except json.JSONDecodeError as exc:
        raise AdapterError(f"validator_invalid_output:{proc.stdout}:{proc.stderr}") from exc
    if proc.returncode != 0:
        return result
    return result


def check_plan_age(plan: dict[str, Any], max_age_seconds: int) -> None:
    ts = plan.get("timestamp")
    if not ts:
        raise AdapterError("missing_plan_timestamp")
    age = (datetime.now(timezone.utc) - parse_iso(ts)).total_seconds()
    if age > max_age_seconds:
        raise AdapterError(f"stale_plan:{age:.1f}s>{max_age_seconds}s")
    if age < -30:
        raise AdapterError(f"plan_timestamp_in_future:{age:.1f}s")


def get_nested(data: dict[str, Any], path: str, default=None):
    cur = data
    for part in path.split("."):
        if not isinstance(cur, dict) or part not in cur:
            return default
        cur = cur[part]
    return cur


def plan_to_order(
    plan: dict[str, Any],
    config: dict[str, Any],
    instrument: dict[str, Any] | None = None,
    attach_stop: bool = True,
) -> dict[str, Any]:
    symbol = plan["symbol"]
    decision = plan["decision"]
    side = plan["side"]
    entry_type = get_nested(plan, "entry_plan.entry_type", "limit")
    entry_price = float(get_nested(plan, "entry_plan.entry_price", 0) or 0)
    stop_price = float(get_nested(plan, "entry_plan.stop_price", 0) or 0)
    td_mode = config.get("margin_mode", "isolated")

    if decision not in {"OPEN_PROBE", "OPEN_CAMPAIGN", "SCALE_IN", "SCALE_OUT", "EXIT"}:
        raise AdapterError(f"decision_not_executable:{decision}")
    if entry_type not in {"limit", "market"}:
        raise AdapterError(f"unsupported_entry_type:{entry_type}")

    if instrument:
        ct_val = float(instrument.get("ctVal") or 0)
        lot_sz = float(instrument.get("lotSz") or 1)
        min_sz = float(instrument.get("minSz") or lot_sz)
        size_base = float(get_nested(plan, "entry_plan.size_base", 0) or 0)
        if ct_val <= 0 or size_base <= 0:
            raise AdapterError("cannot_convert_size_to_contracts")
        contracts = round_down(size_base / ct_val, lot_sz)
        contracts = max(contracts, min_sz)
        decimals = decimal_places(lot_sz)
        sz = f"{contracts:.{decimals}f}" if decimals else str(int(contracts))
    else:
        # Dry-run fallback. Live/testnet execution must provide instrument metadata.
        sz = str(float(get_nested(plan, "entry_plan.size_base", 0) or 0))

    if side == "long":
        okx_side = "buy"
    elif side == "short":
        okx_side = "sell"
    else:
        raise AdapterError("executable_plan_requires_side")

    raw_client_id = str(plan.get("decision_id", ""))
    client_id = re.sub(r"[^A-Za-z0-9]", "", raw_client_id)[-31:] or str(int(time.time()))
    client_id = f"C{client_id}"

    order: dict[str, Any] = {
        "instId": symbol,
        "tdMode": td_mode,
        "side": okx_side,
        "ordType": entry_type,
        "sz": sz,
        "clOrdId": client_id,
    }
    if entry_type == "limit":
        order["px"] = str(entry_price)
    if decision in {"SCALE_OUT", "EXIT"}:
        order["reduceOnly"] = "true"
    elif config.get("require_stop", True) and attach_stop:
        if stop_price <= 0:
            raise AdapterError("stop_required")
        # OKX V5 supports attaching TP/SL algo order objects to order placement.
        # slOrdPx=-1 requests market execution when the trigger fires.
        order["attachAlgoOrds"] = [
            {
                "slTriggerPx": str(stop_price),
                "slOrdPx": "-1",
                "slTriggerPxType": "last",
            }
        ]
    return order


def assert_runtime_guards(plan: dict[str, Any], config: dict[str, Any], validator_result: dict[str, Any]) -> None:
    decision = plan.get("decision")
    mode = plan.get("mode")
    if config.get("require_validator_pass", True) and get_nested(validator_result, "validator.status") != "PASS":
        raise AdapterError(f"validator_rejected:{validator_result}")
    if mode == "live" and not config.get("allow_live", False):
        raise AdapterError("live_blocked_by_config")
    if mode == "live" and config.get("dry_run", True):
        raise AdapterError("live_blocked_by_dry_run")
    if float(get_nested(plan, "risk.leverage", 0) or 0) > float(config.get("max_leverage", 5)):
        raise AdapterError("leverage_exceeds_config")
    notional = float(get_nested(plan, "entry_plan.notional_usdt", 0) or 0)
    if notional > float(config.get("max_order_notional_usdt", 0) or 0):
        raise AdapterError("notional_exceeds_config")
    if decision in {"OPEN_PROBE", "OPEN_CAMPAIGN", "SCALE_IN"} and config.get("require_stop", True):
        if float(get_nested(plan, "entry_plan.stop_price", 0) or 0) <= 0:
            raise AdapterError("stop_required")
    if mode == "live" and config.get("allow_live", False) and not config.get("live_confirm_token"):
        raise AdapterError("live_confirm_token_missing_in_config")


def maybe_check_slippage(plan: dict[str, Any], ticker: dict[str, Any], max_slippage_pct: float) -> None:
    entry_type = get_nested(plan, "entry_plan.entry_type", "limit")
    if entry_type != "market":
        return
    entry = float(get_nested(plan, "entry_plan.entry_price", 0) or 0)
    last = float(ticker.get("last") or ticker.get("askPx") or ticker.get("bidPx") or 0)
    if entry <= 0 or last <= 0:
        raise AdapterError("cannot_check_slippage")
    if abs(last / entry - 1) > max_slippage_pct:
        raise AdapterError("market_price_slippage_exceeds_config")


def main() -> int:
    parser = argparse.ArgumentParser(description="Safe OKX adapter for validated BTC/ETH campaign plans.")
    parser.add_argument("--plan", required=True, help="Path to trade plan JSON.")
    parser.add_argument("--config", default=str(SCRIPT_DIR / "okx_adapter_config.example.json"))
    parser.add_argument("--env", default="", help="Optional .env file containing OKX credentials.")
    parser.add_argument("--allow-live", action="store_true", help="Allow validator to accept live plans.")
    parser.add_argument("--execute", action="store_true", help="Actually send order when config permits.")
    parser.add_argument("--live-confirm-token", default="", help="Required one-time token for live execution.")
    args = parser.parse_args()

    plan_path = Path(args.plan)
    config_path = Path(args.config)
    if args.env:
        load_dotenv(Path(args.env))
    plan = load_json(plan_path)
    config = load_json(config_path)
    if os.environ.get("OKX_USE_TESTNET", "").lower() in {"true", "1", "yes"}:
        config["use_testnet"] = True

    record: dict[str, Any] = {
        "adapter_time": utc_now_iso(),
        "plan_path": str(plan_path),
        "config_path": str(config_path),
        "mode": plan.get("mode"),
        "symbol": plan.get("symbol"),
        "decision": plan.get("decision"),
        "dry_run": bool(config.get("dry_run", True)) or not args.execute or plan.get("mode") == "paper",
    }

    try:
        validator_result = run_validator(plan_path, allow_live=args.allow_live or bool(config.get("allow_live", False)))
        record["validator"] = validator_result
        assert_runtime_guards(plan, config, validator_result)
        if plan.get("decision") in {"NO_TRADE", "HOLD", "COOLDOWN"}:
            record["status"] = "NO_EXECUTION_NEEDED"
            print(json.dumps(record, indent=2, ensure_ascii=False))
            return 0
        check_plan_age(plan, int(config.get("max_plan_age_seconds", 300)))

        client = OKXClient(config)
        dry_run = bool(record["dry_run"])
        instrument = None
        ticker = None
        if dry_run and config.get("fetch_public_in_dry_run", True):
            try:
                ticker = client.get_ticker(plan["symbol"])
                instrument = client.get_instrument(plan["symbol"])
                record["public_dry_run_data"] = {"ticker": ticker, "instrument": instrument}
            except Exception as exc:  # noqa: BLE001 - public dry-run data is helpful but optional.
                record["public_dry_run_warning"] = str(exc)

        if not dry_run:
            if plan.get("mode") == "live":
                expected_token = str(config.get("live_confirm_token", ""))
                if not expected_token or args.live_confirm_token != expected_token:
                    raise AdapterError("live_confirm_token_mismatch")
            ticker = client.get_ticker(plan["symbol"])
            instrument = client.get_instrument(plan["symbol"])
            record["account_balance_check"] = client.get_balance()
            record["positions_check"] = client.get_positions(plan["symbol"])
            try:
                record["open_orders_check"] = client.get_open_orders(plan["symbol"])
            except Exception as exc:  # noqa: BLE001 - not all API keys expose pending-order reads.
                record["open_orders_warning"] = str(exc)
            leverage = str(int(float(get_nested(plan, "risk.leverage", config.get("default_leverage", 1)))))
            td_mode = config.get("margin_mode", "isolated")
            record["set_leverage_request"] = {"instId": plan["symbol"], "lever": leverage, "mgnMode": td_mode}
            record["set_leverage_response"] = client.set_leverage(plan["symbol"], leverage, td_mode)
            maybe_check_slippage(plan, ticker, float(config.get("max_slippage_pct", 0.003)))
        attach_stop = bool(config.get("attach_stop_to_order", True))
        order = plan_to_order(plan, config, instrument=instrument, attach_stop=attach_stop)
        record["order_request"] = order
        if config.get("require_stop", True) and not attach_stop and plan.get("decision") not in {"SCALE_OUT", "EXIT"}:
            record["stop_notice"] = "Stop is required by plan, but attach_stop_to_order=false. Place a separate protective stop immediately after main-order acceptance."

        if dry_run:
            record["status"] = "DRY_RUN"
            record["message"] = "Order was not sent. Set config dry_run=false, mode live/testnet, and pass --execute when ready."
        else:
            response = client.place_order(order)
            record["status"] = "SENT"
            record["okx_response"] = response

    except Exception as exc:  # noqa: BLE001 - adapter must journal all failures.
        record["status"] = "REJECTED"
        record["error"] = str(exc)
        print(json.dumps(record, indent=2, ensure_ascii=False))
        journal = config.get("journal_path")
        if journal:
            write_jsonl((config_path.parent / journal).resolve() if not Path(journal).is_absolute() else Path(journal), record)
        return 1

    journal = config.get("journal_path")
    if journal:
        write_jsonl((config_path.parent / journal).resolve() if not Path(journal).is_absolute() else Path(journal), record)
    print(json.dumps(record, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
