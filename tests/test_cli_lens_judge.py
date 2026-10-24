from typer.testing import CliRunner

from colx.cli import app

runner = CliRunner()


def test_lens_judge_help_lists_commands() -> None:
    result = runner.invoke(app, ["lens-judge", "--help"])
    assert result.exit_code == 0
    assert "labels" in result.output


def test_joint_help_lists_commands() -> None:
    result = runner.invoke(app, ["lens-judge", "joint", "--help"])
    assert result.exit_code == 0
    assert all(c in result.output for c in ("prompts", "judge", "analyse", "pair-scores"))
