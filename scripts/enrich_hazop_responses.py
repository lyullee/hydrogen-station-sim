"""Persist scenario-specific emergency and prevention stages in the HAZOP DB.

Run with PYTHONPATH=src. Existing alarm thresholds, gates and sensors are kept.
The migration is idempotent and updates the 214 rule payloads in one transaction.
"""
from __future__ import annotations

import json
import sqlite3

from h2station.hazop.database import DEFAULT_DB
from h2station.hazop.response import classify_rule, load_playbooks
from h2station.hazop.scenario_actions import build_rule_guidance


def main() -> None:
    data = load_playbooks()
    plans = {plan["id"]: plan for plan in data["plans"]}
    with sqlite3.connect(DEFAULT_DB, timeout=20) as db:
        db.execute("CREATE TABLE IF NOT EXISTS response_actions (rule_id TEXT PRIMARY KEY, payload TEXT NOT NULL)")
        nodes = {node["node_id"]: node for _, payload in db.execute("SELECT id,payload FROM nodes")
                 if (node := json.loads(payload))}
        count = 0
        for rule_id, payload in db.execute("SELECT id,payload FROM rules ORDER BY id").fetchall():
            rule = json.loads(payload)
            plan_id = classify_rule(rule)
            node_name = nodes.get(rule["node_id"], {}).get("설비_라인", rule["node_id"])
            guidance = build_rule_guidance(rule, node_name, plans[plan_id])
            rule["대응유형"] = plan_id
            rule["비상대응_단계"] = guidance["stages"]
            rule["안전관리_방안"] = guidance["stages"]["prevention"]
            rule["대응근거_출처"] = guidance["source_ids"]
            rule["대응검토상태"] = guidance["scope"]
            db.execute("UPDATE rules SET payload=? WHERE id=?",
                       (json.dumps(rule, ensure_ascii=False), rule_id))
            db.execute("INSERT OR REPLACE INTO response_actions VALUES (?,?)",
                       (rule_id, json.dumps(guidance, ensure_ascii=False)))
            count += 1
        db.execute("INSERT OR REPLACE INTO metadata VALUES (?,?)",
                   ("response_actions_version", json.dumps(data["version"])))
    print(f"Enriched {count} HAZOP rule responses in {DEFAULT_DB}")


if __name__ == "__main__":
    main()
