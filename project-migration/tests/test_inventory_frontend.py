from __future__ import annotations

import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Cannot load {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


inventory_module = load_module(
    "inventory_frontend", ROOT / "scripts" / "inventory_frontend.py"
)
compare_module = load_module(
    "compare_frontend_inventory", ROOT / "scripts" / "compare_frontend_inventory.py"
)


class FrontendInventoryTests(unittest.TestCase):
    def create_project(self, root: Path) -> None:
        (root / "src" / "router").mkdir(parents=True)
        (root / "src" / "pages").mkdir(parents=True)
        (root / "pnpm-lock.yaml").write_text("lockfileVersion: '9.0'\n", encoding="utf-8")
        (root / "vite.config.ts").write_text(
            "import { defineConfig } from 'vite'\nexport default defineConfig({})\n",
            encoding="utf-8",
        )
        (root / "package.json").write_text(
            json.dumps(
                {
                    "name": "sample-app",
                    "packageManager": "pnpm@9.12.0",
                    "scripts": {
                        "dev": "vite",
                        "build": "vite build",
                        "test": "vitest run",
                    },
                    "dependencies": {
                        "vue": "^3.5.0",
                        "vue-router": "^4.4.0",
                        "pinia": "^2.2.0",
                    },
                    "devDependencies": {
                        "vite": "^6.0.0",
                        "vitest": "^3.0.0",
                        "typescript": "^5.7.0",
                    },
                }
            ),
            encoding="utf-8",
        )
        (root / "src" / "main.ts").write_text(
            "import { createApp } from 'vue'\n",
            encoding="utf-8",
        )
        (root / "src" / "router" / "index.ts").write_text(
            """
const routes = [
  { path: '/orders/:id', component: OrderPage },
]
const showCancel = featureFlags.isFeatureEnabled('cancel-order')
const canCancel = hasPermission('order.cancel')
""".strip()
            + "\n",
            encoding="utf-8",
        )
        (root / "src" / "pages" / "OrderPage.vue").write_text(
            """
<template><button :disabled="!canCancel">Cancel</button></template>
<script setup lang="ts">
/** @deprecated old refund entry */
</script>
""".strip()
            + "\n",
            encoding="utf-8",
        )

    def test_inventory_detects_stack_routes_and_signals(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            self.create_project(root)
            result = inventory_module.analyze_project(root)

            self.assertEqual(result["package_manager"]["primary"], "pnpm")
            self.assertIn("src/main.ts", result["entry_candidates"])
            self.assertIn("vite.config.ts", result["configs"])

            frameworks = {item["name"] for item in result["stack"]["frameworks"]}
            routers = {item["name"] for item in result["stack"]["routers"]}
            state = {item["name"] for item in result["stack"]["state"]}
            testing = {item["name"] for item in result["stack"]["testing"]}
            self.assertIn("Vue", frameworks)
            self.assertIn("Vue Router", routers)
            self.assertIn("Pinia", state)
            self.assertIn("Vitest", testing)

            routes = {item["value"] for item in result["route_candidates"]}
            self.assertIn("/orders/:id", routes)
            self.assertGreaterEqual(len(result["lifecycle_signals"]["feature_flags"]), 1)
            self.assertGreaterEqual(len(result["lifecycle_signals"]["permissions"]), 1)
            self.assertGreaterEqual(len(result["lifecycle_signals"]["hidden_disabled"]), 1)
            self.assertGreaterEqual(len(result["lifecycle_signals"]["deprecated_legacy"]), 1)

    def test_inventory_is_json_serializable_and_stable(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            self.create_project(root)
            first = inventory_module.analyze_project(root)
            second = inventory_module.analyze_project(root)
            self.assertEqual(
                json.dumps(first, ensure_ascii=False, sort_keys=True),
                json.dumps(second, ensure_ascii=False, sort_keys=True),
            )

    def test_ignored_directories_are_not_scanned(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            self.create_project(root)
            ignored = root / "node_modules" / "fake-package"
            ignored.mkdir(parents=True)
            (ignored / "package.json").write_text(
                json.dumps({"dependencies": {"react": "latest"}}), encoding="utf-8"
            )
            (ignored / "routes.ts").write_text(
                "const route = { path: '/should-not-exist' }\n", encoding="utf-8"
            )

            result = inventory_module.analyze_project(root)
            frameworks = {item["name"] for item in result["stack"]["frameworks"]}
            routes = {item["value"] for item in result["route_candidates"]}
            self.assertNotIn("React", frameworks)
            self.assertNotIn("/should-not-exist", routes)

    def test_compare_reports_package_and_route_changes(self) -> None:
        with tempfile.TemporaryDirectory() as before_dir, tempfile.TemporaryDirectory() as after_dir:
            before_root = Path(before_dir)
            after_root = Path(after_dir)
            self.create_project(before_root)
            self.create_project(after_root)

            package_path = after_root / "package.json"
            package_data = json.loads(package_path.read_text(encoding="utf-8"))
            package_data["dependencies"].pop("vue")
            package_data["dependencies"]["react"] = "^19.0.0"
            package_path.write_text(json.dumps(package_data), encoding="utf-8")
            (after_root / "src" / "router" / "index.ts").write_text(
                "const routes = [{ path: '/orders/:id' }, { path: '/orders' }]\n",
                encoding="utf-8",
            )

            before = inventory_module.analyze_project(before_root)
            after = inventory_module.analyze_project(after_root)
            comparison = compare_module.compare_inventories(before, after)

            self.assertTrue(comparison["has_differences"])
            self.assertIn("stack", comparison["differences"])
            self.assertIn("packages", comparison["differences"])
            self.assertIn("route_candidates", comparison["differences"])


if __name__ == "__main__":
    unittest.main()
