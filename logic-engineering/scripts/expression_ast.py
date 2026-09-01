#!/usr/bin/env python3
"""CLM Typed Expression AST 公共工具。"""

from __future__ import annotations

from typing import Any, Dict, Iterable, Iterator, List, Optional, Set


LOGICAL_OPS = {"all", "any", "not"}
COMPARISON_OPS = {"eq", "ne", "lt", "le", "gt", "ge", "in", "not_in"}
VALUE_KINDS = {"ref", "literal", "enum", "null"}


class ExpressionError(ValueError):
    pass


def is_expression(value: Any) -> bool:
    return isinstance(value, dict) and isinstance(value.get("op"), str)


def iter_refs(expr: Any) -> Iterator[str]:
    if isinstance(expr, dict):
        if isinstance(expr.get("ref"), str):
            yield expr["ref"]
        for value in expr.values():
            yield from iter_refs(value)
    elif isinstance(expr, list):
        for item in expr:
            yield from iter_refs(item)


def validate_expression_shape(expr: Any, path: str = "expression") -> List[str]:
    errors: List[str] = []
    if not isinstance(expr, dict):
        return [f"{path} 必须是对象"]

    op = expr.get("op")
    if op in {"all", "any"}:
        items = expr.get("items")
        if not isinstance(items, list) or not items:
            return [f"{path}.{op} 必须包含非空 items"]
        for i, item in enumerate(items):
            errors.extend(validate_expression_shape(item, f"{path}.items[{i}]"))
        return errors

    if op == "not":
        if "item" not in expr:
            return [f"{path}.not 缺少 item"]
        return validate_expression_shape(expr["item"], f"{path}.item")

    if op in COMPARISON_OPS:
        if "left" not in expr:
            errors.append(f"{path} 缺少 left")
        if "right" not in expr:
            errors.append(f"{path} 缺少 right")
        for side in ("left", "right"):
            if side in expr:
                errors.extend(validate_value_shape(expr[side], f"{path}.{side}"))
        return errors

    return [f"{path}.op 非法或未支持: {op!r}"]


def validate_value_shape(value: Any, path: str) -> List[str]:
    if not isinstance(value, dict):
        return [f"{path} 必须是 typed value 对象"]
    keys = [k for k in VALUE_KINDS if k in value]
    if len(keys) != 1:
        return [f"{path} 必须且只能包含 ref/literal/enum/null 之一"]
    kind = keys[0]
    if kind == "ref" and not isinstance(value["ref"], str):
        return [f"{path}.ref 必须是 Semantic ID"]
    if kind == "enum":
        enum = value["enum"]
        if not isinstance(enum, dict) or not isinstance(enum.get("type"), str) or "value" not in enum:
            return [f"{path}.enum 必须包含 type 和 value"]
    if kind == "null" and value["null"] is not True:
        return [f"{path}.null 只能为 true"]
    return []


def humanize_value(value: Dict[str, Any]) -> str:
    if "ref" in value:
        return value["ref"]
    if "literal" in value:
        return repr(value["literal"])
    if "enum" in value:
        return str(value["enum"].get("value"))
    if "null" in value:
        return "空值"
    return "<?>"


def humanize_expression(expr: Dict[str, Any]) -> str:
    op = expr.get("op")
    if op == "all":
        return "并且".join(f"（{humanize_expression(item)}）" for item in expr.get("items", []))
    if op == "any":
        return "或者".join(f"（{humanize_expression(item)}）" for item in expr.get("items", []))
    if op == "not":
        return f"不满足（{humanize_expression(expr.get('item', {}))}）"
    labels = {
        "eq": "等于",
        "ne": "不等于",
        "lt": "小于",
        "le": "小于等于",
        "gt": "大于",
        "ge": "大于等于",
        "in": "属于",
        "not_in": "不属于",
    }
    return f"{humanize_value(expr.get('left', {}))} {labels.get(op, op)} {humanize_value(expr.get('right', {}))}"
