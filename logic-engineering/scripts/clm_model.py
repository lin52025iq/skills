#!/usr/bin/env python3
"""CLM 公共模型工具。

这是所有脚本共享的唯一节点注册表和遍历入口。
禁止其他脚本自行维护 NODE_COLLECTIONS / COLLECTIONS 副本。
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Iterable, Iterator, Mapping, MutableMapping, Optional, Tuple


# kind -> canonical collection
NODE_KIND_TO_COLLECTION: Dict[str, str] = {
    # Domain
    "entity": "domain",
    "field": "domain",
    "value_type": "domain",
    "enum": "domain",
    "relationship": "domain",

    # Behavior
    "behavior": "behaviors",
    "rule": "rules",
    "decision": "decisions",
    "action": "actions",
    "foreach": "actions",

    # State
    "state_machine": "states",
    "transition": "states",

    # Effect / constraint / scenario / primitive
    "effect": "effects",
    "read": "effects",
    "write": "effects",
    "persist": "effects",
    "external_call": "effects",
    "emit": "effects",
    "schedule": "effects",
    "cache_read": "effects",
    "cache_write": "effects",

    "constraint": "constraints",
    "precondition": "constraints",
    "postcondition": "constraints",
    "invariant": "constraints",
    "uniqueness": "constraints",
    "cardinality": "constraints",
    "ordering": "constraints",
    "temporal": "constraints",
    "concurrency": "constraints",
    "atomicity": "constraints",
    "idempotency": "constraints",
    "forbidden_transition": "constraints",

    "scenario": "scenarios",
    "primitive": "primitives",
}

CANONICAL_COLLECTIONS: Tuple[str, ...] = (
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
)

# Top-level graph/support collections are not semantic node collections.
SUPPORT_COLLECTIONS: Tuple[str, ...] = (
    "relations",
    "evidence",
)


def root_of(clm: Dict[str, Any]) -> Dict[str, Any]:
    root = clm.get("clm")
    return root if isinstance(root, dict) else clm


def canonical_collection_for_kind(kind: str) -> Optional[str]:
    return NODE_KIND_TO_COLLECTION.get(kind)


def iter_nodes(clm: Dict[str, Any]) -> Iterator[Tuple[str, Dict[str, Any]]]:
    """按 canonical collection 遍历所有语义节点。"""
    root = root_of(clm)
    for collection in CANONICAL_COLLECTIONS:
        values = root.get(collection, []) or []
        if not isinstance(values, list):
            continue
        for node in values:
            if isinstance(node, dict):
                yield collection, node


def iter_node_values(clm: Dict[str, Any]) -> Iterator[Dict[str, Any]]:
    for _, node in iter_nodes(clm):
        yield node


def build_node_index(clm: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
    return {
        node["id"]: node
        for _, node in iter_nodes(clm)
        if isinstance(node.get("id"), str) and node["id"]
    }


def build_node_location_index(clm: Dict[str, Any]) -> Dict[str, Tuple[str, Dict[str, Any]]]:
    return {
        node["id"]: (collection, node)
        for collection, node in iter_nodes(clm)
        if isinstance(node.get("id"), str) and node["id"]
    }


def validate_node_collection(node: Mapping[str, Any], collection: str) -> Optional[str]:
    """返回 kind/collection 不一致错误；合法时返回 None。"""
    kind = node.get("kind")
    if not isinstance(kind, str) or not kind:
        return "节点缺少 kind"
    expected = canonical_collection_for_kind(kind)
    if expected is None:
        return f"未知节点 kind: {kind}"
    if expected != collection:
        return f"kind={kind} 应位于 {expected}，实际位于 {collection}"
    return None


def ensure_collection(root: MutableMapping[str, Any], collection: str) -> list:
    if collection not in CANONICAL_COLLECTIONS:
        raise ValueError(f"不是合法 CLM 节点集合: {collection}")
    value = root.setdefault(collection, [])
    if not isinstance(value, list):
        raise ValueError(f"CLM 集合 {collection} 必须是数组")
    return value


def infer_collection_for_node(node: Mapping[str, Any]) -> str:
    kind = node.get("kind")
    if not isinstance(kind, str) or not kind:
        raise ValueError("节点缺少 kind")
    collection = canonical_collection_for_kind(kind)
    if collection is None:
        raise ValueError(f"未知节点 kind: {kind}")
    return collection
