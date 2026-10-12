"""Tests for guard configuration diagnostics emitted by the rule runner."""

from __future__ import annotations

from pathlib import Path

from code_verification_guard.constants.config_keys import ConfigKeys
from code_verification_guard.registry.rule_registry import RuleRegistry
from code_verification_guard.runner.rule_runner import (
    MISSING_TARGET_PATH_ID,
    RULE_TARGETS_PENDING_ID,
    RULE_WITHOUT_TARGETS_ID,
    STALE_TARGETS_PENDING_ID,
    RuleRunner,
)


def _register(
    registry: RuleRegistry,
    rule_id: str,
    include: list[str],
    targets_pending: str | None = None,
) -> None:
    rule = {
        ConfigKeys.ID: rule_id,
        ConfigKeys.TYPE: "regex",
        ConfigKeys.MODE: "line",
        ConfigKeys.SEVERITY: "error",
        ConfigKeys.ENABLED: True,
        ConfigKeys.MESSAGE: "No print.",
        ConfigKeys.INCLUDE: include,
        ConfigKeys.PATTERNS: ["\\bprint\\s*\\("],
    }
    if targets_pending is not None:
        rule[ConfigKeys.TARGETS_PENDING] = targets_pending
    registry.register(rule)


def test_rule_with_missing_literal_include_reports_both_diagnostics(tmp_path: Path) -> None:
    registry = RuleRegistry()
    registry.clear()
    _register(registry, "sample.dead_rule", ["lib/renamed_away.dart"])

    violations = RuleRunner(rule_registry=registry).run(tmp_path)

    rule_ids = [violation.rule_id for violation in violations]
    assert RULE_WITHOUT_TARGETS_ID in rule_ids
    assert MISSING_TARGET_PATH_ID in rule_ids
    assert all(violation.severity == "warning" for violation in violations)
    assert any("sample.dead_rule" in violation.message for violation in violations)
    registry.clear()


def test_rule_with_empty_glob_reports_only_rule_without_targets(tmp_path: Path) -> None:
    registry = RuleRegistry()
    registry.clear()
    _register(registry, "sample.future_boundary", ["lib/data/sync/**/*.dart"])

    violations = RuleRunner(rule_registry=registry).run(tmp_path)

    rule_ids = [violation.rule_id for violation in violations]
    assert rule_ids == [RULE_WITHOUT_TARGETS_ID]
    registry.clear()


def test_healthy_rule_reports_no_config_diagnostics(tmp_path: Path) -> None:
    source = tmp_path / "lib" / "main.dart"
    source.parent.mkdir(parents=True)
    source.write_text("void main() { print('hi'); }\n", encoding="utf-8")
    registry = RuleRegistry()
    registry.clear()
    _register(registry, "sample.healthy", ["lib/main.dart"])

    violations = RuleRunner(rule_registry=registry).run(tmp_path)

    assert [violation.rule_id for violation in violations] == ["sample.healthy"]
    registry.clear()


def test_rootlevel_literal_without_slash_is_not_reported_as_missing(tmp_path: Path) -> None:
    source = tmp_path / "lib" / "main.dart"
    source.parent.mkdir(parents=True)
    source.write_text("void main() {}\n", encoding="utf-8")
    registry = RuleRegistry()
    registry.clear()
    # File-presence-ban style rule: the literal target SHOULD be absent.
    _register(registry, "sample.no_env_file", [".env", "lib/main.dart"])

    violations = RuleRunner(rule_registry=registry).run(tmp_path)

    assert MISSING_TARGET_PATH_ID not in [violation.rule_id for violation in violations]
    registry.clear()


def test_shared_missing_path_is_reported_once_with_rule_references(tmp_path: Path) -> None:
    registry = RuleRegistry()
    registry.clear()
    _register(registry, "sample.first", ["lib/gone.dart", "lib/**/*.dart"])
    _register(registry, "sample.second", ["lib/gone.dart", "lib/**/*.dart"])

    violations = RuleRunner(rule_registry=registry).run(tmp_path)

    missing_path_violations = [
        violation
        for violation in violations
        if violation.rule_id == MISSING_TARGET_PATH_ID
    ]
    assert len(missing_path_violations) == 1
    assert "sample.first" in missing_path_violations[0].message
    assert "sample.second" in missing_path_violations[0].message
    registry.clear()


def test_pending_rule_without_targets_reports_info_only(tmp_path: Path) -> None:
    registry = RuleRegistry()
    registry.clear()
    _register(
        registry,
        "sample.waits_for_ui",
        ["lib/features/*/presentation/**/*.dart"],
        targets_pending="presentation",
    )

    violations = RuleRunner(rule_registry=registry).run(tmp_path)

    assert [(v.rule_id, v.severity) for v in violations] == [
        (RULE_TARGETS_PENDING_ID, "info")
    ]
    assert "sample.waits_for_ui" in violations[0].message
    assert "presentation" in violations[0].message
    registry.clear()


def test_pending_rule_that_gained_targets_reports_a_stale_declaration(tmp_path: Path) -> None:
    screen = tmp_path / "lib" / "features" / "deck" / "presentation" / "screens" / "deck_screen.dart"
    screen.parent.mkdir(parents=True)
    screen.write_text("class DeckScreen {}\n", encoding="utf-8")
    registry = RuleRegistry()
    registry.clear()
    _register(
        registry,
        "sample.waits_for_ui",
        ["lib/features/*/presentation/**/*.dart"],
        targets_pending="presentation",
    )

    violations = RuleRunner(rule_registry=registry).run(tmp_path)

    assert [(v.rule_id, v.severity) for v in violations] == [
        (STALE_TARGETS_PENDING_ID, "warning")
    ]
    assert "sample.waits_for_ui" in violations[0].message
    registry.clear()


def test_pending_rule_does_not_report_its_missing_literal_path(tmp_path: Path) -> None:
    registry = RuleRegistry()
    registry.clear()
    _register(
        registry,
        "sample.waits_for_arb",
        ["lib/l10n/app_en.arb"],
        targets_pending="l10n",
    )

    violations = RuleRunner(rule_registry=registry).run(tmp_path)

    assert [v.rule_id for v in violations] == [RULE_TARGETS_PENDING_ID]
    registry.clear()


def test_undeclared_rule_next_to_a_pending_one_still_warns(tmp_path: Path) -> None:
    registry = RuleRegistry()
    registry.clear()
    _register(
        registry,
        "sample.waits_for_ui",
        ["lib/features/*/presentation/**/*.dart"],
        targets_pending="presentation",
    )
    _register(registry, "sample.dead_rule", ["lib/data/sync/**/*.dart"])

    violations = RuleRunner(rule_registry=registry).run(tmp_path)

    assert sorted((v.rule_id, v.severity) for v in violations) == [
        (RULE_TARGETS_PENDING_ID, "info"),
        (RULE_WITHOUT_TARGETS_ID, "warning"),
    ]
    registry.clear()
