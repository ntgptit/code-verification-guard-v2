"""Configuration and registry loading."""

from __future__ import annotations

from copy import deepcopy
from pathlib import Path
import re
from typing import Any

import yaml

from code_verification_guard.config.resource_locator import ResourceLocator
from code_verification_guard.config.rule_set_resolver import RuleSetResolver
from code_verification_guard.constants.config_keys import ConfigKeys
from code_verification_guard.constants.defaults import Defaults
from code_verification_guard.constants.rule_types import RuleType
from code_verification_guard.constants.severity import Severity
from code_verification_guard.registry.scope_registry import ScopeRegistry


class ConfigManager:
    """Loads project configuration, scopes, profiles, and rule registries."""

    def __init__(self, resource_locator: ResourceLocator | None = None):
        """Create a config manager with a resource locator."""
        self.resource_locator = resource_locator or ResourceLocator()

    def load_project_config(self, config_path: Path) -> dict:
        """Load and validate the project configuration file."""
        # Project config is the single entrypoint for a checked project.
        if not config_path.exists():
            raise FileNotFoundError(f"Config file not found: {config_path}")

        project_config = self._load_yaml(config_path)
        self._validate_project_config(project_config, config_path)
        return project_config

    def load_profile_config(self, project_root: Path, project_config: dict) -> dict:
        """Load the selected profile configuration."""
        profile_name = project_config.get(ConfigKeys.PROFILE) or Defaults.DEFAULT_PROFILE
        profile_path = self.resource_locator.profile_path(project_root, profile_name)

        profile_config = self._load_yaml(profile_path)
        self._validate_profile_config(profile_config, profile_path)
        return profile_config

    def merge_runtime_config(self, profile_config: dict, project_config: dict) -> dict:
        """Merge runtime settings with project precedence."""
        return self._deep_merge(profile_config, project_config)

    def load_rule_definitions(
        self,
        project_root: Path,
        project_config: dict,
        profile_config: dict | None = None,
    ) -> list[dict]:
        """Load final rule definitions for a project."""
        tool_root = self.resource_locator.builtin_root()
        resolver = RuleSetResolver(tool_root, resource_locator=self.resource_locator)
        resolved_paths = resolver.resolve(project_root, project_config)
        scope_registry = self._load_scope_registry(resolved_paths[ConfigKeys.SCOPES])
        rule_configs = self._load_registries(resolved_paths[ConfigKeys.REGISTRIES])

        # Direct callers may provide only the project config.
        if profile_config is None:
            profile_config = self.load_profile_config(project_root, project_config)

        profile_overrides = profile_config.get(ConfigKeys.OVERRIDES, {})
        project_overrides = project_config.get(ConfigKeys.OVERRIDES, {})
        merged_overrides = self._merge_rule_overrides(profile_overrides, project_overrides)
        final_rules = self._apply_overrides(rule_configs, merged_overrides)
        normalized_rules = [
            self._normalize_rule(rule, scope_registry)
            for rule in final_rules
        ]
        self._validate_final_rules(normalized_rules)
        return normalized_rules

    def _load_registries(self, registry_paths: list[Any]) -> list[dict]:
        """Load rule configs from registry files."""
        rule_configs: list[dict] = []
        rule_ids: set[str] = set()

        for registry_path in registry_paths:
            registry = self._load_registry(registry_path)
            for rule in registry.get(ConfigKeys.RULES, []):
                self._validate_rule(rule, registry_path, rule_ids)
                rule_configs.append(deepcopy(rule))

        return rule_configs

    def _load_registry(self, registry_path: Any) -> dict:
        """Load and validate one rule registry file."""
        registry = self._load_yaml(registry_path)
        self._validate_registry_document(registry, registry_path)
        return registry

    def _load_yaml(self, path: Any) -> dict:
        """Read a YAML file as a dictionary."""
        # Contract files must exist before loading starts.
        if not self.resource_locator.exists(path):
            raise FileNotFoundError(f"YAML file not found: {path}")

        self._validate_yaml_source_format(path)

        with path.open("r", encoding="utf-8") as file:
            document = yaml.safe_load(file) or {}

        # YAML contract documents must be mappings.
        if not isinstance(document, dict):
            raise ValueError(f"YAML document must be a mapping: {path}")

        return document

    def _validate_yaml_source_format(self, path: Any) -> None:
        """Validate repository YAML source style before parsing."""
        with path.open("r", encoding="utf-8") as file:
            for line_number, line in enumerate(file, start=1):
                if re.match(r"^-\s+", line):
                    raise ValueError(
                        "YAML list items must be indented under their parent key "
                        f"in {path}:{line_number}"
                    )

    def _apply_overrides(self, rule_configs: list[dict], overrides: dict) -> list[dict]:
        """Apply merged rule overrides."""
        disabled_rules = set(overrides.get(ConfigKeys.DISABLED_RULES, []))
        severity_overrides = overrides.get(ConfigKeys.SEVERITY, {})
        rule_options = overrides.get(ConfigKeys.RULE_OPTIONS, {})
        result: list[dict] = []

        for original_rule in rule_configs:
            rule = deepcopy(original_rule)
            rule_id = rule.get(ConfigKeys.ID)

            # Disabled rules are removed before execution.
            if rule_id in disabled_rules:
                continue

            # Overrides may adjust rule severity.
            if rule_id in severity_overrides:
                rule[ConfigKeys.SEVERITY] = severity_overrides[rule_id]

            # Overrides may tune individual rule options.
            if rule_id in rule_options:
                rule.update(rule_options[rule_id])

            result.append(rule)

        return result

    def _merge_rule_overrides(self, profile_overrides: dict, project_overrides: dict) -> dict:
        """Merge rule overrides with project precedence."""
        merged = self._deep_merge(profile_overrides, project_overrides)
        disabled_rules = [
            *profile_overrides.get(ConfigKeys.DISABLED_RULES, []),
            *project_overrides.get(ConfigKeys.DISABLED_RULES, []),
        ]
        merged[ConfigKeys.DISABLED_RULES] = list(dict.fromkeys(disabled_rules))
        return merged

    def _load_scope_registry(self, scope_paths: list[Any]) -> ScopeRegistry:
        """Load selected scope definitions."""
        registry = ScopeRegistry()
        registry.clear()

        for scope_path in scope_paths:
            self._register_scopes(registry, scope_path)

        return registry

    def _register_scopes(self, registry: ScopeRegistry, scope_path: Any) -> None:
        """Register scopes from one scope document."""
        document = self._load_yaml(scope_path)
        self._validate_scope_document(document, scope_path)

        for name, config in document.get(ConfigKeys.SCOPES, {}).items():
            registry.register(
                name,
                config.get(ConfigKeys.INCLUDE, []),
                config.get(ConfigKeys.EXCLUDE, []),
            )

    def _normalize_rule(self, rule: dict, scope_registry: ScopeRegistry) -> dict:
        """Expand scope references for one rule config."""
        normalized_rule = deepcopy(rule)
        scope_name = normalized_rule.get(ConfigKeys.SCOPE)
        scope_names = normalized_rule.get(ConfigKeys.SCOPES, [])

        # Single scope references are normalized into the multi-scope form.
        if scope_name:
            scope_names = [scope_name, *scope_names]

        # Scope references expand into include and exclude patterns.
        if scope_names:
            scoped_patterns = self._resolve_rule_scopes(scope_registry, scope_names)
            normalized_rule[ConfigKeys.INCLUDE] = [
                *scoped_patterns.get(ConfigKeys.INCLUDE, []),
                *normalized_rule.get(ConfigKeys.INCLUDE, []),
            ]
            normalized_rule[ConfigKeys.EXCLUDE] = [
                *scoped_patterns.get(ConfigKeys.EXCLUDE, []),
                *normalized_rule.get(ConfigKeys.EXCLUDE, []),
            ]

        return normalized_rule

    def _resolve_rule_scopes(
        self,
        scope_registry: ScopeRegistry,
        scope_names: list[str],
    ) -> dict:
        """Resolve rule scope names into include and exclude patterns."""
        include_patterns: list[str] = []
        exclude_patterns: list[str] = []

        for scope_name in scope_names:
            # Rule scopes must be registered before registry rules are loaded.
            if not scope_registry.contains(scope_name):
                raise ValueError(f"Unknown rule scope: {scope_name}")

            scope = scope_registry.get(scope_name)
            include_patterns.extend(scope.get(ConfigKeys.INCLUDE, []))
            exclude_patterns.extend(scope.get(ConfigKeys.EXCLUDE, []))

        return {
            ConfigKeys.INCLUDE: include_patterns,
            ConfigKeys.EXCLUDE: exclude_patterns,
        }

    def _validate_project_config(self, document: dict, path: Path) -> None:
        """Validate the project config contract."""
        self._validate_document_version(document, path)

        # Project config must not define inline rules.
        if ConfigKeys.RULES in document:
            raise ValueError(f"Project config must not contain inline rules: {path}")

        # Project config must identify the checked project.
        if not isinstance(document.get(ConfigKeys.PROJECT), dict):
            raise ValueError(f"Project config must define project metadata: {path}")

        # Project config must declare selected rule sets.
        if not isinstance(document.get(ConfigKeys.RULE_SETS), dict):
            raise ValueError(f"Project config must define rule sets: {path}")

    def _validate_profile_config(self, document: dict, path: Path) -> None:
        """Validate the profile config contract."""
        self._validate_document_version(document, path)

        # Profiles must only override behavior, not define new rules.
        if ConfigKeys.RULES in document:
            raise ValueError(f"Profile config must not contain rules: {path}")

        profile_block = document.get(ConfigKeys.PROFILE)

        # Profiles must declare their own name.
        if not isinstance(profile_block, dict):
            raise ValueError(f"Profile config must define profile metadata: {path}")

        # Profile name is required for traceability.
        if not profile_block.get(ConfigKeys.NAME):
            raise ValueError(f"Profile config must define profile name: {path}")

    def _validate_registry_document(self, document: dict, path: Path) -> None:
        """Validate the rule registry contract."""
        self._validate_document_version(document, path)
        metadata = document.get(ConfigKeys.METADATA)

        # Rule registry metadata must be a mapping.
        if not isinstance(metadata, dict):
            raise ValueError(f"Rule registry metadata must be a mapping: {path}")

        for key in [ConfigKeys.ID, ConfigKeys.NAME, ConfigKeys.DESCRIPTION]:
            # Rule registry metadata requires these fields.
            if not metadata.get(key):
                raise ValueError(f"Rule registry metadata missing '{key}' in {path}")

        # Rule registry entries must be stored in a list.
        if not isinstance(document.get(ConfigKeys.RULES, []), list):
            raise ValueError(f"Rule registry rules must be a list: {path}")

    def _validate_scope_document(self, document: dict, path: Path) -> None:
        """Validate the scope registry contract."""
        self._validate_document_version(document, path)
        metadata = document.get(ConfigKeys.METADATA)

        # Scope registry metadata must be a mapping.
        if not isinstance(metadata, dict):
            raise ValueError(f"Scope registry metadata must be a mapping: {path}")

        for key in [ConfigKeys.ID, ConfigKeys.NAME]:
            # Scope registry metadata requires these fields.
            if not metadata.get(key):
                raise ValueError(f"Scope registry metadata missing '{key}' in {path}")

        scopes = document.get(ConfigKeys.SCOPES)

        # Scope registries must define named scopes.
        if not isinstance(scopes, dict):
            raise ValueError(f"Scope registry scopes must be a mapping: {path}")

        for scope_name, scope_config in scopes.items():
            self._validate_scope_config(scope_name, scope_config, path)

    def _validate_scope_config(
        self,
        scope_name: str,
        scope_config: dict,
        path: Path,
    ) -> None:
        """Validate one scope config."""
        # Scope entries must be mappings.
        if not isinstance(scope_config, dict):
            raise ValueError(f"Scope '{scope_name}' must be a mapping in {path}")

        for key in [ConfigKeys.INCLUDE, ConfigKeys.EXCLUDE]:
            # Scope include and exclude entries must stay list-shaped.
            if key in scope_config and not isinstance(scope_config[key], list):
                raise ValueError(f"Scope '{scope_name}' field '{key}' must be a list in {path}")

    def _validate_final_rules(self, rules: list[dict]) -> None:
        """Validate final rule configs after overrides."""
        rule_ids: set[str] = set()

        for rule in rules:
            self._validate_rule(rule, Path("<final-rules>"), rule_ids)

    def _validate_document_version(self, document: dict, path: Path) -> None:
        """Validate common YAML document version."""
        version = document.get(ConfigKeys.VERSION)

        # Every YAML contract document must declare the supported version.
        if version != Defaults.SCHEMA_VERSION:
            raise ValueError(f"Unsupported YAML schema version in {path}: {version}")

    def _validate_rule(self, rule: dict, path: Path, rule_ids: set[str]) -> None:
        """Validate one rule against the registry contract."""
        required_keys = [
            ConfigKeys.ID,
            ConfigKeys.TYPE,
            ConfigKeys.SEVERITY,
            ConfigKeys.ENABLED,
            ConfigKeys.MESSAGE,
        ]

        for key in required_keys:
            # Rule contract requires these fields in every registry rule.
            if key not in rule:
                raise ValueError(f"Missing rule field '{key}' in {path}")

        rule_id = rule[ConfigKeys.ID]

        # Rule IDs must be globally unique across loaded registries.
        if rule_id in rule_ids:
            raise ValueError(f"Duplicate rule id '{rule_id}' in {path}")

        rule_ids.add(rule_id)
        self._validate_rule_id(rule_id, path)
        self._validate_rule_type(rule[ConfigKeys.TYPE], path)
        self._validate_rule_severity(rule[ConfigKeys.SEVERITY], path)
        self._validate_regex_mode(rule, path)

        # Enabled must be explicit and boolean.
        if not isinstance(rule[ConfigKeys.ENABLED], bool):
            raise ValueError(f"Rule '{rule_id}' has non-boolean enabled in {path}")

        self._validate_optional_rule_fields(rule, path)

    def _validate_regex_mode(self, rule: dict, path: Path) -> None:
        """Validate optional regex matcher mode."""
        # Mode is optional and defaults to line mode.
        if ConfigKeys.MODE not in rule:
            return

        rule_id = rule[ConfigKeys.ID]

        # Mode is currently part of the regex rule contract only.
        if rule[ConfigKeys.TYPE] != RuleType.REGEX:
            raise ValueError(f"Rule '{rule_id}' mode is only supported for regex in {path}")

        # Regex mode must be a scalar string.
        if not isinstance(rule[ConfigKeys.MODE], str):
            raise ValueError(f"Rule '{rule_id}' mode must be a string in {path}")

        valid_modes = {
            Defaults.REGEX_LINE_MODE,
            Defaults.REGEX_FILE_MODE,
        }

        # Regex mode must use a supported matcher scan mode.
        if rule[ConfigKeys.MODE] not in valid_modes:
            raise ValueError(f"Invalid regex mode '{rule[ConfigKeys.MODE]}' in {path}")

    def _validate_rule_id(self, rule_id: str, path: Path) -> None:
        """Validate namespaced rule id format."""
        pattern = r"^[a-z][a-z0-9_]*\.[a-z][a-z0-9_]*(?:_[a-z0-9]+)*$"

        # Namespaced IDs keep rules traceable across registries.
        if not re.match(pattern, rule_id):
            raise ValueError(f"Invalid namespaced rule id '{rule_id}' in {path}")

    def _validate_rule_type(self, rule_type: str, path: Path) -> None:
        """Validate rule type value."""
        valid_types = {item.value for item in RuleType}

        # Rule types must map to a known matcher.
        if rule_type not in valid_types:
            raise ValueError(f"Invalid rule type '{rule_type}' in {path}")

    def _validate_rule_severity(self, severity: str, path: Path) -> None:
        """Validate severity value."""
        valid_severities = {item.value for item in Severity}

        # Severity must be one of the supported reporting levels.
        if severity not in valid_severities:
            raise ValueError(f"Invalid rule severity '{severity}' in {path}")

    def _validate_optional_rule_fields(self, rule: dict, path: Path) -> None:
        """Validate optional rule contract fields when present."""
        for key in [
            ConfigKeys.INCLUDE,
            ConfigKeys.EXCLUDE,
            ConfigKeys.SCOPES,
            ConfigKeys.PATTERNS,
            ConfigKeys.TAGS,
            ConfigKeys.NODE_TYPES,
        ]:
            self._validate_string_list(rule, key, path)

        # Pattern must be a scalar string when present.
        if ConfigKeys.PATTERN in rule and not isinstance(rule[ConfigKeys.PATTERN], str):
            raise ValueError(f"Rule field '{ConfigKeys.PATTERN}' must be a string in {path}")

        # Max lines must be a number when present.
        if ConfigKeys.MAX_LINES in rule and not isinstance(rule[ConfigKeys.MAX_LINES], int):
            raise ValueError(f"Rule field '{ConfigKeys.MAX_LINES}' must be a number in {path}")

        self._validate_fix(rule, path)

    def _validate_string_list(self, rule: dict, key: str, path: Path) -> None:
        """Validate an optional string list field."""
        # Missing optional list fields need no validation.
        if key not in rule:
            return

        # Optional list fields must stay list-shaped.
        if not isinstance(rule[key], list):
            raise ValueError(f"Rule field '{key}' must be a list in {path}")

        for value in rule[key]:
            # Optional list values must be strings.
            if not isinstance(value, str):
                raise ValueError(f"Rule field '{key}' values must be strings in {path}")

    def _validate_fix(self, rule: dict, path: Path) -> None:
        """Validate optional fix metadata."""
        # Rules may omit fix metadata.
        if ConfigKeys.FIX not in rule:
            return

        fix_config = rule[ConfigKeys.FIX]

        # Fix metadata must be a mapping when present.
        if not isinstance(fix_config, dict):
            raise ValueError(f"Rule field '{ConfigKeys.FIX}' must be a mapping in {path}")

        for key in [ConfigKeys.HINT, ConfigKeys.EXAMPLE_BAD, ConfigKeys.EXAMPLE_GOOD]:
            # Fix metadata values must be strings when present.
            if key in fix_config and not isinstance(fix_config[key], str):
                raise ValueError(f"Rule fix field '{key}' must be a string in {path}")

    def _deep_merge(self, base: dict, override: dict) -> dict:
        """Merge two dictionaries recursively with override precedence."""
        result = deepcopy(base)

        for key, value in override.items():
            base_value = result.get(key)

            # Nested dictionaries are merged recursively.
            if isinstance(base_value, dict) and isinstance(value, dict):
                result[key] = self._deep_merge(base_value, value)
                continue

            result[key] = value

        return result
