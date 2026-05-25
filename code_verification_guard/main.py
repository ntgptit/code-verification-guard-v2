"""Command-line interface for code-verification-guard."""

from __future__ import annotations

import typer

from code_verification_guard.application.guard_application import GuardApplication
from code_verification_guard.constants.defaults import Defaults

app = typer.Typer(
    help="Code Verification Guard CLI",
    no_args_is_help=True,
)


@app.callback()
def main() -> None:
    """
    Code Verification Guard command group.
    """
    return


@app.command(name="check")
def check_command(
    project: str = typer.Option(Defaults.PROJECT_PATH, help="Target project path"),
    config: str = typer.Option(Defaults.CONFIG_FILE_NAME, help="Project config file name"),
    ruleset: str | None = typer.Option(None, help="Ruleset bundle name, for example: memox"),
    profile: str | None = typer.Option(None, help="Ruleset profile override"),
) -> None:
    """Run configured rules against a project."""
    if not ruleset:
        raise typer.BadParameter(
            "--ruleset is required. Example: check --project . --ruleset memox"
        )

    should_fail = GuardApplication().run(project, config, ruleset, profile)

    # Return a failing process status only for configured severities.
    if should_fail:
        raise typer.Exit(code=1)


# Run the Typer app when invoked as a module.
if __name__ == "__main__":
    app()
