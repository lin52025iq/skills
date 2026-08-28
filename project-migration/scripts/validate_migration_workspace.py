#!/usr/bin/env python3
"""Validate a .migration workspace without executing project code."""

from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

SMALL_REQUIRED = [
    "迁移上下文",
    "当前状态",
    "功能文档",
    "前端视觉基线",
    "目标项目画像",
    "目标实现蓝图",
    "验证报告",
]
STANDARD_EXTRA = [
    "功能生命周期清单",
    "迁移语义规格",
    "能力迁移矩阵",
    "迁移边界",
    "技术栈迁移规则",
    "迁移计划",
    "差异与失败队列",
    "切换与回滚",
]
PLACEHOLDER_PATTERNS = {
    "TODO": re.compile(r"(?:<!--\s*TODO|\bTODO\s*:)", re.I),
    "TBD": re.compile(r"\bTBD\b", re.I),
    "FILL_ME": re.compile(r"(?:待填写|请填写|<填写|\[填写)", re.I),
}
SECRET_PATTERNS = {
    "private_key": re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----"),
    "aws_access_key": re.compile(r"\bAKIA[0-9A-Z]{16}\b"),
    "github_token": re.compile(r"\bgh[pousr]_[A-Za-z0-9_]{30,}\b"),
    "generic_secret_assignment": re.compile(
        r"(?i)\b(?:api[_-]?key|client[_-]?secret|access[_-]?token|password)\b\s*[:=]\s*[\"'][^\"']{12,}[\"']"
    ),
}
EXECUTABLE_SUFFIXES = {".py", ".sh", ".js", ".mjs", ".cjs", ".ts", ".tsx"}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Check required migration artifacts, placeholders, secrets, and workspace boundaries."
    )
    parser.add_argument("root", help="Frontend repository root.")
    parser.add_argument(
        "--profile", choices=("small", "standard", "full"), default="standard"
    )
    parser.add_argument(
        "--workspace",
        help="Workspace path (default: <root>/.migration).",
    )
    parser.add_argument("--format", choices=("text", "json"), default="text")
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Return non-zero when warnings exist, not only blockers.",
    )
    return parser.parse_args()


def add(
    findings: list[dict[str, str]], severity: str, code: str, message: str, path: str = ""
) -> None:
    findings.append({"severity": severity, "code": code, "message": message, "path": path})


def artifact_index(workspace: Path) -> dict[str, Path]:
    index: dict[str, Path] = {}
    for path in workspace.glob("*.md"):
        if path.is_file():
            index[path.stem] = path
    return index


def required_stems(profile: str, workspace: Path) -> list[str]:
    if profile == "small":
        return SMALL_REQUIRED
    if profile == "standard":
        return SMALL_REQUIRED + STANDARD_EXTRA
    manifest = workspace / "workspace-manifest.json"
    if manifest.exists():
        try:
            data = json.loads(manifest.read_text(encoding="utf-8"))
            names = [Path(item["destination"]).stem for item in data.get("files", [])]
            if names:
                return names
        except (OSError, UnicodeError, json.JSONDecodeError, KeyError, TypeError):
            pass
    return SMALL_REQUIRED + STANDARD_EXTRA


def inspect_markdown(path: Path, findings: list[dict[str, str]], workspace: Path) -> None:
    rel = path.relative_to(workspace).as_posix()
    try:
        text = path.read_text(encoding="utf-8")
    except (OSError, UnicodeError) as exc:
        add(findings, "blocker", "UNREADABLE", f"无法读取文档：{exc}", rel)
        return
    if len(text.strip()) < 20:
        add(findings, "blocker", "EMPTY", "文档为空或几乎为空。", rel)
        return
    for name, pattern in PLACEHOLDER_PATTERNS.items():
        matches = len(pattern.findall(text))
        if matches:
            add(findings, "warning", f"PLACEHOLDER_{name}", f"发现 {matches} 个未解决占位符。", rel)
    for name, pattern in SECRET_PATTERNS.items():
        if pattern.search(text):
            add(
                findings,
                "blocker",
                f"POSSIBLE_SECRET_{name.upper()}",
                "检测到疑似密钥或敏感值；迁移文档应只记录脱敏信息。",
                rel,
            )


def semantic_checks(index: dict[str, Path], findings: list[dict[str, str]], workspace: Path) -> None:
    checks = {
        "功能生命周期清单": ["Active", "Deprecated", "Unknown"],
        "前端视觉基线": ["viewport", "Loading", "响应"],
        "目标项目画像": ["Router", "测试", "样式"],
        "目标实现蓝图": ["目标项目范例", "验证", "Route"],
        "验证报告": ["总体结论", "视觉", "交互"],
        "切换与回滚": ["回滚", "切换"],
    }
    for stem, tokens in checks.items():
        path = index.get(stem)
        if not path:
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except OSError:
            continue
        missing = [token for token in tokens if token.lower() not in text.lower()]
        if missing:
            add(
                findings,
                "warning",
                "MISSING_EXPECTED_SECTION",
                "可能缺少关键主题：" + "、".join(missing),
                path.relative_to(workspace).as_posix(),
            )


def boundary_checks(workspace: Path, findings: list[dict[str, str]]) -> None:
    for path in workspace.iterdir():
        if path.is_file() and path.suffix.lower() in EXECUTABLE_SUFFIXES:
            add(
                findings,
                "blocker",
                "EXECUTABLE_AT_ROOT",
                "可执行迁移代码不应放在 .migration 根目录；移动到 .migration/scripts/。",
                path.name,
            )
        if path.is_symlink():
            add(findings, "warning", "SYMLINK", "工作区包含符号链接，请确认不会引用敏感或外部内容。", path.name)


def output_text(result: dict[str, Any]) -> None:
    print(f"Workspace: {result['workspace']}")
    print(f"Profile: {result['profile']}")
    print(
        f"Findings: blockers={result['summary']['blocker']} warnings={result['summary']['warning']} "
        f"info={result['summary']['info']}"
    )
    for finding in result["findings"]:
        location = f" ({finding['path']})" if finding["path"] else ""
        print(
            f"[{finding['severity'].upper()}] {finding['code']}{location}: {finding['message']}"
        )


def main() -> int:
    args = parse_args()
    root = Path(args.root).expanduser().resolve()
    workspace = (
        Path(args.workspace).expanduser().resolve()
        if args.workspace
        else root / ".migration"
    )
    findings: list[dict[str, str]] = []

    if not root.exists() or not root.is_dir():
        add(findings, "blocker", "ROOT_MISSING", "仓库根目录不存在或不是目录。", str(root))
    if not workspace.exists() or not workspace.is_dir():
        add(findings, "blocker", "WORKSPACE_MISSING", ".migration 工作区不存在。", str(workspace))
    else:
        index = artifact_index(workspace)
        for stem in required_stems(args.profile, workspace):
            if stem not in index:
                add(
                    findings,
                    "blocker",
                    "REQUIRED_ARTIFACT_MISSING",
                    f"缺少 profile={args.profile} 的必要文档：{stem}.md",
                    stem + ".md",
                )
        for path in sorted(workspace.glob("*.md")):
            inspect_markdown(path, findings, workspace)
        semantic_checks(index, findings, workspace)
        boundary_checks(workspace, findings)
        manifest = workspace / "workspace-manifest.json"
        if not manifest.exists():
            add(findings, "info", "MANIFEST_MISSING", "未找到 workspace-manifest.json；手工工作区可忽略。")

    summary = {severity: 0 for severity in ("blocker", "warning", "info")}
    for finding in findings:
        summary[finding["severity"]] += 1
    result: dict[str, Any] = {
        "schema_version": 1,
        "checked_at": datetime.now(timezone.utc).isoformat(),
        "root": str(root),
        "workspace": str(workspace),
        "profile": args.profile,
        "strict": args.strict,
        "summary": summary,
        "findings": findings,
        "valid": summary["blocker"] == 0 and (not args.strict or summary["warning"] == 0),
    }

    if args.format == "json":
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        output_text(result)

    if summary["blocker"]:
        return 2
    if args.strict and summary["warning"]:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
