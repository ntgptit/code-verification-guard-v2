"""Locate guard YAML resources in the source tree."""

from __future__ import annotations

from pathlib import Path

from code_verification_guard.constants.defaults import Defaults


class ResourceLocator:
    """Resolves built-in guard resources from the vendored source tree."""

    def __init__(
        self,
        source_root: Path | None = None,
    ):
        """Create a locator with optional source-root override for tests."""
        self.source_root = source_root or Path(__file__).resolve().parents[2]

    def builtin_root(self) -> Path:
        """Return the source root containing built-in YAML resources."""
        source_manifest = self.source_root / Defaults.MANIFEST_FILE_NAME

        if not source_manifest.exists():
            raise FileNotFoundError(f"Built-in manifest not found: {source_manifest}")

        return self.source_root

    def profile_path(self, project_root: Path, profile_name: str) -> Path:
        """Return project-local profile path or built-in profile resource."""
        profile_path = project_root / Defaults.PROFILES_DIRECTORY / f"{profile_name}.yaml"

        if profile_path.exists():
            return profile_path

        return self.join(self.builtin_root(), Defaults.PROFILES_DIRECTORY, f"{profile_name}.yaml")

    def manifest_path(self) -> Path:
        """Return the built-in guard manifest resource."""
        return self.join(self.builtin_root(), Defaults.MANIFEST_FILE_NAME)

    def join(self, root: Path, *parts: str) -> Path:
        """Join path fragments onto a source-tree path."""
        result = root

        for part in parts:
            for segment in part.replace("\\", "/").split("/"):
                if segment:
                    result = result.joinpath(segment)

        return result

    def exists(self, resource: Path) -> bool:
        """Return whether a source-tree resource exists."""
        return resource.exists()
