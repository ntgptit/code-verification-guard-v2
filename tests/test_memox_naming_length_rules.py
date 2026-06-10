"""Tests for MemoX Flutter naming length guard rules."""

from __future__ import annotations

from copy import deepcopy
from pathlib import Path

import yaml

from code_verification_guard.factory.rule_factory import RuleFactory

REGISTRY_DIR = (
    Path(__file__).parents[1] / "registries" / "projects" / "memox" / "rules"
)


def _rule_config(rule_id: str) -> dict:
    for registry_path in REGISTRY_DIR.glob("*-rules.yaml"):
        registry = yaml.safe_load(registry_path.read_text(encoding="utf-8"))
        for rule_config in registry.get("rules", []):
            if rule_config["id"] == rule_id:
                return deepcopy(rule_config)

    raise AssertionError(f"Rule not found: {rule_id}")


def _violations(rule_id: str, tmp_path: Path, relative_path: str, source: str) -> list:
    source_path = tmp_path / relative_path
    source_path.parent.mkdir(parents=True, exist_ok=True)
    source_path.write_text(source, encoding="utf-8")

    rule_config = _rule_config(rule_id)
    rule_config["enabled"] = True

    return RuleFactory().create(rule_config).check(tmp_path)


def test_local_variable_name_length_flags_outside_range(tmp_path: Path) -> None:
    bad = """
    class SampleWidget {
      Widget build(BuildContext context) {
        final aa = 1;
        final veryLongLocalValueName = 2;
        return const SizedBox();
      }
    }
    """
    good = """
    class SampleWidget {
      Widget build(BuildContext context) {
        final value = 1;
        final localValue = 2;
        return const SizedBox();
      }
    }
    """
    path = "lib/presentation/features/sample/sample_widget.dart"

    assert _violations(
        "memox.coding.local_variable_name_length",
        tmp_path,
        path,
        bad,
    )
    assert not _violations(
        "memox.coding.local_variable_name_length",
        tmp_path,
        path,
        good,
    )


def test_model_state_field_name_length_flags_outside_range(tmp_path: Path) -> None:
    bad = """
    class SampleState {
      final aa = 1;
      final anotherVeryLongStateFieldName = 2;
    }
    """
    good = """
    class SampleState {
      final value = 1;
      final stateValue = 2;
    }
    """
    path = "lib/presentation/features/sample/sample_state.dart"

    assert _violations(
        "memox.coding.model_state_field_name_length",
        tmp_path,
        path,
        bad,
    )
    assert not _violations(
        "memox.coding.model_state_field_name_length",
        tmp_path,
        path,
        good,
    )


def test_boolean_name_length_flags_outside_range(tmp_path: Path) -> None:
    bad = """
    class SampleState {
      bool isOn = true;
      bool isExtremelyVerboseFeatureEnabledFlag = false;
    }

    Widget build(BuildContext context) {
      final flag = true;
      final done = false;
      return const SizedBox();
    }
    """
    good = """
    class SampleState {
      bool isVisible = true;
      bool hasSelection = false;
    }

    Widget build(BuildContext context) {
      final isReady = true;
      final hasItems = false;
      return const SizedBox();
    }
    """
    path = "lib/presentation/features/sample/sample_state.dart"

    assert _violations(
        "memox.coding.boolean_name_length",
        tmp_path,
        path,
        bad,
    )
    assert not _violations(
        "memox.coding.boolean_name_length",
        tmp_path,
        path,
        good,
    )
