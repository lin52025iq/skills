#!/usr/bin/env python3
"""校验 IIR v0.2 的结构与关键技术映射完整性。"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Dict


class Result:
    def __init__(self) -> None:
        self.errors: list[dict[str, Any]] = []
        self.warnings: list[dict[str, Any]] = []

    def error(self, code: str, message: str, path: str | None = None) -> None:
        item: dict[str, Any] = {"code": code, "message": message}
        if path:
            item["path"] = path
        self.errors.append(item)

    def warning(self, code: str, message: str, path: str | None = None) -> None:
        item: dict[str, Any] = {"code": code, "message": message}
        if path:
            item["path"] = path
        self.warnings.append(item)


def load_json(path: Path) -> Dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def schema_validate(document: Dict[str, Any], schema: Dict[str, Any], result: Result) -> None:
    try:
        import jsonschema  # type: ignore
    except ImportError:
        result.warning("JSONSCHEMA_NOT_INSTALLED", "未安装 jsonschema，跳过 IIR Schema 校验")
        return
    validator = jsonschema.Draft202012Validator(schema)
    for error in sorted(validator.iter_errors(document), key=lambda e: list(e.absolute_path)):
        path = ".".join(str(x) for x in error.absolute_path)
        result.error("IIR_SCHEMA_ERROR", error.message, path or None)


def validate(document: Dict[str, Any], schema: Dict[str, Any] | None = None) -> Dict[str, Any]:
    result = Result()
    if schema:
        schema_validate(document, schema, result)

    iir = document.get("iir")
    if not isinstance(iir, dict):
        result.error("INVALID_IIR_ROOT", "IIR 根节点必须包含 iir 对象")
        return {"valid": False, "errors": result.errors, "warnings": result.warnings}

    if str(iir.get("version")) != "0.2":
        result.error("UNSUPPORTED_IIR_VERSION", f"当前只支持 IIR v0.2，实际为 {iir.get('version')}")

    ids: set[str] = set()
    for section in (
        "use_cases", "repository_contracts", "external_ports", "transaction_plans",
        "concurrency_plans", "retry_plans", "idempotency_plans", "error_mappings",
        "generation_regions",
    ):
        for index, item in enumerate(iir.get(section, []) or []):
            if not isinstance(item, dict):
                continue
            item_id = item.get("id")
            if isinstance(item_id, str):
                if item_id in ids:
                    result.error("DUPLICATE_IIR_ID", f"IIR ID 重复：{item_id}", f"{section}[{index}]")
                ids.add(item_id)

    repository_ids = {item.get("id") for item in iir.get("repository_contracts", []) or [] if isinstance(item, dict)}
    port_ids = {item.get("id") for item in iir.get("external_ports", []) or [] if isinstance(item, dict)}
    known_dependencies = repository_ids | port_ids

    for index, uc in enumerate(iir.get("use_cases", []) or []):
        if not isinstance(uc, dict):
            continue
        refs = uc.get("semantic_refs", []) or []
        if not refs:
            result.error("MISSING_TRACEABILITY", "Use Case 缺少 semantic_refs", f"use_cases[{index}]")
        for dep in uc.get("dependencies", []) or []:
            if dep not in known_dependencies:
                result.error("UNRESOLVED_DEPENDENCY", f"Use Case dependency 未定义：{dep}", f"use_cases[{index}].dependencies")

    for index, repo in enumerate(iir.get("repository_contracts", []) or []):
        if not repo.get("entity_ref"):
            result.error("MISSING_ENTITY_REF", "Repository Contract 缺少 entity_ref", f"repository_contracts[{index}]")
        if not repo.get("operations"):
            result.warning("EMPTY_REPOSITORY_CONTRACT", "Repository Contract 没有 operation", f"repository_contracts[{index}]")

    for index, port in enumerate(iir.get("external_ports", []) or []):
        if not port.get("operations"):
            result.error("EMPTY_EXTERNAL_PORT", "External Port 没有 operation", f"external_ports[{index}]")

    for bucket in ("transaction_plans", "concurrency_plans", "retry_plans", "idempotency_plans"):
        for index, plan in enumerate(iir.get(bucket, []) or []):
            if not plan.get("strategy"):
                result.error("MISSING_IMPLEMENTATION_STRATEGY", f"{bucket} 缺少 strategy", f"{bucket}[{index}]")

    blocking = [x for x in iir.get("unresolved", []) or [] if isinstance(x, dict) and x.get("severity") == "blocking"]
    if blocking:
        result.error("BLOCKING_UNRESOLVED", f"存在 {len(blocking)} 个阻塞 unresolved 项")

    trace_ids = {item.get("implementation_id") for item in iir.get("traceability", []) or [] if isinstance(item, dict)}
    for uc in iir.get("use_cases", []) or []:
        if uc.get("id") not in trace_ids:
            result.error("MISSING_TRACEABILITY_ENTRY", f"Use Case {uc.get('id')} 缺少 traceability 映射")

    return {
        "valid": not result.errors,
        "errors": result.errors,
        "warnings": result.warnings,
        "stats": {
            "use_cases": len(iir.get("use_cases", []) or []),
            "repositories": len(iir.get("repository_contracts", []) or []),
            "external_ports": len(iir.get("external_ports", []) or []),
            "blocking_unresolved": len(blocking),
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="校验 IIR v0.2")
    parser.add_argument("iir", type=Path)
    parser.add_argument("--schema", type=Path)
    parser.add_argument("--pretty", action="store_true")
    args = parser.parse_args()
    try:
        document = load_json(args.iir)
        schema = load_json(args.schema) if args.schema else None
    except (OSError, json.JSONDecodeError) as exc:
        print(json.dumps({"valid": False, "error": str(exc)}, ensure_ascii=False))
        return 2
    output = validate(document, schema)
    print(json.dumps(output, ensure_ascii=False, indent=2 if args.pretty else None))
    return 0 if output["valid"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
