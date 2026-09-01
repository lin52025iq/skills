#!/usr/bin/env python3
"""CLM 语义校验器。

覆盖：JSON Schema、节点注册表、引用、Typed Expression、Symbol Table、
Typed Action / Scenario、状态机冲突与 observed 证据要求。
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Dict

from clm_model import iter_nodes, root_of, validate_node_collection
from expression_ast import COMPARISON_OPS, iter_refs, validate_expression_shape, validate_value_shape
from symbol_table import build_symbol_table, compatible_types, enum_contains, is_enum_type, resolve_type

REFERENCE_KEYS = {"preconditions", "flow", "postconditions", "failures", "then", "else", "transitions", "trigger", "effects", "source", "target", "supports", "evidence_refs"}


class ValidationResult:
    def __init__(self) -> None:
        self.errors: list[dict[str, Any]] = []
        self.warnings: list[dict[str, Any]] = []

    def error(self, code: str, message: str, semantic_id: str | None = None, path: str | None = None) -> None:
        item: dict[str, Any] = {"code": code, "message": message}
        if semantic_id: item["semantic_id"] = semantic_id
        if path: item["path"] = path
        self.errors.append(item)

    def warning(self, code: str, message: str, semantic_id: str | None = None, path: str | None = None) -> None:
        item: dict[str, Any] = {"code": code, "message": message}
        if semantic_id: item["semantic_id"] = semantic_id
        if path: item["path"] = path
        self.warnings.append(item)


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


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
        else:
            index[semantic_id] = node
    return index


def is_semantic_ref(value: Any) -> bool:
    return isinstance(value, str) and value.startswith(("domain.", "type.", "behavior.", "rule.", "action.", "decision.", "state.", "state_machine.", "transition.", "effect.", "constraint.", "invariant.", "scenario.", "primitive.", "evidence.", "error.", "event."))


def validate_reference(index: dict[str, dict[str, Any]], result: ValidationResult, owner_id: str, path: str, ref: Any) -> None:
    if isinstance(ref, str) and is_semantic_ref(ref) and ref not in index:
        if ref.startswith(("error.", "event.", "evidence.")):
            result.warning("UNRESOLVED_EXTERNAL_REFERENCE", f"引用尚未建模为一等节点：{ref}", owner_id, path)
        else:
            result.error("BROKEN_REFERENCE", f"引用的语义节点不存在：{ref}", owner_id, path)


def walk_references(value: Any, index: dict[str, dict[str, Any]], result: ValidationResult, owner_id: str, path: str = "") -> None:
    if isinstance(value, dict):
        if isinstance(value.get("ref"), str):
            validate_reference(index, result, owner_id, f"{path}.ref" if path else "ref", value["ref"])
        for key, child in value.items():
            child_path = f"{path}.{key}" if path else key
            if key in REFERENCE_KEYS:
                if isinstance(child, list):
                    for i, ref in enumerate(child): validate_reference(index, result, owner_id, f"{child_path}[{i}]", ref)
                else:
                    validate_reference(index, result, owner_id, child_path, child)
            walk_references(child, index, result, owner_id, child_path)
    elif isinstance(value, list):
        for i, child in enumerate(value): walk_references(child, index, result, owner_id, f"{path}[{i}]")


def infer_value_type(value: Any, symbols: Dict[str, Dict[str, Any]], result: ValidationResult, owner_id: str, path: str) -> str | None:
    if not isinstance(value, dict): return None
    if "ref" in value:
        ref = value.get("ref")
        return resolve_type(symbols, ref) if isinstance(ref, str) else None
    if "enum" in value and isinstance(value["enum"], dict):
        enum_type = value["enum"].get("type"); enum_value = value["enum"].get("value")
        if isinstance(enum_type, str):
            if not is_enum_type(symbols, enum_type): result.error("INVALID_ENUM_TYPE", f"不是已声明 enum 类型：{enum_type}", owner_id, path)
            elif not enum_contains(symbols, enum_type, enum_value): result.error("INVALID_ENUM_VALUE", f"{enum_value!r} 不属于 {enum_type}", owner_id, path)
            return enum_type
    if "literal" in value:
        v = value["literal"]
        if isinstance(v, bool): return "boolean"
        if isinstance(v, int) and not isinstance(v, bool): return "integer"
        if isinstance(v, float): return "number"
        if isinstance(v, str): return "string"
    return None


def validate_typed_value(value: Any, symbols: Dict[str, Dict[str, Any]], result: ValidationResult, owner_id: str, path: str) -> str | None:
    for message in validate_value_shape(value, path): result.error("INVALID_TYPED_VALUE", message, owner_id, path)
    if isinstance(value, dict) and "ref" in value and value["ref"] not in symbols:
        result.error("UNKNOWN_SYMBOL", f"引用未知 symbol：{value['ref']}", owner_id, path)
    return infer_value_type(value, symbols, result, owner_id, path)


def validate_typed_expression(expr: Any, symbols: Dict[str, Dict[str, Any]], result: ValidationResult, owner_id: str, path: str) -> None:
    if not isinstance(expr, dict) or "op" not in expr: return
    op = expr.get("op")
    if op in {"all", "any"} and "args" in expr and "items" not in expr:
        result.warning("LEGACY_EXPRESSION_SHAPE", "组合表达式应从 args 迁移为 items", owner_id, path)
        return
    for message in validate_expression_shape(expr, path): result.error("INVALID_TYPED_EXPRESSION", message, owner_id, path)
    for ref in iter_refs(expr):
        if ref not in symbols: result.error("UNKNOWN_SYMBOL", f"表达式引用未知 symbol：{ref}", owner_id, path)
    if op in COMPARISON_OPS:
        left_type = infer_value_type(expr.get("left"), symbols, result, owner_id, f"{path}.left")
        right = expr.get("right")
        if op in {"in", "not_in"} and isinstance(right, dict) and isinstance(right.get("set"), list):
            for i, item in enumerate(right["set"]):
                item_type = infer_value_type(item, symbols, result, owner_id, f"{path}.right.set[{i}]")
                if not compatible_types(left_type, item_type): result.error("TYPE_MISMATCH", f"集合成员类型 {item_type} 与左侧 {left_type} 不兼容", owner_id, path)
        else:
            right_type = infer_value_type(right, symbols, result, owner_id, f"{path}.right")
            if not compatible_types(left_type, right_type): result.error("TYPE_MISMATCH", f"比较两侧类型不兼容：{left_type} 与 {right_type}", owner_id, path)


def validate_actions_and_scenarios(clm: dict[str, Any], symbols: Dict[str, Dict[str, Any]], index: Dict[str, Dict[str, Any]], result: ValidationResult) -> None:
    for _, node in iter_nodes(clm):
        sid = node.get("id", "<unknown>"); kind = node.get("kind")
        if kind in {"action", "foreach"}:
            if node.get("operation") == "assign":
                target = node.get("target"); value = node.get("value")
                if not isinstance(target, dict) or "ref" not in target:
                    result.error("INVALID_ACTION_TARGET", "assign.target 必须是 {ref: ...}", sid, "target")
                else:
                    target_type = validate_typed_value(target, symbols, result, sid, "target")
                    value_type = validate_typed_value(value, symbols, result, sid, "value")
                    if not compatible_types(target_type, value_type): result.error("TYPE_MISMATCH", f"赋值两侧类型不兼容：{target_type} 与 {value_type}", sid, "value")
            if kind == "foreach" and node.get("collection") is not None:
                validate_typed_value(node.get("collection"), symbols, result, sid, "collection")
        elif kind == "scenario":
            for section in ("given", "then"):
                for i, assignment in enumerate(node.get(section, []) or []):
                    path = f"{section}[{i}]"
                    if not isinstance(assignment, dict):
                        result.error("INVALID_SCENARIO_ASSIGNMENT", "场景赋值必须是对象", sid, path); continue
                    target_type = validate_typed_value(assignment.get("target"), symbols, result, sid, f"{path}.target")
                    value_type = validate_typed_value(assignment.get("value"), symbols, result, sid, f"{path}.value")
                    if not compatible_types(target_type, value_type): result.error("TYPE_MISMATCH", f"场景赋值类型不兼容：{target_type} 与 {value_type}", sid, path)
            for ref in node.get("when", []) or []:
                if isinstance(ref, str) and ref not in index: result.error("BROKEN_REFERENCE", f"Scenario.when 引用不存在：{ref}", sid, "when")


def validate_state_machines(clm: dict[str, Any], result: ValidationResult) -> None:
    transitions=[]; forbidden=set(); seen={}
    for _, node in iter_nodes(clm):
        if node.get("kind") == "transition": transitions.append(node)
        elif node.get("kind") == "forbidden_transition": forbidden.add((node.get("from"), node.get("to")))
    for tr in transitions:
        sid=tr.get("id", "<unknown>"); pair=(tr.get("from"), tr.get("to"))
        if pair in forbidden: result.error("FORBIDDEN_TRANSITION_CONFLICT", f"迁移 {pair[0]} → {pair[1]} 同时被允许和禁止", sid)
        seen.setdefault((tr.get("from"), tr.get("trigger")), []).append(tr)
    for (from_state, trigger), items in seen.items():
        targets={x.get("to") for x in items}
        if len(targets)>1 and not all(x.get("guard") for x in items): result.error("NON_DETERMINISTIC_TRANSITION", f"状态 {from_state} 在触发 {trigger} 时存在多个目标状态且缺少互斥 guard")


def validate_with_jsonschema(document: Any, schema: Any, result: ValidationResult) -> None:
    try: import jsonschema  # type: ignore
    except ImportError:
        result.warning("JSONSCHEMA_NOT_INSTALLED", "未安装 jsonschema，已跳过 JSON Schema 校验"); return
    for error in sorted(jsonschema.Draft202012Validator(schema).iter_errors(document), key=lambda e: list(e.absolute_path)):
        result.error("SCHEMA_VALIDATION_ERROR", error.message, path=".".join(str(p) for p in error.absolute_path) or None)


def validate(document: dict[str, Any], schema: dict[str, Any] | None = None) -> dict[str, Any]:
    result=ValidationResult()
    if schema is not None: validate_with_jsonschema(document, schema, result)
    clm=root_of(document)
    if not isinstance(clm, dict):
        result.error("INVALID_ROOT", "CLM 根节点必须是对象"); return {"valid":False,"errors":result.errors,"warnings":result.warnings,"stats":{}}
    index=build_index(clm,result); symbols=build_symbol_table(clm)
    for _, node in iter_nodes(clm):
        sid=node.get("id","<unknown>"); walk_references(node,index,result,sid)
        for key in ("condition","when","expression","guard"):
            if key in node: validate_typed_expression(node[key],symbols,result,sid,key)
        if node.get("kind")=="rule" and "expression" not in node and "subject" in node: result.warning("LEGACY_RULE_SHAPE", "规则仍使用旧结构", sid)
        if node.get("origin")=="observed" and not node.get("evidence_refs",[]): result.error("MISSING_EVIDENCE", "origin=observed 的节点必须至少绑定一条证据", sid, "evidence_refs")
    validate_actions_and_scenarios(clm,symbols,index,result)
    validate_state_machines(clm,result)
    return {"valid":not result.errors,"errors":result.errors,"warnings":result.warnings,"stats":{"nodes":len(index),"symbols":len(symbols),"canonical":sum(1 for _,n in iter_nodes(clm) if n.get("status")=="canonical"),"candidate":sum(1 for _,n in iter_nodes(clm) if n.get("status")=="candidate")}}


def main() -> int:
    p=argparse.ArgumentParser(description="校验 logic-engineering CLM"); p.add_argument("model",type=Path); p.add_argument("--schema",type=Path); p.add_argument("--pretty",action="store_true"); a=p.parse_args()
    try: document=load_json(a.model); schema=load_json(a.schema) if a.schema else None
    except (OSError,json.JSONDecodeError) as exc:
        print(json.dumps({"valid":False,"error":str(exc)},ensure_ascii=False),file=sys.stderr); return 2
    out=validate(document,schema); print(json.dumps(out,ensure_ascii=False,indent=2 if a.pretty else None)); return 0 if out["valid"] else 1

if __name__ == "__main__": raise SystemExit(main())
