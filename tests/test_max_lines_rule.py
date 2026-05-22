from pathlib import Path

from code_verification_guard.factory.rule_factory import RuleFactory


def test_max_lines_rule_counts_raw_lines_by_default(tmp_path: Path):
    source = tmp_path / "main.dart"
    source.write_text(
        "\n".join(
            [
                "import 'package:flutter/material.dart';",
                "",
                "// comment",
                "void main() {}",
            ]
        ),
        encoding="utf-8",
    )

    rule = RuleFactory().create(
        {
            "id": "common.max_file_lines",
            "type": "max_lines",
            "severity": "warning",
            "enabled": True,
            "message": "File is too long.",
            "include": ["**/*.dart"],
            "max_lines": 3,
        }
    )

    assert len(rule.check(tmp_path)) == 1


def test_max_lines_rule_can_count_logical_source_lines(tmp_path: Path):
    source = tmp_path / "main.dart"
    source.write_text(
        "\n".join(
            [
                "import 'package:flutter/material.dart';",
                "",
                "// comment",
                "/* block comment start",
                " * block comment body",
                " */",
                "void main() {}",
            ]
        ),
        encoding="utf-8",
    )

    rule = RuleFactory().create(
        {
            "id": "common.no_large_source_file",
            "type": "max_lines",
            "severity": "warning",
            "enabled": True,
            "message": "Source file is too large.",
            "include": ["**/*.dart"],
            "max_lines": 1,
            "count_mode": "logical",
        }
    )

    assert rule.check(tmp_path) == []
