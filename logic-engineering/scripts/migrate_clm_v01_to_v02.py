#!/usr/bin/env python3
"""将常见 CLM v0.1 形态迁移为 v0.2 严格结构。

只执行确定性迁移：规则表达式、集合值、Action target/value 和简单 Scenario assignment。
无法确定类型时保留 literal，并由 Validator / 人工继续处理。
"""

from __future__ import annotations

import argparse
import copy
import json
from pathlib import Path
from typing import Any, Dict

from clm_model import iter_nodes


OP_MAP = {
    "==": "eq", "eq": "eq",
    "!=": "ne", "ne": "ne",
    "<": "lt", "lt": "lt",
    "<=": "le", "lte": "le", "le": "le",
    ">": "gt", "gt": "gt",
    ">=": "ge", "gte": "ge", "ge": "ge",
    "in": "in", "not_in": "not_in",
}


def load_json(path: Path) -> Dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def typed_scalar(value: Any, *, prefer_ref: bool = False) -> Dict[str, Any]:
    if isinstance(value, dict) and any(k in value for k in ("ref", "literal", "enum", "null")):
        return value
    if prefer_ref and isinstance(value, str) and "." in value:
        return {"ref": value}
    return {"literal": value}


def typed_value(value: Any, *, prefer_ref: bool = False) -> Dict[str, Any]:
    if isinstance(value, dict) and any(k in value for k in ("ref", "literal", "enum", "null", "set")):
        return value
    if isinstance(value, list):
        return {"set": [typed_scalar(item) for item in value]}
    return typed_scalar(value, prefer_ref=prefer_ref)


def migrate_expr(expr: Any) -> Any:
    if not isinstance(expr, dict):
        return expr
    op = expr.get("op") or expr.get("operator")
    if op in {"all", "any"}:
        children = expr.get("items", expr.get("args", expr.get("conditions", []))) or []
        return {"op": op, "items": [migrate_expr(child) for child in children]}
    if op == "not":
        child = expr.get("item", expr.get("arg", expr.get("condition")))
        return {"op": "not", "item": migrate_expr(child)}
    normalized_op = OP_MAP.get(op)
    if normalized_op:
        left = expr.get("left", expr.get("subject"))
        right = expr.get("right", expr.get("value"))
        return {
            "op": normalized_op,
            "left": typed_scalar(left, prefer_ref=True),
            "right": typed_value(right),
        }
    return expr


def migrate_scenario_entry(entry: Any) -> Any:
    if isinstance(entry, dict) and "target" in entry and "value" in entry:
        target = entry["target"]
        return {
            "target": typed_scalar(target, prefer_ref=True),
            "value": typed_value(entry["value"]),
        }
    if isinstance(entry, str) and "=" in entry:
        left, right = entry.split("=", 1)
        return {
            "target": typed_scalar(left.strip(), prefer_ref=True),
            "value": typed_value(right.strip()),
        }
    return entry


def migrate(document: Dict[str, Any]) -> Dict[str, Any]:
    result = copy.deepcopy(document)
    for _, node in iter_nodes(result):
        kind = node.get("kind")
        if kind == "rule" and "expression" not in node and "subject" in node:
            node["expression"] = migrate_expr({
                "operator": node.get("operator"),
                "subject": node.get("subject"),
                "value": node.get("value"),
            })
            node.pop("subject", None)
            node.pop("operator", None)
            node.pop("value", None)
            node.pop("conditions", None)

        for key in ("when", "expression", "guard", "condition"):
            if key in node and isinstance(node[key], dict):
                node[key] = migrate_expr(node[key])

        if kind == "action":
            if isinstance(node.get("target"), str):
                node["target"] = typed_scalar(node["target"], prefer_ref=True)
            if "value" in node:
                node["value"] = typed_value(node["value"])
        elif kind == "foreach":
            if isinstance(node.get("collection"), str):
                node["collection"] = typed_scalar(node["collection"], prefer_ref=True)

        if kind == "scenario":
            node["given"] = [migrate_scenario_entry(item) for item in node.get("given", [])]
            migrated_then = []
            for item in node.get("then", node.get("expect", [])):
                migrated_then.append(migrate_scenario_entry(item))
            node["then"] = migrated_then
            node.pop("expect", None)

    root = result.get("clm", result)
    root["version"] = "0.2"
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description="迁移 CLM v0.1 → v0.2")
    parser.add_argument("input", type=Path)
    parser.add_argument("-o", "--output", type=Path, required=True)
    args = parser.parse_args()
    try:
        source = load_json(args.input)
        migrated = migrate(source)
        args.output.write_text(json.dumps(migrated, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    except (OSError, json.JSONDecodeError, ValueError) as exc:
        print(json.dumps({"ok": False, "error": str(exc)}, ensure_ascii=False))
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
