#!/usr/bin/env python3
"""Validate a machine-readable frontend migration manifest.

Standard-library only: safe to run before project dependencies are installed.
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any


ENUMS = {
    "tier": {"quick", "slice", "program"},
    "mode": {
        "page-feature",
        "framework",
        "language",
        "router",
        "state-data",
        "form",
        "styling",
        "design-system",
        "bundler-runtime",
        "workspace",
        "ssr-ssg-rsc",
        "micro-frontend",
        "testing",
    },
    "redesignPolicy": {"parity", "approved-redesign", "hybrid"},
    "lifecycle": {
        "active",
        "conditional",
        "hidden",
        "disabled",
        "deprecated",
        "removed",
        "unknown",
    },
    "evidenceStatus": {"observed", "measured", "reported", "inferred", "unknown"},
    "targetDisposition": {"migrate", "adapt", "replace", "drop", "defer"},
    "status": {
        "discovery",
        "planned",
        "pilot",
        "implementing",
        "verifying",
        "ready",
        "released",
        "blocked",
        "stopped",
    },
    "rolloutStrategy": {"direct", "feature-flag", "dual-route", "canary", "incremental"},
    "unknownStatus": {"open", "resolved", "accepted", "blocked"},
}


@dataclass(frozen=True)
class Issue:
    level: str
    path: str
    message: str


class Check:
    def __init__(self) -> None:
        self.issues: list[Issue] = []

    def error(self, path: str, message: str) -> None:
        self.issues.append(Issue("error", path, message))

    def warning(self, path: str, message: str) -> None:
        self.issues.append(Issue("warning", path, message))

    def obj(self, value: Any, path: str) -> dict[str, Any] | None:
        if not isinstance(value, dict):
            self.error(path, "must be an object")
            return None
        return value

    def array(self, value: Any, path: str, *, nonempty: bool = False) -> list[Any] | None:
        if not isinstance(value, list):
            self.error(path, "must be an array")
            return None
        if nonempty and not value:
            self.error(path, "must not be empty")
        return value

    def text(self, obj: dict[str, Any], key: str, path: str, *, required: bool = True) -> str | None:
        field_path = f"{path}.{key}" if path else key
        value = obj.get(key)
        if value is None and not required:
            return None
        if not isinstance(value, str):
            self.error(field_path, "must be a string")
            return None
        if required and not value.strip():
            self.error(field_path, "must not be empty")
        return value

    def enum(self, value: Any, enum_name: str, path: str) -> str | None:
        if not isinstance(value, str):
            self.error(path, "must be a string")
            return None
        allowed = ENUMS[enum_name]
        if value not in allowed:
            self.error(path, f"must be one of: {', '.join(sorted(allowed))}")
        return value

    def string_array(self, value: Any, path: str, *, nonempty: bool = False) -> list[str] | None:
        items = self.array(value, path, nonempty=nonempty)
        if items is None:
            return None
        result: list[str] = []
        for index, item in enumerate(items):
            if not isinstance(item, str) or not item.strip():
                self.error(f"{path}[{index}]", "must be a non-empty string")
            else:
                result.append(item)
        return result


def validate_endpoint(check: Check, value: Any, path: str, *, target: bool = False) -> None:
    endpoint = check.obj(value, path)
    if endpoint is None:
        return
    check.text(endpoint, "root", path)
    check.text(endpoint, "application", path)
    if "commit" in endpoint:
        check.text(endpoint, "commit", path)

    runtime = endpoint.get("runtime")
    if runtime is None:
        check.warning(f"{path}.runtime", "runtime evidence availability is not recorded")
    else:
        runtime_obj = check.obj(runtime, f"{path}.runtime")
        if runtime_obj is not None:
            available = runtime_obj.get("available")
            if not isinstance(available, bool):
                check.error(f"{path}.runtime.available", "must be a boolean")
            elif available:
                check.text(runtime_obj, "url", f"{path}.runtime")
                check.text(runtime_obj, "startCommand", f"{path}.runtime")

    if target:
        references = check.array(endpoint.get("referenceFeatures", []), f"{path}.referenceFeatures")
        if references is not None:
            if not references:
                check.warning(f"{path}.referenceFeatures", "no target-native reference feature is recorded")
            for index, item in enumerate(references):
                item_path = f"{path}.referenceFeatures[{index}]"
                reference = check.obj(item, item_path)
                if reference is not None:
                    check.text(reference, "path", item_path)
                    check.text(reference, "reason", item_path)


def validate_scope(check: Check, value: Any) -> None:
    scope = check.obj(value, "scope")
    if scope is None:
        return
    check.string_array(scope.get("include"), "scope.include", nonempty=True)
    check.string_array(scope.get("exclude", []), "scope.exclude")
    check.string_array(scope.get("nonGoals", []), "scope.nonGoals")


def validate_capabilities(check: Check, value: Any) -> set[str]:
    capabilities = check.array(value, "capabilities", nonempty=True)
    ids: set[str] = set()
    if capabilities is None:
        return ids

    for index, item in enumerate(capabilities):
        path = f"capabilities[{index}]"
        capability = check.obj(item, path)
        if capability is None:
            continue
        capability_id = check.text(capability, "id", path)
        check.text(capability, "name", path)
        lifecycle = check.enum(capability.get("lifecycle"), "lifecycle", f"{path}.lifecycle")
        check.enum(capability.get("evidenceStatus"), "evidenceStatus", f"{path}.evidenceStatus")
        disposition = check.enum(
            capability.get("targetDisposition"), "targetDisposition", f"{path}.targetDisposition"
        )
        check.string_array(capability.get("sourceEvidence"), f"{path}.sourceEvidence", nonempty=True)
        check.string_array(capability.get("acceptance"), f"{path}.acceptance", nonempty=True)

        if capability_id:
            if capability_id in ids:
                check.error(f"{path}.id", f"duplicate capability id: {capability_id}")
            ids.add(capability_id)

        approval = capability.get("approval", "")
        approved = isinstance(approval, str) and bool(approval.strip())
        if lifecycle in {"active", "conditional"} and disposition == "drop" and not approved:
            check.error(f"{path}.approval", "dropping an active or conditional capability requires approval")
        if lifecycle in {"deprecated", "removed"} and disposition in {
            "migrate",
            "adapt",
            "replace",
        } and not approved:
            check.error(
                f"{path}.approval",
                "restoring a deprecated or removed capability requires explicit approval",
            )
        if lifecycle == "unknown" and disposition not in {"defer", "drop"}:
            check.warning(
                f"{path}.targetDisposition",
                "unknown capability is scheduled for implementation before lifecycle resolution",
            )
        if disposition in {"migrate", "adapt", "replace"}:
            check.text(capability, "targetLocation", path)
    return ids


def validate_routes(check: Check, value: Any) -> tuple[set[str], list[tuple[str, str]]]:
    routes = check.array(value, "routes")
    route_ids: set[str] = set()
    scenario_refs: list[tuple[str, str]] = []
    if routes is None:
        return route_ids, scenario_refs

    for index, item in enumerate(routes):
        path = f"routes[{index}]"
        route = check.obj(item, path)
        if route is None:
            continue
        route_id = check.text(route, "id", path)
        check.text(route, "sourcePath", path)
        lifecycle = check.enum(route.get("lifecycle"), "lifecycle", f"{path}.lifecycle")
        if route_id:
            if route_id in route_ids:
                check.error(f"{path}.id", f"duplicate route id: {route_id}")
            route_ids.add(route_id)
        if lifecycle in {"active", "conditional", "hidden", "disabled"}:
            check.text(route, "targetPath", path)

        ids = check.string_array(route.get("acceptanceScenarioIds", []), f"{path}.acceptanceScenarioIds")
        if ids is not None:
            if lifecycle in {"active", "conditional"} and not ids:
                check.warning(f"{path}.acceptanceScenarioIds", "live route has no acceptance scenarios")
            scenario_refs.extend(
                (f"{path}.acceptanceScenarioIds[{scenario_index}]", scenario_id)
                for scenario_index, scenario_id in enumerate(ids)
            )
    return route_ids, scenario_refs


def validate_viewports(check: Check, value: Any) -> int:
    viewports = check.array(value, "viewports")
    names: set[str] = set()
    if viewports is None:
        return 0
    for index, item in enumerate(viewports):
        path = f"viewports[{index}]"
        viewport = check.obj(item, path)
        if viewport is None:
            continue
        name = check.text(viewport, "name", path)
        if name:
            if name in names:
                check.error(f"{path}.name", f"duplicate viewport name: {name}")
            names.add(name)
        for field in ("width", "height"):
            number = viewport.get(field)
            if not isinstance(number, int) or isinstance(number, bool) or number <= 0:
                check.error(f"{path}.{field}", "must be a positive integer")
        scale = viewport.get("deviceScaleFactor", 1)
        if not isinstance(scale, (int, float)) or isinstance(scale, bool) or scale <= 0:
            check.error(f"{path}.deviceScaleFactor", "must be a positive number")
    return len(viewports)


def validate_scenarios(check: Check, value: Any, capability_ids: set[str]) -> set[str]:
    scenarios = check.array(value, "scenarios")
    ids: set[str] = set()
    if scenarios is None:
        return ids
    for index, item in enumerate(scenarios):
        path = f"scenarios[{index}]"
        scenario = check.obj(item, path)
        if scenario is None:
            continue
        scenario_id = check.text(scenario, "id", path)
        capability_id = check.text(scenario, "capabilityId", path)
        check.text(scenario, "title", path)
        check.string_array(scenario.get("steps"), f"{path}.steps", nonempty=True)
        check.string_array(scenario.get("assertions"), f"{path}.assertions", nonempty=True)
        if scenario_id:
            if scenario_id in ids:
                check.error(f"{path}.id", f"duplicate scenario id: {scenario_id}")
            ids.add(scenario_id)
        if capability_id and capability_id not in capability_ids:
            check.error(f"{path}.capabilityId", f"references unknown capability {capability_id}")
        for field in ("visual", "accessibility"):
            if field in scenario and not isinstance(scenario[field], bool):
                check.error(f"{path}.{field}", "must be a boolean")
    return ids


def validate_verification(check: Check, value: Any, root: dict[str, Any], viewport_count: int) -> None:
    verification = check.obj(value, "verification")
    if verification is None:
        return
    commands = check.array(verification.get("commands"), "verification.commands", nonempty=True)
    if commands is not None:
        names: set[str] = set()
        for index, item in enumerate(commands):
            path = f"verification.commands[{index}]"
            command = check.obj(item, path)
            if command is None:
                continue
            name = check.text(command, "name", path)
            check.text(command, "cwd", path)
            check.text(command, "command", path)
            if name:
                if name in names:
                    check.warning(f"{path}.name", f"duplicate command name: {name}")
                names.add(name)

    visual = check.obj(verification.get("visual", {}), "verification.visual")
    if visual is not None:
        required = visual.get("required")
        if not isinstance(required, bool):
            check.error("verification.visual.required", "must be a boolean")
        elif required:
            if viewport_count == 0:
                check.error("viewports", "visual verification requires at least one viewport")
            check.text(visual, "baselineDocument", "verification.visual")
            check.text(visual, "browser", "verification.visual")
        elif root.get("redesignPolicy") == "parity":
            check.warning(
                "verification.visual.required",
                "parity policy normally requires visual verification for user-facing pages",
            )

    accessibility = check.obj(
        verification.get("accessibility", {}), "verification.accessibility"
    )
    if accessibility is not None:
        required = accessibility.get("required")
        if not isinstance(required, bool):
            check.error("verification.accessibility.required", "must be a boolean")
        elif required:
            automated = accessibility.get("automated")
            manual = accessibility.get("manual")
            has_automated = isinstance(automated, str) and bool(automated.strip())
            has_manual = isinstance(manual, list) and bool(manual)
            if not has_automated and not has_manual:
                check.error(
                    "verification.accessibility",
                    "required accessibility verification needs automated or manual checks",
                )


def validate_differences(check: Check, value: Any) -> None:
    differences = check.array(value, "approvedDifferences")
    ids: set[str] = set()
    if differences is None:
        return
    for index, item in enumerate(differences):
        path = f"approvedDifferences[{index}]"
        difference = check.obj(item, path)
        if difference is None:
            continue
        difference_id = check.text(difference, "id", path)
        check.text(difference, "decision", path)
        check.text(difference, "approvedBy", path)
        if difference_id:
            if difference_id in ids:
                check.error(f"{path}.id", f"duplicate difference id: {difference_id}")
            ids.add(difference_id)


def validate_unknowns(check: Check, value: Any) -> None:
    unknowns = check.array(value, "unknowns")
    ids: set[str] = set()
    if unknowns is None:
        return
    for index, item in enumerate(unknowns):
        path = f"unknowns[{index}]"
        unknown = check.obj(item, path)
        if unknown is None:
            continue
        unknown_id = check.text(unknown, "id", path)
        check.text(unknown, "question", path)
        check.text(unknown, "impact", path)
        check.text(unknown, "owner", path)
        check.enum(unknown.get("status"), "unknownStatus", f"{path}.status")
        if unknown_id:
            if unknown_id in ids:
                check.error(f"{path}.id", f"duplicate unknown id: {unknown_id}")
            ids.add(unknown_id)


def validate_rollout(check: Check, value: Any, tier: str | None) -> None:
    if value is None:
        if tier == "program":
            check.error("rollout", "program tier requires rollout and rollback details")
        return
    rollout = check.obj(value, "rollout")
    if rollout is None:
        return
    check.enum(rollout.get("strategy"), "rolloutStrategy", "rollout.strategy")
    check.text(rollout, "rollback", "rollout")
    monitoring = check.string_array(rollout.get("monitoring", []), "rollout.monitoring")
    check.string_array(
        rollout.get("cleanupConditions"), "rollout.cleanupConditions", nonempty=True
    )
    if monitoring is not None and not monitoring:
        check.warning("rollout.monitoring", "no rollout monitoring signals are recorded")


def validate_manifest(data: Any) -> list[Issue]:
    check = Check()
    root = check.obj(data, "$manifest")
    if root is None:
        return check.issues

    required = {
        "schemaVersion",
        "migrationId",
        "title",
        "status",
        "tier",
        "modes",
        "redesignPolicy",
        "source",
        "target",
        "scope",
        "capabilities",
        "verification",
    }
    for key in sorted(required - root.keys()):
        check.error(key, "required field is missing")

    check.text(root, "schemaVersion", "")
    check.text(root, "migrationId", "")
    check.text(root, "title", "")
    check.enum(root.get("status"), "status", "status")
    tier = check.enum(root.get("tier"), "tier", "tier")
    check.enum(root.get("redesignPolicy"), "redesignPolicy", "redesignPolicy")

    modes = check.string_array(root.get("modes"), "modes", nonempty=True)
    if modes is not None:
        seen: set[str] = set()
        for index, mode in enumerate(modes):
            if mode not in ENUMS["mode"]:
                check.error(f"modes[{index}]", f"unknown mode: {mode}")
            if mode in seen:
                check.warning(f"modes[{index}]", f"duplicate mode: {mode}")
            seen.add(mode)

    validate_endpoint(check, root.get("source"), "source")
    validate_endpoint(check, root.get("target"), "target", target=True)
    validate_scope(check, root.get("scope"))
    capability_ids = validate_capabilities(check, root.get("capabilities"))
    _, route_scenario_refs = validate_routes(check, root.get("routes", []))
    viewport_count = validate_viewports(check, root.get("viewports", []))
    check.string_array(root.get("states", []), "states")
    scenario_ids = validate_scenarios(check, root.get("scenarios", []), capability_ids)
    for path, scenario_id in route_scenario_refs:
        if scenario_id not in scenario_ids:
            check.error(path, f"references unknown scenario {scenario_id}")
    validate_verification(check, root.get("verification"), root, viewport_count)
    validate_differences(check, root.get("approvedDifferences", []))
    validate_unknowns(check, root.get("unknowns", []))
    validate_rollout(check, root.get("rollout"), tier)
    return check.issues


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Validate a frontend migration manifest JSON file.")
    parser.add_argument("manifest", type=Path, help="Path to manifest.json")
    parser.add_argument("--strict", action="store_true", help="Treat warnings as failure")
    parser.add_argument(
        "--format",
        choices=("text", "json"),
        default="text",
        help="Validation output format (default: text)",
    )
    return parser.parse_args()


def load_manifest(path: Path) -> Any:
    try:
        raw = path.read_text(encoding="utf-8")
    except OSError as exc:
        raise ValueError(f"cannot read {path}: {exc}") from exc
    try:
        return json.loads(raw)
    except json.JSONDecodeError as exc:
        raise ValueError(
            f"invalid JSON at line {exc.lineno}, column {exc.colno}: {exc.msg}"
        ) from exc


def main() -> int:
    args = parse_args()
    try:
        data = load_manifest(args.manifest)
    except ValueError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    issues = validate_manifest(data)
    errors = [issue for issue in issues if issue.level == "error"]
    warnings = [issue for issue in issues if issue.level == "warning"]

    if args.format == "json":
        print(
            json.dumps(
                {
                    "valid": not errors and not (args.strict and warnings),
                    "errorCount": len(errors),
                    "warningCount": len(warnings),
                    "issues": [asdict(issue) for issue in issues],
                },
                ensure_ascii=False,
                indent=2,
            )
        )
    else:
        for issue in issues:
            marker = "ERROR" if issue.level == "error" else "WARN"
            print(f"{marker} {issue.path}: {issue.message}")
        if not issues:
            print("OK: migration manifest is valid")
        else:
            print(f"Summary: {len(errors)} error(s), {len(warnings)} warning(s)")

    return 1 if errors or (args.strict and warnings) else 0


if __name__ == "__main__":
    raise SystemExit(main())
