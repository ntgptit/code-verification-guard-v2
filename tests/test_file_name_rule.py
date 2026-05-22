from pathlib import Path

from code_verification_guard.factory.rule_factory import RuleFactory


def test_file_name_rule_detects_bad_file_name(tmp_path: Path):
    source = tmp_path / "BadName.py"
    source.write_text("", encoding="utf-8")

    rule = RuleFactory().create(
        {
            "id": "python.file_snake_case",
            "type": "file_name",
            "severity": "error",
            "enabled": True,
            "message": "Bad file name.",
            "include": ["**/*.py"],
            "pattern": "^[a-z0-9_]+\\.py$",
        }
    )

    violations = rule.check(tmp_path)

    assert len(violations) == 1
