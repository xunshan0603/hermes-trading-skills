#!/usr/bin/env python3
"""Append a trade decision to a JSONL journal."""

from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser(description="Append normalized decision JSON to journal.")
    parser.add_argument("decision_json", help="Path to decision JSON.")
    parser.add_argument("--journal", required=True, help="Path to JSONL journal.")
    args = parser.parse_args()

    decision_path = Path(args.decision_json)
    raw = decision_path.read_bytes()
    decision = json.loads(raw.decode("utf-8"))
    record = {
        "journaled_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "source_path": str(decision_path),
        "source_sha256": hashlib.sha256(raw).hexdigest(),
        "decision": decision,
    }
    journal_path = Path(args.journal)
    journal_path.parent.mkdir(parents=True, exist_ok=True)
    with journal_path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(record, ensure_ascii=False, separators=(",", ":")) + "\n")
    print(json.dumps({"status": "OK", "journal": str(journal_path)}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
