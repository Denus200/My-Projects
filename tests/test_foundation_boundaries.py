import ast
import re
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def python_files(folder: str):
    return tuple((ROOT / folder).rglob("*.py"))


class FoundationBoundaryTests(unittest.TestCase):
    def test_domain_does_not_import_flet(self):
        for path in python_files("overlord/domain"):
            tree = ast.parse(path.read_text(encoding="utf-8"))
            imports = [node for node in ast.walk(tree) if isinstance(node, (ast.Import, ast.ImportFrom))]
            self.assertFalse(any(
                (isinstance(node, ast.Import) and any(alias.name.startswith("flet") for alias in node.names))
                or (isinstance(node, ast.ImportFrom) and (node.module or "").startswith("flet"))
                for node in imports
            ), path)

    def test_presentation_does_not_import_sqlite_or_concrete_repositories(self):
        for path in python_files("overlord/presentation"):
            source = path.read_text(encoding="utf-8")
            self.assertNotIn("import sqlite3", source, path)
            self.assertNotIn("infrastructure.sqlite.repositories", source, path)
            self.assertNotIn("overlord.bootstrap", source, path)

    def test_interface_does_not_use_non_lucide_icon_sets(self):
        for path in python_files("overlord/presentation"):
            source = path.read_text(encoding="utf-8")
            self.assertNotIn("ft.Icons", source, path)
            self.assertNotIn("ft.CupertinoIcons", source, path)
            self.assertNotIn("FontAwesome", source, path)

    def test_raw_hex_colors_are_centralized(self):
        for path in python_files("overlord/presentation"):
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
