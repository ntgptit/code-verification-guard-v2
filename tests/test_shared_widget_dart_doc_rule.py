from __future__ import annotations

from copy import deepcopy
from pathlib import Path

import pytest
import yaml

from code_verification_guard.factory.rule_factory import RuleFactory

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
    ("flutter.shared_widget.dart_doc.required", "MxMissingDocButton"),
    ("flutter.shared_widget.dart_doc.summary_required", "MxBrokenButton"),
    ("flutter.shared_widget.dart_doc.purpose_required", "MxBrokenButton"),
    ("flutter.shared_widget.dart_doc.use_when_required", "MxBrokenButton"),
    ("flutter.shared_widget.dart_doc.do_not_use_when_required", "MxBrokenButton"),
    ("flutter.shared_widget.dart_doc.category_required", "MxBrokenButton"),
    ("flutter.shared_widget.dart_doc.category_allowed_value", "MxBrokenButton"),
    ("flutter.shared_widget.dart_doc.public_api_required", "MxBrokenButton"),
    ("flutter.shared_widget.dart_doc.states_required_when_state_field_exists", "MxBrokenButton"),
    ("flutter.shared_widget.dart_doc.variants_required_when_variant_field_exists", "MxBrokenButton"),
    ("flutter.shared_widget.dart_doc.expected_contracts_required", "MxBrokenButton"),
]


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


@pytest.mark.parametrize("rule_id, _expected_class_name", RULE_CASES)
def test_shared_widget_dart_doc_rule_accepts_valid_fixture(
    rule_id: str,
    _expected_class_name: str,
    tmp_path: Path,
) -> None:
    violations = _run_rule(rule_id, tmp_path, _fixture_text("valid.dart"))

    assert violations == []
