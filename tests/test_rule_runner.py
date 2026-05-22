from pathlib import Path

from code_verification_guard.constants.config_keys import ConfigKeys
from code_verification_guard.registry.rule_registry import RuleRegistry
from code_verification_guard.runner.rule_runner import RuleRunner


def test_rule_runner_reads_rules_from_rule_registry(tmp_path: Path):
    source = tmp_path / "main.py"
    source.write_text("print('hello')\n", encoding="utf-8")
    registry = RuleRegistry()
    registry.clear()
    registry.register(
        {
            ConfigKeys.ID: "python.no_print",
            ConfigKeys.TYPE: "regex",
            ConfigKeys.MODE: "line",
            ConfigKeys.SEVERITY: "warning",
            ConfigKeys.ENABLED: True,
            ConfigKeys.MESSAGE: "No print.",
            ConfigKeys.INCLUDE: ["**/*.py"],
            ConfigKeys.PATTERNS: ["\\bprint\\s*\\("],
        }
    )

    violations = RuleRunner(rule_registry=registry).run(tmp_path)

    assert len(violations) == 1
    assert violations[0].rule_id == "python.no_print"
    registry.clear()


def test_rule_runner_reports_progress_for_enabled_rules(tmp_path: Path):
    source = tmp_path / "main.py"
    source.write_text("print('hello')\n", encoding="utf-8")
    registry = RuleRegistry()
    registry.clear()
    registry.register(
        {
            ConfigKeys.ID: "python.no_print",
            ConfigKeys.TYPE: "regex",
            ConfigKeys.MODE: "line",
            ConfigKeys.SEVERITY: "warning",
            ConfigKeys.ENABLED: True,
            ConfigKeys.MESSAGE: "No print.",
            ConfigKeys.INCLUDE: ["**/*.py"],
            ConfigKeys.PATTERNS: ["\\bprint\\s*\\("],
        }
    )
    registry.register(
        {
            ConfigKeys.ID: "python.disabled",
            ConfigKeys.TYPE: "regex",
            ConfigKeys.MODE: "line",
            ConfigKeys.SEVERITY: "warning",
            ConfigKeys.ENABLED: False,
            ConfigKeys.MESSAGE: "Disabled.",
            ConfigKeys.INCLUDE: ["**/*.py"],
            ConfigKeys.PATTERNS: ["disabled"],
        }
    )
    progress_events = []

    def record_progress(completed_rules: int, total_rules: int, rule_id: str) -> None:
        progress_events.append((completed_rules, total_rules, rule_id))

    RuleRunner(rule_registry=registry).run(tmp_path, progress_callback=record_progress)

    assert progress_events == [(1, 1, "python.no_print")]
    registry.clear()
