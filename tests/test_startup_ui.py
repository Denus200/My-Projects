import ast
import unittest
from pathlib import Path


class StartupUiTests(unittest.TestCase):
    def test_main_does_not_mount_file_picker_on_startup(self):
        main_source = Path("main.py").read_text(encoding="utf-8")
        tree = ast.parse(main_source)

        attribute_names = [
            node.attr
            for node in ast.walk(tree)
            if isinstance(node, ast.Attribute)
        ]

        self.assertNotIn("FilePicker", attribute_names)


if __name__ == "__main__":
    unittest.main()
