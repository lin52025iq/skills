#!/usr/bin/env python3
"""将 CLM 投影为中文逻辑视图。

当前实现聚焦 Behavior、Rule、Decision、Action、StateMachine、Constraint。
自然语言只解释现有 CLM，不产生新业务规则。
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Dict, Iterable, List, Tuple

COLLECTIONS = ("domain", "behaviors", "states", "effects", "constraints", "scenarios", "primitives")


def load_json(path: Path) -> Dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def iter_nodes(clm: Dict[str, Any]) -> Iterable[Dict[str, Any]]:
    root = clm.get("clm", clm)
    for collection in COLLECTIONS:
        for node in root.get(collection, []) or []:
            if isinstance(node, dict):
                yield node


def index_nodes(clm: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
    return {node["id"]: node for node in iter_nodes(clm) if node.get("id")}


def zh_name(value: Any) -> str:
    text = str(value)
    mapping = {
        "PENDING_PAYMENT": "待支付",
        "PENDING_SHIPMENT": "待发货",
        "PENDING_ACCEPTANCE": "待接单",
        "PAID": "已支付",
        "SHIPPED": "已发货",
        "CANCELLED": "已取消",
        "SUCCEEDED": "成功",
        "FAILED": "失败",
        "true": "是",
        "false": "否",
    }
    return mapping.get(text, text)


def render_expr(expr: Any) -> str:
    if isinstance(expr, str):
        return expr
    if not isinstance(expr, dict):
        return str(expr)

    op = expr.get("operator") or expr.get("op")
    if op in {"all", "any"}:
        parts = [render_expr(x) for x in expr.get("conditions", [])]
        joiner = "，并且" if op == "all" else "，或者"
        return joiner.join(parts)
    if op == "not":
        return f"不满足（{render_expr(expr.get('condition'))}）"

    left = expr.get("subject", expr.get("left"))
    right = expr.get("value", expr.get("right"))
    operators = {
        "eq": "等于",
        "==": "等于",
        "ne": "不等于",
        "!=": "不等于",
        "gt": "大于",
        ">": "大于",
        "gte": "大于等于",
        ">=": "大于等于",
        "lt": "小于",
        "<": "小于",
        "lte": "小于等于",
        "<=": "小于等于",
        "in": "属于",
        "not_in": "不属于",
        "exists": "存在",
    }
    if op in {"in", "not_in"} and isinstance(right, list):
        rendered = "、".join(f"“{zh_name(v)}”" for v in right)
        return f"{left}{operators[op]}以下范围：{rendered}"
    if op == "exists":
        return f"{left}{operators[op]}"
    return f"{left}{operators.get(op, op or '满足')}{zh_name(right)}"


def render_rule(node: Dict[str, Any]) -> str:
    if "conditions" in node:
        expr = {"operator": node.get("operator"), "conditions": node.get("conditions", [])}
        return render_expr(expr)
    expr = {
        "operator": node.get("operator"),
        "subject": node.get("subject"),
        "value": node.get("value"),
    }
    return render_expr(expr)


def render_action(node: Dict[str, Any]) -> str:
    op = node.get("operation")
    if node.get("kind") == "foreach":
        return f"遍历 {node.get('collection')}，对满足条件的项执行关联操作"
    if op == "assign":
        return f"将 {node.get('target')} 设置为“{zh_name(node.get('value'))}”"
    if op:
        return node.get("description") or f"执行 {op}"
    return node.get("description") or node.get("name") or node.get("id", "执行操作")


def render_behavior(node: Dict[str, Any], idx: Dict[str, Dict[str, Any]]) -> str:
    lines: List[str] = []
    lines.append(f"## {node.get('name') or node['id']}")
    lines.append("")
    lines.append(f"标识：`{node['id']}`")
    if node.get("description"):
        lines.append(f"\n目的：{node['description']}")

    pres = node.get("preconditions", []) or []
    if pres:
        lines.append("\n### 前置条件")
        for ref in pres:
            target = idx.get(ref)
            text = render_rule(target) if target else ref
            lines.append(f"- {text}。")

    flow = node.get("flow", []) or []
    if flow:
        lines.append("\n### 处理过程")
        for n, ref in enumerate(flow, 1):
            target = idx.get(ref)
            if not target:
                text = ref
            elif target.get("kind") == "decision":
                cond = target.get("when")
                if isinstance(cond, str) and cond in idx:
                    cond_text = render_rule(idx[cond])
                else:
                    cond_text = render_expr(cond)
                then_refs = target.get("then", []) or []
                then_texts = []
                for t in then_refs:
                    tnode = idx.get(t)
                    then_texts.append(render_action(tnode) if tnode else t)
                text = f"如果 {cond_text}，则 {'；'.join(then_texts) or '执行对应处理'}"
            else:
                text = render_action(target)
            lines.append(f"{n}. {text}。")

    failures = node.get("failures", []) or []
    if failures:
        lines.append("\n### 失败情况")
        for ref in failures:
            target = idx.get(ref)
            lines.append(f"- {(target or {}).get('name') or ref}。")

    posts = node.get("postconditions", []) or []
    if posts:
        lines.append("\n### 完成条件 / 保证")
        for ref in posts:
            target = idx.get(ref)
            if target and target.get("expression"):
                text = render_expr(target["expression"])
            else:
                text = (target or {}).get("description") or ref
            lines.append(f"- {text}。")

    return "\n".join(lines)


def render_state_machine(node: Dict[str, Any], idx: Dict[str, Dict[str, Any]]) -> str:
    lines = [f"## 状态模型：{node.get('name') or node['id']}", ""]
    states = node.get("states", []) or []
    if states:
        lines.append("状态：" + "、".join(f"“{zh_name(s)}”" for s in states))
    transitions = node.get("transitions", []) or []
    if transitions:
        lines.append("\n状态变化：")
        for ref in transitions:
            t = idx.get(ref)
            if t:
                lines.append(f"- “{zh_name(t.get('from'))}” → “{zh_name(t.get('to'))}”，由 `{t.get('trigger')}` 触发。")
            else:
                lines.append(f"- {ref}")
    return "\n".join(lines)


def render(clm: Dict[str, Any]) -> str:
    idx = index_nodes(clm)
    root = clm.get("clm", clm)
    title = root.get("name") or root.get("id") or "逻辑模型"
    chunks = [f"# {title} — 人类可读逻辑", ""]

    for behavior in root.get("behaviors", []) or []:
        chunks.append(render_behavior(behavior, idx))
        chunks.append("")

    for state in root.get("states", []) or []:
        if state.get("kind") == "state_machine":
            chunks.append(render_state_machine(state, idx))
            chunks.append("")

    constraints = root.get("constraints", []) or []
    if constraints:
        chunks.extend(["## 全局约束", ""])
        for c in constraints:
            if c.get("kind") in {"invariant", "postcondition", "precondition"}:
                text = render_expr(c.get("expression")) if c.get("expression") else c.get("description")
            elif c.get("kind") == "temporal":
                text = f"当 {c.get('trigger')} 发生后，最终必须发生 {c.get('requirement')}"
                if c.get("time_bound"):
                    text += f"，时间限制为 {c['time_bound']}"
            elif c.get("kind") == "concurrency":
                text = f"对 {c.get('resource')} 的操作必须满足并发策略 {c.get('policy')}"
            else:
                text = c.get("description") or c.get("id")
            chunks.append(f"- {text}。")

    return "\n".join(chunks).rstrip() + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description="将 CLM 投影为中文逻辑视图")
    parser.add_argument("clm", type=Path)
    parser.add_argument("-o", "--output", type=Path)
    args = parser.parse_args()

    try:
        clm = load_json(args.clm)
        text = render(clm)
    except (OSError, json.JSONDecodeError) as exc:
        print(f"读取失败: {exc}")
        return 1

    if args.output:
        args.output.write_text(text, encoding="utf-8")
    else:
        print(text, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
