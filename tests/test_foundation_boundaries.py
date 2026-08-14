import ast
import re
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def python_files(folder: str):
    return tuple((ROOT / folder).rglob("*.py"))


def imported_modules(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    modules = {
        alias.name
        for node in ast.walk(tree)
        if isinstance(node, ast.Import)
        for alias in node.names
    }
    for node in ast.walk(tree):
        if not isinstance(node, ast.ImportFrom):
            continue
        module = node.module or ""
        modules.add(module)
        modules.update(f"{module}.{alias.name}" for alias in node.names if module and alias.name != "*")
    return modules


def page_module_root(module: str) -> str | None:
    for prefix in ("overlord.presentation.pages.", "overlord.ui.pages."):
        if module.startswith(prefix):
            return f"{prefix}{module.removeprefix(prefix).partition('.')[0]}"
    return None


class FoundationBoundaryTests(unittest.TestCase):
    def test_page_modules_do_not_import_other_page_modules(self):
        page_files = (
            *python_files("overlord/presentation/pages"),
            *python_files("overlord/ui/pages"),
        )
        for path in page_files:
            if path.name == "__init__.py":
                continue
            relative = path.relative_to(ROOT).with_suffix("")
            current_root = ".".join(relative.parts[:4])
            imported_roots = {
                root
                for module in imported_modules(path)
                if (root := page_module_root(module)) is not None
            }
            violations = sorted(root for root in imported_roots if root != current_root)
            self.assertFalse(violations, f"{path} imports another page: {violations}")

    def test_shared_task_ui_does_not_import_pages_or_infrastructure(self):
        path = ROOT / "overlord/ui/components/tasks.py"
        forbidden = (
            "overlord.presentation",
            "overlord.infrastructure",
            "overlord.ui.pages",
            "sqlite3",
        )
        violations = sorted(
            module
            for module in imported_modules(path)
            if any(module == prefix or module.startswith(f"{prefix}.") for prefix in forbidden)
        )
        self.assertFalse(violations, f"{path} imports a forbidden shared-UI dependency: {violations}")

    def test_canonical_runtime_does_not_import_retired_canonical_pages(self):
        retired_root = "overlord.presentation.pages"
        active_files = (
            ROOT / "main.py",
            *python_files("overlord"),
            *python_files("tests"),
            *python_files("scripts"),
        )
        for path in active_files:
            violations = {
                module
                for module in imported_modules(path)
                if module == retired_root or module.startswith(f"{retired_root}.")
            }
            self.assertFalse(violations, path)

        self.assertFalse((ROOT / "overlord/presentation/pages").exists())
        self.assertFalse((ROOT / "overlord/presentation/pages/dashboard.py").exists())
        self.assertFalse((ROOT / "overlord/presentation/pages/daily_planning.py").exists())
        self.assertFalse((ROOT / "overlord/presentation/pages/tasks.py").exists())
        self.assertFalse((ROOT / "overlord/presentation/pages/projects.py").exists())
        self.assertFalse((ROOT / "overlord/presentation/pages/cycles.py").exists())
        self.assertTrue((ROOT / "overlord/ui/pages/dashboard/page.py").exists())
        self.assertFalse((ROOT / "overlord/ui/pages/planning/page.py").exists())
        self.assertTrue((ROOT / "overlord/ui/pages/tasks/page.py").exists())
        self.assertTrue((ROOT / "overlord/ui/pages/projects/page.py").exists())
        self.assertTrue((ROOT / "overlord/ui/pages/settings/page.py").exists())
        self.assertTrue((ROOT / "overlord/ui/pages/cycles/page.py").exists())

    def test_presentation_namespace_is_retired_and_overlord_app_is_canonical(self):
        runtime_files = (
            ROOT / "main.py",
            *python_files("overlord"),
            *python_files("tests"),
            *python_files("scripts"),
        )
        for path in runtime_files:
            violations = {
                module
                for module in imported_modules(path)
                if module == "overlord.presentation" or module.startswith("overlord.presentation.")
            }
            self.assertFalse(violations, path)

        self.assertFalse((ROOT / "overlord/presentation").exists())
        self.assertTrue((ROOT / "overlord/ui/app.py").exists())
        app_definitions = [
            path.relative_to(ROOT).as_posix()
            for path in python_files("overlord")
            if any(
                isinstance(node, ast.ClassDef) and node.name == "OverlordApp"
                for node in ast.walk(ast.parse(path.read_text(encoding="utf-8")))
            )
        ]
        self.assertEqual(["overlord/ui/app.py"], app_definitions)
        self.assertIn("overlord.ui.app", imported_modules(ROOT / "main.py"))

    def test_canonical_pages_do_not_import_presentation_or_infrastructure(self):
        forbidden = ("overlord.presentation", "overlord.infrastructure")
        for path in python_files("overlord/ui/pages"):
            violations = sorted(
                module
                for module in imported_modules(path)
                if any(module == prefix or module.startswith(f"{prefix}.") for prefix in forbidden)
            )
            self.assertFalse(violations, f"{path} imports a forbidden page dependency: {violations}")

    def test_recovery_ui_does_not_import_orchestration_or_business_layers(self):
        path = ROOT / "overlord/ui/recovery.py"
        forbidden = (
            "overlord.presentation",
            "overlord.application",
            "overlord.infrastructure",
            "overlord.domain",
        )
        violations = sorted(
            module
            for module in imported_modules(path)
            if any(module == prefix or module.startswith(f"{prefix}.") for prefix in forbidden)
        )
        self.assertFalse(violations, f"{path} imports orchestration or business layers: {violations}")

    def test_app_shell_does_not_import_orchestration_or_business_layers(self):
        path = ROOT / "overlord/ui/shell/app_shell.py"
        forbidden = (
            "overlord.presentation",
            "overlord.application",
            "overlord.infrastructure",
            "overlord.domain",
        )
        violations = sorted(
            module
            for module in imported_modules(path)
            if any(module == prefix or module.startswith(f"{prefix}.") for prefix in forbidden)
        )
        self.assertFalse(violations, f"{path} imports orchestration or business layers: {violations}")

    def test_canonical_runtime_does_not_import_retired_ui_support_paths(self):
        retired_modules = {
            "overlord.presentation.navigation",
            "overlord.presentation.state",
            "overlord.presentation.strings",
        }
        runtime_files = (ROOT / "main.py", *python_files("overlord"))

        for path in runtime_files:
            violations = retired_modules & imported_modules(path)
            self.assertFalse(violations, f"{path} imports retired UI support: {sorted(violations)}")

        for name in ("navigation.py", "state.py", "strings.py"):
            self.assertFalse((ROOT / "overlord/presentation" / name).exists())

    def test_ui_foundation_does_not_import_presentation(self):
        for path in python_files("overlord/ui"):
            violations = sorted(
                module
                for module in imported_modules(path)
                if module == "overlord.presentation" or module.startswith("overlord.presentation.")
            )
            self.assertFalse(violations, f"{path} imports Presentation: {violations}")

    def test_canonical_runtime_does_not_import_retired_shared_component_path(self):
        retired_path = "overlord.presentation.components"
        runtime_files = (ROOT / "main.py", *python_files("overlord"))

        for path in runtime_files:
            self.assertNotIn(retired_path, path.read_text(encoding="utf-8"), path)

        self.assertFalse((ROOT / "overlord/presentation/components").exists())
        self.assertTrue((ROOT / "overlord/ui/components").is_dir())

    def test_canonical_runtime_does_not_import_retired_design_system_path(self):
        retired_path = "overlord.presentation.design_system"
        runtime_files = (ROOT / "main.py", *python_files("overlord"))

        for path in runtime_files:
            self.assertNotIn(retired_path, path.read_text(encoding="utf-8"), path)

        self.assertFalse((ROOT / "overlord/presentation/design_system").exists())

    def test_canonical_runtime_does_not_import_retired_architecture(self):
        retired_packages = {"core", "services", "storage"}
        runtime_files = (ROOT / "main.py", *python_files("overlord"))

        for path in runtime_files:
            tree = ast.parse(path.read_text(encoding="utf-8"))
            imported_modules = [
                alias.name
                for node in ast.walk(tree)
                if isinstance(node, ast.Import)
                for alias in node.names
            ]
            imported_modules.extend(
                node.module or ""
                for node in ast.walk(tree)
                if isinstance(node, ast.ImportFrom)
            )
            imported_roots = {module.partition(".")[0] for module in imported_modules}

            self.assertTrue(
                retired_packages.isdisjoint(imported_roots),
                f"{path} imports retired architecture: {sorted(retired_packages & imported_roots)}",
            )

    def test_feature_applications_have_one_canonical_module(self):
        canonical_by_class = {
            "TaskApplication": ROOT / "overlord/modules/tasks/application.py",
            "ProjectApplication": ROOT / "overlord/modules/projects/application.py",
            "CycleApplication": ROOT / "overlord/modules/cycles/application.py",
            "SettingsApplication": ROOT / "overlord/modules/settings/application.py",
        }
        retired_modules = {
            "overlord.application.tasks",
            "overlord.application.projects",
            "overlord.application.daily_planning",
            "overlord.application.cycles",
            "overlord.application.settings",
        }
        retired_files = {
            ROOT / f"{module.replace('.', '/')}.py"
            for module in retired_modules
        }

        self.assertTrue(all(not path.exists() for path in retired_files))
        self.assertTrue(all(path.is_file() for path in canonical_by_class.values()))

        implementations: dict[str, list[Path]] = {name: [] for name in canonical_by_class}
        runtime_files = (ROOT / "main.py", *python_files("overlord"), *python_files("scripts"))
        for path in runtime_files:
            tree = ast.parse(path.read_text(encoding="utf-8"))
            for node in ast.walk(tree):
                if isinstance(node, ast.ClassDef) and node.name in implementations:
                    implementations[node.name].append(path)
                if not isinstance(node, ast.ImportFrom):
                    continue
                self.assertNotIn(node.module, retired_modules, path)
                if path.parent == ROOT / "overlord/application":
                    self.assertFalse(
                        node.level == 1
                        and f"overlord.application.{node.module}" in retired_modules,
                        path,
                    )

        for class_name, canonical in canonical_by_class.items():
            self.assertEqual([canonical], implementations[class_name])

    def test_business_modules_do_not_import_flet_or_infrastructure(self):
        forbidden = ("flet", "overlord.infrastructure")
        for path in python_files("overlord/modules"):
            violations = sorted(
                module
                for module in imported_modules(path)
                if any(module == prefix or module.startswith(f"{prefix}.") for prefix in forbidden)
            )
            self.assertFalse(violations, f"{path} imports a forbidden dependency: {violations}")

    def test_stage6_business_ownership_and_retired_paths_are_canonical(self):
        expected = {
            "tasks": ("domain.py", "application.py", "read_models.py", "repository.py"),
            "projects": ("domain.py", "application.py", "read_models.py", "repository.py"),
            "blockers": ("domain.py", "repository.py"),
            "cycles": ("domain.py", "application.py", "read_models.py", "repository.py"),
            "settings": ("domain.py", "application.py", "repository.py"),
            "dashboard": ("application.py", "read_models.py", "repository.py"),
        }
        for module, names in expected.items():
            for name in names:
                self.assertTrue((ROOT / "overlord/modules" / module / name).is_file())

        retired_modules = ("overlord.application", "overlord.domain")
        runtime_files = (ROOT / "main.py", *python_files("overlord"), *python_files("scripts"))
        for path in runtime_files:
            violations = sorted(
                module
                for module in imported_modules(path)
                if any(module == prefix or module.startswith(f"{prefix}.") for prefix in retired_modules)
            )
            self.assertFalse(violations, f"{path} imports a retired path: {violations}")

        self.assertFalse((ROOT / "overlord/application/common.py").exists())
        self.assertFalse((ROOT / "overlord/application/dashboard.py").exists())
        self.assertFalse((ROOT / "overlord/infrastructure/sqlite/repositories.py").exists())
        self.assertFalse(any((ROOT / "overlord/domain").glob("*.py")))

    def test_sqlite_repositories_never_own_transactions(self):
        for path in python_files("overlord/infrastructure/sqlite/repositories"):
            tree = ast.parse(path.read_text(encoding="utf-8"))
            transaction_calls = [
                node
                for node in ast.walk(tree)
                if isinstance(node, ast.Call)
                and isinstance(node.func, ast.Attribute)
                and node.func.attr in {"commit", "rollback"}
            ]
            self.assertFalse(transaction_calls, f"{path} owns transaction completion")

    def test_ui_app_does_not_import_sqlite_or_concrete_repositories(self):
        path = ROOT / "overlord/ui/app.py"
        source = path.read_text(encoding="utf-8")
        self.assertNotIn("import sqlite3", source, path)
        self.assertNotIn("infrastructure.sqlite.repositories", source, path)
        self.assertNotIn("overlord.bootstrap", source, path)

    def test_interface_does_not_use_non_lucide_icon_sets(self):
        for path in (*python_files("overlord/presentation"), *python_files("overlord/ui")):
            source = path.read_text(encoding="utf-8")
            self.assertNotIn("ft.Icons", source, path)
            self.assertNotIn("ft.CupertinoIcons", source, path)
            self.assertNotIn("FontAwesome", source, path)

    def test_raw_hex_colors_are_centralized(self):
        for path in (*python_files("overlord/presentation"), *python_files("overlord/ui")):
            if path.name == "tokens.py":
                continue
            matches = re.findall(r"#[0-9A-Fa-f]{6}", path.read_text(encoding="utf-8"))
            self.assertEqual([], matches, path)

    def test_main_uses_current_flet_runner(self):
        source = (ROOT / "main.py").read_text(encoding="utf-8")
        self.assertIn("ft.run", source)
        self.assertNotIn("ft.app", source)


if __name__ == "__main__":
    unittest.main()
