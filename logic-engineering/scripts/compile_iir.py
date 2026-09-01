#!/usr/bin/env python3
"""将 CLM v0.2 编译为 IIR v0.2。

IIR v0.2 显式产生：
- Use Case
- Repository Contract
- External Port
- Transaction / Concurrency / Retry / Idempotency Plan
- Error Mapping
- Primitive Binding
- Generation Region
- Traceability
- Unresolved
"""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any, Dict, Iterable, List, Set

from clm_model import build_node_index, root_of
from semantic_hash import semantic_hash


def load_json(path: Path) -> Dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def save_json(path: Path, value: Dict[str, Any]) -> None:
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def compile_target_profile(profile: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "id": profile.get("id") or profile.get("name"),
        "language": profile.get("language"),
        "version": profile.get("version"),
        "framework": profile.get("framework"),
        "architecture": profile.get("architecture"),
        "persistence": profile.get("persistence"),
        "messaging": profile.get("messaging"),
        "transaction_strategy": profile.get("transaction_strategy"),
        "concurrency_strategy": profile.get("concurrency_strategy"),
        "retry_strategy": profile.get("retry_strategy"),
        "error_model": profile.get("error_model"),
        "test_framework": profile.get("test_framework"),
    }


def safe_name(semantic_id: str) -> str:
    return re.sub(r"[^A-Za-z0-9_]+", "_", semantic_id).strip("_")


def entity_from_resource(resource: Any, idx: Dict[str, Dict[str, Any]]) -> str | None:
    if not isinstance(resource, str):
        return None
    if resource in idx and idx[resource].get("kind") == "entity":
        return resource
    parts = resource.split(".")
    for i in range(len(parts), 1, -1):
        candidate = ".".join(parts[:i])
        node = idx.get(candidate)
        if node and node.get("kind") == "entity":
            return candidate
    # Entity fields are often nested and not top-level nodes.
    for node_id, node in idx.items():
        if node.get("kind") != "entity":
            continue
        for field in node.get("fields", []) or []:
            if isinstance(field, dict) and field.get("id") == resource:
                return node_id
    return None


def compile_guard(rule: Dict[str, Any]) -> Dict[str, Any]:
    expression = rule.get("expression")
    if expression is None:
        expression = {
            "operator": rule.get("operator"),
            "subject": rule.get("subject"),
            "value": rule.get("value"),
        }
    return {
        "semantic_ref": rule.get("id"),
        "expression": expression,
        "failure_ref": rule.get("failure"),
    }


def compile_effect(effect: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "semantic_ref": effect.get("id"),
        "kind": effect.get("kind"),
        "resource": effect.get("resource"),
        "system": effect.get("system"),
        "operation": effect.get("operation"),
        "idempotency": effect.get("idempotency"),
    }


def compile_action(action: Dict[str, Any], idx: Dict[str, Dict[str, Any]]) -> Dict[str, Any]:
    result: Dict[str, Any] = {
        "semantic_ref": action.get("id"),
        "kind": action.get("kind", "action"),
        "operation": action.get("operation"),
        "target": action.get("target"),
        "value": action.get("value"),
        "effects": [],
    }
    for ref in action.get("effects", []) or []:
        effect = idx.get(ref)
        result["effects"].append(compile_effect(effect) if effect else {"semantic_ref": ref, "unresolved": True})
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
        "semantic_ref": decision.get("id"),
        "kind": "decision",
        "when": decision.get("when"),
        "then": decision.get("then", []),
        "else": decision.get("else", []),
    }


def compile_behavior(behavior: Dict[str, Any], idx: Dict[str, Dict[str, Any]]) -> Dict[str, Any]:
    guards: List[Dict[str, Any]] = []
    steps: List[Dict[str, Any]] = []
    dependencies: Set[str] = set()

    for ref in behavior.get("preconditions", []) or []:
        rule = idx.get(ref)
        guards.append(compile_guard(rule) if rule else {"semantic_ref": ref, "unresolved": True})

    for ref in behavior.get("flow", []) or []:
        node = idx.get(ref)
        if not node:
            steps.append({"semantic_ref": ref, "unresolved": True})
            continue
        if node.get("kind") == "decision":
            steps.append(compile_decision(node))
        else:
            step = compile_action(node, idx)
            steps.append(step)
            for effect in step.get("effects", []):
                if effect.get("kind") in {"write", "persist", "read"}:
                    entity = entity_from_resource(effect.get("resource"), idx)
                    if entity:
                        dependencies.add(f"repository.{safe_name(entity)}")
                elif effect.get("kind") == "external_call" and effect.get("system"):
                    dependencies.add(f"port.{safe_name(str(effect['system']))}")

    return {
        "id": f"usecase.{safe_name(str(behavior.get('id')))}",
        "kind": "use_case",
        "semantic_refs": [behavior.get("id")],
        "name": behavior.get("name"),
        "inputs": behavior.get("inputs", []),
        "guards": guards,
        "steps": steps,
        "outputs": behavior.get("outputs", []),
        "failure_refs": behavior.get("failures", []),
        "postcondition_refs": behavior.get("postconditions", []),
        "dependencies": sorted(dependencies),
    }


def collect_repository_contracts(root: Dict[str, Any], idx: Dict[str, Dict[str, Any]], profile: Dict[str, Any]) -> List[Dict[str, Any]]:
    by_entity: Dict[str, Dict[str, Any]] = {}
    for effect in root.get("effects", []) or []:
        if effect.get("kind") not in {"read", "write", "persist"}:
            continue
        entity = entity_from_resource(effect.get("resource"), idx)
        if not entity:
            continue
        contract = by_entity.setdefault(entity, {
            "id": f"repository.{safe_name(entity)}",
            "kind": "repository_contract",
            "entity_ref": entity,
            "operations": [],
            "binding": {
                "strategy": "relational" if profile.get("persistence") else "unspecified",
                "provider": profile.get("persistence"),
            },
        })
        operation_name = {"read": "load", "write": "save", "persist": "save"}.get(effect.get("kind"), "execute")
        contract["operations"].append({
            "name": operation_name,
            "semantic_refs": [effect.get("id")],
            "resource_ref": effect.get("resource"),
        })
    return list(by_entity.values())


def collect_external_ports(root: Dict[str, Any]) -> List[Dict[str, Any]]:
    by_system: Dict[str, Dict[str, Any]] = {}
    for effect in root.get("effects", []) or []:
        if effect.get("kind") != "external_call" or not effect.get("system"):
            continue
        system = str(effect["system"])
        port = by_system.setdefault(system, {
            "id": f"port.{safe_name(system)}",
            "kind": "external_port",
            "system": system,
            "operations": [],
            "generation_mode": "contract_only",
        })
        port["operations"].append({
            "name": effect.get("operation") or safe_name(str(effect.get("id"))),
            "semantic_refs": [effect.get("id")],
        })
    return list(by_system.values())


def constraint_plan(constraint: Dict[str, Any], profile: Dict[str, Any]) -> Dict[str, Any] | None:
    kind = constraint.get("kind")
    cid = str(constraint.get("id"))
    common = {"semantic_refs": [cid]}
    if kind == "atomicity":
        return {
            "id": f"transaction.{safe_name(cid)}",
            "kind": "transaction_plan",
            **common,
            "members": constraint.get("actions", []),
            "strategy": profile.get("transaction_strategy"),
            "provider": profile.get("persistence"),
        }
    if kind == "concurrency":
        return {
            "id": f"concurrency.{safe_name(cid)}",
            "kind": "concurrency_plan",
            **common,
            "resource_ref": constraint.get("resource"),
            "scope": constraint.get("scope"),
            "strategy": constraint.get("implementation_strategy") or profile.get("concurrency_strategy"),
            "key_ref": constraint.get("key"),
        }
    if kind == "idempotency":
        return {
            "id": f"idempotency.{safe_name(cid)}",
            "kind": "idempotency_plan",
            **common,
            "operation_ref": constraint.get("operation"),
            "key_ref": constraint.get("key"),
            "strategy": constraint.get("implementation_strategy") or "idempotency_key",
        }
    if kind == "constraint" and constraint.get("policy") == "retry":
        return {
            "id": f"retry.{safe_name(cid)}",
            "kind": "retry_plan",
            **common,
            "operation_ref": constraint.get("operation"),
            "strategy": constraint.get("strategy") or profile.get("retry_strategy"),
            "max_attempts": constraint.get("max_attempts"),
        }
    return None


def compile_primitive_bindings(root: Dict[str, Any], profile: Dict[str, Any]) -> List[Dict[str, Any]]:
    profile_id = profile.get("id") or profile.get("name")
    bindings = []
    for primitive in root.get("primitives", []) or []:
        raw = primitive.get("bindings", {}) or {}
        binding = None
        for key in (profile_id, profile.get("binding_key")):
            if key and key in raw:
                binding = raw[key]
                break
        bindings.append({
            "primitive_ref": primitive.get("id"),
            "binding": binding,
            "required_contract": primitive.get("contract", {}),
            "resolved": binding is not None,
        })
    return bindings


def make_error_mapping(error_ref: str, profile: Dict[str, Any]) -> Dict[str, Any]:
    suffix = error_ref.split(".")[-1]
    target = "".join(part.capitalize() for part in suffix.split("_")) or "DomainError"
    return {
        "id": f"error_mapping.{safe_name(error_ref)}",
        "semantic_error_ref": error_ref,
        "target_error": target,
        "transport": {},
        "error_model": profile.get("error_model"),
    }


def compile_iir(clm: Dict[str, Any], profile: Dict[str, Any]) -> Dict[str, Any]:
    root = root_of(clm)
    idx = build_node_index(clm)
    out: Dict[str, Any] = {
        "version": "0.2",
        "source_clm_id": root.get("id"),
        "source_clm_version": root.get("version"),
        "source_semantic_hash": semantic_hash(clm),
        "target_profile": compile_target_profile(profile),
        "use_cases": [],
        "repository_contracts": [],
        "external_ports": [],
        "transaction_plans": [],
        "concurrency_plans": [],
        "retry_plans": [],
        "idempotency_plans": [],
        "error_mappings": [],
        "primitive_bindings": [],
        "generation_regions": [],
        "traceability": [],
        "unresolved": [],
    }

    for behavior in root.get("behaviors", []) or []:
        uc = compile_behavior(behavior, idx)
        out["use_cases"].append(uc)
        out["generation_regions"].append({
            "id": f"region.{safe_name(uc['id'])}",
            "mode": "generated",
            "semantic_refs": [behavior.get("id")],
        })
        out["traceability"].append({
            "implementation_id": uc["id"],
            "semantic_refs": [behavior.get("id")] + list(behavior.get("preconditions", []) or []) + list(behavior.get("flow", []) or []),
            "expected_artifact_kinds": ["use_case", "unit_test"],
        })
        for error_ref in behavior.get("failures", []) or []:
            if isinstance(error_ref, str) and not any(m["semantic_error_ref"] == error_ref for m in out["error_mappings"]):
                out["error_mappings"].append(make_error_mapping(error_ref, profile))

    out["repository_contracts"] = collect_repository_contracts(root, idx, profile)
    out["external_ports"] = collect_external_ports(root)

    for repo in out["repository_contracts"]:
        out["generation_regions"].append({"id": f"region.{repo['id']}", "mode": "contract_only", "semantic_refs": [repo["entity_ref"]]})
    for port in out["external_ports"]:
        refs = [r for op in port["operations"] for r in op.get("semantic_refs", [])]
        out["generation_regions"].append({"id": f"region.{port['id']}", "mode": "contract_only", "semantic_refs": refs})

    for constraint in root.get("constraints", []) or []:
        plan = constraint_plan(constraint, profile)
        if not plan:
            continue
        bucket = {
            "transaction_plan": "transaction_plans",
            "concurrency_plan": "concurrency_plans",
            "retry_plan": "retry_plans",
            "idempotency_plan": "idempotency_plans",
        }[plan["kind"]]
        out[bucket].append(plan)
        if not plan.get("strategy"):
            out["unresolved"].append({
                "semantic_ref": constraint.get("id"),
                "reason": f"目标配置缺少 {plan['kind']} 的实现策略",
                "required_for": plan.get("id"),
                "severity": "blocking",
            })

    out["primitive_bindings"] = compile_primitive_bindings(root, profile)
    for binding in out["primitive_bindings"]:
        if binding["resolved"]:
            out["generation_regions"].append({
                "id": f"region.{safe_name(str(binding['primitive_ref']))}",
                "mode": "verified_binding",
                "semantic_refs": [binding["primitive_ref"]],
            })
        else:
            out["unresolved"].append({
                "semantic_ref": binding["primitive_ref"],
                "reason": "目标配置缺少 Primitive binding",
                "required_for": None,
                "severity": "blocking",
            })

    for uc in out["use_cases"]:
        for guard in uc.get("guards", []):
            if guard.get("unresolved"):
                out["unresolved"].append({"semantic_ref": guard["semantic_ref"], "reason": "Use Case guard 无法解析", "required_for": uc["id"], "severity": "blocking"})
        for step in uc.get("steps", []):
            if step.get("unresolved"):
                out["unresolved"].append({"semantic_ref": step["semantic_ref"], "reason": "Use Case step 无法解析", "required_for": uc["id"], "severity": "blocking"})
            for effect in step.get("effects", []) or []:
                if effect.get("unresolved"):
                    out["unresolved"].append({"semantic_ref": effect["semantic_ref"], "reason": "Action effect 无法解析", "required_for": uc["id"], "severity": "blocking"})

    return {"iir": out}


def main() -> int:
    parser = argparse.ArgumentParser(description="CLM v0.2 → IIR v0.2 编译器")
    parser.add_argument("clm", type=Path)
    parser.add_argument("profile", type=Path)
    parser.add_argument("-o", "--output", type=Path)
    args = parser.parse_args()

    try:
        clm = load_json(args.clm)
        profile = load_json(args.profile)
        profile = profile.get("target_profile", profile)
        iir = compile_iir(clm, profile)
    except (OSError, json.JSONDecodeError, ValueError) as exc:
        print(json.dumps({"ok": False, "error": str(exc)}, ensure_ascii=False, indent=2))
        return 1

    if args.output:
        save_json(args.output, iir)
    else:
        print(json.dumps(iir, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
