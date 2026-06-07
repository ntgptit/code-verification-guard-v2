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

    def load_ruleset_runtime(
        self,
        project_root: Path,
        ruleset_name: str,
        profile_override: str | None = None,
    ) -> tuple[dict, list[dict]]:
        """Load runtime config and rules from a named ruleset bundle."""
        ruleset_root, manifest = self._load_ruleset_manifest(ruleset_name)
        profile_config = self._load_ruleset_profile(
            ruleset_root,
            manifest,
            profile_override,
        )
        ruleset_config = self._load_ruleset_config(ruleset_root, manifest)
        runtime_config = self.merge_runtime_config(profile_config, ruleset_config)
        shared_paths = self._ruleset_shared_paths(project_root, manifest)
        scope_paths = self._ruleset_scope_paths(ruleset_root, manifest)
        rule_paths = self._ruleset_rule_paths(ruleset_root, manifest)
        runtime_config["_load_info"] = self._ruleset_load_info(
            ruleset_name,
            ruleset_root,
            manifest,
            shared_paths,
            scope_paths,
            rule_paths,
            profile_override,
        )
        scope_registry = self._load_scope_registry([
            *shared_paths[ConfigKeys.SCOPES],
            *scope_paths,
        ])
        rule_configs = self._load_registries([
            *shared_paths[ConfigKeys.REGISTRIES],
            *rule_paths,
        ])
        merged_overrides = self._merge_rule_overrides(
            profile_config.get(ConfigKeys.OVERRIDES, {}),
            ruleset_config.get(ConfigKeys.OVERRIDES, {}),
        )
        final_rules = self._apply_overrides(rule_configs, merged_overrides)
        normalized_rules = [
            self._normalize_rule(rule, scope_registry)
            for rule in final_rules
        ]
        self._validate_final_rules(normalized_rules)
        return runtime_config, normalized_rules

    def load_profile_config(self, project_root: Path, project_config: dict) -> dict:
        """Load the selected profile configuration."""
        profile_name = project_config.get(ConfigKeys.PROFILE) or Defaults.DEFAULT_PROFILE
        profile_path = self.resource_locator.profile_path(project_root, profile_name)

        profile_config = self._load_yaml(profile_path)
        self._validate_profile_config(profile_config, profile_path)
        return profile_config

    def _load_ruleset_manifest(self, ruleset_name: str) -> tuple[Path, dict]:
        """Load and validate a ruleset-local guard manifest."""
        tool_root = self.resource_locator.builtin_root()
        ruleset_root = self.resource_locator.join(
            tool_root,
            Defaults.REGISTRIES_DIRECTORY,
            Defaults.PROJECTS_DIRECTORY,
            ruleset_name,
        )

        if not self.resource_locator.exists(ruleset_root):
            raise FileNotFoundError(f"Ruleset not found: {ruleset_name}")

        manifest_path = self.resource_locator.join(
            ruleset_root,
            Defaults.MANIFEST_FILE_NAME,
        )

        if not self.resource_locator.exists(manifest_path):
            raise FileNotFoundError(f"Ruleset guard-manifest.yaml not found: {manifest_path}")

        manifest = self._load_yaml(manifest_path)
        self._validate_ruleset_manifest(manifest, manifest_path, ruleset_name)
        return ruleset_root, manifest

    def _load_ruleset_profile(
        self,
        ruleset_root: Path,
        manifest: dict,
        profile_override: str | None,
    ) -> dict:
        """Load the selected ruleset profile config."""
        profile_name = profile_override or manifest.get(ConfigKeys.PROFILE) or Defaults.DEFAULT_PROFILE
        profiles_path = self._ruleset_config_path(
            ruleset_root,
            manifest,
            ConfigKeys.PROFILES,
        )
        profiles_document = self._load_yaml(profiles_path)
        self._validate_ruleset_profiles(profiles_document, profiles_path)
        profiles = profiles_document.get(ConfigKeys.PROFILES, {})
        profile_config = profiles.get(profile_name)

        if profile_config is None:
            raise ValueError(f"Ruleset profile not found: {profile_name}")

        return self._normalize_ruleset_profile(profile_name, profile_config)

    def _load_ruleset_config(self, ruleset_root: Path, manifest: dict) -> dict:
        """Load ruleset overrides and manifest-level runtime config."""
        ruleset_config = deepcopy(manifest)
        overrides_path = self._ruleset_config_path(
            ruleset_root,
            manifest,
            ConfigKeys.OVERRIDES,
        )
        overrides_document = self._load_yaml(overrides_path)
        self._validate_ruleset_overrides(overrides_document, overrides_path)
        ruleset_config[ConfigKeys.OVERRIDES] = overrides_document.get(
            ConfigKeys.OVERRIDES,
            {},
        )
        return ruleset_config

    def _ruleset_config_path(self, ruleset_root: Path, manifest: dict, key: str) -> Path:
        """Resolve one ruleset config path."""
        config_block = manifest.get(ConfigKeys.CONFIG, {})
        path_text = config_block.get(key)

        if not path_text:
            raise ValueError(f"Ruleset manifest config missing '{key}'")

        return self._resolve_ruleset_path(ruleset_root, path_text)

    def _ruleset_scope_paths(self, ruleset_root: Path, manifest: dict) -> list[Path]:
        """Resolve ruleset scope document paths."""
        config_block = manifest.get(ConfigKeys.CONFIG, {})
        return [
            self._resolve_ruleset_path(ruleset_root, path_text)
            for path_text in self._as_string_list(config_block.get(ConfigKeys.SCOPES, []))
        ]

    def _ruleset_rule_paths(self, ruleset_root: Path, manifest: dict) -> list[Path]:
        """Resolve ruleset rule registry paths."""
        return [
            self._resolve_ruleset_path(ruleset_root, path_text)
            for path_text in self._as_string_list(manifest.get(ConfigKeys.RULES, []))
        ]

    def _ruleset_shared_paths(self, project_root: Path, manifest: dict) -> dict:
        """Resolve shared rule set paths selected by a ruleset manifest."""
        if ConfigKeys.RULE_SETS not in manifest:
            return {
                ConfigKeys.SCOPES: [],
                ConfigKeys.REGISTRIES: [],
            }

        resolver = RuleSetResolver(
            self.resource_locator.builtin_root(),
            resource_locator=self.resource_locator,
        )
        return resolver.resolve(
            project_root,
            {
                ConfigKeys.RULE_SETS: manifest.get(ConfigKeys.RULE_SETS, {}),
                ConfigKeys.SCOPES: [],
                ConfigKeys.REGISTRIES: [],
            },
        )

    def _ruleset_load_info(
        self,
        ruleset_name: str,
        ruleset_root: Path,
        manifest: dict,
        shared_paths: dict,
        scope_paths: list[Path],
        rule_paths: list[Path],
        profile_override: str | None,
    ) -> dict:
        """Build user-facing load metadata for console diagnostics."""
        profile_name = (
            profile_override
            or manifest.get(ConfigKeys.PROFILE)
            or Defaults.DEFAULT_PROFILE
        )
        return {
            "ruleset": ruleset_name,
            "profile": profile_name,
            "ruleset_root": str(ruleset_root),
            "manifest": str(
                self.resource_locator.join(
                    ruleset_root,
                    Defaults.MANIFEST_FILE_NAME,
                )
            ),
            "config": {
                ConfigKeys.PROFILES: str(
                    self._ruleset_config_path(
                        ruleset_root,
                        manifest,
                        ConfigKeys.PROFILES,
                    )
                ),
                ConfigKeys.SCOPES: str(
                    self._ruleset_config_path(
                        ruleset_root,
                        manifest,
                        ConfigKeys.SCOPES,
                    )
                ),
                ConfigKeys.OVERRIDES: str(
                    self._ruleset_config_path(
                        ruleset_root,
                        manifest,
                        ConfigKeys.OVERRIDES,
                    )
                ),
            },
            "shared_scopes": [
                str(path)
                for path in shared_paths.get(ConfigKeys.SCOPES, [])
            ],
            "shared_registries": [
                str(path)
                for path in shared_paths.get(ConfigKeys.REGISTRIES, [])
            ],
            "ruleset_scopes": [
                str(path)
                for path in scope_paths
            ],
            "ruleset_registries": [
                str(path)
                for path in rule_paths
            ],
        }

    def _resolve_ruleset_path(self, ruleset_root: Path, path_text: str) -> Path:
        """Resolve a ruleset-local resource path."""
        path = Path(path_text)

        if path.is_absolute():
            return path

        return self.resource_locator.join(ruleset_root, path_text)

    def _as_string_list(self, value: Any) -> list[str]:
        """Normalize a scalar or list config field to strings."""
        if isinstance(value, str):
            return [value]

        if not isinstance(value, list):
            raise ValueError("Ruleset path fields must be strings or string lists")

        for item in value:
            if not isinstance(item, str):
                raise ValueError("Ruleset path fields must contain only strings")

        return value

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

    def _validate_ruleset_manifest(
        self,
        document: dict,
        path: Path,
        ruleset_name: str,
    ) -> None:
        """Validate the ruleset manifest contract."""
        self._validate_document_version(document, path)

        ruleset_block = document.get(ConfigKeys.RULESET)
        if not isinstance(ruleset_block, dict):
            raise ValueError(f"Ruleset manifest must define ruleset metadata: {path}")

        if ruleset_block.get(ConfigKeys.NAME) != ruleset_name:
            raise ValueError(f"Ruleset manifest name must match requested ruleset: {path}")

        if not isinstance(document.get(ConfigKeys.CONFIG), dict):
            raise ValueError(f"Ruleset manifest must define config paths: {path}")

        if ConfigKeys.RULE_SETS in document and not isinstance(
            document.get(ConfigKeys.RULE_SETS),
            dict,
        ):
            raise ValueError(f"Ruleset manifest rule_sets must be a mapping: {path}")

        if not isinstance(document.get(ConfigKeys.RULES), list):
            raise ValueError(f"Ruleset manifest rules must be a list: {path}")

    def _validate_ruleset_profiles(self, document: dict, path: Path) -> None:
        """Validate a ruleset profiles document."""
        self._validate_document_version(document, path)

        profiles = document.get(ConfigKeys.PROFILES)
        if not isinstance(profiles, dict):
            raise ValueError(f"Ruleset profiles must be a mapping: {path}")

    def _validate_ruleset_overrides(self, document: dict, path: Path) -> None:
        """Validate a ruleset overrides document."""
        self._validate_document_version(document, path)

        if not isinstance(document.get(ConfigKeys.OVERRIDES, {}), dict):
            raise ValueError(f"Ruleset overrides must be a mapping: {path}")

    def _normalize_ruleset_profile(self, profile_name: str, profile_config: dict) -> dict:
        """Normalize a profile entry from a ruleset profiles document."""
        if not isinstance(profile_config, dict):
            raise ValueError(f"Ruleset profile must be a mapping: {profile_name}")

        normalized = deepcopy(profile_config)
        normalized[ConfigKeys.VERSION] = Defaults.SCHEMA_VERSION
        normalized.setdefault(
            ConfigKeys.PROFILE,
            {
                ConfigKeys.NAME: profile_name,
            },
        )
        self._validate_profile_config(normalized, Path(f"<ruleset-profile:{profile_name}>"))
        return normalized

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
        pattern = r"^[a-z][a-z0-9_]*(?:\.[a-z][a-z0-9_]*)+$"

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
            ConfigKeys.WIDGET_BASE_CLASSES,
            ConfigKeys.STATE_FIELD_NAMES,
            ConfigKeys.VARIANT_FIELD_NAMES,
            ConfigKeys.ALLOWED_VALUES,
            ConfigKeys.KNOWN_CONTRACTS,
            ConfigKeys.ONLY_CATEGORIES,
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
