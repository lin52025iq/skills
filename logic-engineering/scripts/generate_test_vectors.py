#!/usr/bin/env python3
"""从 CLM 直接生成与目标编程语言无关的测试向量。"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional


def load_json(path: Path) -> Dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def root_of(clm: Dict[str, Any]) -> Dict[str, Any]:
    return clm.get("clm", clm)


def iter_nodes(clm: Dict[str, Any]) -> Iterable[Dict[str, Any]]:
    root = root_of(clm)
    for section in (
        "domain",
        "behaviors",
        "rules",
        "decisions",
        "actions",
        "states",
        "effects",
        "constraints",
        "scenarios",
        "primitives",
    ):
        for node in root.get(section, []) or []:
            if isinstance(node, dict) and node.get("id"):
                yield node


def node_index(clm: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
    return {node["id"]: node for node in iter_nodes(clm)}


def enum_values_for_subject(subject: str, nodes: Dict[str, Dict[str, Any]]) -> Optional[List[Any]]:
    field = nodes.get(subject)
    if not field:
        # Some v0.1 fixtures use inline field objects nested inside entity rather than top-level nodes.
        for node in nodes.values():
            if node.get("kind") == "entity":
                for f in node.get("fields", []) or []:
                    if isinstance(f, dict) and f.get("id") == subject:
                        field = f
                        break
            if field:
                break
    if not field:
        return None
    type_id = field.get("type")
    enum = nodes.get(type_id) if isinstance(type_id, str) else None
    if enum and enum.get("kind") == "enum":
        values = enum.get("values")
        if isinstance(values, list):
            return values
    return None


def make_id(source_id: str, suffix: str) -> str:
    return f"test.{source_id}.{suffix}"


def rule_vectors(rule: Dict[str, Any], nodes: Dict[str, Dict[str, Any]]) -> List[Dict[str, Any]]:
    rule_id = rule["id"]
    operator = rule.get("operator")
    subject = rule.get("subject")
    value = rule.get("value")
    vectors: List[Dict[str, Any]] = []

    if operator in {"in", "not_in"} and isinstance(subject, str) and isinstance(value, list):
        positive_values = value if operator == "in" else []
        negative_values = value if operator == "not_in" else []
        for i, item in enumerate(positive_values, 1):
            vectors.append({
                "id": make_id(rule_id, f"allowed.{i}"),
                "source_semantic_id": rule_id,
                "kind": "rule_positive",
                "given": {subject: item},
                "when": None,
                "expect": {"rule_result": True},
            })
        for i, item in enumerate(negative_values, 1):
            vectors.append({
                "id": make_id(rule_id, f"rejected.{i}"),
                "source_semantic_id": rule_id,
                "kind": "rule_negative",
                "given": {subject: item},
                "when": None,
                "expect": {"rule_result": False},
            })

        universe = enum_values_for_subject(subject, nodes)
        if universe:
            excluded = set(value)
            counterexamples = [item for item in universe if item not in excluded]
            for i, item in enumerate(counterexamples, 1):
                result = operator == "not_in"
                vectors.append({
                    "id": make_id(rule_id, f"enum-counterexample.{i}"),
                    "source_semantic_id": rule_id,
                    "kind": "rule_negative" if not result else "rule_positive",
                    "given": {subject: item},
                    "when": None,
                    "expect": {"rule_result": result},
                })
        return vectors

    if operator in {"==", "!=", ">", ">=", "<", "<="} and isinstance(subject, str):
        vectors.append({
            "id": make_id(rule_id, "declared-boundary"),
            "source_semantic_id": rule_id,
            "kind": "boundary_intent",
            "given": {"subject": subject, "operator": operator, "boundary": value},
            "when": None,
            "expect": {"derive_around_boundary": True},
            "note": "v0.1 不猜测数值类型的最小步长；目标测试生成器应根据 ValueType 决定边界样例。",
        })
        return vectors

    if operator in {"all", "any", "not"}:
        conditions = rule.get("conditions") or []
        vectors.append({
            "id": make_id(rule_id, "logical-combination"),
            "source_semantic_id": rule_id,
            "kind": "condition_assignment_intent",
            "given": {"operator": operator, "conditions": conditions},
            "when": None,
            "expect": {"generate_truth_table_subset": True},
            "note": "当无法安全构造领域对象时，保留组合条件意图而不伪造输入。",
        })
        return vectors

    expression = rule.get("expression")
    if expression is not None:
        vectors.append({
            "id": make_id(rule_id, "expression-property"),
            "source_semantic_id": rule_id,
            "kind": "rule_expression_intent",
            "given": {"expression": expression},
            "when": None,
            "expect": {"evaluate_expression": True},
        })
    return vectors


def scenario_vector(scenario: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "id": make_id(scenario["id"], "example"),
        "source_semantic_id": scenario["id"],
        "kind": "scenario",
        "given": scenario.get("given", []),
        "when": scenario.get("when", []),
        "expect": scenario.get("then", scenario.get("expect", [])),
    }


def transition_vectors(node: Dict[str, Any]) -> List[Dict[str, Any]]:
    if node.get("kind") == "transition":
        return [{
            "id": make_id(node["id"], "allowed"),
            "source_semantic_id": node["id"],
            "kind": "state_transition",
            "given": {"state": node.get("from")},
            "when": {"trigger": node.get("trigger")},
            "expect": {"state": node.get("to")},
        }]
    if node.get("kind") == "forbidden_transition":
        return [{
            "id": make_id(node["id"], "forbidden"),
            "source_semantic_id": node["id"],
            "kind": "forbidden_state_transition",
            "given": {"state": node.get("from")},
            "when": {"target_state": node.get("to")},
            "expect": {"allowed": False},
        }]
    return []


def constraint_vectors(node: Dict[str, Any]) -> List[Dict[str, Any]]:
    kind = node.get("kind")
    if kind in {"invariant", "postcondition", "precondition"} and node.get("expression") is not None:
        return [{
            "id": make_id(node["id"], "property"),
            "source_semantic_id": node["id"],
            "kind": "property_intent",
            "given": {},
            "when": None,
            "expect": {"property": node.get("expression")},
        }]
    if kind == "temporal":
        return [{
            "id": make_id(node["id"], "temporal"),
            "source_semantic_id": node["id"],
            "kind": "temporal_integration_intent",
            "given": {},
            "when": {"trigger": node.get("trigger")},
            "expect": {
                "eventually": node.get("requirement"),
                "time_bound": node.get("time_bound"),
            },
        }]
    return []


def generate(clm: Dict[str, Any]) -> Dict[str, Any]:
    nodes = node_index(clm)
    vectors: List[Dict[str, Any]] = []
    warnings: List[str] = []

    for node in nodes.values():
        kind = node.get("kind")
        if kind == "rule":
            vectors.extend(rule_vectors(node, nodes))
        elif kind == "scenario":
            vectors.append(scenario_vector(node))
        elif kind in {"transition", "forbidden_transition"}:
            vectors.extend(transition_vectors(node))
        elif kind in {"invariant", "postcondition", "precondition", "temporal"}:
            vectors.extend(constraint_vectors(node))

    if not vectors:
        warnings.append("当前 CLM 中没有生成任何测试向量；请检查是否存在 Rule、Scenario、Transition 或 Constraint。")

    return {
        "source_clm": root_of(clm).get("id"),
        "test_vector_version": "0.1",
        "vectors": vectors,
        "warnings": warnings,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="从 CLM 生成语言无关测试向量")
    parser.add_argument("clm", type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()

    result = generate(load_json(args.clm))
    text = json.dumps(result, ensure_ascii=False, indent=2)
    if args.output:
        args.output.write_text(text + "\n", encoding="utf-8")
    else:
        print(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
