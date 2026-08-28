from __future__ import annotations

import copy
import json
import sys
import tempfile
import unittest
from pathlib import Path


SCRIPTS_DIR = Path(__file__).resolve().parents[1]
SKILL_DIR = SCRIPTS_DIR.parent
sys.path.insert(0, str(SCRIPTS_DIR))

from inspect_frontend_project import inspect_project  # noqa: E402
from validate_migration_manifest import validate_manifest  # noqa: E402


class InspectFrontendProjectTests(unittest.TestCase):
    def test_detects_stack_and_package_manager(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            package_json = {
                "name": "fixture-app",
                "private": True,
                "packageManager": "pnpm@10.0.0",
                "scripts": {
                    "dev": "vite",
                    "build": "vite build",
                    "test:e2e": "playwright test",
                },
                "dependencies": {
                    "react": "^19.0.0",
                    "react-dom": "^19.0.0",
                    "react-router-dom": "^7.0.0",
                    "zustand": "^5.0.0",
                },
                "devDependencies": {
                    "vite": "^7.0.0",
                    "typescript": "^5.0.0",
                    "@playwright/test": "^1.0.0",
                },
            }
            (root / "package.json").write_text(
                json.dumps(package_json), encoding="utf-8"
            )
            (root / "pnpm-lock.yaml").write_text("lockfileVersion: '9.0'\n", encoding="utf-8")
            (root / "vite.config.ts").write_text("export default {}\n", encoding="utf-8")
            (root / "tsconfig.json").write_text("{}\n", encoding="utf-8")
            (root / "src").mkdir()

            result = inspect_project(root)

            self.assertEqual(result["packageManager"]["selected"], "pnpm")
            self.assertEqual(result["packageManager"]["version"], "10.0.0")
            self.assertTrue(
                any(item["name"] == "React" for item in result["detected"]["frameworks"])
            )
            self.assertTrue(
                any(item["name"] == "Vite" for item in result["detected"]["bundlers"])
            )
            self.assertTrue(
                any(item["name"] == "Playwright" for item in result["detected"]["testing"])
            )
            self.assertIn("vite.config.ts", result["configFiles"])
            self.assertNotIn("No build script was found in package.json.", result["warnings"])

    def test_warns_on_multiple_lockfiles(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            (root / "package.json").write_text(
                json.dumps(
                    {
                        "name": "fixture-app",
                        "scripts": {"dev": "vite", "build": "vite build"},
                        "dependencies": {"vue": "^3.0.0"},
                        "devDependencies": {"vite": "^7.0.0"},
                    }
                ),
                encoding="utf-8",
            )
            (root / "pnpm-lock.yaml").write_text("", encoding="utf-8")
            (root / "package-lock.json").write_text("{}", encoding="utf-8")

            result = inspect_project(root)

            self.assertTrue(
                any("Multiple package-manager lockfiles" in warning for warning in result["warnings"])
            )


class ManifestValidatorTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        template_path = SKILL_DIR / "templates" / "00-前端迁移清单.json"
        cls.valid_manifest = json.loads(template_path.read_text(encoding="utf-8"))

    def test_template_is_valid(self) -> None:
        issues = validate_manifest(copy.deepcopy(self.valid_manifest))
        self.assertEqual([], issues)

    def test_duplicate_capability_id_is_error(self) -> None:
        manifest = copy.deepcopy(self.valid_manifest)
        duplicate = copy.deepcopy(manifest["capabilities"][0])
        manifest["capabilities"].append(duplicate)

        issues = validate_manifest(manifest)

        self.assertTrue(
            any(
                issue.level == "error" and "duplicate capability id" in issue.message
                for issue in issues
            )
        )

    def test_program_requires_rollout(self) -> None:
        manifest = copy.deepcopy(self.valid_manifest)
        manifest["tier"] = "program"
        manifest.pop("rollout", None)

        issues = validate_manifest(manifest)

        self.assertTrue(
            any(issue.level == "error" and issue.path == "rollout" for issue in issues)
        )

    def test_route_reference_to_unknown_scenario_is_error(self) -> None:
        manifest = copy.deepcopy(self.valid_manifest)
        manifest["routes"][0]["acceptanceScenarioIds"].append("SCN-DOES-NOT-EXIST")

        issues = validate_manifest(manifest)

        self.assertTrue(
            any(
                issue.level == "error"
                and issue.path.startswith("routes[0].acceptanceScenarioIds")
                and "unknown scenario" in issue.message
                for issue in issues
            )
        )

    def test_removed_capability_restore_requires_approval(self) -> None:
        manifest = copy.deepcopy(self.valid_manifest)
        capability = manifest["capabilities"][1]
        capability["targetDisposition"] = "migrate"
        capability["targetLocation"] = "src/features/legacy-export"
        capability["approval"] = ""

        issues = validate_manifest(manifest)

        self.assertTrue(
            any(
                issue.level == "error" and "restoring a deprecated or removed" in issue.message
                for issue in issues
            )
        )


if __name__ == "__main__":
    unittest.main()
