#!/usr/bin/env python3
"""Initialize a .migration workspace from the skill's existing templates."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

SMALL_STEMS = [
    "迁移上下文",
    "当前状态",
    "功能文档",
    "前端视觉基线",
    "目标项目画像",
    "目标实现蓝图",
    "验证报告",
]
STANDARD_EXTRA_STEMS = [
    "可行性评估",
    "源系统理解",
    "功能生命周期清单",
    "迁移语义规格",
    "业务规则台账",
    "依赖与副作用",
    "能力迁移矩阵",
    "迁移边界",
    "目标架构映射",
    "技术栈迁移规则",
    "设计改进台账",
    "迁移计划",
    "差异与失败队列",
    "切换与回滚",
]
FULL_SUBDIRS = ["workstreams", "tests", "fixtures", "results", "scripts"]
PREFIX_RE = re.compile(r"^\d+-")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Create a non-destructive .migration evidence workspace from bundled templates."
    )
    parser.add_argument("root", help="Target frontend repository root.")
    parser.add_argument(
        "--profile",
        choices=("small", "standard", "full"),
        default="standard",
        help="Workspace intensity (default: standard).",
    )
    parser.add_argument(
        "--destination",
        help="Destination directory (default: <root>/.migration).",
    )
    parser.add_argument(
        "--templates-dir",
        help="Override bundled templates directory; useful for testing or custom forks.",
    )
    parser.add_argument("--dry-run", action="store_true", help="Print planned actions only.")
    parser.add_argument(
        "--force",
        action="store_true",
        help="Overwrite existing generated files. Default is non-destructive.",
    )
    parser.add_argument("--format", choices=("text", "json"), default="text")
    return parser.parse_args()


def normalized_name(path: Path) -> str:
    return PREFIX_RE.sub("", path.name)


def normalized_stem(path: Path) -> str:
    return Path(normalized_name(path)).stem


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(65536), b""):
            digest.update(chunk)
    return digest.hexdigest()


def discover_templates(templates_dir: Path) -> tuple[list[Path], dict[str, list[Path]]]:
    templates = sorted(path for path in templates_dir.glob("*.md") if path.is_file())
    by_stem: dict[str, list[Path]] = {}
    for path in templates:
        by_stem.setdefault(normalized_stem(path), []).append(path)
    return templates, by_stem


def select_templates(
    profile: str, templates: list[Path], by_stem: dict[str, list[Path]]
) -> tuple[list[Path], list[str]]:
    if profile == "full":
        return templates, []

    requested = SMALL_STEMS if profile == "small" else SMALL_STEMS + STANDARD_EXTRA_STEMS
    selected: list[Path] = []
    warnings: list[str] = []
    for stem in requested:
        matches = by_stem.get(stem, [])
        if not matches:
            warnings.append(f"未找到模板：{stem}.md")
            continue
        if len(matches) > 1:
            warnings.append(
                f"模板名归一化后重复：{stem}；将使用 {matches[0].name}，其余跳过。"
            )
        selected.append(matches[0])
    return selected, warnings


def emit(result: dict[str, Any], fmt: str) -> None:
    if fmt == "json":
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return
    print(f"Profile: {result['profile']}")
    print(f"Destination: {result['destination']}")
    prefix = "[dry-run] " if result["dry_run"] else ""
    for action in result["actions"]:
        print(f"{prefix}{action['status']}: {action['source']} -> {action['destination']}")
    for directory in result["directories"]:
        print(f"{prefix}directory: {directory}")
    for warning in result["warnings"]:
        print(f"warning: {warning}", file=sys.stderr)
    print(
        f"Summary: created={result['summary']['created']} overwritten={result['summary']['overwritten']} "
        f"skipped={result['summary']['skipped']} planned={result['summary']['planned']}"
    )


def main() -> int:
    args = parse_args()
    root = Path(args.root).expanduser().resolve()
    if not root.exists() or not root.is_dir():
        print(f"错误：目标根目录不存在或不是目录：{root}", file=sys.stderr)
        return 2

    skill_root = Path(__file__).resolve().parent.parent
    templates_dir = (
        Path(args.templates_dir).expanduser().resolve()
        if args.templates_dir
        else skill_root / "templates"
    )
    if not templates_dir.exists() or not templates_dir.is_dir():
        print(f"错误：模板目录不存在：{templates_dir}", file=sys.stderr)
        return 2

    destination = (
        Path(args.destination).expanduser().resolve()
        if args.destination
        else root / ".migration"
    )
    templates, by_stem = discover_templates(templates_dir)
    if not templates:
        print(f"错误：模板目录中没有 Markdown 文件：{templates_dir}", file=sys.stderr)
        return 2

    selected, warnings = select_templates(args.profile, templates, by_stem)
    actions: list[dict[str, str]] = []
    manifest_files: list[dict[str, str]] = []
    summary = {"created": 0, "overwritten": 0, "skipped": 0, "planned": 0}

    for source in selected:
        target = destination / normalized_name(source)
        status: str
        if target.exists() and not args.force:
            status = "skipped-existing"
            summary["skipped"] += 1
        elif target.exists() and args.force:
            status = "overwrite" if args.dry_run else "overwritten"
            summary["planned" if args.dry_run else "overwritten"] += 1
            if not args.dry_run:
                destination.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(source, target)
        else:
            status = "create" if args.dry_run else "created"
            summary["planned" if args.dry_run else "created"] += 1
            if not args.dry_run:
                destination.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(source, target)
        actions.append(
            {
                "source": str(source),
                "destination": str(target),
                "status": status,
            }
        )
        manifest_files.append(
            {
                "template": source.name,
                "destination": target.name,
                "sha256": sha256(source),
                "status": status,
            }
        )

    directories: list[str] = []
    if args.profile == "full":
        for name in FULL_SUBDIRS:
            path = destination / name
            directories.append(str(path))
            if not args.dry_run:
                path.mkdir(parents=True, exist_ok=True)

    manifest = {
        "schema_version": 1,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "profile": args.profile,
        "templates_dir": str(templates_dir),
        "destination": str(destination),
        "files": manifest_files,
        "directories": [Path(path).name for path in directories],
        "notes": [
            "模板编号已从目标文件名移除。",
            "默认不覆盖已有迁移文档；使用 --force 才会替换。",
            "模板是证据结构，不要求机械填满无关字段。",
        ],
    }
    manifest_path = destination / "workspace-manifest.json"
    if not args.dry_run:
        if manifest_path.exists() and not args.force:
            warnings.append("workspace-manifest.json 已存在，未覆盖。")
        else:
            destination.mkdir(parents=True, exist_ok=True)
            manifest_path.write_text(
                json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
            )

    result: dict[str, Any] = {
        "profile": args.profile,
        "root": str(root),
        "destination": str(destination),
        "templates_dir": str(templates_dir),
        "dry_run": args.dry_run,
        "force": args.force,
        "actions": actions,
        "directories": directories,
        "warnings": warnings,
        "summary": summary,
        "manifest": str(manifest_path),
    }
    emit(result, args.format)

    if not selected:
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
