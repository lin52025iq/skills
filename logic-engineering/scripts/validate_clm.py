#!/usr/bin/env python3
"""CLM v0.1 基础校验器。

当前实现目标：
1. 读取 CLM JSON；
2. 可选使用 jsonschema 执行结构校验；
3. 执行跨节点语义校验；
4. 输出稳定错误码，供 Skill、CI 或后续工具链调用。

用法：
    python logic-engineering/scripts/validate_clm.py model.json
    python logic-engineering/scripts/validate_clm.py model.json --schema logic-engineering/schemas/clm-v0.1.schema.json

退出码：
    0 = 校验通过
    1 = 模型存在错误
    2 = 输入、解析或工具使用错误
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Iterable


REFERENCE_KEYS = {
    "preconditions",
    "flow",
    "postconditions",
    "failures",
    "then",
    "else",
    "transitions",
    "trigger",
    "effects",
    "source",
    "target",
    "supports",
    "evidence_refs",
}

KNOWN_NODE_COLLECTIONS = (
    "domain",
    "behaviors",
    "rules",
    "actions",
    "decisions",
    "states",
    "effects",
    "constraints",
    "scenarios",
    "primitives",
    "evidence",
)


class ValidationResult:
    def __init__(self) -> None:
        self.errors: list[dict[str, Any]] = []
        self.warnings: list[dict[str, Any]] = []

    def error(self, code: str, message: str, semantic_id: str | None = None, path: str | None = None) -> None:
        item: dict[str, Any] = {"code": code, "message": message}
        if semantic_id:
            item["semantic_id"] = semantic_id
        if path:
            item["path"] = path
        self.errors.append(item)

    def warning(self, code: str, message: str, semantic_id: str | None = None, path: str | None = None) -> None:
        item: dict[str, Any] = {"code": code, "message": message}
        if semantic_id:
            item["semantic_id"] = semantic_id
        if path:
            item["path"] = path
        self.warnings.append(item)


def load_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def iter_nodes(clm: dict[str, Any]) -> Iterable[tuple[str, dict[str, Any]]]:
    for collection in KNOWN_NODE_COLLECTIONS:
        values = clm.get(collection, [])
        if not isinstance(values, list):
            continue
        for node in values:
            if isinstance(node, dict):
                yield collection, node


def build_index(clm: dict[str, Any], result: ValidationResult) -> dict[str, dict[str, Any]]:
    index: dict[str, dict[str, Any]] = {}
    for collection, node in iter_nodes(clm):
        semantic_id = node.get("id")
        if not isinstance(semantic_id, str) or not semantic_id:
            continue
        if semantic_id in index:
            result.error(
                "DUPLICATE_SEMANTIC_ID",
                f"语义 ID 重复：{semantic_id}",
                semantic_id,
                collection,
            )
            continue
        index[semantic_id] = node
    return index


def is_semantic_ref(value: Any) -> bool:
    if not isinstance(value, str):
        return False
    prefixes = (
        "domain.",
        "type.",
        "behavior.",
        "rule.",
        "action.",
        "decision.",
        "state.",
        "state_machine.",
        "transition.",
        "effect.",
        "constraint.",
        "invariant.",
        "scenario.",
        "primitive.",
        "evidence.",
        "error.",
        "event.",
    )
    return value.startswith(prefixes)


def validate_reference(index: dict[str, dict[str, Any]], result: ValidationResult, owner_id: str, path: str, ref: Any) -> None:
    if isinstance(ref, str) and is_semantic_ref(ref) and ref not in index:
        # error.* / event.* may be external until first-class node kinds are added.
        if ref.startswith(("error.", "event.")):
            result.warning(
                "UNRESOLVED_EXTERNAL_REFERENCE",
                f"引用尚未建模为一等节点：{ref}",
                owner_id,
                path,
            )
            return
        result.error(
            "BROKEN_REFERENCE",
            f"引用的语义节点不存在：{ref}",
            owner_id,
            path,
        )


def walk_references(value: Any, index: dict[str, dict[str, Any]], result: ValidationResult, owner_id: str, path: str = "") -> None:
    if isinstance(value, dict):
        for key, child in value.items():
            child_path = f"{path}.{key}" if path else key
            if key in REFERENCE_KEYS:
                if isinstance(child, list):
                    for i, ref in enumerate(child):
                        validate_reference(index, result, owner_id, f"{child_path}[{i}]", ref)
                else:
                    validate_reference(index, result, owner_id, child_path, child)
            walk_references(child, index, result, owner_id, child_path)
    elif isinstance(value, list):
        for i, child in enumerate(value):
            walk_references(child, index, result, owner_id, f"{path}[{i}]")


def validate_condition(expr: Any, result: ValidationResult, owner_id: str, path: str) -> None:
    if not isinstance(expr, dict):
        return

    op = expr.get("op")
    if op in {"all", "any"}:
        args = expr.get("args")
        if not isinstance(args, list) or not args:
            result.error(
                "INVALID_CONDITION",
                f"组合条件 {op} 至少需要一个子条件",
                owner_id,
                path,
            )
            return
        for i, child in enumerate(args):
            validate_condition(child, result, owner_id, f"{path}.args[{i}]")
    elif op == "not":
        arg = expr.get("arg")
        if not isinstance(arg, dict):
            result.error(
                "INVALID_CONDITION",
                "not 条件必须包含且只包含一个子条件",
                owner_id,
                path,
            )
        else:
            validate_condition(arg, result, owner_id, f"{path}.arg")


def validate_conditions(clm: dict[str, Any], result: ValidationResult) -> None:
    for _, node in iter_nodes(clm):
        semantic_id = node.get("id", "<unknown>")
        for key in ("condition", "when", "expression"):
            if key in node:
                validate_condition(node[key], result, semantic_id, key)


def validate_state_machines(clm: dict[str, Any], index: dict[str, dict[str, Any]], result: ValidationResult) -> None:
    transitions: list[dict[str, Any]] = []
    forbidden: set[tuple[Any, Any]] = set()

    for _, node in iter_nodes(clm):
        kind = node.get("kind")
        if kind == "transition":
            transitions.append(node)
        elif kind == "forbidden_transition":
            forbidden.add((node.get("from"), node.get("to")))

    seen: dict[tuple[Any, Any], list[dict[str, Any]]] = {}
    for tr in transitions:
        semantic_id = tr.get("id", "<unknown>")
        from_state = tr.get("from")
        to_state = tr.get("to")
        if (from_state, to_state) in forbidden:
            result.error(
                "FORBIDDEN_TRANSITION_CONFLICT",
                f"迁移 {from_state} → {to_state} 同时被允许和禁止",
                semantic_id,
            )
        key = (from_state, tr.get("trigger"))
        seen.setdefault(key, []).append(tr)

    for (from_state, trigger), items in seen.items():
        targets = {item.get("to") for item in items}
        if len(targets) > 1:
            has_guards = all(item.get("guard") for item in items)
            if not has_guards:
                result.error(
                    "NON_DETERMINISTIC_TRANSITION",
                    f"状态 {from_state} 在触发 {trigger} 时存在多个目标状态且缺少互斥 guard：{sorted(str(x) for x in targets)}",
                )


def validate_observed_evidence(clm: dict[str, Any], result: ValidationResult) -> None:
    for _, node in iter_nodes(clm):
        if node.get("origin") != "observed":
            continue
        semantic_id = node.get("id", "<unknown>")
        refs = node.get("evidence_refs", [])
        if not refs:
            result.error(
                "MISSING_EVIDENCE",
                "origin=observed 的节点必须至少绑定一条证据",
                semantic_id,
                "evidence_refs",
            )


def validate_with_jsonschema(document: Any, schema: Any, result: ValidationResult) -> bool:
    try:
        import jsonschema  # type: ignore
    except ImportError:
        result.warning(
            "JSONSCHEMA_NOT_INSTALLED",
            "未安装 jsonschema，已跳过 JSON Schema 校验",
        )
        return False

    validator = jsonschema.Draft202012Validator(schema)
    for error in sorted(validator.iter_errors(document), key=lambda e: list(e.absolute_path)):
        path = ".".join(str(p) for p in error.absolute_path)
        result.error("SCHEMA_VALIDATION_ERROR", error.message, path=path or None)
    return True


def validate(document: dict[str, Any], schema: dict[str, Any] | None = None) -> dict[str, Any]:
    result = ValidationResult()

    if schema is not None:
        validate_with_jsonschema(document, schema, result)

    clm = document.get("clm") if isinstance(document.get("clm"), dict) else document
    if not isinstance(clm, dict):
        result.error("INVALID_ROOT", "CLM 根节点必须是对象")
        return {"valid": False, "errors": result.errors, "warnings": result.warnings, "stats": {}}

    index = build_index(clm, result)

    for _, node in iter_nodes(clm):
        owner_id = node.get("id", "<unknown>")
        walk_references(node, index, result, owner_id)

    validate_conditions(clm, result)
    validate_state_machines(clm, index, result)
    validate_observed_evidence(clm, result)

    canonical = sum(1 for _, n in iter_nodes(clm) if n.get("status") == "canonical")
    candidate = sum(1 for _, n in iter_nodes(clm) if n.get("status") == "candidate")

    return {
        "valid": not result.errors,
        "errors": result.errors,
        "warnings": result.warnings,
        "stats": {
            "nodes": len(index),
            "canonical": canonical,
            "candidate": candidate,
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="校验 logic-engineering CLM v0.1 JSON")
    parser.add_argument("model", type=Path, help="CLM JSON 文件")
    parser.add_argument("--schema", type=Path, help="可选 JSON Schema 文件")
    parser.add_argument("--pretty", action="store_true", help="格式化输出 JSON")
    args = parser.parse_args()

    try:
        document = load_json(args.model)
        schema = load_json(args.schema) if args.schema else None
    except (OSError, json.JSONDecodeError) as exc:
        print(json.dumps({"valid": False, "error": str(exc)}, ensure_ascii=False), file=sys.stderr)
        return 2

    output = validate(document, schema)
    print(json.dumps(output, ensure_ascii=False, indent=2 if args.pretty else None))
    return 0 if output["valid"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
