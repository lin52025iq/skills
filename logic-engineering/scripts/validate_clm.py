#!/usr/bin/env python3
"""CLM 语义校验器。

当前覆盖：
1. JSON Schema（可选）；
2. 统一节点注册表与 kind/collection 一致性；
3. Semantic ID 唯一与引用完整性；
4. Typed Expression AST 结构；
5. Symbol Table 基础类型检查与 enum 值检查；
6. 状态迁移冲突；
7. observed 节点证据要求。
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Dict

from clm_model import (
    build_node_index,
    iter_nodes,
    root_of,
    validate_node_collection,
)
from expression_ast import COMPARISON_OPS, iter_refs, validate_expression_shape
from symbol_table import build_symbol_table, compatible_types, enum_contains, is_enum_type, resolve_type


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


def build_index(clm: dict[str, Any], result: ValidationResult) -> dict[str, dict[str, Any]]:
    index: dict[str, dict[str, Any]] = {}
    for collection, node in iter_nodes(clm):
        semantic_id = node.get("id")
        if not isinstance(semantic_id, str) or not semantic_id:
            continue
        placement_error = validate_node_collection(node, collection)
        if placement_error:
            result.error("NODE_COLLECTION_MISMATCH", placement_error, semantic_id, collection)
        if semantic_id in index:
            result.error("DUPLICATE_SEMANTIC_ID", f"语义 ID 重复：{semantic_id}", semantic_id, collection)
            continue
        index[semantic_id] = node
    return index


def is_semantic_ref(value: Any) -> bool:
    if not isinstance(value, str):
        return False
    prefixes = (
        "domain.", "type.", "behavior.", "rule.", "action.", "decision.",
        "state.", "state_machine.", "transition.", "effect.", "constraint.",
        "invariant.", "scenario.", "primitive.", "evidence.", "error.", "event.",
    )
    return value.startswith(prefixes)


def validate_reference(index: dict[str, dict[str, Any]], result: ValidationResult, owner_id: str, path: str, ref: Any) -> None:
    if isinstance(ref, str) and is_semantic_ref(ref) and ref not in index:
        if ref.startswith(("error.", "event.", "evidence.")):
            result.warning("UNRESOLVED_EXTERNAL_REFERENCE", f"引用尚未建模为一等节点：{ref}", owner_id, path)
            return
        result.error("BROKEN_REFERENCE", f"引用的语义节点不存在：{ref}", owner_id, path)


def walk_references(value: Any, index: dict[str, dict[str, Any]], result: ValidationResult, owner_id: str, path: str = "") -> None:
    if isinstance(value, dict):
        if isinstance(value.get("ref"), str):
            validate_reference(index, result, owner_id, f"{path}.ref" if path else "ref", value["ref"])
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


def infer_value_type(value: Any, symbols: Dict[str, Dict[str, Any]], result: ValidationResult, owner_id: str, path: str) -> str | None:
    if not isinstance(value, dict):
        return None
    if "ref" in value:
        ref = value.get("ref")
        if isinstance(ref, str):
            return resolve_type(symbols, ref)
    if "enum" in value and isinstance(value["enum"], dict):
        enum_type = value["enum"].get("type")
        enum_value = value["enum"].get("value")
        if isinstance(enum_type, str):
            if not is_enum_type(symbols, enum_type):
                result.error("INVALID_ENUM_TYPE", f"不是已声明 enum 类型：{enum_type}", owner_id, path)
            elif not enum_contains(symbols, enum_type, enum_value):
                result.error("INVALID_ENUM_VALUE", f"{enum_value!r} 不属于 {enum_type}", owner_id, path)
            return enum_type
    if "literal" in value:
        literal = value["literal"]
        if isinstance(literal, bool):
            return "boolean"
        if isinstance(literal, int) and not isinstance(literal, bool):
            return "integer"
        if isinstance(literal, float):
            return "number"
        if isinstance(literal, str):
            return "string"
    if "null" in value:
        return None
    return None


def validate_typed_expression(expr: Any, symbols: Dict[str, Dict[str, Any]], result: ValidationResult, owner_id: str, path: str) -> None:
    if not isinstance(expr, dict) or "op" not in expr:
        return

    # v0.1 兼容：旧 all/any 使用 args，not 使用 arg。保留为 warning，鼓励迁移。
    op = expr.get("op")
    if op in {"all", "any"} and "args" in expr and "items" not in expr:
        result.warning("LEGACY_EXPRESSION_SHAPE", "组合表达式应从 args 迁移为 items", owner_id, path)
        for i, child in enumerate(expr.get("args", []) or []):
            validate_typed_expression(child, symbols, result, owner_id, f"{path}.args[{i}]")
        return
    if op == "not" and "arg" in expr and "item" not in expr:
        result.warning("LEGACY_EXPRESSION_SHAPE", "not 表达式应从 arg 迁移为 item", owner_id, path)
        validate_typed_expression(expr.get("arg"), symbols, result, owner_id, f"{path}.arg")
        return

    for message in validate_expression_shape(expr, path):
        result.error("INVALID_TYPED_EXPRESSION", message, owner_id, path)
    if any(e.get("semantic_id") == owner_id and e.get("code") == "INVALID_TYPED_EXPRESSION" for e in result.errors):
        return

    for ref in iter_refs(expr):
        if ref not in symbols:
            result.error("UNKNOWN_SYMBOL", f"表达式引用未知 symbol：{ref}", owner_id, path)

    if op in COMPARISON_OPS:
        left_type = infer_value_type(expr.get("left"), symbols, result, owner_id, f"{path}.left")
        right_type = infer_value_type(expr.get("right"), symbols, result, owner_id, f"{path}.right")
        if not compatible_types(left_type, right_type):
            result.error(
                "TYPE_MISMATCH",
                f"比较两侧类型不兼容：{left_type} 与 {right_type}",
                owner_id,
                path,
            )


def validate_expressions(clm: dict[str, Any], symbols: Dict[str, Dict[str, Any]], result: ValidationResult) -> None:
    for _, node in iter_nodes(clm):
        semantic_id = node.get("id", "<unknown>")
        for key in ("condition", "when", "expression", "guard"):
            if key in node:
                validate_typed_expression(node[key], symbols, result, semantic_id, key)
        # v0.2 rule 可以直接使用 expression；旧 subject/operator/value 暂保留兼容。
        if node.get("kind") == "rule" and "expression" not in node and "subject" in node:
            result.warning(
                "LEGACY_RULE_SHAPE",
                "规则仍使用 subject/operator/value，建议迁移为 typed expression AST",
                semantic_id,
            )


def validate_state_machines(clm: dict[str, Any], result: ValidationResult) -> None:
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
            result.error("FORBIDDEN_TRANSITION_CONFLICT", f"迁移 {from_state} → {to_state} 同时被允许和禁止", semantic_id)
        key = (from_state, tr.get("trigger"))
        seen.setdefault(key, []).append(tr)

    for (from_state, trigger), items in seen.items():
        targets = {item.get("to") for item in items}
        if len(targets) > 1 and not all(item.get("guard") for item in items):
            result.error(
                "NON_DETERMINISTIC_TRANSITION",
                f"状态 {from_state} 在触发 {trigger} 时存在多个目标状态且缺少互斥 guard：{sorted(str(x) for x in targets)}",
            )


def validate_observed_evidence(clm: dict[str, Any], result: ValidationResult) -> None:
    for _, node in iter_nodes(clm):
        if node.get("origin") != "observed":
            continue
        semantic_id = node.get("id", "<unknown>")
        if not node.get("evidence_refs", []):
            result.error("MISSING_EVIDENCE", "origin=observed 的节点必须至少绑定一条证据", semantic_id, "evidence_refs")


def validate_with_jsonschema(document: Any, schema: Any, result: ValidationResult) -> bool:
    try:
        import jsonschema  # type: ignore
    except ImportError:
        result.warning("JSONSCHEMA_NOT_INSTALLED", "未安装 jsonschema，已跳过 JSON Schema 校验")
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

    clm = root_of(document)
    if not isinstance(clm, dict):
        result.error("INVALID_ROOT", "CLM 根节点必须是对象")
        return {"valid": False, "errors": result.errors, "warnings": result.warnings, "stats": {}}

    index = build_index(clm, result)
    symbols = build_symbol_table(clm)

    for _, node in iter_nodes(clm):
        owner_id = node.get("id", "<unknown>")
        walk_references(node, index, result, owner_id)

    validate_expressions(clm, symbols, result)
    validate_state_machines(clm, result)
    validate_observed_evidence(clm, result)

    canonical = sum(1 for _, n in iter_nodes(clm) if n.get("status") == "canonical")
    candidate = sum(1 for _, n in iter_nodes(clm) if n.get("status") == "candidate")

    return {
        "valid": not result.errors,
        "errors": result.errors,
        "warnings": result.warnings,
        "stats": {
            "nodes": len(index),
            "symbols": len(symbols),
            "canonical": canonical,
            "candidate": candidate,
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="校验 logic-engineering CLM")
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
