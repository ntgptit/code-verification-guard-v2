"""Manifest-driven rule set path resolution."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from code_verification_guard.config.resource_locator import ResourceLocator
from code_verification_guard.constants.config_keys import ConfigKeys
from code_verification_guard.constants.defaults import Defaults


class RuleSetResolver:
    """Resolves selected rule sets through the guard manifest."""

    def __init__(
        self,
        tool_root: Any,
        manifest_path: Any | None = None,
        resource_locator: ResourceLocator | None = None,
    ):
        """Create a resolver rooted at the installed tool directory."""
        self.tool_root = tool_root
        self.resource_locator = resource_locator or ResourceLocator()
        self.manifest_path = manifest_path or self.resource_locator.join(
            tool_root,
            Defaults.MANIFEST_FILE_NAME,
        )
        self.manifest = self._load_manifest(self.manifest_path)

    def resolve(self, project_root: Path, project_config: dict) -> dict:
        """Resolve selected scope and registry paths for a project config."""
        result = {
            ConfigKeys.SCOPES: [],
            ConfigKeys.REGISTRIES: [],
        }

        for rule_set_name in self._selected_rule_sets(project_config):
            rule_set = self._manifest_rule_set(rule_set_name)
            result[ConfigKeys.SCOPES].extend(
                self._resolve_builtin_paths(rule_set.get(ConfigKeys.SCOPES, []))
            )
            result[ConfigKeys.REGISTRIES].extend(
                self._resolve_builtin_paths(rule_set.get(ConfigKeys.REGISTRIES, []))
            )

        for custom_scope in project_config.get(ConfigKeys.SCOPES, []):
            result[ConfigKeys.SCOPES].append(
                self._resolve_project_path(project_root, custom_scope)
            )

        for custom_registry in project_config.get(ConfigKeys.REGISTRIES, []):
            result[ConfigKeys.REGISTRIES].append(
                self._resolve_project_path(project_root, custom_registry)
            )

        return result

    def _load_manifest(self, manifest_path: Any) -> dict:
        """Load and validate the guard manifest."""
        # The manifest is the only builtin rule set source.
        if not self.resource_locator.exists(manifest_path):
            raise FileNotFoundError(f"Manifest file not found: {manifest_path}")

        with manifest_path.open("r", encoding="utf-8") as file:
            manifest = yaml.safe_load(file) or {}

        # Manifest files must use the supported schema version.
        if manifest.get(ConfigKeys.VERSION) != Defaults.SCHEMA_VERSION:
            raise ValueError(f"Unsupported manifest schema version in {manifest_path}")

        # Manifest files must define available rule sets.
        if not isinstance(manifest.get(ConfigKeys.RULE_SETS), dict):
            raise ValueError(f"Manifest rule sets must be a mapping in {manifest_path}")

        return manifest

    def _selected_rule_sets(self, project_config: dict) -> list[str]:
        """Return rule set names selected by the project config."""
        rule_sets = project_config.get(ConfigKeys.RULE_SETS, {})
        selected: list[str] = []

        # Common rules are enabled unless the project opts out.
        if rule_sets.get(ConfigKeys.COMMON, True):
            selected.append(ConfigKeys.COMMON)

        selected.extend(rule_sets.get(ConfigKeys.LANGUAGES, []))
        selected.extend(rule_sets.get(ConfigKeys.PROJECTS, []))
        return selected

    def _manifest_rule_set(self, rule_set_name: str) -> dict:
        """Return one manifest rule set entry."""
        rule_sets = self.manifest.get(ConfigKeys.RULE_SETS, {})
        rule_set = rule_sets.get(rule_set_name)

        # Selected rule sets must be present in the manifest.
        if rule_set is None:
            raise ValueError(f"Unsupported rule set: {rule_set_name}")

        return rule_set

    def _resolve_builtin_paths(self, paths: list[str]) -> list[Any]:
        """Resolve manifest paths relative to the tool root."""
        return [
            self.resource_locator.join(self.tool_root, path)
            for path in paths
        ]

    def _resolve_project_path(self, project_root: Path, path_text: str) -> Path:
        """Resolve a custom project path."""
        path = Path(path_text)

        # Absolute custom paths can be used as-is.
        if path.is_absolute():
            return path

        return project_root / path
