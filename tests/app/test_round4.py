import ast

from colx.app import APP_FILE


def test_app_file_defines_a_marimo_app() -> None:
    tree = ast.parse(APP_FILE.read_text())
    names = {t.id for node in tree.body if isinstance(node, ast.Assign) for t in node.targets}
    assert "app" in names
