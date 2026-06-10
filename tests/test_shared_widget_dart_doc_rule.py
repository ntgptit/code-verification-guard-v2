from __future__ import annotations

from copy import deepcopy
from pathlib import Path

import pytest
import yaml

from code_verification_guard.factory.rule_factory import RuleFactory
from code_verification_guard.registry.rule_registry import RuleRegistry
from code_verification_guard.runner.rule_runner import RuleRunner

RULE_REGISTRY = (
    Path(__file__).parents[1]
    / "registries"
    / "projects"
    / "memox"
    / "rules"
    / "memox-shared-widget-doc-rules.yaml"
)
FIXTURE_DIR = Path(__file__).parent / "fixtures" / "shared_widget_dart_doc"
SOURCE_PATH = (
    "lib/presentation/shared/widgets/sample_shared_widget.dart"
)

RULE_CASES = [
    ("memox.shared_widget_doc.required", "MxMissingDocButton"),
    ("memox.shared_widget_doc.summary_required", "MxBrokenButton"),
    ("memox.shared_widget_doc.purpose_required", "MxBrokenButton"),
    ("memox.shared_widget_doc.use_when_required", "MxBrokenButton"),
    ("memox.shared_widget_doc.category_required", "MxBrokenButton"),
    ("memox.shared_widget_doc.category_allowed_value", "MxBrokenButton"),
    ("memox.shared_widget_doc.public_api_required", "MxBrokenButton"),
    ("memox.shared_widget_doc.states_required_when_state_field_exists", "MxBrokenButton"),
    ("memox.shared_widget_doc.variants_required_when_variant_field_exists", "MxBrokenButton"),
]

EXPECTED_SEVERITIES = {
    "memox.shared_widget_doc.summary_required": "warning",
    "memox.shared_widget_doc.purpose_required": "warning",
    "memox.shared_widget_doc.use_when_required": "warning",
    "memox.shared_widget_doc.do_not_use_when_required": "warning",
    "memox.shared_widget_doc.category_required": "warning",
    "memox.shared_widget_doc.public_api_required": "warning",
    "memox.shared_widget_doc.states_required_when_state_field_exists": "warning",
    "memox.shared_widget_doc.variants_required_when_variant_field_exists": "warning",
}


def _rule_config(rule_id: str) -> dict:
    registry = yaml.safe_load(RULE_REGISTRY.read_text(encoding="utf-8"))
    for rule_config in registry.get("rules", []):
        if rule_config["id"] == rule_id:
            return deepcopy(rule_config)

    raise AssertionError(f"Rule not found: {rule_id}")


def _run_rule(rule_id: str, tmp_path: Path, source: str):
    source_path = tmp_path / SOURCE_PATH
    source_path.parent.mkdir(parents=True, exist_ok=True)
    source_path.write_text(source, encoding="utf-8")

    rule_config = _rule_config(rule_id)
    rule_config.pop("scopes", None)
    rule_config["include"] = ["lib/presentation/shared/**/*.dart"]
    rule_config["exclude"] = []
    rule_config["enabled"] = True

    return RuleFactory().create(rule_config).check(tmp_path)


def _run_disabled_rule(rule_id: str, tmp_path: Path, source: str):
    source_path = tmp_path / SOURCE_PATH
    source_path.parent.mkdir(parents=True, exist_ok=True)
    source_path.write_text(source, encoding="utf-8")

    rule_config = _rule_config(rule_id)
    rule_config.pop("scopes", None)
    rule_config["include"] = ["lib/presentation/shared/**/*.dart"]
    rule_config["exclude"] = []
    rule_config["enabled"] = False

    registry = RuleRegistry()
    registry.clear()
    registry.register(rule_config)

    try:
        return RuleRunner(rule_registry=registry).run(tmp_path)
    finally:
        registry.clear()


def _fixture_text(name: str) -> str:
    return (FIXTURE_DIR / name).read_text(encoding="utf-8")


@pytest.mark.parametrize("rule_id, expected_class_name", RULE_CASES)
def test_shared_widget_dart_doc_rule_flags_invalid_fixture(
    rule_id: str,
    expected_class_name: str,
    tmp_path: Path,
) -> None:
    violations = _run_rule(rule_id, tmp_path, _fixture_text("invalid.dart"))

    assert any(
        violation.rule_id == rule_id and violation.class_name == expected_class_name
        for violation in violations
    )
    if rule_id in EXPECTED_SEVERITIES:
        violation = next(
            violation
            for violation in violations
            if violation.rule_id == rule_id and violation.class_name == expected_class_name
        )
        assert violation.severity == EXPECTED_SEVERITIES[rule_id]


@pytest.mark.parametrize("rule_id, _expected_class_name", RULE_CASES)
def test_shared_widget_dart_doc_rule_accepts_valid_fixture(
    rule_id: str,
    _expected_class_name: str,
    tmp_path: Path,
) -> None:
    violations = _run_rule(rule_id, tmp_path, _fixture_text("valid.dart"))

    assert violations == []


def test_do_not_use_when_required_applies_only_to_configured_categories(tmp_path: Path) -> None:
    source = """
    import 'package:flutter/material.dart';

    /// Summary.
    /// Purpose:
    /// Why.
    /// Use when:
    /// When.
    /// Category:
    /// button
    ///
    /// Public API:
    /// - label: text.
    class MxButtonLike extends StatelessWidget {
      const MxButtonLike({required this.label, super.key});

      final String label;

      @override
      Widget build(BuildContext context) => Text(label);
    }
    """

    violations = _run_rule(
        "memox.shared_widget_doc.do_not_use_when_required",
        tmp_path,
        source,
    )

    assert any(violation.class_name == "MxButtonLike" for violation in violations)


def test_do_not_use_when_required_skips_unlisted_categories(tmp_path: Path) -> None:
    source = """
    import 'package:flutter/material.dart';

    /// Summary.
    /// Purpose:
    /// Why.
    /// Use when:
    /// When.
    /// Category:
    /// display
    ///
    /// Public API:
    /// - label: text.
    class MxDisplayWidget extends StatelessWidget {
      const MxDisplayWidget({required this.label, super.key});

      final String label;

      @override
      Widget build(BuildContext context) => Text(label);
    }
    """

    violations = _run_rule(
        "memox.shared_widget_doc.do_not_use_when_required",
        tmp_path,
        source,
    )

    assert violations == []


@pytest.mark.parametrize("field_name", ["variant", "type", "style"])
def test_variant_field_names_still_trigger_variant_rule(
    field_name: str,
    tmp_path: Path,
) -> None:
    source = f"""
    import 'package:flutter/material.dart';

    /// Summary.
    /// Purpose:
    /// Why.
    /// Use when:
    /// When.
    /// Category:
    /// button
    ///
    /// Public API:
    /// - {field_name}: variant field.
    class MxVariantWidget extends StatelessWidget {{
      const MxVariantWidget({{
        required this.{field_name},
        super.key,
      }});

      final String {field_name};

      @override
      Widget build(BuildContext context) => Text({field_name});
    }}
    """

    violations = _run_rule(
        "memox.shared_widget_doc.variants_required_when_variant_field_exists",
        tmp_path,
        source,
    )

    assert any(violation.class_name == "MxVariantWidget" for violation in violations)


def test_size_field_does_not_trigger_variant_rule(tmp_path: Path) -> None:
    source = """
    import 'package:flutter/material.dart';

    /// Summary.
    /// Purpose:
    /// Why.
    /// Use when:
    /// When.
    /// Category:
    /// button
    ///
    /// Public API:
    /// - size: icon size.
    class MxSizedWidget extends StatelessWidget {
      const MxSizedWidget({
        required this.size,
        super.key,
      });

      final double size;

      @override
      Widget build(BuildContext context) => Text('$size');
    }
    """

    violations = _run_rule(
        "memox.shared_widget_doc.variants_required_when_variant_field_exists",
        tmp_path,
        source,
    )

    assert violations == []


def test_expected_contracts_required_does_not_run_when_disabled(tmp_path: Path) -> None:
    source = _fixture_text("invalid.dart")

    violations = _run_disabled_rule(
        "memox.shared_widget_doc.expected_contracts_required",
        tmp_path,
        source,
    )

    assert violations == []
