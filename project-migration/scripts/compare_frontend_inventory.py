#!/usr/bin/env python3
"""Compare two JSON files produced by inventory_frontend.py."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Iterable


def _load_inventory(path: str | Path) -> dict[str, Any]:
    source = Path(path).expanduser()
    try:
        data = json.loads(source.read_text(encoding="utf-8"))
    except OSError as exc:
        raise ValueError(f"无法读取 {source}: {exc}") from exc
    except json.JSONDecodeError as exc:
        raise ValueError(f"{source} 不是有效 JSON: {exc}") from exc
    if not isinstance(data, dict):
        raise ValueError(f"{source} 顶层必须是 JSON object")
    if "schema_version" not in data:
        raise ValueError(f"{source} 缺少 schema_version，可能不是前端盘点文件")
    return data


def _set_diff(before: Iterable[str], after: Iterable[str]) -> dict[str, list[str]] | None:
    before_set = set(before)
    after_set = set(after)
    added = sorted(after_set - before_set)
    removed = sorted(before_set - after_set)
    if not added and not removed:
        return None
    return {"added": added, "removed": removed}


def _stack_names(inventory: dict[str, Any], category: str) -> list[str]:
    items = inventory.get("stack", {}).get(category, [])
    return sorted(
        str(item.get("name"))
        for item in items
        if isinstance(item, dict) and item.get("name")
    )


def _aggregate_packages(inventory: dict[str, Any]) -> dict[str, list[str]]:
    packages: dict[str, set[str]] = {}
    for manifest in inventory.get("manifests", []):
        if not isinstance(manifest, dict):
            continue
        for key in ("dependencies", "dev_dependencies", "peer_dependencies"):
            values = manifest.get(key, {})
            if not isinstance(values, dict):
                continue
            for name, version in values.items():
                packages.setdefault(str(name), set()).add(str(version))
    return {name: sorted(versions) for name, versions in sorted(packages.items())}


def _aggregate_scripts(inventory: dict[str, Any]) -> dict[str, list[str]]:
    scripts: dict[str, set[str]] = {}
    for manifest in inventory.get("manifests", []):
        if not isinstance(manifest, dict):
            continue
        values = manifest.get("scripts", {})
        if not isinstance(values, dict):
            continue
        for name, command in values.items():
            scripts.setdefault(str(name), set()).add(str(command))
    return {name: sorted(commands) for name, commands in sorted(scripts.items())}


def _mapping_diff(
    before: dict[str, list[str]], after: dict[str, list[str]]
) -> dict[str, Any] | None:
    added = sorted(set(after) - set(before))
    removed = sorted(set(before) - set(after))
    changed = {
        key: {"before": before[key], "after": after[key]}
        for key in sorted(set(before) & set(after))
        if before[key] != after[key]
    }
    if not added and not removed and not changed:
        return None
    return {"added": added, "removed": removed, "changed": changed}


def _route_keys(inventory: dict[str, Any]) -> list[str]:
    keys: set[str] = set()
    for item in inventory.get("route_candidates", []):
        if not isinstance(item, dict):
            continue
        kind = item.get("kind")
        value = item.get("value")
        if kind and value:
            keys.add(f"{kind}:{value}")
    return sorted(keys)


def compare_inventories(before: dict[str, Any], after: dict[str, Any]) -> dict[str, Any]:
    differences: dict[str, Any] = {}

    before_manager = before.get("package_manager", {}).get("primary")
    after_manager = after.get("package_manager", {}).get("primary")
    if before_manager != after_manager:
        differences["package_manager"] = {
            "before": before_manager,
            "after": after_manager,
        }

    stack_diff: dict[str, Any] = {}
    categories = sorted(
        set(before.get("stack", {})) | set(after.get("stack", {}))
    )
    for category in categories:
        diff = _set_diff(_stack_names(before, category), _stack_names(after, category))
        if diff:
            stack_diff[category] = diff
    if stack_diff:
        differences["stack"] = stack_diff

    package_diff = _mapping_diff(_aggregate_packages(before), _aggregate_packages(after))
    if package_diff:
        differences["packages"] = package_diff

    script_diff = _mapping_diff(_aggregate_scripts(before), _aggregate_scripts(after))
    if script_diff:
        differences["scripts"] = script_diff

    for key, label in (
        ("configs", "configs"),
        ("entry_candidates", "entry_candidates"),
    ):
        diff = _set_diff(before.get(key, []), after.get(key, []))
        if diff:
            differences[label] = diff

    route_diff = _set_diff(_route_keys(before), _route_keys(after))
    if route_diff:
        differences["route_candidates"] = route_diff

    before_counts = before.get("counts", {}).get("lifecycle_signals", {})
    after_counts = after.get("counts", {}).get("lifecycle_signals", {})
    signal_changes = {
        key: {"before": before_counts.get(key, 0), "after": after_counts.get(key, 0)}
        for key in sorted(set(before_counts) | set(after_counts))
        if before_counts.get(key, 0) != after_counts.get(key, 0)
    }
    if signal_changes:
        differences["lifecycle_signal_counts"] = signal_changes

    return {
        "schema_version": "1.0",
        "before_root": before.get("root"),
        "after_root": after.get("root"),
        "has_differences": bool(differences),
        "differences": differences,
    }


def comparison_to_markdown(comparison: dict[str, Any]) -> str:
    lines = [
        "# Frontend Inventory Comparison",
        "",
        f"- Before: `{comparison.get('before_root')}`",
        f"- After: `{comparison.get('after_root')}`",
        f"- Has differences: `{str(comparison['has_differences']).lower()}`",
    ]

    if not comparison["differences"]:
        lines.extend(["", "No inventory differences detected."])
        return "\n".join(lines) + "\n"

    for section, value in comparison["differences"].items():
        lines.extend(["", f"## {section}", "", "```json"])
        lines.append(json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True))
        lines.append("```")
    return "\n".join(lines) + "\n"


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="比较两份前端项目盘点 JSON。")
    parser.add_argument("before", help="迁移前 inventory JSON")
    parser.add_argument("after", help="迁移后 inventory JSON")
    parser.add_argument(
        "--format",
        choices=("markdown", "json"),
        default="markdown",
        help="输出格式（默认: markdown）",
    )
    parser.add_argument("-o", "--output", help="输出文件；省略时写到 stdout")
    parser.add_argument(
        "--fail-on-diff",
        action="store_true",
        help="检测到差异时返回 exit code 1",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)
    try:
        before = _load_inventory(args.before)
        after = _load_inventory(args.after)
    except ValueError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    comparison = compare_inventories(before, after)
    if args.format == "json":
        rendered = json.dumps(comparison, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    else:
        rendered = comparison_to_markdown(comparison)

    if args.output:
        output = Path(args.output).expanduser()
        try:
            output.parent.mkdir(parents=True, exist_ok=True)
            output.write_text(rendered, encoding="utf-8")
        except OSError as exc:
            print(f"error: 无法写入 {output}: {exc}", file=sys.stderr)
            return 2
    else:
        sys.stdout.write(rendered)

    if args.fail_on_diff and comparison["has_differences"]:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
