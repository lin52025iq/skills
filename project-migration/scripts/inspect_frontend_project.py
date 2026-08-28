#!/usr/bin/env python3
"""Deterministically inspect a JavaScript/TypeScript frontend project.

The script reads project metadata only. It never installs packages, executes project
scripts, reads environment values, or traverses dependency directories.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Iterable


PACKAGE_GROUPS: dict[str, dict[str, tuple[str, ...]]] = {
    "frameworks": {
        "React": ("react", "react-dom"),
        "Vue": ("vue",),
        "Angular": ("@angular/core",),
        "Svelte": ("svelte",),
        "Preact": ("preact",),
        "Solid": ("solid-js",),
    },
    "metaFrameworks": {
        "Next.js": ("next",),
        "Nuxt": ("nuxt",),
        "SvelteKit": ("@sveltejs/kit",),
        "Astro": ("astro",),
        "Gatsby": ("gatsby",),
        "Remix": ("@remix-run/react",),
    },
    "bundlers": {
        "Vite": ("vite",),
        "Webpack": ("webpack",),
        "Rspack": ("@rspack/core",),
        "Rollup": ("rollup",),
        "Parcel": ("parcel",),
        "esbuild": ("esbuild",),
        "Create React App": ("react-scripts",),
        "Vue CLI": ("@vue/cli-service",),
        "Angular CLI": ("@angular/cli",),
    },
    "routers": {
        "React Router": ("react-router", "react-router-dom"),
        "Vue Router": ("vue-router",),
        "Angular Router": ("@angular/router",),
        "TanStack Router": ("@tanstack/react-router",),
    },
    "state": {
        "Redux Toolkit": ("@reduxjs/toolkit",),
        "Redux": ("redux", "react-redux"),
        "Zustand": ("zustand",),
        "Pinia": ("pinia",),
        "Vuex": ("vuex",),
        "NgRx": ("@ngrx/store",),
        "MobX": ("mobx", "mobx-react-lite"),
        "Jotai": ("jotai",),
        "Recoil": ("recoil",),
        "XState": ("xstate",),
    },
    "dataFetching": {
        "TanStack Query": ("@tanstack/react-query", "@tanstack/vue-query"),
        "SWR": ("swr",),
        "Apollo Client": ("@apollo/client",),
        "urql": ("urql", "@urql/core"),
        "Axios": ("axios",),
        "GraphQL Request": ("graphql-request",),
        "RTK Query": ("@reduxjs/toolkit",),
    },
    "forms": {
        "React Hook Form": ("react-hook-form",),
        "Formik": ("formik",),
        "Final Form": ("final-form", "react-final-form"),
        "VeeValidate": ("vee-validate",),
        "Angular Forms": ("@angular/forms",),
    },
    "uiLibraries": {
        "MUI": ("@mui/material",),
        "Ant Design": ("antd",),
        "Chakra UI": ("@chakra-ui/react",),
        "Radix UI": ("@radix-ui/react-dialog", "@radix-ui/react-slot"),
        "Headless UI": ("@headlessui/react", "@headlessui/vue"),
        "Vuetify": ("vuetify",),
        "Element Plus": ("element-plus",),
        "PrimeReact": ("primereact",),
        "PrimeVue": ("primevue",),
        "Bootstrap": ("bootstrap", "react-bootstrap"),
        "Quasar": ("quasar",),
    },
    "styling": {
        "Tailwind CSS": ("tailwindcss",),
        "Sass": ("sass", "node-sass"),
        "Less": ("less",),
        "styled-components": ("styled-components",),
        "Emotion": ("@emotion/react", "@emotion/styled"),
        "Vanilla Extract": ("@vanilla-extract/css",),
        "PostCSS": ("postcss",),
    },
    "testing": {
        "Vitest": ("vitest",),
        "Jest": ("jest",),
        "Mocha": ("mocha",),
        "Testing Library": (
            "@testing-library/react",
            "@testing-library/vue",
            "@testing-library/angular",
            "@testing-library/svelte",
        ),
        "Playwright": ("@playwright/test", "playwright"),
        "Cypress": ("cypress",),
        "Storybook": ("storybook", "@storybook/react", "@storybook/vue3"),
        "axe": ("axe-core", "@axe-core/playwright", "jest-axe"),
    },
    "observability": {
        "Sentry": ("@sentry/react", "@sentry/vue", "@sentry/angular", "@sentry/nextjs"),
        "Datadog RUM": ("@datadog/browser-rum",),
        "OpenTelemetry": ("@opentelemetry/api",),
    },
}

PREFIX_GROUPS: dict[str, tuple[str, ...]] = {
    "Storybook packages": ("@storybook/",),
    "Angular packages": ("@angular/",),
    "NgRx packages": ("@ngrx/",),
    "Radix UI packages": ("@radix-ui/",),
}

CONFIG_FILES: tuple[str, ...] = (
    "tsconfig.json",
    "jsconfig.json",
    "vite.config.ts",
    "vite.config.js",
    "vite.config.mts",
    "webpack.config.js",
    "webpack.config.ts",
    "rspack.config.js",
    "rspack.config.ts",
    "rollup.config.js",
    "rollup.config.ts",
    "next.config.js",
    "next.config.mjs",
    "next.config.ts",
    "nuxt.config.ts",
    "nuxt.config.js",
    "svelte.config.js",
    "astro.config.mjs",
    "angular.json",
    "vue.config.js",
    "tailwind.config.js",
    "tailwind.config.ts",
    "postcss.config.js",
    "postcss.config.cjs",
    "eslint.config.js",
    "eslint.config.mjs",
    ".eslintrc",
    ".eslintrc.js",
    ".eslintrc.json",
    "prettier.config.js",
    ".prettierrc",
    ".prettierrc.json",
    "vitest.config.ts",
    "vitest.config.js",
    "jest.config.js",
    "jest.config.ts",
    "playwright.config.ts",
    "playwright.config.js",
    "cypress.config.ts",
    "cypress.config.js",
    "turbo.json",
    "nx.json",
    "lerna.json",
    "pnpm-workspace.yaml",
)

SOURCE_DIR_CANDIDATES: tuple[str, ...] = (
    "src",
    "app",
    "pages",
    "apps",
    "packages",
    "components",
    "public",
    "tests",
    "e2e",
    ".storybook",
)

LOCKFILES: dict[str, str] = {
    "pnpm-lock.yaml": "pnpm",
    "yarn.lock": "yarn",
    "package-lock.json": "npm",
    "npm-shrinkwrap.json": "npm",
    "bun.lock": "bun",
    "bun.lockb": "bun",
}

IMPORTANT_SCRIPT_NAMES: tuple[str, ...] = (
    "dev",
    "start",
    "build",
    "preview",
    "typecheck",
    "type-check",
    "lint",
    "test",
    "test:unit",
    "test:component",
    "test:e2e",
    "e2e",
    "storybook",
    "build-storybook",
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Inspect a frontend project without executing it. Outputs detected stack, "
            "package manager, workspace, scripts, configs, tests, and migration warnings."
        )
    )
    parser.add_argument("root", type=Path, help="Frontend project or workspace root")
    parser.add_argument(
        "--format",
        choices=("json", "markdown"),
        default="json",
        help="Output format (default: json)",
    )
    parser.add_argument("--output", type=Path, help="Write output to this file")
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Return exit code 1 when inspection warnings are present",
    )
    return parser.parse_args()


def load_package_json(path: Path) -> dict[str, Any]:
    try:
        raw = path.read_text(encoding="utf-8")
    except OSError as exc:
        raise ValueError(f"cannot read {path}: {exc}") from exc

    try:
        data = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise ValueError(
            f"invalid JSON in {path} at line {exc.lineno}, column {exc.colno}: {exc.msg}"
        ) from exc

    if not isinstance(data, dict):
        raise ValueError(f"{path} must contain a JSON object")
    return data


def string_dict(value: Any) -> dict[str, str]:
    if not isinstance(value, dict):
        return {}
    return {str(key): str(item) for key, item in value.items() if isinstance(item, str)}


def combined_dependencies(package_json: dict[str, Any]) -> dict[str, str]:
    result: dict[str, str] = {}
    for field in ("dependencies", "devDependencies", "peerDependencies", "optionalDependencies"):
        result.update(string_dict(package_json.get(field)))
    return result


def present_packages(dependencies: dict[str, str], candidates: Iterable[str]) -> list[str]:
    return sorted(package for package in candidates if package in dependencies)


def detect_groups(dependencies: dict[str, str]) -> dict[str, list[dict[str, Any]]]:
    detected: dict[str, list[dict[str, Any]]] = {}
    for group, products in PACKAGE_GROUPS.items():
        entries: list[dict[str, Any]] = []
        for product, packages in products.items():
            matches = present_packages(dependencies, packages)
            if matches:
                entries.append(
                    {
                        "name": product,
                        "packages": [
                            {"name": package, "version": dependencies[package]}
                            for package in matches
                        ],
                    }
                )
        detected[group] = entries
    return detected


def detect_prefixes(dependencies: dict[str, str]) -> list[dict[str, Any]]:
    result: list[dict[str, Any]] = []
    for name, prefixes in PREFIX_GROUPS.items():
        matches = sorted(
            package
            for package in dependencies
            if any(package.startswith(prefix) for prefix in prefixes)
        )
        if matches:
            result.append(
                {
                    "name": name,
                    "packages": [
                        {"name": package, "version": dependencies[package]}
                        for package in matches
                    ],
                }
            )
    return result


def normalize_workspaces(value: Any) -> list[str]:
    if isinstance(value, list):
        return [str(item) for item in value]
    if isinstance(value, dict):
        packages = value.get("packages")
        if isinstance(packages, list):
            return [str(item) for item in packages]
    return []


def detect_package_manager(root: Path, package_json: dict[str, Any]) -> tuple[dict[str, Any], list[str]]:
    warnings: list[str] = []
    declared = package_json.get("packageManager")
    declared_name = ""
    declared_version = ""
    if isinstance(declared, str) and declared:
        declared_name, separator, declared_version = declared.partition("@")
        if not separator:
            declared_version = ""

    found_lockfiles = [
        {"file": filename, "manager": manager}
        for filename, manager in LOCKFILES.items()
        if (root / filename).exists()
    ]
    lock_managers = sorted({entry["manager"] for entry in found_lockfiles})

    selected = declared_name or (lock_managers[0] if len(lock_managers) == 1 else "unknown")
    source = "packageManager field" if declared_name else "lockfile"
    if selected == "unknown":
        source = "undetermined"
        warnings.append("No packageManager field or recognized lockfile was found.")

    if len(lock_managers) > 1:
        warnings.append(
            "Multiple package-manager lockfiles were found: "
            + ", ".join(entry["file"] for entry in found_lockfiles)
        )
    if declared_name and lock_managers and declared_name not in lock_managers:
        warnings.append(
            f"packageManager declares {declared_name}, but lockfile(s) indicate "
            + ", ".join(lock_managers)
        )

    return (
        {
            "selected": selected,
            "version": declared_version,
            "source": source,
            "declared": declared if isinstance(declared, str) else "",
            "lockfiles": found_lockfiles,
        },
        warnings,
    )


def inspect_project(root: Path) -> dict[str, Any]:
    root = root.expanduser().resolve()
    if not root.exists():
        raise ValueError(f"project root does not exist: {root}")
    if not root.is_dir():
        raise ValueError(f"project root is not a directory: {root}")

    package_path = root / "package.json"
    if not package_path.exists():
        raise ValueError(f"package.json not found at project root: {package_path}")

    package_json = load_package_json(package_path)
    dependencies = combined_dependencies(package_json)
    package_manager, warnings = detect_package_manager(root, package_json)

    scripts = string_dict(package_json.get("scripts"))
    important_scripts = {
        name: scripts[name] for name in IMPORTANT_SCRIPT_NAMES if name in scripts
    }

    config_files = [filename for filename in CONFIG_FILES if (root / filename).exists()]
    source_dirs = [dirname for dirname in SOURCE_DIR_CANDIDATES if (root / dirname).is_dir()]
    env_files = sorted(
        path.name
        for path in root.glob(".env*")
        if path.is_file() and path.name not in {".env", ".env.local"}
    )
    if (root / ".env").is_file():
        env_files.insert(0, ".env")
    if (root / ".env.local").is_file() and ".env.local" not in env_files:
        env_files.append(".env.local")

    workspaces = normalize_workspaces(package_json.get("workspaces"))
    workspace_tools = [
        filename
        for filename in ("pnpm-workspace.yaml", "turbo.json", "nx.json", "lerna.json")
        if (root / filename).exists()
    ]

    if not important_scripts.get("build"):
        warnings.append("No build script was found in package.json.")
    if not any(name in important_scripts for name in ("dev", "start")):
        warnings.append("No dev or start script was found in package.json.")
    if not any(name.startswith("test") or name == "e2e" for name in scripts):
        warnings.append("No test or e2e script was found in package.json.")
    if "typescript" not in dependencies and not (root / "tsconfig.json").exists():
        warnings.append("TypeScript was not detected.")
    if len(package_manager["lockfiles"]) == 0:
        warnings.append("No lockfile was found; dependency resolution may not be reproducible.")

    detected = detect_groups(dependencies)
    has_framework = bool(detected["frameworks"] or detected["metaFrameworks"])
    if not has_framework:
        warnings.append("No recognized frontend framework or meta-framework was detected.")

    result: dict[str, Any] = {
        "root": str(root),
        "package": {
            "name": package_json.get("name", ""),
            "version": package_json.get("version", ""),
            "private": bool(package_json.get("private", False)),
            "type": package_json.get("type", "commonjs-default"),
            "engines": package_json.get("engines", {}),
        },
        "packageManager": package_manager,
        "workspace": {
            "patterns": workspaces,
            "tools": workspace_tools,
            "isWorkspaceRoot": bool(workspaces or workspace_tools),
        },
        "detected": detected,
        "packagePrefixes": detect_prefixes(dependencies),
        "scripts": important_scripts,
        "allScriptNames": sorted(scripts),
        "configFiles": config_files,
        "sourceDirectories": source_dirs,
        "environmentFileNames": env_files,
        "browserslist": package_json.get("browserslist", None),
        "dependencyCount": len(dependencies),
        "warnings": sorted(set(warnings)),
    }
    return result


def format_packages(entries: list[dict[str, Any]]) -> str:
    if not entries:
        return "未检测到"
    rendered: list[str] = []
    for entry in entries:
        packages = ", ".join(
            f"{item['name']}@{item['version']}" for item in entry.get("packages", [])
        )
        rendered.append(f"{entry['name']} ({packages})")
    return "；".join(rendered)


def to_markdown(result: dict[str, Any]) -> str:
    package = result["package"]
    manager = result["packageManager"]
    workspace = result["workspace"]
    lines = [
        "# 前端项目盘点",
        "",
        f"- 根目录：`{result['root']}`",
        f"- 包：`{package['name'] or '(未命名)'}` `{package['version'] or ''}`",
        f"- module type：`{package['type']}`",
        f"- package manager：`{manager['selected']}`"
        + (f" `@{manager['version']}`" if manager.get("version") else ""),
        f"- workspace root：`{str(workspace['isWorkspaceRoot']).lower()}`",
        "",
        "## 技术栈",
        "",
    ]
    labels = {
        "frameworks": "Framework",
        "metaFrameworks": "Meta-framework",
        "bundlers": "Bundler",
        "routers": "Router",
        "state": "State",
        "dataFetching": "Data fetching",
        "forms": "Form",
        "uiLibraries": "UI library",
        "styling": "Styling",
        "testing": "Testing",
        "observability": "Observability",
    }
    for key, label in labels.items():
        lines.append(f"- **{label}**：{format_packages(result['detected'][key])}")

    lines.extend(
        [
            "",
            "## 工程",
            "",
            "- Workspace patterns："
            + (", ".join(f"`{item}`" for item in workspace["patterns"]) or "无"),
            "- Workspace tools："
            + (", ".join(f"`{item}`" for item in workspace["tools"]) or "无"),
            "- Source directories："
            + (", ".join(f"`{item}`" for item in result["sourceDirectories"]) or "未检测到"),
            "- Config files："
            + (", ".join(f"`{item}`" for item in result["configFiles"]) or "未检测到"),
            "- Env file names："
            + (", ".join(f"`{item}`" for item in result["environmentFileNames"]) or "未检测到"),
            "",
            "## 关键脚本",
            "",
        ]
    )
    if result["scripts"]:
        for name, command in result["scripts"].items():
            lines.append(f"- `{name}`：`{command}`")
    else:
        lines.append("- 未检测到")

    lines.extend(["", "## 迁移提示", ""])
    if result["warnings"]:
        lines.extend(f"- ⚠️ {warning}" for warning in result["warnings"])
    else:
        lines.append("- 未发现结构性警告；仍需运行时和代码证据确认。")

    lines.extend(
        [
            "",
            "> 本报告只读取文件名、package.json 和配置是否存在；不执行脚本，也不读取环境变量内容。",
            "",
        ]
    )
    return "\n".join(lines)


def main() -> int:
    args = parse_args()
    try:
        result = inspect_project(args.root)
    except ValueError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    output = (
        json.dumps(result, ensure_ascii=False, indent=2) + "\n"
        if args.format == "json"
        else to_markdown(result)
    )

    if args.output:
        try:
            args.output.parent.mkdir(parents=True, exist_ok=True)
            args.output.write_text(output, encoding="utf-8")
        except OSError as exc:
            print(f"error: cannot write {args.output}: {exc}", file=sys.stderr)
            return 2
    else:
        print(output, end="")

    return 1 if args.strict and result["warnings"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
