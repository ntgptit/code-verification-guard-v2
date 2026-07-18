"""Scope boundary tests for widget UI async guard rules."""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from code_verification_guard.constants.config_keys import ConfigKeys
from code_verification_guard.scanner.file_scanner import FileScanner


@pytest.fixture
def widget_ui_scope_patterns(
    tmp_path: Path,
) -> tuple[Path, list[str], list[str]]:
    """Load widget_ui_async_surfaces include/exclude from MemoX ruleset scopes."""
    scopes_path = (
        Path(__file__).resolve().parents[1]
        / "registries"
        / "projects"
        / "memox"
        / "config"
        / "scopes.yaml"
    )
    document = yaml.safe_load(scopes_path.read_text(encoding="utf-8"))
    scope = document["scopes"]["widget_ui_async_surfaces"]
    fixture_paths = (
        "lib/presentation/features/flashcards/screens/flashcard_editor_screen.dart",
        "lib/presentation/shared/widgets/mx_text.dart",
        "lib/presentation/shared/widgets/buttons/mx_primary_button.dart",
        "lib/presentation/features/flashcards/viewmodels/flashcard_editor_viewmodel.dart",
        "lib/presentation/features/decks/viewmodels/deck_action_viewmodel.dart",
    )
    for relative_path in fixture_paths:
        source_path = tmp_path / relative_path
        source_path.parent.mkdir(parents=True, exist_ok=True)
        source_path.write_text("// scope fixture\n", encoding="utf-8")

    return tmp_path, scope["include"], scope["exclude"]


def test_widget_ui_scope_includes_screens_and_widgets(
    widget_ui_scope_patterns: tuple[Path, list[str], list[str]],
) -> None:
    """Use collect_files like the guard runner (fnmatch ** is expanded by walking)."""
    project_root, include_patterns, exclude_patterns = widget_ui_scope_patterns
    scanner = FileScanner()
    matched = [
        path.relative_to(project_root).as_posix()
        for path in scanner.collect_files(
            project_root,
            include_patterns,
            exclude_patterns,
        )
    ] 

    assert (
        "lib/presentation/features/flashcards/screens/flashcard_editor_screen.dart"
        in matched
    )
    assert any(
        path.startswith("lib/presentation/shared/widgets/")
        for path in matched
    )
    assert "lib/presentation/shared/widgets/buttons/mx_primary_button.dart" in matched


def test_widget_ui_scope_excludes_providers_and_viewmodels(
    widget_ui_scope_patterns: tuple[Path, list[str], list[str]],
) -> None:
    project_root, include_patterns, exclude_patterns = widget_ui_scope_patterns
    scanner = FileScanner()
    matched = [
        path.relative_to(project_root).as_posix()
        for path in scanner.collect_files(
            project_root,
            include_patterns,
            exclude_patterns,
        )
    ] 

    assert (
        "lib/presentation/features/flashcards/viewmodels/flashcard_editor_viewmodel.dart"
        not in matched
    )
    assert (
        "lib/presentation/features/decks/viewmodels/deck_action_viewmodel.dart"
        not in matched
    )
