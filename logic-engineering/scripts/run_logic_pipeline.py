#!/usr/bin/env python3
"""运行逻辑工程最小流水线。

流程：
1. 自动识别 CLM 版本并选择 schema
2. 校验原始 CLM
3. 可选应用 Semantic Patch
4. 校验更新后的 CLM
5. 分析修改影响范围
6. 生成中文逻辑投影
7. 从 CLM 独立生成测试向量
8. 可选编译 IIR
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path
from typing import Any, Dict, List


SCRIPT_DIR = Path(__file__).resolve().parent
SCHEMA_DIR = SCRIPT_DIR.parent / "schemas"


def run(cmd: List[str], label: str) -> str:
    proc = subprocess.run(cmd, text=True, capture_output=True)
    if proc.returncode != 0:
        payload = {
            "ok": False,
            "stage": label,
            "command": cmd,
            "stdout": proc.stdout,
            "stderr": proc.stderr,
        }
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        raise SystemExit(proc.returncode)
    if proc.stdout.strip():
        print(f"[{label}]\n{proc.stdout.strip()}")
    return proc.stdout


def load_json(path: Path) -> Dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def detect_schema(clm_path: Path) -> Path:
    document = load_json(clm_path)
    root = document.get("clm", document)
    version = str(root.get("version", "0.1"))
    if version in {"0.2", "2", "2.0"}:
        return SCHEMA_DIR / "clm-v0.2.schema.json"
    return SCHEMA_DIR / "clm-v0.1.schema.json"


def patch_changed_ids(path: Path) -> List[str]:
    patch = load_json(path)
    patch = patch.get("semantic_patch", patch)
    ids: List[str] = []
    target = patch.get("target_semantic_id") or patch.get("target")
    if isinstance(target, str):
        ids.append(target)
    for item in patch.get("changes", []) or []:
        if isinstance(item, dict):
            item_target = item.get("target_semantic_id") or item.get("target")
            if isinstance(item_target, str):
                ids.append(item_target)
    return list(dict.fromkeys(ids))


def validate_model(path: Path, schema: Path, label: str) -> None:
    run([
        sys.executable,
        str(SCRIPT_DIR / "validate_clm.py"),
        str(path),
        "--schema",
        str(schema),
    ], label)


def main() -> int:
    parser = argparse.ArgumentParser(description="运行逻辑工程最小流水线")
    parser.add_argument("clm", type=Path)
    parser.add_argument("--patch", type=Path)
    parser.add_argument("--target-profile", type=Path)
    parser.add_argument("--output-dir", type=Path, default=Path(".logic-engineering-output"))
    parser.add_argument("--schema", type=Path, help="显式覆盖自动 schema 选择")
    args = parser.parse_args()

    out = args.output_dir
    out.mkdir(parents=True, exist_ok=True)

    working_clm = args.clm
    schema = args.schema or detect_schema(working_clm)
    validate_model(working_clm, schema, "校验原始 CLM")

    impact = None
    changed_ids: List[str] = []

    if args.patch:
        changed_ids = patch_changed_ids(args.patch)
        updated = out / "updated.clm.json"
        diff = out / "semantic-diff.json"
        run([
            sys.executable,
            str(SCRIPT_DIR / "apply_semantic_patch.py"),
            str(working_clm),
            str(args.patch),
            "-o",
            str(updated),
            "--diff-output",
            str(diff),
        ], "应用语义补丁")
        working_clm = updated

        # 补丁可能升级模型版本，因此应用后重新自动选择 schema。
        schema = args.schema or detect_schema(working_clm)
        validate_model(working_clm, schema, "校验更新后的 CLM")

        if changed_ids:
            impact = out / "impact-analysis.json"
            run([
                sys.executable,
                str(SCRIPT_DIR / "analyze_impact.py"),
                str(working_clm),
                *changed_ids,
                "--output",
                str(impact),
            ], "分析语义影响")

    symbol_table = out / "symbol-table.json"
    run([
        sys.executable,
        str(SCRIPT_DIR / "symbol_table.py"),
        str(working_clm),
        "-o",
        str(symbol_table),
    ], "生成 Symbol Table")

    human_logic = out / "human-logic.md"
    run([
        sys.executable,
        str(SCRIPT_DIR / "render_human_logic.py"),
        str(working_clm),
        "-o",
        str(human_logic),
    ], "生成中文逻辑投影")

    test_vectors = out / "test-vectors.json"
    run([
        sys.executable,
        str(SCRIPT_DIR / "generate_test_vectors.py"),
        str(working_clm),
        "--output",
        str(test_vectors),
    ], "生成测试向量")

    iir = None
    if args.target_profile:
        iir = out / "implementation.iir.json"
        run([
            sys.executable,
            str(SCRIPT_DIR / "compile_iir.py"),
            str(working_clm),
            str(args.target_profile),
            "-o",
            str(iir),
        ], "编译 IIR")

    result = {
        "ok": True,
        "schema": str(schema),
        "clm": str(working_clm),
        "symbol_table": str(symbol_table),
        "human_logic": str(human_logic),
        "semantic_diff": str(out / "semantic-diff.json") if args.patch else None,
        "impact_analysis": str(impact) if impact else None,
        "test_vectors": str(test_vectors),
        "iir": str(iir) if iir else None,
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
