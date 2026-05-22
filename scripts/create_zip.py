"""Create a clean source archive for code-verification-guard."""

from __future__ import annotations

import sys
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile


EXCLUDED_DIRECTORIES = {
    ".git",
    ".hg",
    ".svn",
    ".venv",
    "venv",
    "env",
    "node_modules",
    "__pycache__",
    ".pytest_cache",
    ".mypy_cache",
    ".ruff_cache",
    ".tox",
    ".nox",
    "build",
    "dist",
    ".dart_tool",
    "htmlcov",
}

EXCLUDED_FILE_NAMES = {
    ".coverage",
}

EXCLUDED_SUFFIXES = {
    ".pyc",
    ".pyo",
    ".pyd",
    ".zip",
}

INCLUDED_ITEMS = [
    "code_verification_guard",
    "configs",
    "docs",
    "guard",
    "profiles",
    "registries",
    "scopes",
    "scripts",
    "templates",
    "tests",
    ".gitignore",
    "code-verification-guard.yaml",
    "create_zip.bat",
    "guard-manifest.yaml",
    "pyproject.toml",
    "README.md",
    "requirements.txt",
]


def main() -> int:
    """Create the requested zip archive."""
    if len(sys.argv) != 3:
        print("Usage: create_zip.py <root-dir> <output-zip>")
        return 1

    root_dir = Path(sys.argv[1]).resolve()
    output_zip = Path(sys.argv[2]).resolve()

    if not root_dir.exists():
        print(f"ERROR: Root directory does not exist: {root_dir}")
        return 1

    if output_zip.exists():
        output_zip.unlink()

    paths = list(iter_included_files(root_dir, output_zip))

    if not paths:
        print("ERROR: No files were found to compress.")
        return 1

    with ZipFile(output_zip, "w", compression=ZIP_DEFLATED) as archive:
        for file_path in paths:
            archive.write(file_path, file_path.relative_to(root_dir).as_posix())

    print(f"Archive created successfully: {output_zip}")
    print(f"Files archived: {len(paths)}")
    return 0


def iter_included_files(root_dir: Path, output_zip: Path):
    """Yield package files while excluding generated artifacts."""
    for item in INCLUDED_ITEMS:
        path = root_dir / item

        if not path.exists():
            print(f"WARNING: Missing item skipped: {item}")
            continue

        if path.is_file():
            if should_include_file(path, root_dir, output_zip):
                yield path
            continue

        for file_path in path.rglob("*"):
            if should_include_file(file_path, root_dir, output_zip):
                yield file_path


def should_include_file(file_path: Path, root_dir: Path, output_zip: Path) -> bool:
    """Return whether a file belongs in the source archive."""
    if not file_path.is_file():
        return False

    if file_path.resolve() == output_zip:
        return False

    relative_parts = file_path.relative_to(root_dir).parts

    if any(is_excluded_directory(part) for part in relative_parts[:-1]):
        return False

    if file_path.name in EXCLUDED_FILE_NAMES:
        return False

    return file_path.suffix not in EXCLUDED_SUFFIXES


def is_excluded_directory(name: str) -> bool:
    """Return whether a directory name should be skipped."""
    return name in EXCLUDED_DIRECTORIES or name.endswith(".egg-info")


if __name__ == "__main__":
    raise SystemExit(main())
