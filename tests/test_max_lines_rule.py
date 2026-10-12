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


def test_logical_count_drops_dartdoc_and_part_directives(tmp_path: Path):
    """Dartdoc is the dominant comment form in Flutter code, so it must not count.

    `///` is caught by the `//` prefix rather than by a rule of its own, which is
    easy to break while tidying `_is_logical_source_line`. memox-v8 points its
    file-length gates at this mode (`config/overrides.yaml`), because a
    documented file is mostly dartdoc, so this is the case that matters most there.
    """
    source = tmp_path / "tokens.dart"
    source.write_text(
        "\n".join(
            [
                "import 'package:flutter/material.dart';",
                "export 'other.dart';",
                "part 'tokens.g.dart';",
                "",
                "/// Dartdoc line one.",
                "///",
                "/// Dartdoc line two, explaining at length why this value is",
                "/// the value it is.",
                "const int token = 1;",
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
            # Only `const int token = 1;` is logical; nine lines total.
            "max_lines": 1,
            "count_mode": "logical",
        }
    )

    assert rule.check(tmp_path) == []


def test_logical_count_still_reports_a_genuinely_long_file(tmp_path: Path):
    """The point of the mode is a truer count, not a toothless one."""
    source = tmp_path / "long.dart"
    source.write_text(
        "\n".join(
            ["/// A well documented but genuinely long file."]
            + [f"const int value{index} = {index};" for index in range(5)]
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
            "max_lines": 4,
            "count_mode": "logical",
        }
    )

    violations = rule.check(tmp_path)

    assert len(violations) == 1
    assert "Current lines: 5" in violations[0].message
