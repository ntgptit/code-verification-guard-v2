from pathlib import Path

from code_verification_guard.factory.rule_factory import RuleFactory


def test_max_build_lines_counts_raw_method_lines_by_default(tmp_path: Path):
    source = tmp_path / "sample.dart"
    source.write_text(
        "\n".join(
            [
                "class Sample {",
                "  Widget build(BuildContext context) {",
                "    // comment",
                "",
                "    return const SizedBox();",
                "  }",
                "}",
            ]
        ),
        encoding="utf-8",
    )

    rule = RuleFactory().create(
        {
            "id": "flutter.max_build_lines",
            "type": "max_build_lines",
            "severity": "warning",
            "enabled": True,
            "message": "build() is too long.",
            "include": ["**/*.dart"],
            "max_lines": 3,
        }
    )

    assert len(rule.check(tmp_path)) == 1


def test_max_build_lines_can_count_logical_method_lines(tmp_path: Path):
    source = tmp_path / "sample.dart"
    source.write_text(
        "\n".join(
            [
                "class Sample {",
                "  Widget build(BuildContext context) {",
                "    // comment",
                "",
                "    /* block comment */",
                "    return const SizedBox();",
                "  }",
                "}",
            ]
        ),
        encoding="utf-8",
    )

    rule = RuleFactory().create(
        {
            "id": "flutter.max_build_lines",
            "type": "max_build_lines",
            "severity": "warning",
            "enabled": True,
            "message": "build() is too long.",
            "include": ["**/*.dart"],
            "max_lines": 3,
            "count_mode": "logical",
        }
    )

    assert rule.check(tmp_path) == []
