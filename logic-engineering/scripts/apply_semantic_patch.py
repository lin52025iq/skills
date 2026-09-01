#!/usr/bin/env python3
"""应用语义补丁到 CLM。

第一版目标：
- 支持 UPDATE_FIELD / ADD_MEMBER / REMOVE_MEMBER / ADD_NODE / REMOVE_NODE
- 修改前校验 before/preconditions
- 输出语义差异摘要
- 保持操作目标基于稳定 Semantic ID，而不是文件路径
- 节点集合与 kind 映射统一由 clm_model.py 管理
"""

from __future__ import annotations

import argparse
import copy
import json
import sys
from pathlib import Path
from typing import Any, Dict, List, Tuple

from clm_model import (
    CANONICAL_COLLECTIONS,
    build_node_location_index,
    ensure_collection,
    infer_collection_for_node,
    root_of,
)


class PatchError(Exception):
    pass


def load_json(path: Path) -> Dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def save_json(path: Path, value: Dict[str, Any]) -> None:
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def find_node(clm: Dict[str, Any], semantic_id: str) -> Tuple[str, Dict[str, Any]]:
    item = build_node_location_index(clm).get(semantic_id)
    if item is None:
        raise PatchError(f"找不到目标语义节点: {semantic_id}")
    return item


def get_by_path(obj: Any, path: List[str]) -> Any:
    cur = obj
    for part in path:
        if isinstance(cur, dict):
            if part not in cur:
                raise PatchError(f"字段不存在: {'.'.join(path)}")
            cur = cur[part]
        elif isinstance(cur, list):
            try:
                idx = int(part)
            except ValueError as exc:
                raise PatchError(f"列表路径必须使用整数索引: {part}") from exc
            if idx < 0 or idx >= len(cur):
                raise PatchError(f"列表索引越界: {part}")
            cur = cur[idx]
        else:
            raise PatchError(f"无法继续解析字段路径: {'.'.join(path)}")
    return cur


def set_by_path(obj: Any, path: List[str], value: Any) -> None:
    if not path:
        raise PatchError("UPDATE_FIELD 必须提供字段路径")
    cur = obj
    for part in path[:-1]:
        if isinstance(cur, dict):
            if part not in cur:
                raise PatchError(f"字段不存在: {'.'.join(path)}")
            cur = cur[part]
        elif isinstance(cur, list):
            try:
                idx = int(part)
            except ValueError as exc:
                raise PatchError(f"列表路径必须使用整数索引: {part}") from exc
            if idx < 0 or idx >= len(cur):
                raise PatchError(f"列表索引越界: {part}")
            cur = cur[idx]
        else:
            raise PatchError(f"无法继续解析字段路径: {'.'.join(path)}")

    last = path[-1]
    if isinstance(cur, dict):
        if last not in cur:
            raise PatchError(f"字段不存在: {'.'.join(path)}")
        cur[last] = value
    elif isinstance(cur, list):
        try:
            idx = int(last)
        except ValueError as exc:
            raise PatchError(f"列表路径必须使用整数索引: {last}") from exc
        if idx < 0 or idx >= len(cur):
            raise PatchError(f"列表索引越界: {last}")
        cur[idx] = value
    else:
        raise PatchError(f"无法更新字段路径: {'.'.join(path)}")


def normalize_patch(raw: Dict[str, Any]) -> Dict[str, Any]:
    return raw.get("semantic_patch", raw)


def ensure_before(node: Dict[str, Any], patch: Dict[str, Any]) -> None:
    before = patch.get("before")
    field_path = patch.get("field_path")
    if before is None or not field_path:
        return
    current = get_by_path(node, field_path.split("."))
    if current != before:
        raise PatchError(f"补丁前置值不匹配：期望 {before!r}，实际 {current!r}")


def apply_patch(clm: Dict[str, Any], raw_patch: Dict[str, Any]) -> Tuple[Dict[str, Any], Dict[str, Any]]:
    patch = normalize_patch(raw_patch)
    target = patch.get("target_semantic_id")
    operation = patch.get("operation")
    if not operation:
        raise PatchError("补丁缺少 operation")

    result = copy.deepcopy(clm)
    root = root_of(result)
    diff: Dict[str, Any] = {
        "patch_id": patch.get("patch_id"),
        "target_semantic_id": target,
        "operation": operation,
        "changes": [],
    }

    if operation == "ADD_NODE":
        node = patch.get("after")
        if not isinstance(node, dict) or not node.get("id"):
            raise PatchError("ADD_NODE after 必须是带 id 的完整节点")
        try:
            find_node(result, node["id"])
        except PatchError:
            pass
        else:
            raise PatchError(f"语义 ID 已存在: {node['id']}")

        requested_collection = patch.get("collection")
        try:
            inferred_collection = infer_collection_for_node(node)
        except ValueError as exc:
            raise PatchError(str(exc)) from exc
        collection = requested_collection or inferred_collection
        if collection not in CANONICAL_COLLECTIONS:
            raise PatchError(f"ADD_NODE collection 非法: {collection}")
        if collection != inferred_collection:
            raise PatchError(
                f"ADD_NODE 节点 kind={node.get('kind')} 应位于 {inferred_collection}，"
                f"不能写入 {collection}"
            )
        ensure_collection(root, collection).append(node)
        diff["changes"].append({"type": "node_added", "id": node["id"], "collection": collection})
        return result, diff

    if not target:
        raise PatchError(f"{operation} 需要 target_semantic_id")

    collection, node = find_node(result, target)
    ensure_before(node, patch)

    if operation == "REMOVE_NODE":
        root[collection] = [item for item in root.get(collection, []) if item.get("id") != target]
        diff["changes"].append({"type": "node_removed", "id": target, "collection": collection})

    elif operation == "UPDATE_FIELD":
        field_path = patch.get("field_path")
        if not field_path:
            raise PatchError("UPDATE_FIELD 缺少 field_path")
        parts = field_path.split(".")
        old_value = copy.deepcopy(get_by_path(node, parts))
        new_value = patch.get("after")
        set_by_path(node, parts, new_value)
        diff["changes"].append({
            "type": "field_updated",
            "id": target,
            "field": field_path,
            "before": old_value,
            "after": new_value,
        })

    elif operation in {"ADD_MEMBER", "REMOVE_MEMBER"}:
        field_path = patch.get("field_path") or "value"
        members = get_by_path(node, field_path.split("."))
        if not isinstance(members, list):
            raise PatchError(f"{operation} 的目标字段必须是列表: {field_path}")
        member = patch.get("value", patch.get("after"))
        before_members = copy.deepcopy(members)
        if operation == "ADD_MEMBER":
            if member not in members:
                members.append(member)
        else:
            if member not in members:
                raise PatchError(f"待移除成员不存在: {member!r}")
            members.remove(member)
        diff["changes"].append({
            "type": "members_updated",
            "id": target,
            "field": field_path,
            "before": before_members,
            "after": copy.deepcopy(members),
        })

    else:
        raise PatchError(f"第一版脚本暂不支持操作: {operation}")

    return result, diff


def main() -> int:
    parser = argparse.ArgumentParser(description="应用 Semantic Patch 到 CLM")
    parser.add_argument("clm", type=Path)
    parser.add_argument("patch", type=Path)
    parser.add_argument("-o", "--output", type=Path)
    parser.add_argument("--diff-output", type=Path)
    args = parser.parse_args()

    try:
        clm = load_json(args.clm)
        patch = load_json(args.patch)
        updated, diff = apply_patch(clm, patch)
    except (OSError, json.JSONDecodeError, PatchError) as exc:
        print(json.dumps({"ok": False, "error": str(exc)}, ensure_ascii=False, indent=2))
        return 1

    if args.output:
        save_json(args.output, updated)
    else:
        print(json.dumps(updated, ensure_ascii=False, indent=2))

    if args.diff_output:
        save_json(args.diff_output, diff)
    else:
        print(json.dumps({"semantic_diff": diff}, ensure_ascii=False, indent=2), file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
