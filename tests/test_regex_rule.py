from pathlib import Path

from code_verification_guard.factory.rule_factory import RuleFactory


def test_regex_rule_detects_violation(tmp_path: Path):
    source = tmp_path / "main.py"
    source.write_text("print('hello')\n", encoding="utf-8")

    rule = RuleFactory().create(
        {
            "id": "python.no_print",
            "type": "regex",
            "mode": "line",
            "severity": "warning",
            "enabled": True,
            "message": "No print.",
            "include": ["**/*.py"],
            "patterns": ["\\bprint\\s*\\("],
        }
    )

    violations = rule.check(tmp_path)

    assert len(violations) == 1
    assert violations[0].rule_id == "python.no_print"


def test_regex_rule_file_mode_detects_multiline_violation(tmp_path: Path):
    source = tmp_path / "main.py"
    source.write_text("first\n\n\n\nlast\n", encoding="utf-8")

    rule = RuleFactory().create(
        {
            "id": "common.no_multiple_blank_lines",
            "type": "regex",
            "mode": "file",
            "severity": "warning",
            "enabled": True,
            "message": "No repeated blank lines.",
            "include": ["**/*.py"],
            "patterns": ["(\\r?\\n\\s*){4,}"],
        }
    )

    violations = rule.check(tmp_path)

    assert len(violations) == 1
    assert violations[0].line_number == 2


def test_env_file_rule_targets_environment_files_only(tmp_path: Path):
    env_file = tmp_path / ".env"
    env_file.write_text("VALUE=secret\n", encoding="utf-8")
    source = tmp_path / "main.py"
    source.write_text("VALUE=secret\n", encoding="utf-8")
    example = tmp_path / ".env.example"
    example.write_text("VALUE=example\n", encoding="utf-8")

    rule = RuleFactory().create(
        {
            "id": "common.no_committed_environment_file",
            "type": "regex",
            "mode": "line",
            "severity": "warning",
            "enabled": True,
            "message": "No env files.",
            "include": [".env", ".env.*"],
            "exclude": [".env.example", ".env.sample", ".env.template"],
            "patterns": [".+"],
        }
    )

    violations = rule.check(tmp_path)

    assert [violation.file_path.name for violation in violations] == [".env"]
