"""Regression tests for the active MemoX v6 ruleset contract."""

from __future__ import annotations

from copy import deepcopy
from pathlib import Path

import yaml

from code_verification_guard.factory.rule_factory import RuleFactory

RULESET_ROOT = (
    Path(__file__).parents[1] / "registries" / "projects" / "memox"
)


def _study_rule(rule_id: str) -> dict:
    registry_path = RULESET_ROOT / "rules" / "memox-study-rules.yaml"
    registry = yaml.safe_load(registry_path.read_text(encoding="utf-8"))
    for rule_config in registry.get("rules", []):
        if rule_config["id"] == rule_id:
            return deepcopy(rule_config)

    raise AssertionError(f"Rule not found: {rule_id}")


def _write_source(tmp_path: Path, relative_path: str, source: str) -> None:
    source_path = tmp_path / relative_path
    source_path.parent.mkdir(parents=True, exist_ok=True)
    source_path.write_text(source, encoding="utf-8")


def test_active_rules_use_memox_v6_package_namespace() -> None:
    stale_occurrences: list[str] = []
    for registry_path in (RULESET_ROOT / "rules").glob("*.yaml"):
        if "package:memox/" in registry_path.read_text(encoding="utf-8"):
            stale_occurrences.append(registry_path.name)

    assert stale_occurrences == []


def test_active_registry_does_not_target_retired_folder_domain() -> None:
    retired_fragments = (
        "features/folders",
        "folder_repository_impl.dart",
        "FolderDetail",
        "updateFolder",
        "Subfolder",
    )
    stale_occurrences: list[str] = []
    for registry_path in RULESET_ROOT.rglob("*.yaml"):
        content = registry_path.read_text(encoding="utf-8")
        if any(fragment in content for fragment in retired_fragments):
            stale_occurrences.append(str(registry_path.relative_to(RULESET_ROOT)))

    assert stale_occurrences == []


def test_srs_transition_math_is_allowed_only_in_canonical_domain_policy(
    tmp_path: Path,
) -> None:
    _write_source(
        tmp_path,
        "lib/domain/learning_progress/srs_8_box_policy.dart",
        "int intervalForBox(int box) => box;",
    )
    _write_source(
        tmp_path,
        "lib/data/repositories/study_repository_impl.dart",
        "int boxAfterFinalization(int box) => box + 1;",
    )

    rule_config = _study_rule("memox.study.srs_logic_single_source")
    violations = RuleFactory().create(rule_config).check(tmp_path)

    assert len(violations) == 1
    assert violations[0].file_path.name == "study_repository_impl.dart"


def test_memox_ci_profile_treats_warnings_as_errors() -> None:
    profiles_path = RULESET_ROOT / "config" / "profiles.yaml"
    profiles = yaml.safe_load(profiles_path.read_text(encoding="utf-8"))["profiles"]

    assert profiles["local"]["failure"]["warning_as_error"] is False
    assert profiles["ci"]["failure"]["warning_as_error"] is True
