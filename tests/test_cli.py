import re

from typer.testing import CliRunner

from code_verification_guard import main

_ANSI_ESCAPE = re.compile(r"\x1b\[[0-9;]*m")


def _plain(text: str) -> str:
    """Strip ANSI styling so an assertion reads text rather than colour.

    Typer renders a `BadParameter` through rich, which highlights option-like
    tokens *inside* the message -- so `--ruleset is required` arrives split by
    escape codes wherever the terminal reports colour support. A developer
    machine usually reports none and the raw substring matches; a CI runner
    reports colour and it does not, which is why this only ever failed until
    the suite started running in CI.
    """
    return _ANSI_ESCAPE.sub("", text)


def test_check_command_requires_ruleset(tmp_path):
    runner = CliRunner()

    result = runner.invoke(main.app, ["check", "--project", str(tmp_path)])

    assert result.exit_code != 0
    assert "--ruleset is required" in _plain(result.output)


def test_check_command_passes_project_ruleset_and_profile(monkeypatch, tmp_path):
    runner = CliRunner()
    calls = []

    class FakeApplication:
        def run(self, project, config, ruleset, profile, debug):
            calls.append(
                {
                    "project": project,
                    "config": config,
                    "ruleset": ruleset,
                    "profile": profile,
                    "debug": debug,
                }
            )
            return False

    monkeypatch.setattr(main, "GuardApplication", FakeApplication)

    result = runner.invoke(
        main.app,
        [
            "check",
            "--project",
            str(tmp_path),
            "--ruleset",
            "memox",
            "--profile",
            "local",
            "--debug",
        ],
    )

    assert result.exit_code == 0
    assert calls == [
        {
            "project": str(tmp_path),
            "config": "code-verification-guard.yaml",
            "ruleset": "memox",
            "profile": "local",
            "debug": True,
        }
    ]


def test_check_command_defaults_debug_to_false(monkeypatch, tmp_path):
    runner = CliRunner()
    calls = []

    class FakeApplication:
        def run(self, project, config, ruleset, profile, debug):
            calls.append(debug)
            return False

    monkeypatch.setattr(main, "GuardApplication", FakeApplication)

    result = runner.invoke(
        main.app,
        [
            "check",
            "--project",
            str(tmp_path),
            "--ruleset",
            "memox",
        ],
    )

    assert result.exit_code == 0
    assert calls == [False]
