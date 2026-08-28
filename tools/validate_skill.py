#!/usr/bin/env python3
"""Repository-local validation for an Agent Skill.

The validator intentionally uses only the Python standard library so it can run
in CI without installing dependencies.
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any

NAME_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
MARKDOWN_LINK_RE = re.compile(r"\[[^\]]*\]\(([^)]+)\)")
BACKTICK_RESOURCE_RE = re.compile(r"`((?:references|scripts|templates|agents)/[^`]+)`")
QUOTED_YAML_VALUE_RE = re.compile(r'^\s+[a-zA-Z0-9_-]+:\s+(["\']).*\1\s*$')


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Validate a skill directory and bundled resources.")
    parser.add_argument("skill_dir", nargs="?", default="project-migration")
    parser.add_argument(
        "--strict", action="store_true", help="Treat warnings as validation failures."
    )
    return parser.parse_args()


def parse_frontmatter(text: str) -> tuple[dict[str, str], str]:
    if not text.startswith("---\n"):
        raise ValueError("SKILL.md must start with YAML frontmatter")
    end = text.find("\n---\n", 4)
    if end < 0:
        raise ValueError("SKILL.md frontmatter is not terminated by ---")
    block = text[4:end]
    body = text[end + 5 :]
    values: dict[str, str] = {}
    current_key: str | None = None
    for raw in block.splitlines():
        if not raw.strip() or raw.lstrip().startswith("#"):
            continue
        if raw.startswith((" ", "\t")) and current_key:
            values[current_key] += " " + raw.strip()
            continue
        match = re.match(r"^([A-Za-z0-9_-]+):\s*(.*)$", raw)
        if not match:
            raise ValueError(f"unsupported frontmatter line: {raw}")
        current_key = match.group(1)
        value = match.group(2).strip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in {'"', "'"}:
            value = value[1:-1]
        values[current_key] = value
    return values, body


def add(findings: list[dict[str, str]], severity: str, code: str, message: str) -> None:
    findings.append({"severity": severity, "code": code, "message": message})


def validate_frontmatter(skill_dir: Path, findings: list[dict[str, str]]) -> tuple[str, str]:
    skill_md = skill_dir / "SKILL.md"
    if not skill_md.exists():
        add(findings, "error", "SKILL_MISSING", f"Missing {skill_md}")
        return "", ""
    try:
        text = skill_md.read_text(encoding="utf-8")
        frontmatter, body = parse_frontmatter(text)
    except (OSError, UnicodeError, ValueError) as exc:
        add(findings, "error", "FRONTMATTER_INVALID", str(exc))
        return "", ""

    allowed = {"name", "description", "license", "allowed-tools", "metadata"}
    unexpected = sorted(set(frontmatter) - allowed)
    if unexpected:
        add(findings, "error", "FRONTMATTER_KEYS", f"Unexpected keys: {', '.join(unexpected)}")

    name = frontmatter.get("name", "").strip()
    description = frontmatter.get("description", "").strip()
    if not name:
        add(findings, "error", "NAME_MISSING", "Frontmatter name is required")
    elif not NAME_RE.fullmatch(name):
        add(findings, "error", "NAME_FORMAT", "Name must use lowercase hyphen-case")
    elif len(name) > 64:
        add(findings, "error", "NAME_LENGTH", "Name must be <= 64 characters")
    if name and name != skill_dir.name:
        add(findings, "error", "NAME_FOLDER_MISMATCH", f"name={name} but folder={skill_dir.name}")

    if not description:
        add(findings, "error", "DESCRIPTION_MISSING", "Frontmatter description is required")
    elif len(description) > 1024:
        add(
            findings,
            "error",
            "DESCRIPTION_LENGTH",
            f"Description is {len(description)} characters; maximum is 1024",
        )
    if "<" in description or ">" in description:
        add(findings, "error", "DESCRIPTION_ANGLE_BRACKET", "Description cannot contain < or >")

    line_count = len(text.splitlines())
    if line_count > 500:
        add(findings, "error", "SKILL_TOO_LONG", f"SKILL.md has {line_count} lines; maximum is 500")
    elif line_count > 450:
        add(findings, "warning", "SKILL_NEAR_LIMIT", f"SKILL.md has {line_count} lines")
    if len(body.strip()) < 200:
        add(findings, "error", "BODY_TOO_SMALL", "SKILL.md body appears incomplete")
    return name, text


def resolve_link(base: Path, target: str) -> Path | None:
    target = target.split("#", 1)[0].strip()
    if not target or target.startswith(("http://", "https://", "mailto:", "#")):
        return None
    if target.startswith("/"):
        return None
    return (base / target).resolve()


def validate_links(skill_dir: Path, skill_text: str, findings: list[dict[str, str]]) -> None:
    targets = set(BACKTICK_RESOURCE_RE.findall(skill_text))
    targets.update(MARKDOWN_LINK_RE.findall(skill_text))
    for target in sorted(targets):
        resolved = resolve_link(skill_dir, target)
        if resolved is not None and not resolved.exists():
            add(findings, "error", "BROKEN_RESOURCE", f"Referenced resource does not exist: {target}")

    repo_readme = skill_dir.parent / "README.md"
    if repo_readme.exists():
        try:
            text = repo_readme.read_text(encoding="utf-8")
        except (OSError, UnicodeError) as exc:
            add(findings, "warning", "README_UNREADABLE", str(exc))
            return
        for target in MARKDOWN_LINK_RE.findall(text):
            resolved = resolve_link(repo_readme.parent, target)
            if resolved is not None and not resolved.exists():
                add(findings, "error", "README_BROKEN_LINK", f"README link does not exist: {target}")


def yaml_scalar(text: str, key: str) -> str | None:
    match = re.search(rf"^\s*{re.escape(key)}:\s*([\"'])(.*?)\1\s*$", text, re.M)
    return match.group(2) if match else None


def validate_openai_yaml(skill_dir: Path, skill_name: str, findings: list[dict[str, str]]) -> None:
    path = skill_dir / "agents" / "openai.yaml"
    if not path.exists():
        add(findings, "error", "OPENAI_YAML_MISSING", "agents/openai.yaml is missing")
        return
    try:
        text = path.read_text(encoding="utf-8")
    except (OSError, UnicodeError) as exc:
        add(findings, "error", "OPENAI_YAML_UNREADABLE", str(exc))
        return
    for key in ("display_name", "short_description", "default_prompt"):
        value = yaml_scalar(text, key)
        if value is None:
            add(findings, "error", "OPENAI_YAML_FIELD", f"{key} must exist and be quoted")
    short = yaml_scalar(text, "short_description") or ""
    if short and not 25 <= len(short) <= 64:
        add(
            findings,
            "error",
            "SHORT_DESCRIPTION_LENGTH",
            f"short_description has {len(short)} characters; expected 25-64",
        )
    prompt = yaml_scalar(text, "default_prompt") or ""
    if skill_name and f"${skill_name}" not in prompt:
        add(findings, "error", "DEFAULT_PROMPT_TRIGGER", f"default_prompt must mention ${skill_name}")
    if prompt.count("。") + prompt.count(".") > 2:
        add(findings, "warning", "DEFAULT_PROMPT_LONG", "default_prompt should normally be one concise sentence")


def validate_scripts(skill_dir: Path, findings: list[dict[str, str]]) -> None:
    scripts_dir = skill_dir / "scripts"
    if not scripts_dir.exists():
        add(findings, "warning", "SCRIPTS_MISSING", "No scripts directory")
        return
    scripts = sorted(scripts_dir.glob("*.py"))
    for script in scripts:
        try:
            source = script.read_text(encoding="utf-8")
            compile(source, str(script), "exec")
        except (OSError, UnicodeError, SyntaxError) as exc:
            add(findings, "error", "SCRIPT_COMPILE", f"{script.name}: {exc}")
            continue
        try:
            result = subprocess.run(
                [sys.executable, str(script), "--help"],
                capture_output=True,
                text=True,
                timeout=15,
                check=False,
            )
        except (OSError, subprocess.TimeoutExpired) as exc:
            add(findings, "error", "SCRIPT_HELP", f"{script.name} --help failed: {exc}")
            continue
        if result.returncode != 0:
            add(
                findings,
                "error",
                "SCRIPT_HELP",
                f"{script.name} --help exited {result.returncode}: {result.stderr.strip()}",
            )


def validate_references(skill_dir: Path, findings: list[dict[str, str]]) -> None:
    references = skill_dir / "references"
    if not references.exists():
        add(findings, "error", "REFERENCES_MISSING", "references directory is missing")
        return
    for path in sorted(references.glob("*.md")):
        try:
            text = path.read_text(encoding="utf-8")
        except (OSError, UnicodeError) as exc:
            add(findings, "error", "REFERENCE_UNREADABLE", f"{path.name}: {exc}")
            continue
        lines = text.splitlines()
        if len(lines) > 100 and "## 目录" not in text[:1500]:
            add(
                findings,
                "warning",
                "REFERENCE_TOC",
                f"{path.name} has {len(lines)} lines but no early '## 目录' section",
            )


def validate_evals(skill_dir: Path, findings: list[dict[str, str]]) -> None:
    path = skill_dir / "evals" / "evals.json"
    if not path.exists():
        add(findings, "error", "EVALS_MISSING", "evals/evals.json is missing")
        return
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        add(findings, "error", "EVALS_INVALID_JSON", str(exc))
        return
    if data.get("skill_name") != skill_dir.name:
        add(findings, "error", "EVAL_SKILL_NAME", "evals skill_name must match folder")
    evals = data.get("evals")
    if not isinstance(evals, list) or len(evals) < 3:
        add(findings, "error", "EVAL_COUNT", "evals must contain at least three realistic cases")
        return
    ids: set[Any] = set()
    names: set[str] = set()
    for index, item in enumerate(evals):
        if not isinstance(item, dict):
            add(findings, "error", "EVAL_ITEM", f"eval[{index}] must be an object")
            continue
        eval_id = item.get("id")
        name = item.get("name")
        if eval_id in ids:
            add(findings, "error", "EVAL_ID_DUPLICATE", f"duplicate eval id: {eval_id}")
        ids.add(eval_id)
        if not isinstance(name, str) or not name:
            add(findings, "error", "EVAL_NAME", f"eval[{index}] missing name")
        elif name in names:
            add(findings, "error", "EVAL_NAME_DUPLICATE", f"duplicate eval name: {name}")
        names.add(name or "")
        for field in ("prompt", "expected_output"):
            if not isinstance(item.get(field), str) or len(item[field].strip()) < 20:
                add(findings, "error", "EVAL_FIELD", f"eval[{index}] {field} is missing or too short")
        assertions = item.get("assertions")
        if not isinstance(assertions, list) or len(assertions) < 2 or not all(
            isinstance(value, str) and value.strip() for value in assertions
        ):
            add(findings, "error", "EVAL_ASSERTIONS", f"eval[{index}] needs at least two string assertions")
        files = item.get("files")
        if not isinstance(files, list):
            add(findings, "error", "EVAL_FILES", f"eval[{index}] files must be an array")


def smoke_test_inventory(skill_dir: Path, findings: list[dict[str, str]]) -> None:
    script = skill_dir / "scripts" / "frontend_inventory.py"
    if not script.exists():
        return
    with tempfile.TemporaryDirectory() as temp_dir:
        output = Path(temp_dir) / "inventory.json"
        result = subprocess.run(
            [sys.executable, str(script), str(skill_dir), "--format", "json", "--output", str(output)],
            capture_output=True,
            text=True,
            timeout=30,
            check=False,
        )
        if result.returncode != 0 or not output.exists():
            add(
                findings,
                "error",
                "INVENTORY_SMOKE",
                f"frontend_inventory smoke test failed: {result.stderr.strip()}",
            )
            return
        try:
            data = json.loads(output.read_text(encoding="utf-8"))
        except (OSError, UnicodeError, json.JSONDecodeError) as exc:
            add(findings, "error", "INVENTORY_OUTPUT", f"Invalid inventory JSON: {exc}")
            return
        if data.get("schema_version") != 1:
            add(findings, "error", "INVENTORY_SCHEMA", "Unexpected inventory schema_version")


def main() -> int:
    args = parse_args()
    skill_dir = Path(args.skill_dir).expanduser().resolve()
    findings: list[dict[str, str]] = []
    if not skill_dir.exists() or not skill_dir.is_dir():
        add(findings, "error", "SKILL_DIR", f"Skill directory does not exist: {skill_dir}")
    else:
        skill_name, skill_text = validate_frontmatter(skill_dir, findings)
        if skill_text:
            validate_links(skill_dir, skill_text, findings)
        validate_openai_yaml(skill_dir, skill_name, findings)
        validate_scripts(skill_dir, findings)
        validate_references(skill_dir, findings)
        validate_evals(skill_dir, findings)
        smoke_test_inventory(skill_dir, findings)

    errors = sum(item["severity"] == "error" for item in findings)
    warnings = sum(item["severity"] == "warning" for item in findings)
    for item in findings:
        print(f"[{item['severity'].upper()}] {item['code']}: {item['message']}")
    print(f"Validation summary: errors={errors}, warnings={warnings}")
    if errors:
        return 2
    if args.strict and warnings:
        return 1
    print("Skill validation passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
