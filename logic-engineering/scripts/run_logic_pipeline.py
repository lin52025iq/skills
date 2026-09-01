#!/usr/bin/env python3
"""运行最小逻辑工程流水线。

流程：
1. 校验原始 CLM
2. 可选应用 Semantic Patch
3. 校验更新后的 CLM
4. 生成中文逻辑投影
5. 可选编译 IIR

该脚本通过调用同目录脚本实现，作为 Skill 的统一可执行入口。
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import List


SCRIPT_DIR = Path(__file__).resolve().parent


def run(cmd: List[str], label: str) -> None:
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


def main() -> int:
    parser = argparse.ArgumentParser(description="运行逻辑工程最小流水线")
    parser.add_argument("clm", type=Path)
    parser.add_argument("--patch", type=Path)
    parser.add_argument("--target-profile", type=Path)
    parser.add_argument("--output-dir", type=Path, default=Path(".logic-engineering-output"))
    parser.add_argument("--schema", type=Path)
    args = parser.parse_args()

    out = args.output_dir
    out.mkdir(parents=True, exist_ok=True)

    schema = args.schema or (SCRIPT_DIR.parent / "schemas" / "clm-v0.1.schema.json")
    working_clm = args.clm

    run([
        sys.executable,
        str(SCRIPT_DIR / "validate_clm.py"),
        str(working_clm),
        "--schema",
        str(schema),
    ], "校验原始 CLM")

    if args.patch:
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

        run([
            sys.executable,
            str(SCRIPT_DIR / "validate_clm.py"),
            str(working_clm),
            "--schema",
            str(schema),
        ], "校验更新后的 CLM")

    human_logic = out / "human-logic.md"
    run([
        sys.executable,
        str(SCRIPT_DIR / "render_human_logic.py"),
        str(working_clm),
        "-o",
        str(human_logic),
    ], "生成中文逻辑投影")

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
        "clm": str(working_clm),
        "human_logic": str(human_logic),
        "semantic_diff": str(out / "semantic-diff.json") if args.patch else None,
        "iir": str(iir) if iir else None,
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
