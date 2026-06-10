"""Tests for MemoX Flutter class name length guard rules."""

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


def test_flutter_class_name_length_flags_names_outside_range(
    tmp_path: Path,
) -> None:
    bad = """
    class Util extends StatelessWidget {
      @override
      Widget build(BuildContext context) => const SizedBox();
    }
    """
    long_bad = """
    class ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789ABCD extends StatelessWidget {
      @override
      Widget build(BuildContext context) => const SizedBox();
    }
    """
    good = """
    class SampleWidget extends StatelessWidget {
      @override
      Widget build(BuildContext context) => const SizedBox();
    }
    """
    path = "lib/presentation/features/sample/sample_screen.dart"

    assert _violations(
        "memox.coding.class_name_length",
        tmp_path,
        path,
        bad,
    )
    assert _violations(
        "memox.coding.class_name_length",
        tmp_path,
        path,
        long_bad,
    )
    assert not _violations(
        "memox.coding.class_name_length",
        tmp_path,
        path,
        good,
    )


def test_flutter_class_name_length_exempts_mx_prefix(tmp_path: Path) -> None:
    source = """
    class MxABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789ABCD extends StatelessWidget {
      @override
      Widget build(BuildContext context) => const SizedBox();
    }
    """
    path = "lib/presentation/shared/widgets/mx_demo.dart"

    assert not _violations(
        "memox.coding.class_name_length",
        tmp_path,
        path,
        source,
    )
