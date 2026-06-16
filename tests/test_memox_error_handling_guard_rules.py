"""Integration-style tests for MemoX error-handling guard regex rules."""

from __future__ import annotations

from copy import deepcopy
from pathlib import Path

import yaml

from code_verification_guard.factory.rule_factory import RuleFactory

REGISTRY_PATH = (
    Path(__file__).parents[1]
    / "registries"
    / "projects"
    / "memox"
    / "rules"
    / "memox-error-handling-rules.yaml"
)


def _rule_config(rule_id: str) -> dict:
    registry = yaml.safe_load(REGISTRY_PATH.read_text(encoding="utf-8"))
    for rule_config in registry.get("rules", []):
        if rule_config["id"] == rule_id:
            return deepcopy(rule_config)

    raise AssertionError(f"Rule not found: {rule_id}")


def test_no_unwrap_repository_lookup_flags_await_find_bang_and_is_a_warning(
    tmp_path: Path,
) -> None:
    """`(await dao.findX(id))!` in a repository bypasses the AppFailure.NotFound
    boundary, so the rule must flag it (as a warning) while leaving guarded null
    handling and Drift typed-result reads alone."""
    bad = """
    Future<FlashcardRow> findFlashcard(String id) async {
      return (await _dao.findFlashcard(id))!;
    }

    Future<FolderRow> moveFolder(String newParentId) async {
      final FolderRow newParent = (await dao.findFolder(newParentId))!;
      return newParent;
    }
    """
    good = """
    Future<Result<FlashcardRow>> findFlashcard(String id) async {
      final FlashcardRow? row = await _dao.findFlashcard(id);
      if (row == null) {
        return const Result.failure(AppFailure.notFound());
      }
      return Result.success(row);
    }

    String readColumn(TypedResult row) => row.read(flashcardIdExpr)!;
    """
    rule_config = _rule_config("memox.error_handling.no_unwrap_repository_lookup")

    assert rule_config["severity"] == "warning"

    bad_path = tmp_path / "lib/data/repositories/folder_repository_impl.dart"
    bad_path.parent.mkdir(parents=True, exist_ok=True)
    bad_path.write_text(bad, encoding="utf-8")

    good_path = tmp_path / "lib/data/repositories/flashcard_repository_impl.dart"
    good_path.write_text(good, encoding="utf-8")

    rule = RuleFactory().create(rule_config)
    violations = rule.check(tmp_path)
    flagged_files = {str(v.file_path) for v in violations}

    # Two bad unwraps in the first file, none in the guarded/Drift-read file.
    assert len([v for v in violations if str(v.file_path) == str(bad_path)]) == 2
    assert str(good_path) not in flagged_files


def test_no_unwrap_repository_lookup_only_targets_data_repositories(
    tmp_path: Path,
) -> None:
    """A `(await find())!` outside lib/data/repositories is out of this rule's
    scope (the generic non-null rule covers domain/presentation)."""
    source = """
    Future<Folder> load(String id) async {
      return (await _dao.findFolder(id))!;
    }
    """
    usecase_path = tmp_path / "lib/domain/usecases/folder/load_folder_usecase.dart"
    usecase_path.parent.mkdir(parents=True, exist_ok=True)
    usecase_path.write_text(source, encoding="utf-8")

    rule = RuleFactory().create(
        _rule_config("memox.error_handling.no_unwrap_repository_lookup")
    )

    assert rule.check(tmp_path) == []


def test_no_blind_json_decode_cast_flags_cast_but_allows_type_guard(
    tmp_path: Path,
) -> None:
    bad = """
    Map<String, Object?> parse(String raw) {
      return jsonDecode(raw) as Map<String, Object?>;
    }
    """
    good = """
    CloudAccountLink? load(String raw) {
      final Object? decoded = jsonDecode(raw);
      if (decoded is! Map<String, Object?>) {
        return null;
      }
      return CloudAccountLink.fromJson(decoded);
    }
    """
    rule_config = _rule_config("memox.error_handling.no_blind_json_decode_cast")
    assert rule_config["severity"] == "warning"

    bad_path = tmp_path / "lib/data/datasources/local/preferences/bad_store.dart"
    bad_path.parent.mkdir(parents=True, exist_ok=True)
    bad_path.write_text(bad, encoding="utf-8")

    good_path = tmp_path / "lib/data/datasources/local/preferences/cloud_account_store.dart"
    good_path.write_text(good, encoding="utf-8")

    rule = RuleFactory().create(rule_config)
    flagged = {str(v.file_path) for v in rule.check(tmp_path)}

    assert str(bad_path) in flagged
    assert str(good_path) not in flagged
