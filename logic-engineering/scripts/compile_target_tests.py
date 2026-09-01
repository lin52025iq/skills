#!/usr/bin/env python3
"""将语言无关 Test Vectors + IIR 编译为 Target Test Plan v0.1。"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Dict, List


def load_json(path: Path) -> Dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def save_json(path: Path, value: Dict[str, Any]) -> None:
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def behavior_to_usecase(iir: Dict[str, Any]) -> Dict[str, str]:
    result: Dict[str, str] = {}
    for uc in iir.get("iir", iir).get("use_cases", []) or []:
        for ref in uc.get("semantic_refs", []) or []:
            if isinstance(ref, str) and ref.startswith("behavior."):
                result[ref] = uc.get("id")
    return result


def semantic_to_usecase(iir: Dict[str, Any]) -> Dict[str, str]:
    root = iir.get("iir", iir)
    result = behavior_to_usecase(iir)
    for trace in root.get("traceability", []) or []:
        impl = trace.get("implementation_id")
        if not isinstance(impl, str):
            continue
        for ref in trace.get("semantic_refs", []) or []:
            if isinstance(ref, str):
                result.setdefault(ref, impl)
    return result


def dependencies_for_usecase(iir: Dict[str, Any], usecase_id: str | None) -> List[str]:
    if not usecase_id:
        return []
    root = iir.get("iir", iir)
    for uc in root.get("use_cases", []) or []:
        if uc.get("id") == usecase_id:
            return list(uc.get("dependencies", []) or [])
    return []


def scenario_behavior(vector: Dict[str, Any]) -> str | None:
    when = vector.get("when")
    if isinstance(when, dict):
        behaviors = when.get("behaviors")
        if isinstance(behaviors, list) and behaviors:
            return behaviors[0]
        trigger = when.get("trigger")
        if isinstance(trigger, str) and trigger.startswith("behavior."):
            return trigger
    return None


def compile_case(vector: Dict[str, Any], iir: Dict[str, Any], mapping: Dict[str, str]) -> Dict[str, Any]:
    source = vector.get("source_semantic_id")
    target_use_case = mapping.get(source) if isinstance(source, str) else None
    if not target_use_case:
        behavior = scenario_behavior(vector)
        if behavior:
            target_use_case = mapping.get(behavior)

    unsupported: List[str] = []
    kind = vector.get("kind")
    if kind in {"property_intent", "temporal_integration_intent"}:
        unsupported.append("该测试类型需要专用 property/integration generator")
    if kind == "boundary_intent" and vector.get("expect", {}).get("derive_around_boundary"):
        unsupported.append("需要根据 ValueType 推导目标语言具体边界值")
    if target_use_case is None and kind in {"scenario", "state_transition", "forbidden_state_transition"}:
        unsupported.append("无法定位对应 Use Case")

    required_fakes = dependencies_for_usecase(iir, target_use_case)
    return {
        "id": vector.get("id"),
        "source_semantic_id": source,
        "kind": kind,
        "target_use_case": target_use_case,
        "given": vector.get("given", {}),
        "invoke": vector.get("when"),
        "expect": vector.get("expect", {}),
        "required_fakes": required_fakes,
        "unsupported": unsupported,
    }


def compile_plan(vectors: Dict[str, Any], iir: Dict[str, Any]) -> Dict[str, Any]:
    iir_root = iir.get("iir", iir)
    profile = iir_root.get("target_profile", {})
    mapping = semantic_to_usecase(iir)
    cases = [compile_case(vector, iir, mapping) for vector in vectors.get("vectors", []) or []]
    unsupported_count = sum(1 for case in cases if case["unsupported"])
    return {
        "target_test_plan": {
            "version": "0.1",
            "source_clm_id": iir_root.get("source_clm_id"),
            "source_semantic_hash": iir_root.get("source_semantic_hash"),
            "language": profile.get("language"),
            "framework": profile.get("test_framework"),
            "cases": cases,
            "summary": {
                "total": len(cases),
                "ready": len(cases) - unsupported_count,
                "unsupported": unsupported_count,
            },
        }
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="编译 Target Test Plan")
    parser.add_argument("test_vectors", type=Path)
    parser.add_argument("iir", type=Path)
    parser.add_argument("-o", "--output", type=Path)
    args = parser.parse_args()
    try:
        plan = compile_plan(load_json(args.test_vectors), load_json(args.iir))
    except (OSError, json.JSONDecodeError) as exc:
        print(json.dumps({"ok": False, "error": str(exc)}, ensure_ascii=False, indent=2))
        return 1
    if args.output:
        save_json(args.output, plan)
    else:
        print(json.dumps(plan, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
