#!/usr/bin/env python3
"""构建 CLM Symbol Table，并提供基础类型解析。"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Dict, Iterable, Optional

from clm_model import iter_nodes


BUILTIN_TYPES = {
    "string",
    "boolean",
    "integer",
    "number",
    "datetime",
    "date",
    "duration",
}


def load_json(path: Path) -> Dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def build_symbol_table(clm: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
    table: Dict[str, Dict[str, Any]] = {}
    for collection, node in iter_nodes(clm):
        node_id = node.get("id")
        if not isinstance(node_id, str) or not node_id:
            continue
        kind = node.get("kind")
        entry = {
            "id": node_id,
            "kind": kind,
            "collection": collection,
            "type": node.get("type"),
            "nullable": node.get("nullable"),
            "cardinality": node.get("cardinality"),
            "owner": node.get("owner"),
        }
        if kind == "enum":
            entry["type"] = node_id
            entry["enum_values"] = list(node.get("values", []) or [])
        if kind == "value_type":
            entry["type"] = node_id
            entry["base_type"] = node.get("base_type")
        table[node_id] = entry

        if kind == "entity":
            for field in node.get("fields", []) or []:
                if not isinstance(field, dict):
                    continue
                field_id = field.get("id")
                if not isinstance(field_id, str) or not field_id:
                    continue
                table[field_id] = {
                    "id": field_id,
                    "kind": "field",
                    "collection": "domain",
                    "type": field.get("type"),
                    "nullable": field.get("nullable", False),
                    "cardinality": field.get("cardinality", "one"),
                    "owner": node_id,
                }
    return table


def resolve_type(table: Dict[str, Dict[str, Any]], semantic_id: str) -> Optional[str]:
    entry = table.get(semantic_id)
    if not entry:
        return None
    return entry.get("type")


def is_enum_type(table: Dict[str, Dict[str, Any]], type_id: Optional[str]) -> bool:
    if not type_id:
        return False
    entry = table.get(type_id)
    return bool(entry and entry.get("kind") == "enum")


def enum_contains(table: Dict[str, Dict[str, Any]], type_id: str, value: Any) -> bool:
    entry = table.get(type_id)
    return bool(entry and value in (entry.get("enum_values") or []))


def compatible_types(left: Optional[str], right: Optional[str]) -> bool:
    if left is None or right is None:
        return True
    if left == right:
        return True
    numeric = {"integer", "number"}
    return left in numeric and right in numeric


def main() -> int:
    parser = argparse.ArgumentParser(description="构建 CLM Symbol Table")
    parser.add_argument("clm", type=Path)
    parser.add_argument("-o", "--output", type=Path)
    args = parser.parse_args()

    try:
        table = build_symbol_table(load_json(args.clm))
    except (OSError, json.JSONDecodeError) as exc:
        print(json.dumps({"ok": False, "error": str(exc)}, ensure_ascii=False, indent=2))
        return 1

    text = json.dumps({"symbols": table}, ensure_ascii=False, indent=2)
    if args.output:
        args.output.write_text(text + "\n", encoding="utf-8")
    else:
        print(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
