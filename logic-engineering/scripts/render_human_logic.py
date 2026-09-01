#!/usr/bin/env python3
"""将 CLM 投影为中文逻辑视图。

自然语言只解释现有 CLM，不产生新业务规则。
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Dict, List

from clm_model import build_node_index, root_of


def load_json(path: Path) -> Dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


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


def render_value(value: Any) -> str:
    if isinstance(value, dict):
        if "ref" in value:
            return value["ref"]
        if "literal" in value:
            return zh_name(value["literal"])
        if "enum" in value and isinstance(value["enum"], dict):
            return zh_name(value["enum"].get("value"))
        if "null" in value:
            return "空值"
        if "set" in value:
            return "、".join(f"“{render_value(item)}”" for item in value.get("set", []))
    if isinstance(value, list):
        return "、".join(f"“{zh_name(v)}”" for v in value)
    return zh_name(value)


def render_expr(expr: Any) -> str:
    if isinstance(expr, str):
        return expr
    if not isinstance(expr, dict):
        return str(expr)
    if "op" in expr and ("left" in expr or "items" in expr or "item" in expr):
        op = expr.get("op")
        if op in {"all", "any"}:
            parts = [render_expr(x) for x in expr.get("items", [])]
            return ("，并且" if op == "all" else "，或者").join(parts)
        if op == "not":
            return f"不满足（{render_expr(expr.get('item'))}）"
        left = render_value(expr.get("left"))
        right = render_value(expr.get("right"))
        operators = {
            "eq": "等于", "ne": "不等于", "gt": "大于", "ge": "大于等于",
            "lt": "小于", "le": "小于等于", "in": "属于", "not_in": "不属于",
        }
        return f"{left}{operators.get(op, op or '满足')}{right}"

    op = expr.get("operator") or expr.get("op")
    if op in {"all", "any"}:
        parts = [render_expr(x) for x in expr.get("conditions", expr.get("args", []))]
        return ("，并且" if op == "all" else "，或者").join(parts)
    if op == "not":
        return f"不满足（{render_expr(expr.get('condition', expr.get('arg')))}）"
    left = expr.get("subject", expr.get("left"))
    right = expr.get("value", expr.get("right"))
    operators = {
        "eq": "等于", "==": "等于", "ne": "不等于", "!=": "不等于",
        "gt": "大于", ">": "大于", "gte": "大于等于", ">=": "大于等于",
        "lt": "小于", "<": "小于", "lte": "小于等于", "<=": "小于等于",
        "in": "属于", "not_in": "不属于", "exists": "存在",
    }
    if op in {"in", "not_in"} and isinstance(right, list):
        rendered = "、".join(f"“{zh_name(v)}”" for v in right)
        return f"{left}{operators[op]}以下范围：{rendered}"
    if op == "exists":
        return f"{left}{operators[op]}"
    return f"{left}{operators.get(op, op or '满足')}{zh_name(right)}"


def render_rule(node: Dict[str, Any]) -> str:
    if "expression" in node:
        return render_expr(node["expression"])
    if "conditions" in node:
        return render_expr({"operator": node.get("operator"), "conditions": node.get("conditions", [])})
    return render_expr({"operator": node.get("operator"), "subject": node.get("subject"), "value": node.get("value")})


def render_action(node: Dict[str, Any]) -> str:
    op = node.get("operation")
    if node.get("kind") == "foreach":
        cond = f"，仅处理满足“{render_expr(node['when'])}”的项" if node.get("when") else ""
        return f"遍历 {render_value(node.get('collection'))}{cond}，执行关联操作"
    if op == "assign":
        return f"将 {render_value(node.get('target'))} 设置为“{render_value(node.get('value'))}”"
    if op:
        return node.get("description") or f"执行 {op}"
    return node.get("description") or node.get("name") or node.get("id", "执行操作")


def render_assignment(item: Dict[str, Any]) -> str:
    return f"{render_value(item.get('target'))} = {render_value(item.get('value'))}"


def render_scenario(node: Dict[str, Any], idx: Dict[str, Dict[str, Any]]) -> str:
    lines = [f"### 场景：{node.get('name') or node['id']}"]
    given = node.get("given", []) or []
    if given:
        lines.append("- 已知：" + "；".join(render_assignment(x) for x in given if isinstance(x, dict)))
    when = node.get("when", []) or []
    if when:
        names = []
        for ref in when:
            target = idx.get(ref)
            names.append((target or {}).get("name") or ref)
        lines.append("- 当：" + "；".join(names))
    then = node.get("then", []) or []
    if then:
        results = []
        for item in then:
            if isinstance(item, dict) and "target" in item:
                results.append(render_assignment(item))
            elif isinstance(item, dict) and "expression" in item:
                results.append(render_expr(item["expression"]))
        lines.append("- 则：" + "；".join(results))
    return "\n".join(lines)


def render_behavior(node: Dict[str, Any], idx: Dict[str, Dict[str, Any]]) -> str:
    lines: List[str] = [f"## {node.get('name') or node['id']}", "", f"标识：`{node['id']}`"]
    if node.get("description"):
        lines.append(f"\n目的：{node['description']}")
    pres = node.get("preconditions", []) or []
    if pres:
        lines.append("\n### 前置条件")
        for ref in pres:
            target = idx.get(ref)
            lines.append(f"- {(render_rule(target) if target else ref)}。")
    flow = node.get("flow", []) or []
    if flow:
        lines.append("\n### 处理过程")
        for n, ref in enumerate(flow, 1):
            target = idx.get(ref)
            if not target:
                text = ref
            elif target.get("kind") == "decision":
                cond = target.get("when")
                cond_text = render_rule(idx[cond]) if isinstance(cond, str) and cond in idx else render_expr(cond)
                then_texts = [render_action(idx[t]) if t in idx else t for t in target.get("then", []) or []]
                else_texts = [render_action(idx[t]) if t in idx else t for t in target.get("else", []) or []]
                text = f"如果 {cond_text}，则 {'；'.join(then_texts) or '执行对应处理'}"
                if else_texts:
                    text += f"；否则 {'；'.join(else_texts)}"
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
            text = render_expr(target["expression"]) if target and target.get("expression") else (target or {}).get("description") or ref
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
                line = f"- “{zh_name(t.get('from'))}” → “{zh_name(t.get('to'))}”，由 `{t.get('trigger')}` 触发"
                if t.get("guard"):
                    line += f"，条件为：{render_expr(t['guard'])}"
                lines.append(line + "。")
            else:
                lines.append(f"- {ref}")
    return "\n".join(lines)


def render(clm: Dict[str, Any]) -> str:
    idx = build_node_index(clm)
    root = root_of(clm)
    title = root.get("name") or root.get("id") or "逻辑模型"
    chunks = [f"# {title} — 人类可读逻辑", ""]
    for behavior in root.get("behaviors", []) or []:
        chunks.extend([render_behavior(behavior, idx), ""])
    for state in root.get("states", []) or []:
        if state.get("kind") == "state_machine":
            chunks.extend([render_state_machine(state, idx), ""])
    scenarios = root.get("scenarios", []) or []
    if scenarios:
        chunks.extend(["## 示例场景", ""])
        for scenario in scenarios:
            chunks.extend([render_scenario(scenario, idx), ""])
    constraints = root.get("constraints", []) or []
    if constraints:
        chunks.extend(["## 全局约束", ""])
        for c in constraints:
            if c.get("kind") in {"invariant", "postcondition", "precondition", "constraint"}:
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
        text = render(load_json(args.clm))
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
