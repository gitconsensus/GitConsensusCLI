from click.testing import CliRunner
from gitconsensus.gitconsensus import cli

def test_cli_command():
    runner = CliRunner()
    result = runner.invoke(cli, ["get-repository"])
    assert result.exit_code == 2

