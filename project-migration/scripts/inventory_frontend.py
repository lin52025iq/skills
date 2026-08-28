#!/usr/bin/env python3
"""Generate a deterministic inventory of a frontend repository.

The output contains evidence and candidates, not product or lifecycle decisions.
Only the Python standard library is required.
"""

from __future__ import annotations

import argparse
import fnmatch
import json
import os
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Iterable

SCHEMA_VERSION = "1.0"
IGNORED_DIRS = {
    ".git", ".hg", ".svn", ".idea", ".vscode", "node_modules", "vendor",
    "dist", "build", "out", "coverage", ".next", ".nuxt", ".svelte-kit",
    ".astro", ".angular", ".cache", ".parcel-cache", ".turbo", ".vercel",
    "storybook-static",
}
CODE_EXTENSIONS = {
    ".js", ".jsx", ".mjs", ".cjs", ".ts", ".tsx", ".mts", ".cts",
    ".vue", ".svelte", ".astro", ".html", ".htm",
}
SOURCE_EXTENSIONS = CODE_EXTENSIONS | {".css", ".scss", ".sass", ".less", ".styl"}
TEXT_EXTENSIONS = SOURCE_EXTENSIONS | {".json", ".jsonc", ".yaml", ".yml", ".toml"}
LOCKFILES = {
    "pnpm-lock.yaml": "pnpm", "yarn.lock": "yarn", "package-lock.json": "npm",
    "npm-shrinkwrap.json": "npm", "bun.lock": "bun", "bun.lockb": "bun",
}

# A matcher ending in '/' matches a package prefix.
STACK_RULES: dict[str, tuple[tuple[str, tuple[str, ...]], ...]] = {
    "frameworks": (
        ("React", ("react",)), ("Vue", ("vue",)), ("Angular", ("@angular/core",)),
        ("Svelte", ("svelte",)), ("Next.js", ("next",)), ("Nuxt", ("nuxt",)),
        ("Astro", ("astro",)), ("SolidJS", ("solid-js",)),
        ("Qwik", ("@builder.io/qwik",)), ("Remix", ("@remix-run/react",)),
    ),
    "build_tools": (
        ("Vite", ("vite",)), ("Webpack", ("webpack",)),
        ("Rspack", ("@rspack/core",)), ("Rollup", ("rollup",)),
        ("Parcel", ("parcel",)), ("esbuild", ("esbuild",)),
        ("SWC", ("@swc/core",)), ("Babel", ("@babel/core", "babel")),
    ),
    "language_tooling": (("TypeScript", ("typescript",)), ("Flow", ("flow-bin",))),
    "routers": (
        ("React Router", ("react-router", "react-router-dom")),
        ("Vue Router", ("vue-router",)), ("Angular Router", ("@angular/router",)),
        ("TanStack Router", ("@tanstack/react-router",)),
        ("svelte-routing", ("svelte-routing",)),
    ),
    "state": (
        ("Redux", ("redux", "@reduxjs/toolkit")), ("Zustand", ("zustand",)),
        ("MobX", ("mobx", "mobx-react-lite")), ("Pinia", ("pinia",)),
        ("Vuex", ("vuex",)), ("NgRx", ("@ngrx/store",)),
        ("Jotai", ("jotai",)), ("XState", ("xstate",)),
    ),
    "data": (
        ("TanStack Query", ("@tanstack/react-query", "@tanstack/vue-query")),
        ("SWR", ("swr",)), ("Apollo Client", ("@apollo/client", "apollo-client")),
        ("urql", ("urql",)), ("Axios", ("axios",)), ("Ky", ("ky",)),
        ("RxJS", ("rxjs",)),
    ),
    "forms_validation": (
        ("React Hook Form", ("react-hook-form",)), ("Formik", ("formik",)),
        ("VeeValidate", ("vee-validate",)), ("Angular Forms", ("@angular/forms",)),
        ("Zod", ("zod",)), ("Yup", ("yup",)), ("Valibot", ("valibot",)),
    ),
    "ui": (
        ("Ant Design", ("antd", "@ant-design/")), ("Material UI", ("@mui/material",)),
        ("Chakra UI", ("@chakra-ui/react",)), ("Radix UI", ("@radix-ui/",)),
        ("Element UI", ("element-ui",)), ("Element Plus", ("element-plus",)),
        ("Vuetify", ("vuetify",)), ("Headless UI", ("@headlessui/",)),
        ("Fluent UI", ("@fluentui/",)), ("Mantine", ("@mantine/",)),
    ),
    "styling": (
        ("Tailwind CSS", ("tailwindcss",)), ("Sass", ("sass",)),
        ("Less", ("less",)), ("styled-components", ("styled-components",)),
        ("Emotion", ("@emotion/react",)), ("vanilla-extract", ("@vanilla-extract/",)),
        ("UnoCSS", ("unocss",)), ("PostCSS", ("postcss",)),
    ),
    "testing": (
        ("Playwright", ("@playwright/test", "playwright")), ("Cypress", ("cypress",)),
        ("Vitest", ("vitest",)), ("Jest", ("jest",)),
        ("Storybook", ("storybook", "@storybook/")),
        ("Testing Library", ("@testing-library/",)), ("Karma", ("karma",)),
    ),
    "i18n": (
        ("i18next", ("i18next", "react-i18next")), ("Vue I18n", ("vue-i18n",)),
        ("Angular Localize", ("@angular/localize",)), ("next-intl", ("next-intl",)),
        ("FormatJS", ("react-intl", "@formatjs/")),
    ),
    "observability_analytics": (
        ("Sentry", ("@sentry/",)), ("Datadog", ("@datadog/",)),
        ("OpenTelemetry", ("@opentelemetry/",)), ("PostHog", ("posthog-js",)),
        ("Segment", ("@segment/analytics-next",)), ("Web Vitals", ("web-vitals",)),
    ),
}

CONFIG_PATTERNS = (
    "angular.json", "workspace.json", "project.json", "vite.config.*",
    "webpack.config.*", "rspack.config.*", "rollup.config.*", "next.config.*",
    "nuxt.config.*", "svelte.config.*", "astro.config.*", "remix.config.*",
    "tsconfig*.json", "jsconfig*.json", "babel.config.*", ".babelrc*",
    "postcss.config.*", "tailwind.config.*", "uno.config.*", "eslint.config.*",
    ".eslintrc*", "prettier.config.*", ".prettierrc*", "playwright.config.*",
    "cypress.config.*", "vitest.config.*", "jest.config.*", ".storybook/main.*",
    "vercel.json", "netlify.toml",
)
ENTRY_PATTERNS = (
    "src/main.*", "src/index.*", "src/app.*", "src/bootstrap.*", "src/client.*",
    "src/entry-client.*", "src/entry-server.*", "app/layout.*", "app/page.*",
    "pages/_app.*", "pages/index.*", "src/routes/+layout.*", "src/routes/+page.*",
    "public/index.html", "index.html",
)
ROUTE_PATTERNS = (
    ("route-object", re.compile(r"\bpath\s*:\s*[\"']([^\"']+)[\"']")),
    ("jsx-route", re.compile(r"<Route\b[^>]*\bpath\s*=\s*[\"']([^\"']+)[\"']", re.I)),
    ("router-call", re.compile(r"\b(?:route|addRoute|defineRoute)\s*\(\s*[\"']([^\"']+)[\"']")),
)
SIGNAL_PATTERNS = {
    "feature_flags": re.compile(
        r"\b(?:feature[_-]?flags?|isFeatureEnabled|flagEnabled|launchDarkly|unleash)\b", re.I
    ),
    "permissions": re.compile(
        r"\b(?:permissions?|hasPermission|authorize|authorization|roles?|can[A-Z][A-Za-z0-9_]*)\b"
    ),
    "hidden_disabled": re.compile(
        r"(?:display\s*:\s*none|visibility\s*:\s*hidden|\bhidden\s*=|\bv-if\s*=|\bngIf\b|\bdisabled\s*=)", re.I
    ),
    "deprecated_legacy": re.compile(
        r"(?:@deprecated|\bdeprecated\b|\blegacy\b|(?:TODO|FIXME).{0,60}\b(?:remove|delete|migrate|replace)\b)", re.I
    ),
}
MAX_MANIFESTS = 200
MAX_ROUTES = 1000
MAX_SIGNALS = 250


def _relative(path: Path, root: Path) -> str:
    return path.relative_to(root).as_posix()


def _iter_files(root: Path, max_files: int) -> tuple[list[Path], bool]:
    result: list[Path] = []
    truncated = False
    for current, dirs, names in os.walk(root, followlinks=False):
        dirs[:] = sorted(name for name in dirs if name not in IGNORED_DIRS)
        for name in sorted(names):
            result.append(Path(current) / name)
            if len(result) >= max_files:
                truncated = True
                break
        if truncated:
            break
    result.sort(key=lambda path: _relative(path, root))
    return result, truncated


def _load_manifests(root: Path, files: Iterable[Path]) -> tuple[list[dict[str, Any]], list[str]]:
    manifests: list[dict[str, Any]] = []
    warnings: list[str] = []
    candidates = [path for path in files if path.name == "package.json"]
    for path in candidates[:MAX_MANIFESTS]:
        rel = _relative(path, root)
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
            warnings.append(f"无法解析 {rel}: {exc}")
            continue
        if not isinstance(data, dict):
            warnings.append(f"无法解析 {rel}: 顶层不是 object")
            continue

        def mapping(key: str) -> dict[str, str]:
            value = data.get(key)
            return {str(k): str(v) for k, v in sorted(value.items())} if isinstance(value, dict) else {}

        manifests.append({
            "path": rel,
            "name": data.get("name") if isinstance(data.get("name"), str) else None,
            "private": data.get("private") if isinstance(data.get("private"), bool) else None,
            "package_manager": data.get("packageManager") if isinstance(data.get("packageManager"), str) else None,
            "scripts": mapping("scripts"),
            "dependencies": mapping("dependencies"),
            "dev_dependencies": mapping("devDependencies"),
            "peer_dependencies": mapping("peerDependencies"),
        })
    if len(candidates) > MAX_MANIFESTS:
        warnings.append(f"package.json 数量超过上限 {MAX_MANIFESTS}，结果已截断")
    return manifests, warnings


def _package_manager(root: Path, files: Iterable[Path], manifests: list[dict[str, Any]]) -> dict[str, Any]:
    evidence: dict[str, set[str]] = defaultdict(set)
    declarations: list[tuple[str, str]] = []
    for path in files:
        manager = LOCKFILES.get(path.name)
        if manager:
            evidence[manager].add(_relative(path, root))
    for manifest in manifests:
        value = manifest.get("package_manager")
        if value:
            manager = str(value).split("@", 1)[0]
            marker = f"{manifest['path']}#packageManager"
            evidence[manager].add(marker)
            declarations.append((manager, marker))
    if declarations:
        root_value = next((item for item in declarations if item[1] == "package.json#packageManager"), None)
        primary = (root_value or declarations[0])[0]
    else:
        primary = next((name for name in ("pnpm", "yarn", "npm", "bun") if name in evidence), None)
    return {
        "primary": primary,
        "detected": sorted(evidence),
        "evidence": {name: sorted(items) for name, items in sorted(evidence.items())},
    }


def _package_matches(package: str, matcher: str) -> bool:
    return package.startswith(matcher) if matcher.endswith("/") else package == matcher


def _collect_stack(manifests: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    packages: list[tuple[str, str]] = []
    for manifest in manifests:
        names: set[str] = set()
        for key in ("dependencies", "dev_dependencies", "peer_dependencies"):
            names.update(manifest.get(key, {}))
        packages.extend((name, manifest["path"]) for name in names)

    result: dict[str, list[dict[str, Any]]] = {}
    for category, rules in STACK_RULES.items():
        found: dict[str, set[str]] = defaultdict(set)
        for display, matchers in rules:
            for package, manifest_path in packages:
                if any(_package_matches(package, matcher) for matcher in matchers):
                    found[display].add(f"{manifest_path}:{package}")
        result[category] = [
            {"name": name, "evidence": sorted(items)} for name, items in sorted(found.items())
        ]
    return result


def _matches_any(relative: str, patterns: Iterable[str]) -> bool:
    basename = Path(relative).name
    return any(fnmatch.fnmatch(relative, pattern) or fnmatch.fnmatch(basename, pattern) for pattern in patterns)


def _route_segment(segment: str) -> str | None:
    if not segment or segment.startswith("(") or segment.startswith("@"):
        return None
    if segment.startswith("[[...") and segment.endswith("]]" ):
        return f"*{segment[5:-2]}?"
    if segment.startswith("[...") and segment.endswith("]"):
        return f"*{segment[4:-1]}"
    if segment.startswith("[[") and segment.endswith("]]" ):
        return f":{segment[2:-2]}?"
    if segment.startswith("[") and segment.endswith("]"):
        return f":{segment[1:-1]}"
    return segment


def _route_value(segments: Iterable[str]) -> str:
    converted = [value for segment in segments if (value := _route_segment(segment))]
    return "/" + "/".join(converted) if converted else "/"


def _file_route(path: Path, root: Path) -> dict[str, Any] | None:
    relative = path.relative_to(root)
    parts = list(relative.parts)
    name = path.name
    app_indexes = [i for i, part in enumerate(parts[:-1]) if part == "app"]
    if app_indexes and re.match(r"^page\.(?:[cm]?[jt]sx?|vue|svelte)$", name):
        i = app_indexes[-1]
        return {"kind": "file-route-app", "path": relative.as_posix(), "line": 0,
                "value": _route_value(parts[i + 1:-1])}
    if "routes" in parts[:-1] and name.startswith("+page."):
        i = max(i for i, part in enumerate(parts[:-1]) if part == "routes")
        return {"kind": "file-route-sveltekit", "path": relative.as_posix(), "line": 0,
                "value": _route_value(parts[i + 1:-1])}
    page_indexes = [i for i, part in enumerate(parts[:-1]) if part == "pages"]
    if page_indexes and path.suffix.lower() in CODE_EXTENSIONS:
        i = page_indexes[-1]
        route_parts = parts[i + 1:]
        if not route_parts or route_parts[0] == "api" or name.startswith("_"):
            return None
        stem = name[:-len(path.suffix)] if path.suffix else name
        route_parts[-1] = stem
        if route_parts[-1] == "index":
            route_parts.pop()
        return {"kind": "file-route-pages", "path": relative.as_posix(), "line": 0,
                "value": _route_value(route_parts)}
    return None


def _scan(root: Path, files: Iterable[Path], max_bytes: int) -> tuple[
    list[dict[str, Any]], dict[str, list[dict[str, Any]]], Counter[str], list[str]
]:
    routes: list[dict[str, Any]] = []
    signals = {name: [] for name in SIGNAL_PATTERNS}
    extensions: Counter[str] = Counter()
    warnings: list[str] = []
    for path in files:
        suffix = path.suffix.lower()
        if suffix in SOURCE_EXTENSIONS:
            extensions[suffix] += 1
        candidate = _file_route(path, root)
        if candidate and len(routes) < MAX_ROUTES:
            routes.append(candidate)
        if suffix not in TEXT_EXTENSIONS or path.name in LOCKFILES or ".min." in path.name:
            continue
        try:
            if path.stat().st_size > max_bytes:
                continue
            lines = path.read_text(encoding="utf-8", errors="ignore").splitlines()
        except OSError as exc:
            warnings.append(f"无法读取 {_relative(path, root)}: {exc}")
            continue
        rel = _relative(path, root)
        for number, line in enumerate(lines, 1):
            if suffix in CODE_EXTENSIONS and len(routes) < MAX_ROUTES:
                for kind, pattern in ROUTE_PATTERNS:
                    for match in pattern.finditer(line):
                        routes.append({"kind": kind, "path": rel, "line": number, "value": match.group(1)})
                        if len(routes) >= MAX_ROUTES:
                            break
            for kind, pattern in SIGNAL_PATTERNS.items():
                bucket = signals[kind]
                if len(bucket) >= MAX_SIGNALS:
                    continue
                match = pattern.search(line)
                if match:
                    snippet = line.strip()
                    bucket.append({
                        "path": rel, "line": number, "match": match.group(0),
                        "snippet": snippet[:177] + "..." if len(snippet) > 180 else snippet,
                    })
    unique: dict[tuple[str, str, int, str], dict[str, Any]] = {}
    for item in routes:
        unique[(item["kind"], item["path"], item["line"], item["value"])] = item
    routes = sorted(unique.values(), key=lambda item: (item["value"], item["path"], item["line"], item["kind"]))
    if len(routes) >= MAX_ROUTES:
        warnings.append(f"Route 候选达到上限 {MAX_ROUTES}，结果可能被截断")
    for kind, bucket in signals.items():
        bucket.sort(key=lambda item: (item["path"], item["line"], item["match"]))
        if len(bucket) >= MAX_SIGNALS:
            warnings.append(f"{kind} 线索达到上限 {MAX_SIGNALS}，结果可能被截断")
    return routes, signals, extensions, warnings


def analyze_project(project_root: str | Path, *, max_files: int = 25_000,
                    max_bytes: int = 512_000) -> dict[str, Any]:
    root = Path(project_root).expanduser().resolve()
    if not root.exists():
        raise FileNotFoundError(f"项目目录不存在: {root}")
    if not root.is_dir():
        raise NotADirectoryError(f"项目路径不是目录: {root}")
    files, truncated = _iter_files(root, max_files)
    manifests, warnings = _load_manifests(root, files)
    routes, signals, extensions, scan_warnings = _scan(root, files, max_bytes)
    warnings.extend(scan_warnings)
    if truncated:
        warnings.append(f"扫描文件数达到上限 {max_files}，结果可能不完整")
    if not manifests:
        warnings.append("未发现可解析的 package.json；可能不是 Node 前端项目或扫描范围不正确")
    return {
        "schema_version": SCHEMA_VERSION,
        "root": str(root),
        "package_manager": _package_manager(root, files, manifests),
        "manifests": manifests,
        "stack": _collect_stack(manifests),
        "configs": sorted(_relative(path, root) for path in files
                          if _matches_any(_relative(path, root), CONFIG_PATTERNS)),
        "entry_candidates": sorted(_relative(path, root) for path in files
                                   if _matches_any(_relative(path, root), ENTRY_PATTERNS)),
        "route_candidates": routes,
        "lifecycle_signals": signals,
        "counts": {
            "scanned_files": len(files), "source_files": sum(extensions.values()),
            "package_manifests": len(manifests), "route_candidates": len(routes),
            "lifecycle_signals": {key: len(value) for key, value in sorted(signals.items())},
            "source_extensions": dict(sorted(extensions.items())),
        },
        "warnings": sorted(set(warnings)),
    }


def inventory_to_markdown(inventory: dict[str, Any]) -> str:
    lines = [
        "# Frontend Inventory", "", f"- Root: `{inventory['root']}`",
        f"- Package manager: `{inventory['package_manager'].get('primary') or 'unknown'}`",
        f"- Scanned files: {inventory['counts']['scanned_files']}",
        f"- Source files: {inventory['counts']['source_files']}", "", "## Stack", "",
    ]
    for category, items in inventory["stack"].items():
        lines.append(f"- **{category}**: {', '.join(item['name'] for item in items) or '—'}")
    lines.extend(["", "## Entries", ""])
    lines.extend(f"- `{item}`" for item in inventory["entry_candidates"] or ["—"])
    lines.extend(["", "## Route candidates", ""])
    for item in inventory["route_candidates"]:
        location = f"{item['path']}:{item['line']}" if item["line"] else item["path"]
        lines.append(f"- `{item['value']}` — {item['kind']} — `{location}`")
    if not inventory["route_candidates"]:
        lines.append("- —")
    lines.extend(["", "## Lifecycle signals", ""])
    for kind, items in inventory["lifecycle_signals"].items():
        lines.append(f"- **{kind}**: {len(items)}")
    if inventory["warnings"]:
        lines.extend(["", "## Warnings", ""])
        lines.extend(f"- {item}" for item in inventory["warnings"])
    return "\n".join(lines) + "\n"


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="生成前端项目的确定性盘点 JSON/Markdown。")
    parser.add_argument("project_root", help="要扫描的前端项目根目录")
    parser.add_argument("-o", "--output", help="输出文件；省略时写到 stdout")
    parser.add_argument("--format", choices=("json", "markdown"), default="json")
    parser.add_argument("--max-files", type=int, default=25_000)
    parser.add_argument("--max-bytes", type=int, default=512_000)
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = _parser()
    args = parser.parse_args(argv)
    if args.max_files <= 0 or args.max_bytes <= 0:
        parser.error("--max-files 和 --max-bytes 必须大于 0")
    try:
        inventory = analyze_project(args.project_root, max_files=args.max_files,
                                    max_bytes=args.max_bytes)
    except (FileNotFoundError, NotADirectoryError, PermissionError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    rendered = (inventory_to_markdown(inventory) if args.format == "markdown" else
                json.dumps(inventory, ensure_ascii=False, indent=2, sort_keys=True) + "\n")
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
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
