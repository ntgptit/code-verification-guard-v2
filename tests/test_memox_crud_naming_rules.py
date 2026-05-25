"""Tests for MemoX CRUD naming guard rules."""

from __future__ import annotations

from copy import deepcopy
from pathlib import Path

import yaml

from code_verification_guard.factory.rule_factory import RuleFactory

REGISTRY_DIR = Path(__file__).parents[1] / "registries" / "projects" / "memox"


def _rule_config(rule_id: str) -> dict:
    for registry_path in REGISTRY_DIR.glob("*.yaml"):
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


def test_crud_screen_class_naming_flags_vague_screen_classes(tmp_path: Path) -> None:
    bad = """
    class DeckImportView extends ConsumerWidget {
      @override
      Widget build(BuildContext context, WidgetRef ref) => const SizedBox();
    }
    """
    good = bad.replace("DeckImportView", "DeckImportScreen")
    path = "lib/presentation/features/flashcards/screens/deck_import_screen.dart"

    assert _violations("memox.crud_screen_class_naming", tmp_path, path, bad)
    assert not _violations("memox.crud_screen_class_naming", tmp_path, path, good)


def test_crud_screen_class_naming_allows_non_entity_overview_names(
    tmp_path: Path,
) -> None:
    source = """
    class LibraryOverviewView extends ConsumerWidget {
      @override
      Widget build(BuildContext context, WidgetRef ref) => const SizedBox();
    }
    """
    path = "lib/presentation/features/folders/screens/library_overview_screen.dart"

    assert not _violations("memox.crud_screen_class_naming", tmp_path, path, source)


def test_crud_viewmodel_controller_naming_flags_vague_controllers(
    tmp_path: Path,
) -> None:
    bad = """
    class FlashcardManagerController extends _$FlashcardManagerController {
      @override
      FutureOr<void> build() {}
    }
    """
    good = bad.replace("FlashcardManagerController", "FlashcardActionController")
    path = "lib/presentation/features/flashcards/viewmodels/flashcard_list_viewmodel.dart"

    assert _violations("memox.crud_viewmodel_controller_naming", tmp_path, path, bad)
    assert not _violations(
        "memox.crud_viewmodel_controller_naming",
        tmp_path,
        path,
        good,
    )


def test_crud_command_method_names_must_include_entity(tmp_path: Path) -> None:
    bad = """
    class FolderActionController extends _$FolderActionController {
      @override
      FutureOr<void> build() {}

      Future<bool> delete() async => true;
    }
    """
    good = bad.replace("delete()", "deleteFolder()")
    path = "lib/presentation/features/folders/viewmodels/folder_detail_viewmodel.dart"

    assert _violations(
        "memox.crud_command_method_names_include_entity",
        tmp_path,
        path,
        bad,
    )
    assert not _violations(
        "memox.crud_command_method_names_include_entity",
        tmp_path,
        path,
        good,
    )


def test_crud_command_method_names_flag_vague_save(tmp_path: Path) -> None:
    bad = """
    class FlashcardEditorController extends _$FlashcardEditorController {
      @override
      FutureOr<void> build() {}

      Future<bool> save({bool keepCreating = false}) async => true;
    }
    """
    good = bad.replace("save({", "saveFlashcard({")
    path = "lib/presentation/features/flashcards/viewmodels/flashcard_editor_viewmodel.dart"

    assert _violations(
        "memox.crud_command_method_names_include_entity",
        tmp_path,
        path,
        bad,
    )
    assert not _violations(
        "memox.crud_command_method_names_include_entity",
        tmp_path,
        path,
        good,
    )
