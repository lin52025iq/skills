#!/usr/bin/env python3
"""原子应用 Semantic Change Set v0.2。

所有操作先在内存副本中依次执行；任一步失败则整个变更集失败，不写出部分模型。
"""

from __future__ import annotations

import argparse
import copy
import json
from pathlib import Path
from typing import Any, Dict, List, Tuple

from apply_semantic_patch import PatchError, apply_patch
from clm_model import find_node, root_of


class ChangeSetError(ValueError):
    pass


def load_json(path: Path) -> Dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def replace_reference(value: Any, old: str, new: str) -> int:
    count = 0
    if isinstance(value, dict):
        for key, child in list(value.items()):
            if isinstance(child, str) and child == old:
                value[key] = new
                count += 1
            else:
                count += replace_reference(child, old, new)
    elif isinstance(value, list):
        for i, child in enumerate(value):
            if isinstance(child, str) and child == old:
                value[i] = new
                count += 1
            else:
                count += replace_reference(child, old, new)
    return count


def apply_relation(model: Dict[str, Any], op: Dict[str, Any], remove: bool) -> Dict[str, Any]:
    root = root_of(model)
    relation = {
        "source": op.get("source"),
        "relation": op.get("relation"),
        "target": op.get("target"),
    }
    relations = root.setdefault("relations", [])
    if remove:
        before = len(relations)
        root["relations"] = [item for item in relations if not all(item.get(k) == v for k, v in relation.items())]
        if len(root["relations"]) == before:
            raise ChangeSetError(f"待移除关系不存在: {relation}")
        return {"type": "relation_removed", **relation}
    if any(all(item.get(k) == v for k, v in relation.items()) for item in relations):
        return {"type": "relation_unchanged", **relation}
    relations.append(relation)
    return {"type": "relation_added", **relation}


def apply_one(model: Dict[str, Any], op: Dict[str, Any]) -> Tuple[Dict[str, Any], Dict[str, Any]]:
    operation = op.get("operation")
    if operation in {"ADD_RELATION", "REMOVE_RELATION"}:
        result = copy.deepcopy(model)
        diff = apply_relation(result, op, operation == "REMOVE_RELATION")
        return result, diff

    if operation == "REPLACE_REFERENCE":
        target_id = op.get("target_semantic_id")
        new_ref = op.get("after") or op.get("value")
        if not isinstance(target_id, str) or not isinstance(new_ref, str):
            raise ChangeSetError("REPLACE_REFERENCE 需要 target_semantic_id 和字符串 after/value")
        result = copy.deepcopy(model)
        _, node = find_node(result, target_id)
        old_ref = op.get("before")
        if not isinstance(old_ref, str):
            raise ChangeSetError("REPLACE_REFERENCE 需要 before 指定旧引用")
        count = replace_reference(node, old_ref, new_ref)
        if count == 0:
            raise ChangeSetError(f"节点 {target_id} 中不存在引用 {old_ref}")
        return result, {"type": "reference_replaced", "id": target_id, "before": old_ref, "after": new_ref, "count": count}

    patch = dict(op)
    patch["patch_id"] = op.get("operation_id") or f"patch.change-set.{operation.lower()}"
    try:
        updated, raw_diff = apply_patch(model, patch)
    except PatchError as exc:
        raise ChangeSetError(str(exc)) from exc
    changes = raw_diff.get("changes", [])
    return updated, {"type": "patch_operation", "operation": operation, "changes": changes}


def apply_change_set(document: Dict[str, Any], change_set: Dict[str, Any]) -> Tuple[Dict[str, Any], Dict[str, Any]]:
    cs = change_set.get("semantic_change_set", change_set)
    working = copy.deepcopy(document)
    root = root_of(working)
    expected_version = cs.get("base_model_version")
    if expected_version is not None and str(root.get("version")) != str(expected_version):
        raise ChangeSetError(f"模型版本不匹配：期望 {expected_version}，实际 {root.get('version')}")

    operation_diffs: List[Dict[str, Any]] = []
    changed_ids: List[str] = []
    for index, op in enumerate(cs.get("operations", [])):
        try:
            working, diff = apply_one(working, op)
        except Exception as exc:
            raise ChangeSetError(f"第 {index + 1} 个操作失败（{op.get('operation')}）：{exc}") from exc
        operation_diffs.append({"index": index, "operation_id": op.get("operation_id"), **diff})
        for candidate in (op.get("target_semantic_id"), op.get("source"), op.get("target")):
            if isinstance(candidate, str):
                changed_ids.append(candidate)
        after = op.get("after")
        if op.get("operation") == "ADD_NODE" and isinstance(after, dict) and isinstance(after.get("id"), str):
            changed_ids.append(after["id"])

    diff = {
        "change_set_id": cs.get("change_set_id"),
        "intent": cs.get("intent"),
        "behavior_change_level": cs.get("behavior_change_level"),
        "changed_semantic_ids": list(dict.fromkeys(changed_ids)),
        "operations": operation_diffs,
        "verification_required": cs.get("verification_required", []),
    }
    return working, diff


def main() -> int:
    parser = argparse.ArgumentParser(description="原子应用语义变更集 v0.2")
    parser.add_argument("clm", type=Path)
    parser.add_argument("change_set", type=Path)
    parser.add_argument("-o", "--output", type=Path, required=True)
    parser.add_argument("--diff-output", type=Path)
    args = parser.parse_args()

    try:
        updated, diff = apply_change_set(load_json(args.clm), load_json(args.change_set))
    except (OSError, json.JSONDecodeError, ChangeSetError) as exc:
        print(json.dumps({"ok": False, "error": str(exc)}, ensure_ascii=False, indent=2))
        return 1

    args.output.write_text(json.dumps(updated, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    if args.diff_output:
        args.diff_output.write_text(json.dumps(diff, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    else:
        print(json.dumps(diff, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
