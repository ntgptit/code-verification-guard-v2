"""Scope boundary tests for widget UI async guard rules."""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from code_verification_guard.constants.config_keys import ConfigKeys
from code_verification_guard.scanner.file_scanner import FileScanner


@pytest.fixture
def widget_ui_scope_patterns(tmp_path: Path) -> tuple[list[str], list[str]]:
    """Load widget_ui_async_surfaces include/exclude from memox-scopes.yaml."""
    scopes_path = (
        Path(__file__).resolve().parents[1] / "scopes" / "memox-scopes.yaml"
    )
    document = yaml.safe_load(scopes_path.read_text(encoding="utf-8"))
    scope = document["scopes"]["widget_ui_async_surfaces"]
    return scope["include"], scope["exclude"]


def test_widget_ui_scope_includes_screens_and_widgets(
    widget_ui_scope_patterns: tuple[list[str], list[str]],
) -> None:
    """Use collect_files like the guard runner (fnmatch ** is expanded by walking)."""
    include_patterns, exclude_patterns = widget_ui_scope_patterns
    scanner = FileScanner()
    project_root = Path(__file__).resolve().parents[2]
    matched = [
        path.relative_to(project_root).as_posix()
        for path in scanner.collect_files(
            project_root,
            include_patterns,
            exclude_patterns,
        )
    ]

    assert (
        "lib/presentation/features/study/screens/study_entry_screen.dart"
        in matched
    )
    assert any(
        path.startswith("lib/presentation/features/study/widgets/")
        for path in matched
    )
    assert "lib/presentation/shared/widgets/mx_card.dart" in matched


def test_widget_ui_scope_excludes_providers_and_viewmodels(
    widget_ui_scope_patterns: tuple[list[str], list[str]],
) -> None:
    include_patterns, exclude_patterns = widget_ui_scope_patterns
    scanner = FileScanner()
    project_root = Path(__file__).resolve().parents[2]
    matched = [
        path.relative_to(project_root).as_posix()
        for path in scanner.collect_files(
            project_root,
            include_patterns,
            exclude_patterns,
        )
    ]

    assert (
        "lib/presentation/features/study/providers/study_entry_notifier.dart"
        not in matched
    )
    assert (
        "lib/presentation/features/decks/viewmodels/deck_action_viewmodel.dart"
        not in matched
    )


