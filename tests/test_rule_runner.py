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
