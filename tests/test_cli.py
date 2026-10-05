from typer.testing import CliRunner

from colx import __version__
from colx.cli import app

runner = CliRunner()


def test_version_is_set() -> None:
    assert __version__


def test_info_runs() -> None:
    result = runner.invoke(app, ["info"])
    assert result.exit_code == 0
    assert "colx" in result.output
