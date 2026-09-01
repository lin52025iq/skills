#!/usr/bin/env python3
"""从 CLM 直接生成与目标编程语言无关的测试向量。"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Dict, List, Optional

from clm_model import build_node_index, root_of
from symbol_table import build_symbol_table


def load_json(path: Path) -> Dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def enum_values_for_subject(subject: str, nodes: Dict[str, Dict[str, Any]], symbols: Dict[str, Dict[str, Any]]) -> Optional[List[Any]]:
    symbol = symbols.get(subject)
    if not symbol:
        return None
    type_id = symbol.get("type")
    enum = nodes.get(type_id) if isinstance(type_id, str) else None
    if enum and enum.get("kind") == "enum" and isinstance(enum.get("values"), list):
        return enum["values"]
    return None


def make_id(source_id: str, suffix: str) -> str:
    return f"test.{source_id}.{suffix}"


def unwrap_ref(value: Any) -> Optional[str]:
    return value.get("ref") if isinstance(value, dict) and isinstance(value.get("ref"), str) else None


def unwrap_literal(value: Any) -> Any:
    if isinstance(value, dict) and "literal" in value:
        return value["literal"]
    if isinstance(value, dict) and isinstance(value.get("enum"), dict):
        return value["enum"].get("value")
    return None


def v02_rule_vectors(rule: Dict[str, Any], nodes: Dict[str, Dict[str, Any]], symbols: Dict[str, Dict[str, Any]]) -> List[Dict[str, Any]]:
    expr = rule.get("expression")
    if not isinstance(expr, dict):
        return []
    rule_id = rule["id"]
    op = expr.get("op")
    vectors: List[Dict[str, Any]] = []

    if op in {"in", "not_in"}:
        subject = unwrap_ref(expr.get("left"))
        values = unwrap_literal(expr.get("right"))
        if isinstance(subject, str) and isinstance(values, list):
            for i, item in enumerate(values, 1):
                expected = op == "in"
                vectors.append({
                    "id": make_id(rule_id, f"declared.{i}"),
                    "source_semantic_id": rule_id,
                    "kind": "rule_positive" if expected else "rule_negative",
                    "given": {subject: item},
                    "when": None,
                    "expect": {"rule_result": expected},
                })
            universe = enum_values_for_subject(subject, nodes, symbols)
            if universe:
                declared = set(values)
                for i, item in enumerate([v for v in universe if v not in declared], 1):
                    expected = op == "not_in"
                    vectors.append({
                        "id": make_id(rule_id, f"enum-counterexample.{i}"),
                        "source_semantic_id": rule_id,
                        "kind": "rule_positive" if expected else "rule_negative",
                        "given": {subject: item},
                        "when": None,
                        "expect": {"rule_result": expected},
                    })
            return vectors

    if op in {"eq", "ne", "lt", "le", "gt", "ge"}:
        subject = unwrap_ref(expr.get("left"))
        boundary = unwrap_literal(expr.get("right"))
        vectors.append({
            "id": make_id(rule_id, "typed-boundary"),
            "source_semantic_id": rule_id,
            "kind": "boundary_intent",
            "given": {"subject": subject, "operator": op, "boundary": boundary},
            "when": None,
            "expect": {"derive_around_boundary": True},
            "note": "目标测试生成器应根据 Symbol Table / ValueType 推导最小步长和合法边界。",
        })
        return vectors

    if op in {"all", "any", "not"}:
        vectors.append({
            "id": make_id(rule_id, "logical-combination"),
            "source_semantic_id": rule_id,
            "kind": "condition_assignment_intent",
            "given": {"expression": expr},
            "when": None,
            "expect": {"generate_truth_table_subset": True},
        })
        return vectors

    return [{
        "id": make_id(rule_id, "expression-property"),
        "source_semantic_id": rule_id,
        "kind": "rule_expression_intent",
        "given": {"expression": expr},
        "when": None,
        "expect": {"evaluate_expression": True},
    }]


def v01_rule_vectors(rule: Dict[str, Any], nodes: Dict[str, Dict[str, Any]], symbols: Dict[str, Dict[str, Any]]) -> List[Dict[str, Any]]:
    rule_id = rule["id"]
    operator = rule.get("operator")
    subject = rule.get("subject")
    value = rule.get("value")
    vectors: List[Dict[str, Any]] = []

    if operator in {"in", "not_in"} and isinstance(subject, str) and isinstance(value, list):
        for i, item in enumerate(value, 1):
            expected = operator == "in"
            vectors.append({
                "id": make_id(rule_id, f"declared.{i}"),
                "source_semantic_id": rule_id,
                "kind": "rule_positive" if expected else "rule_negative",
                "given": {subject: item},
                "when": None,
                "expect": {"rule_result": expected},
            })
        universe = enum_values_for_subject(subject, nodes, symbols)
        if universe:
            declared = set(value)
            for i, item in enumerate([v for v in universe if v not in declared], 1):
                expected = operator == "not_in"
                vectors.append({
                    "id": make_id(rule_id, f"enum-counterexample.{i}"),
                    "source_semantic_id": rule_id,
                    "kind": "rule_positive" if expected else "rule_negative",
                    "given": {subject: item},
                    "when": None,
                    "expect": {"rule_result": expected},
                })
        return vectors

    if operator in {"==", "!=", ">", ">=", "<", "<="} and isinstance(subject, str):
        return [{
            "id": make_id(rule_id, "declared-boundary"),
            "source_semantic_id": rule_id,
            "kind": "boundary_intent",
            "given": {"subject": subject, "operator": operator, "boundary": value},
            "when": None,
            "expect": {"derive_around_boundary": True},
            "note": "v0.1 兼容模式；建议迁移到 Typed Expression AST。",
        }]
    return []


def rule_vectors(rule: Dict[str, Any], nodes: Dict[str, Dict[str, Any]], symbols: Dict[str, Dict[str, Any]]) -> List[Dict[str, Any]]:
    if isinstance(rule.get("expression"), dict):
        return v02_rule_vectors(rule, nodes, symbols)
    return v01_rule_vectors(rule, nodes, symbols)


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
            "when": {"trigger": node.get("trigger"), "guard": node.get("guard")},
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
    if kind in {"invariant", "postcondition", "precondition", "constraint"} and node.get("expression") is not None:
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
            "expect": {"eventually": node.get("requirement"), "time_bound": node.get("time_bound")},
        }]
    return []


def generate(clm: Dict[str, Any]) -> Dict[str, Any]:
    nodes = build_node_index(clm)
    symbols = build_symbol_table(clm)
    vectors: List[Dict[str, Any]] = []
    warnings: List[str] = []

    for node in nodes.values():
        kind = node.get("kind")
        if kind == "rule":
            vectors.extend(rule_vectors(node, nodes, symbols))
        elif kind == "scenario":
            vectors.append(scenario_vector(node))
        elif kind in {"transition", "forbidden_transition"}:
            vectors.extend(transition_vectors(node))
        elif kind in {"invariant", "postcondition", "precondition", "constraint", "temporal"}:
            vectors.extend(constraint_vectors(node))

    if not vectors:
        warnings.append("当前 CLM 中没有生成任何测试向量；请检查是否存在 Rule、Scenario、Transition 或 Constraint。")

    return {
        "source_clm": root_of(clm).get("id"),
        "test_vector_version": "0.2",
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
