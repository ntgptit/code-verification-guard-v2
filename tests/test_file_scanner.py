from pathlib import Path

from code_verification_guard.scanner.file_scanner import FileScanner


def test_collect_files_excludes_root_virtualenv(tmp_path: Path):
    source = tmp_path / "app.py"
    source.write_text("print('app')\n", encoding="utf-8")

    vendored = tmp_path / ".venv" / "Lib" / "site-packages" / "pip" / "_vendor.py"
    vendored.parent.mkdir(parents=True)
    vendored.write_text("print('vendored')\n", encoding="utf-8")

    files = FileScanner().collect_files(
        tmp_path,
        include_patterns=["**/*.py"],
        exclude_patterns=["**/.venv/**"],
    )

    assert files == [source]


def test_collect_files_excludes_default_cache_and_dependency_paths(tmp_path: Path):
    source = tmp_path / "app.py"
    source.write_text("print('app')\n", encoding="utf-8")
    excluded_directories = [
        ".pytest_cache",
        ".mypy_cache",
        ".ruff_cache",
        ".tox",
        ".nox",
        "__pycache__",
        "build",
        "dist",
        "node_modules",
        ".venv",
        "venv",
        "env",
        ".dart_tool",
    ]

    for directory_name in excluded_directories:
        cached = tmp_path / directory_name / "cached.txt"
        cached.parent.mkdir(parents=True)
        cached.write_text("cached\n", encoding="utf-8")

    coverage_file = tmp_path / ".coverage"
    coverage_file.write_text("coverage\n", encoding="utf-8")

    files = FileScanner().collect_files(
        tmp_path,
        include_patterns=["**/*"],
        exclude_patterns=[],
    )

    assert files == [source]


def test_matches_double_star_pattern_at_project_root():
    scanner = FileScanner()

    assert scanner.matches_any("main.py", ["**/*.py"])
    assert scanner.matches_any(".venv/Lib/site-packages/pkg.py", ["**/.venv/**"])


def test_each_nested_globstar_independently_matches_zero_directories():
    scanner = FileScanner()
    pattern = "lib/presentation/features/**/widgets/**/*_tile.dart"

    # Second globstar collapses while the first one still matches a directory.
    assert scanner.matches_any(
        "lib/presentation/features/folders/widgets/folder_deck_tile.dart",
        [pattern],
    )
    # First globstar collapses while the second one still matches a directory.
    assert scanner.matches_any(
        "lib/presentation/features/widgets/cards/folder_deck_tile.dart",
        [pattern],
    )
    # Both globstars collapse.
    assert scanner.matches_any(
        "lib/presentation/features/widgets/folder_deck_tile.dart",
        [pattern],
    )
    # Both globstars match directories.
    assert scanner.matches_any(
        "lib/presentation/features/folders/widgets/cards/folder_deck_tile.dart",
        [pattern],
    )
