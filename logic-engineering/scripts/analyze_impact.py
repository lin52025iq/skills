#!/usr/bin/env python3
"""分析 CLM 中一个或多个 Semantic ID 的影响范围。"""

from __future__ import annotations

import argparse
import json
from collections import defaultdict, deque
from pathlib import Path
from typing import Any, Dict, Iterable, List, Set, Tuple

from clm_model import build_node_index, iter_node_values, root_of
from expression_ast import iter_refs


PROPAGATING_RELATIONS = {
    "REQUIRES",
    "INVOKES",
    "READS",
    "WRITES",
    "TRANSITIONS",
    "EMITS",
    "HANDLES",
    "GUARANTEES",
    "CONSTRAINED_BY",
    "USES_PRIMITIVE",
    "DERIVED_FROM",
}

DERIVED_BY_KIND = {
    "rule": {"human_projection", "boundary_tests", "scenario_tests", "target_iir", "generated_code"},
    "behavior": {"human_projection", "scenario_tests", "target_iir", "generated_code"},
    "decision": {"human_projection", "scenario_tests", "target_iir", "generated_code"},
    "action": {"human_projection", "scenario_tests", "target_iir", "generated_code"},
    "foreach": {"human_projection", "scenario_tests", "target_iir", "generated_code"},
    "effect": {"target_iir", "generated_code", "integration_tests"},
    "read": {"target_iir", "generated_code", "integration_tests"},
    "write": {"target_iir", "generated_code", "integration_tests"},
    "external_call": {"target_iir", "generated_code", "integration_tests"},
    "emit": {"target_iir", "generated_code", "integration_tests"},
    "state_machine": {"human_projection", "state_tests", "target_iir", "generated_code"},
    "transition": {"human_projection", "state_tests", "target_iir", "generated_code"},
    "constraint": {"human_projection", "property_tests", "formal_projection"},
    "invariant": {"human_projection", "property_tests", "formal_projection"},
    "scenario": {"human_projection", "scenario_tests"},
    "primitive": {"target_iir", "generated_code", "integration_tests"},
    "entity": {"human_projection", "target_iir", "generated_code"},
    "enum": {"human_projection", "target_iir", "generated_code", "scenario_tests"},
    "value_type": {"human_projection", "target_iir", "generated_code", "boundary_tests"},
}


def load_json(path: Path) -> Dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def add_ref(reverse: Dict[str, List[Tuple[str, str]]], target: Any, source: str, reason: str) -> None:
    if isinstance(target, str) and target:
        reverse[target].append((source, reason))
    elif isinstance(target, list):
        for item in target:
            add_ref(reverse, item, source, reason)


def collect_expr_refs(expr: Any, reverse: Dict[str, List[Tuple[str, str]]], source: str, reason: str) -> None:
    for ref in iter_refs(expr):
        reverse[ref].append((source, reason))


def build_reverse_dependencies(clm: Dict[str, Any]) -> Tuple[Dict[str, Dict[str, Any]], Dict[str, List[Tuple[str, str]]]]:
    root = root_of(clm)
    nodes = build_node_index(clm)
    reverse: Dict[str, List[Tuple[str, str]]] = defaultdict(list)

    for rel in root.get("relations", []) or []:
        if not isinstance(rel, dict):
            continue
        relation = rel.get("relation")
        if relation not in PROPAGATING_RELATIONS:
            continue
        source = rel.get("source")
        target = rel.get("target")
        if isinstance(source, str) and isinstance(target, str):
            reverse[target].append((source, f"关系 {relation} 指向发生变化的节点"))

    for node_id, node in nodes.items():
        kind = node.get("kind")
        if kind == "behavior":
            add_ref(reverse, node.get("preconditions"), node_id, "Behavior.preconditions 引用")
            add_ref(reverse, node.get("flow"), node_id, "Behavior.flow 引用")
            add_ref(reverse, node.get("postconditions"), node_id, "Behavior.postconditions 引用")
            add_ref(reverse, node.get("failures"), node_id, "Behavior.failures 引用")
        elif kind == "decision":
            collect_expr_refs(node.get("when"), reverse, node_id, "Decision.when 引用")
            add_ref(reverse, node.get("then"), node_id, "Decision.then 引用")
            add_ref(reverse, node.get("else"), node_id, "Decision.else 引用")
        elif kind in {"action", "foreach"}:
            add_ref(reverse, node.get("effects"), node_id, "Action.effects 引用")
            add_ref(reverse, node.get("do"), node_id, "Foreach.do 引用")
            collect_expr_refs(node.get("when"), reverse, node_id, "Action.when 引用")
        elif kind == "state_machine":
            add_ref(reverse, node.get("transitions"), node_id, "StateMachine.transitions 引用")
        elif kind == "transition":
            add_ref(reverse, node.get("trigger"), node_id, "Transition.trigger 引用")
            collect_expr_refs(node.get("guard"), reverse, node_id, "Transition.guard 引用")
        elif kind == "scenario":
            add_ref(reverse, node.get("when"), node_id, "Scenario.when 引用")
        elif kind == "rule":
            add_ref(reverse, node.get("subject"), node_id, "Rule.subject 引用")
            collect_expr_refs(node.get("expression"), reverse, node_id, "Rule.expression 引用")
            collect_expr_refs(node.get("conditions"), reverse, node_id, "Rule.conditions 引用")
        elif kind in {"constraint", "invariant", "precondition", "postcondition"}:
            collect_expr_refs(node.get("expression"), reverse, node_id, "Constraint.expression 引用")

    return nodes, reverse


def analyze(clm: Dict[str, Any], changed: List[str]) -> Dict[str, Any]:
    nodes, reverse = build_reverse_dependencies(clm)
    queue = deque((node_id, 0) for node_id in changed)
    visited: Set[str] = set(changed)
    affected: List[Dict[str, Any]] = []
    derived: Set[str] = set()
    review: List[Dict[str, Any]] = []

    for node_id in changed:
        node = nodes.get(node_id)
        if node:
            derived |= DERIVED_BY_KIND.get(node.get("kind"), set())
        else:
            review.append({"id": node_id, "reason": "变化节点不在当前 CLM 中，无法确定完整影响范围"})

    while queue:
        current, depth = queue.popleft()
        for source, reason in reverse.get(current, []):
            if source in visited:
                continue
            visited.add(source)
            level = "DIRECT" if depth == 0 else "TRANSITIVE"
            affected.append({"id": source, "level": level, "reason": reason, "via": current})
            node = nodes.get(source)
            if node:
                derived |= DERIVED_BY_KIND.get(node.get("kind"), set())
            queue.append((source, depth + 1))

    for node_id in changed:
        node = nodes.get(node_id)
        if node and node.get("kind") in {"enum", "entity", "value_type"}:
            derived |= {"scenario_tests", "target_iir", "generated_code"}
            review.append({"id": node_id, "reason": "领域结构变化需要检查状态机、规则和场景覆盖是否完整"})

    revalidation = {"clm_validator"}
    affected_kinds = {nodes[item["id"]].get("kind") for item in affected if item["id"] in nodes}
    changed_kinds = {nodes[node_id].get("kind") for node_id in changed if node_id in nodes}
    all_kinds = affected_kinds | changed_kinds
    if all_kinds & {"rule", "behavior", "decision", "scenario"}:
        revalidation.add("scenario_consistency")
    if all_kinds & {"state_machine", "transition", "constraint", "invariant"}:
        revalidation.add("state_consistency")
    if all_kinds & {"effect", "read", "write", "external_call", "action", "foreach", "primitive", "constraint"}:
        revalidation.add("implementation_mapping")

    return {
        "changed": changed,
        "affected_nodes": affected,
        "derived_artifacts": sorted(derived),
        "review_candidates": review,
        "revalidation": sorted(revalidation),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="分析 CLM 语义节点变化的影响范围")
    parser.add_argument("clm", type=Path)
    parser.add_argument("changed", nargs="+", help="发生变化的 Semantic ID")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()

    result = analyze(load_json(args.clm), args.changed)
    text = json.dumps(result, ensure_ascii=False, indent=2)
    if args.output:
        args.output.write_text(text + "\n", encoding="utf-8")
    else:
        print(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
