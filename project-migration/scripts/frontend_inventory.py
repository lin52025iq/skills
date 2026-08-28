#!/usr/bin/env python3
"""Read-only frontend repository inventory for migration planning.

It never executes project code and never reads values from .env files.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

IGNORED_DIRS = set(
    ".git .hg .svn node_modules dist build out .next .nuxt .svelte-kit .astro "
    ".vite .turbo .cache coverage playwright-report test-results storybook-static "
    "vendor tmp temp".split()
)
ALLOWED_HIDDEN_DIRS = {".storybook", ".github"}
TEXT_EXTENSIONS = set(
    ".js .jsx .mjs .cjs .ts .tsx .vue .svelte .astro .html .css .scss .sass "
    ".less .styl .json .jsonc .yaml .yml .md".split()
)
SOURCE_EXTENSIONS = TEXT_EXTENSIONS - {".md", ".json", ".jsonc", ".yaml", ".yml"}
ENV_FILE_RE = re.compile(r"^\.env(?:\..+)?$")

TECHNOLOGIES: dict[str, dict[str, str]] = {
    "frameworks": {
        "react": "React", "react-dom": "React DOM", "next": "Next.js",
        "vue": "Vue", "nuxt": "Nuxt", "@angular/core": "Angular",
        "svelte": "Svelte", "@sveltejs/kit": "SvelteKit", "solid-js": "Solid",
        "@builder.io/qwik": "Qwik", "astro": "Astro", "preact": "Preact",
    },
    "bundlers": {
        "vite": "Vite", "webpack": "Webpack", "rollup": "Rollup",
        "parcel": "Parcel", "@rspack/core": "Rspack", "esbuild": "esbuild",
        "react-scripts": "Create React App",
        "@angular-devkit/build-angular": "Angular CLI Build",
    },
    "routers": {
        "react-router": "React Router", "react-router-dom": "React Router DOM",
        "vue-router": "Vue Router", "@angular/router": "Angular Router",
        "@tanstack/react-router": "TanStack Router", "wouter": "Wouter",
    },
    "server_state": {
        "@tanstack/react-query": "TanStack Query", "react-query": "React Query",
        "swr": "SWR", "@apollo/client": "Apollo Client", "urql": "urql",
        "@ngrx/effects": "NgRx Effects",
    },
    "client_state": {
        "redux": "Redux", "@reduxjs/toolkit": "Redux Toolkit", "zustand": "Zustand",
        "pinia": "Pinia", "vuex": "Vuex", "mobx": "MobX", "xstate": "XState",
        "jotai": "Jotai", "recoil": "Recoil", "@ngrx/store": "NgRx Store",
    },
    "forms": {
        "react-hook-form": "React Hook Form", "formik": "Formik",
        "final-form": "Final Form", "vee-validate": "VeeValidate",
        "@angular/forms": "Angular Forms", "zod": "Zod", "yup": "Yup",
        "valibot": "Valibot",
    },
    "styling": {
        "tailwindcss": "Tailwind CSS", "sass": "Sass", "less": "Less",
        "styled-components": "styled-components", "@emotion/react": "Emotion",
        "@vanilla-extract/css": "vanilla-extract", "unocss": "UnoCSS",
        "postcss": "PostCSS",
    },
    "ui": {
        "antd": "Ant Design", "@mui/material": "MUI",
        "@chakra-ui/react": "Chakra UI", "element-plus": "Element Plus",
        "element-ui": "Element UI", "vuetify": "Vuetify", "naive-ui": "Naive UI",
        "primereact": "PrimeReact", "primevue": "PrimeVue",
        "@radix-ui/react-dialog": "Radix UI", "@headlessui/react": "Headless UI",
        "@headlessui/vue": "Headless UI Vue",
    },
    "testing": {
        "@playwright/test": "Playwright", "cypress": "Cypress", "vitest": "Vitest",
        "jest": "Jest", "@testing-library/react": "Testing Library React",
        "@testing-library/vue": "Testing Library Vue",
        "@testing-library/angular": "Testing Library Angular",
        "storybook": "Storybook", "@storybook/react": "Storybook React",
        "@storybook/vue3": "Storybook Vue", "axe-core": "axe-core",
        "@axe-core/playwright": "axe Playwright",
    },
    "i18n": {
        "i18next": "i18next", "react-i18next": "react-i18next",
        "vue-i18n": "Vue I18n", "next-intl": "next-intl",
        "@angular/localize": "Angular Localize",
    },
    "micro_frontend": {
        "single-spa": "single-spa", "@module-federation/enhanced": "Module Federation",
        "qiankun": "qiankun", "wujie": "Wujie",
    },
}

SIGNALS: dict[str, list[re.Pattern[str]]] = {
    "feature_flag": [
        re.compile(r"\bfeature[_-]?flags?\b", re.I), re.compile(r"\buseFeatureFlag\b"),
        re.compile(r"(?:process\.env|import\.meta\.env)\.[A-Z0-9_]*FEATURE[A-Z0-9_]*"),
    ],
    "deprecated_or_legacy": [
        re.compile(r"@deprecated\b|\bdeprecated\b|\blegacy\b", re.I),
        re.compile(r"TODO[^\n]{0,80}\bremove\b", re.I),
    ],
    "hidden_or_disabled": [
        re.compile(r"display\s*:\s*none|visibility\s*:\s*hidden", re.I),
        re.compile(r"\bif\s*\(\s*false\s*\)|v-if\s*=\s*[\"']false[\"']", re.I),
        re.compile(r"\bdisabled\s*=\s*[\"'{]?true\b", re.I),
    ],
    "skipped_tests": [
        re.compile(r"\b(?:describe|it|test)\.skip\s*\("),
        re.compile(r"\b(?:xdescribe|xit|xtest)\s*\("),
    ],
    "browser_only": [
        re.compile(r"\bwindow\.|\bdocument\.|\blocalStorage\b|\bsessionStorage\b")
    ],
}

CONFIG_NAMES = set(
    "package.json tsconfig.json jsconfig.json angular.json vue.config.js svelte.config.js "
    "astro.config.mjs tailwind.config.js tailwind.config.ts postcss.config.js".split()
)
CONFIG_PREFIXES = (
    "tsconfig.", "vite.config.", "webpack.config.", "next.config.", "nuxt.config.",
    "playwright.config.", "cypress.config.", "vitest.config.", "jest.config.",
    "eslint.config.",
)
INSTRUCTIONS = {"AGENTS.md", "CLAUDE.md", "CONTRIBUTING.md", "README.md",
                ".github/copilot-instructions.md"}
LOCKFILES = {
    "pnpm-lock.yaml": "pnpm", "yarn.lock": "yarn", "package-lock.json": "npm",
    "npm-shrinkwrap.json": "npm", "bun.lock": "bun", "bun.lockb": "bun",
}
WORKSPACE_FILES = {"pnpm-workspace.yaml", "lerna.json", "nx.json", "turbo.json", "rush.json"}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Read-only inventory of a frontend repository for migration planning."
    )
    parser.add_argument("root", nargs="?", default=".", help="Repository or package root.")
    parser.add_argument("--format", choices=("markdown", "json"), default="markdown")
    parser.add_argument("--output", help="Write report to a file instead of stdout.")
    parser.add_argument("--max-depth", type=int, default=8)
    parser.add_argument("--max-files", type=int, default=50000)
    parser.add_argument("--max-signal-samples", type=int, default=30)
    return parser.parse_args()


def rel(path: Path, root: Path) -> str:
    return path.relative_to(root).as_posix() or "."


def collect_files(root: Path, max_depth: int, max_files: int) -> tuple[list[Path], bool]:
    files: list[Path] = []
    for current, dirs, names in os.walk(root, followlinks=False):
        current_path = Path(current)
        depth = len(current_path.relative_to(root).parts)
        dirs[:] = [
            name for name in dirs
            if name not in IGNORED_DIRS
            and (not name.startswith(".") or name in ALLOWED_HIDDEN_DIRS)
            and depth < max_depth
        ]
        for name in names:
            path = current_path / name
            if not path.is_symlink():
                files.append(path)
                if len(files) >= max_files:
                    return files, True
    return files, False


def read_manifest(path: Path, root: Path, errors: list[str]) -> dict[str, Any] | None:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        errors.append(f"无法解析 {rel(path, root)}: {exc}")
        return None
    if not isinstance(data, dict):
        errors.append(f"{rel(path, root)} 顶层不是 JSON object")
        return None
    dependencies: dict[str, str] = {}
    for key in ("dependencies", "devDependencies", "peerDependencies", "optionalDependencies"):
        value = data.get(key)
        if isinstance(value, dict):
            dependencies.update({str(k): str(v) for k, v in value.items()})
    scripts = data.get("scripts") if isinstance(data.get("scripts"), dict) else {}
    return {
        "path": rel(path, root), "name": data.get("name"), "private": data.get("private"),
        "package_manager": data.get("packageManager"), "workspaces": data.get("workspaces"),
        "scripts": {str(k): str(v) for k, v in scripts.items()}, "dependencies": dependencies,
    }


def classify(dependencies: dict[str, str]) -> dict[str, list[dict[str, str]]]:
    result: dict[str, list[dict[str, str]]] = {}
    for category, packages in TECHNOLOGIES.items():
        matches = [
            {"package": package, "label": label, "version": dependencies[package]}
            for package, label in packages.items() if package in dependencies
        ]
        if matches:
            result[category] = sorted(matches, key=lambda item: item["package"])
    return result


def is_route(path: Path, root: Path) -> bool:
    location = f"/{rel(path, root).lower()}/"
    stem = path.stem.lower()
    return (
        stem in {"route", "routes", "router", "routing", "navigation", "menu", "page", "layout"}
        or any(f"/{part}/" in location for part in ("pages", "views", "routes", "app"))
    )


def is_entry(path: Path) -> bool:
    return path.suffix.lower() in SOURCE_EXTENSIONS and path.stem.lower() in {
        "main", "index", "app", "bootstrap", "entry-client", "entry-server", "client", "server"
    }


def is_test(path: Path) -> bool:
    location = f"/{path.as_posix().lower()}/"
    return (
        any(f"/{part}/" in location for part in ("test", "tests", "__tests__", "e2e", "cypress", "playwright", "stories"))
        or re.search(r"\.(?:test|spec|stories)\.[^.]+$", path.name.lower()) is not None
    )


def scan_signals(paths: Iterable[Path], root: Path, limit: int, errors: list[str]) -> dict[str, Any]:
    counts: Counter[str] = Counter()
    samples: dict[str, list[str]] = defaultdict(list)
    for path in paths:
        if path.suffix.lower() not in SOURCE_EXTENSIONS or ENV_FILE_RE.match(path.name):
            continue
        try:
            if path.stat().st_size > 2_000_000:
                continue
            lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
        except OSError as exc:
            errors.append(f"无法读取 {rel(path, root)}: {exc}")
            continue
        for line_number, line in enumerate(lines, 1):
            for name, patterns in SIGNALS.items():
                if any(pattern.search(line) for pattern in patterns):
                    counts[name] += 1
                    if len(samples[name]) < limit:
                        samples[name].append(f"{rel(path, root)}:{line_number}")
    return {name: {"count": counts[name], "samples": samples[name]} for name in SIGNALS}


def build_inventory(root: Path, args: argparse.Namespace) -> dict[str, Any]:
    errors: list[str] = []
    files, truncated = collect_files(root, args.max_depth, args.max_files)
    manifests = [
        value for value in (read_manifest(path, root, errors) for path in files if path.name == "package.json")
        if value is not None
    ]
    all_dependencies: dict[str, str] = {}
    for manifest in manifests:
        all_dependencies.update(manifest["dependencies"])
        manifest["technology"] = classify(manifest["dependencies"])

    lockfiles = [
        {"manager": manager, "source": name}
        for name, manager in LOCKFILES.items() if (root / name).exists()
    ]
    managers = sorted({item["manager"] for item in lockfiles})
    package_manager = {
        "primary": managers[0] if len(managers) == 1 else None,
        "lockfiles": lockfiles,
        "declared": [
            {"value": item["package_manager"], "source": item["path"]}
            for item in manifests if item["package_manager"]
        ],
        "conflict": len(managers) > 1,
    }

    paths = lambda predicate, cap: sorted(rel(path, root) for path in files if predicate(path))[:cap]
    instructions = paths(lambda p: rel(p, root) in INSTRUCTIONS or p.name in INSTRUCTIONS, 100)
    configs = paths(lambda p: p.name in CONFIG_NAMES or p.name.startswith(CONFIG_PREFIXES), 200)
    entries = paths(is_entry, 200)
    routes = paths(lambda p: p.suffix.lower() in SOURCE_EXTENSIONS and is_route(p, root), 300)
    tests = paths(is_test, 300)
    env_files = paths(lambda p: ENV_FILE_RE.match(p.name) is not None, 200)
    workspaces = paths(lambda p: p.name in WORKSPACE_FILES, 50)
    recommended = list(dict.fromkeys(instructions[:10] + configs[:20] + routes[:30] + entries[:15]))

    warnings: list[str] = []
    if not manifests:
        warnings.append("未发现 package.json；该目录可能不是前端根目录。")
    if package_manager["conflict"]:
        warnings.append("根目录存在多个 package manager 锁文件；实施前确认权威工具。")
    if truncated:
        warnings.append(f"达到 --max-files={args.max_files}，结果已截断。")
    if env_files:
        warnings.append("发现环境变量文件；只列路径，未读取内容。")

    return {
        "schema_version": 1,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "root": str(root),
        "scan": {
            "max_depth": args.max_depth, "max_files": args.max_files,
            "files_seen": len(files), "truncated": truncated,
            "ignored_directories": sorted(IGNORED_DIRS),
        },
        "package_manager": package_manager, "workspace_files": workspaces,
        "manifests": manifests, "technology_summary": classify(all_dependencies),
        "instruction_candidates": instructions, "config_candidates": configs,
        "entry_candidates": entries, "route_candidates": routes,
        "test_story_candidates": tests, "environment_file_paths": env_files,
        "extension_counts": dict(Counter(p.suffix.lower() or "[no-extension]" for p in files).most_common()),
        "lifecycle_risk_signals": scan_signals(files, root, args.max_signal_samples, errors),
        "recommended_next_reads": recommended, "warnings": warnings, "errors": errors,
        "limitations": [
            "静态盘点不能证明 Route、Flag、权限或功能当前可达。",
            "脚本不执行构建、测试或浏览器流程，也不判断视觉等价性。",
            "信号匹配可能误报，必须回到代码和运行证据确认。",
        ],
    }


def table(headers: list[str], rows: list[list[str]]) -> str:
    if not rows:
        return "_无_"
    output = ["| " + " | ".join(headers) + " |", "|" + "|".join("---" for _ in headers) + "|"]
    output += ["| " + " | ".join(cell.replace("|", "\\|") for cell in row) + " |" for row in rows]
    return "\n".join(output)


def markdown(data: dict[str, Any]) -> str:
    scan, pm = data["scan"], data["package_manager"]
    lines = [
        "# 前端静态盘点", "", f"- 根目录：`{data['root']}`",
        f"- 生成时间：`{data['generated_at']}`", f"- 扫描文件：{scan['files_seen']}",
        f"- 是否截断：{'是' if scan['truncated'] else '否'}", "",
        "## Package manager 与 workspace", "",
        f"- 推断主工具：`{pm['primary'] or '未唯一确认'}`",
    ]
    if pm["lockfiles"]:
        lines.append("- 锁文件：" + "、".join(f"`{x['source']}` → {x['manager']}" for x in pm["lockfiles"]))
    if pm["declared"]:
        lines.append("- packageManager：" + "、".join(f"`{x['value']}`（{x['source']}）" for x in pm["declared"]))
    if data["workspace_files"]:
        lines.append("- Workspace：" + "、".join(f"`{x}`" for x in data["workspace_files"]))

    tech_rows = [
        [category, "、".join(f"{x['label']} (`{x['package']}` {x['version']})" for x in items)]
        for category, items in data["technology_summary"].items()
    ]
    lines += ["", "## 技术摘要", "", table(["类别", "检测结果"], tech_rows)]
    script_rows = [
        [manifest["path"], name, f"`{command}`"]
        for manifest in data["manifests"] for name, command in sorted(manifest["scripts"].items())
    ]
    lines += ["", "## Package scripts", "", table(["Manifest", "Script", "Command"], script_rows[:150])]

    for title, key, cap in (
        ("仓库指令候选", "instruction_candidates", 50), ("配置候选", "config_candidates", 100),
        ("入口候选", "entry_candidates", 100), ("Route / 页面候选", "route_candidates", 150),
        ("测试 / Story 候选", "test_story_candidates", 150),
        ("建议优先阅读", "recommended_next_reads", 100),
    ):
        values = data[key]
        lines += ["", f"## {title}", ""] + ([f"- `{x}`" for x in values[:cap]] or ["_无_"])
        if len(values) > cap:
            lines.append(f"- …另有 {len(values) - cap} 项（JSON 输出中保留）")

    signal_rows = [
        [name, str(value["count"]), "、".join(f"`{x}`" for x in value["samples"][:10]) or "—"]
        for name, value in data["lifecycle_risk_signals"].items()
    ]
    lines += ["", "## 生命周期与迁移风险信号", "", table(["信号", "次数", "样例位置"], signal_rows)]
    if data["environment_file_paths"]:
        lines += ["", "## 环境变量文件路径", ""] + [f"- `{x}`（未读取内容）" for x in data["environment_file_paths"]]
    for title, key in (("警告", "warnings"), ("扫描错误", "errors"), ("限制", "limitations")):
        lines += ["", f"## {title}", ""] + ([f"- {x}" for x in data[key]] or ["_无_"])
    return "\n".join(lines).rstrip() + "\n"


def main() -> int:
    args = parse_args()
    root = Path(args.root).expanduser().resolve()
    if not root.is_dir():
        print(f"错误：目录不存在或不是目录：{root}", file=sys.stderr)
        return 2
    if args.max_depth < 0 or args.max_files < 1 or args.max_signal_samples < 0:
        print("错误：max-depth/max-signal-samples 必须 >= 0，max-files 必须 >= 1。", file=sys.stderr)
        return 2
    data = build_inventory(root, args)
    output = json.dumps(data, ensure_ascii=False, indent=2) + "\n" if args.format == "json" else markdown(data)
    if not args.output:
        sys.stdout.write(output)
        return 0
    path = Path(args.output).expanduser()
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(output, encoding="utf-8")
    except OSError as exc:
        print(f"错误：无法写入 {path}: {exc}", file=sys.stderr)
        return 2
    print(f"已写入：{path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
