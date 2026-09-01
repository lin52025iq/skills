#!/usr/bin/env python3
"""将 CLM 编译为最小实现中间表示（IIR）。

第一版只做确定性技术映射：
- Behavior → use case
- Rule → guard / validation
- Action → operation
- Effect → persistence / external IO / event
- Constraint → transaction / concurrency / idempotency requirement
- Primitive → target binding

节点索引统一使用 clm_model.py，避免 rules / decisions / actions 被遗漏。
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Dict

from clm_model import build_node_index, root_of


def load_json(path: Path) -> Dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def save_json(path: Path, value: Dict[str, Any]) -> None:
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def compile_target_profile(profile: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "language": profile.get("language"),
        "version": profile.get("version"),
        "framework": profile.get("framework"),
        "architecture": profile.get("architecture"),
        "persistence": profile.get("persistence"),
        "messaging": profile.get("messaging"),
        "transaction_strategy": profile.get("transaction_strategy"),
        "error_model": profile.get("error_model"),
        "test_framework": profile.get("test_framework"),
    }


def compile_rule(rule: Dict[str, Any]) -> Dict[str, Any]:
    condition: Dict[str, Any]
    if "expression" in rule:
        condition = {"expression": rule.get("expression")}
    elif "conditions" in rule:
        condition = {"operator": rule.get("operator"), "conditions": rule.get("conditions", [])}
    else:
        condition = {
            "operator": rule.get("operator"),
            "subject": rule.get("subject"),
            "value": rule.get("value"),
        }
    return {
        "semantic_id": rule.get("id"),
        "kind": "guard",
        "condition": condition,
        "failure": rule.get("failure"),
    }


def compile_action(action: Dict[str, Any], idx: Dict[str, Dict[str, Any]]) -> Dict[str, Any]:
    result = {
        "semantic_id": action.get("id"),
        "kind": action.get("kind", "action"),
        "operation": action.get("operation"),
        "target": action.get("target"),
        "value": action.get("value"),
        "effects": [],
    }
    for ref in action.get("effects", []) or []:
        effect = idx.get(ref)
        if effect:
            result["effects"].append({
                "semantic_id": ref,
                "kind": effect.get("kind"),
                "resource": effect.get("resource"),
                "system": effect.get("system"),
                "operation": effect.get("operation"),
                "idempotency": effect.get("idempotency"),
            })
        else:
            result["effects"].append({"semantic_id": ref, "unresolved": True})
    if action.get("kind") == "foreach":
        result.update({
            "collection": action.get("collection"),
            "item": action.get("item"),
            "when": action.get("when"),
            "do": action.get("do", []),
        })
    return result


def compile_decision(decision: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "semantic_id": decision.get("id"),
        "kind": "decision",
        "when": decision.get("when"),
        "then": decision.get("then", []),
        "else": decision.get("else", []),
    }


def compile_constraint(c: Dict[str, Any]) -> Dict[str, Any]:
    result = {"semantic_id": c.get("id"), "kind": c.get("kind")}
    for key in (
        "expression", "trigger", "requirement", "time_bound", "resource",
        "scope", "policy", "actions", "guarantee", "operation", "key",
    ):
        if key in c:
            result[key] = c[key]
    return result


def compile_behavior(behavior: Dict[str, Any], idx: Dict[str, Dict[str, Any]]) -> Dict[str, Any]:
    guards = []
    for ref in behavior.get("preconditions", []) or []:
        rule = idx.get(ref)
        guards.append(compile_rule(rule) if rule else {"semantic_id": ref, "unresolved": True})

    steps = []
    for ref in behavior.get("flow", []) or []:
        node = idx.get(ref)
        if not node:
            steps.append({"semantic_id": ref, "unresolved": True})
        elif node.get("kind") == "decision":
            steps.append(compile_decision(node))
        else:
            steps.append(compile_action(node, idx))

    return {
        "semantic_id": behavior.get("id"),
        "name": behavior.get("name"),
        "kind": "use_case",
        "inputs": behavior.get("inputs", []),
        "guards": guards,
        "steps": steps,
        "outputs": behavior.get("outputs", []),
        "failures": behavior.get("failures", []),
        "postconditions": behavior.get("postconditions", []),
    }


def compile_primitive_bindings(root: Dict[str, Any], profile: Dict[str, Any]) -> list[Dict[str, Any]]:
    profile_id = profile.get("id") or profile.get("name")
    bindings = []
    for p in root.get("primitives", []) or []:
        raw = p.get("bindings", {}) or {}
        binding = None
        if profile_id and profile_id in raw:
            binding = raw[profile_id]
        elif profile.get("binding_key") and profile["binding_key"] in raw:
            binding = raw[profile["binding_key"]]
        bindings.append({
            "semantic_id": p.get("id"),
            "binding": binding,
            "required_contract": p.get("contract", {}),
            "resolved": binding is not None,
        })
    return bindings


def compile_iir(clm: Dict[str, Any], profile: Dict[str, Any]) -> Dict[str, Any]:
    root = root_of(clm)
    idx = build_node_index(root)
    iir = {
        "iir": {
            "source_clm_id": root.get("id"),
            "source_clm_version": root.get("version"),
            "target_profile": compile_target_profile(profile),
            "use_cases": [],
            "constraints": [],
            "state_models": [],
            "primitive_bindings": [],
            "unresolved": [],
        }
    }
    out = iir["iir"]

    for b in root.get("behaviors", []) or []:
        out["use_cases"].append(compile_behavior(b, idx))

    for c in root.get("constraints", []) or []:
        out["constraints"].append(compile_constraint(c))

    for s in root.get("states", []) or []:
        if s.get("kind") == "state_machine":
            transitions = []
            for ref in s.get("transitions", []) or []:
                t = idx.get(ref)
                if t:
                    transitions.append({
                        "semantic_id": t.get("id"),
                        "from": t.get("from"),
                        "to": t.get("to"),
                        "trigger": t.get("trigger"),
                        "guard": t.get("guard"),
                    })
                else:
                    transitions.append({"semantic_id": ref, "unresolved": True})
            out["state_models"].append({
                "semantic_id": s.get("id"),
                "states": s.get("states", []),
                "transitions": transitions,
            })

    out["primitive_bindings"] = compile_primitive_bindings(root, profile)

    for use_case in out["use_cases"]:
        for guard in use_case["guards"]:
            if guard.get("unresolved"):
                out["unresolved"].append(guard["semantic_id"])
        for step in use_case["steps"]:
            if step.get("unresolved"):
                out["unresolved"].append(step["semantic_id"])
            for effect in step.get("effects", []) or []:
                if effect.get("unresolved"):
                    out["unresolved"].append(effect["semantic_id"])
    for binding in out["primitive_bindings"]:
        if not binding["resolved"]:
            out["unresolved"].append(binding["semantic_id"])

    out["unresolved"] = sorted(set(out["unresolved"]))
    return iir


def main() -> int:
    parser = argparse.ArgumentParser(description="CLM → IIR 最小编译器")
    parser.add_argument("clm", type=Path)
    parser.add_argument("profile", type=Path)
    parser.add_argument("-o", "--output", type=Path)
    args = parser.parse_args()

    try:
        clm = load_json(args.clm)
        profile = load_json(args.profile)
        profile = profile.get("target_profile", profile)
        iir = compile_iir(clm, profile)
    except (OSError, json.JSONDecodeError) as exc:
        print(json.dumps({"ok": False, "error": str(exc)}, ensure_ascii=False, indent=2))
        return 1

    if args.output:
        save_json(args.output, iir)
    else:
        print(json.dumps(iir, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
