from pathlib import Path
from textwrap import dedent

import pytest

from code_verification_guard.config.config_manager import ConfigManager
from code_verification_guard.config.resource_locator import ResourceLocator
from code_verification_guard.constants.config_keys import ConfigKeys


def write_yaml(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(dedent(content).strip() + "\n", encoding="utf-8")


def project_config(*, registries: list[str] | None = None, scopes: list[str] | None = None) -> dict:
    return {
        ConfigKeys.PROJECT: {
            ConfigKeys.NAME: "sample",
            ConfigKeys.PROJECT_ROOT: ".",
            ConfigKeys.SOURCE_ROOTS: ["src"],
        },
        ConfigKeys.PROFILE: "local",
        ConfigKeys.RULE_SETS: {
            ConfigKeys.COMMON: False,
            ConfigKeys.LANGUAGES: [],
            ConfigKeys.PROJECTS: [],
        },
        ConfigKeys.SCOPES: scopes or [],
        ConfigKeys.REGISTRIES: registries or [],
        ConfigKeys.OVERRIDES: {
            ConfigKeys.DISABLED_RULES: [],
            ConfigKeys.SEVERITY: {},
            ConfigKeys.RULE_OPTIONS: {},
        },
    }


def profile_config(overrides: dict | None = None) -> dict:
    return {
        ConfigKeys.OVERRIDES: overrides or {},
    }


def registry_yaml(rule_id: str, severity: str = "warning") -> str:
    return f"""
    version: 1
    metadata:
      id: sample-registry
      name: Sample Registry
      description: Test registry.
    rules:
      - id: {rule_id}
        type: regex
        severity: {severity}
        enabled: true
        message: Sample rule.
        include:
          - "**/*.py"
        patterns:
          - "sample"
    """


def test_project_config_with_inline_rules_is_rejected(tmp_path: Path):
    config_path = tmp_path / "code-verification-guard.yaml"
    write_yaml(
        config_path,
        """
        version: 1
        project:
          name: sample
          root: .
          source_roots:
            - src
        rule_sets:
          common: false
          languages: []
          projects: []
        rules: []
        """,
    )

    with pytest.raises(ValueError, match="inline rules"):
        ConfigManager().load_project_config(config_path)


def test_profile_with_rules_is_rejected(tmp_path: Path):
    write_yaml(
        tmp_path / "profiles" / "bad.yaml",
        """
        version: 1
        profile:
          name: bad
        rules: []
        failure:
          fail_on:
            - error
          warning_as_error: false
        overrides:
          disabled_rules: []
          severity: {}
          rule_options: {}
        """,
    )

    with pytest.raises(ValueError, match="must not contain rules"):
        ConfigManager().load_profile_config(
            tmp_path,
            {
                ConfigKeys.PROFILE: "bad",
            },
        )


def test_duplicate_rule_ids_are_rejected(tmp_path: Path):
    write_yaml(tmp_path / "registries" / "one.yaml", registry_yaml("sample.duplicate"))
    write_yaml(tmp_path / "registries" / "two.yaml", registry_yaml("sample.duplicate"))
    config = project_config(
        registries=[
            "registries/one.yaml",
            "registries/two.yaml",
        ],
    )

    with pytest.raises(ValueError, match="Duplicate rule id"):
        ConfigManager().load_rule_definitions(tmp_path, config, profile_config())


def test_custom_scopes_and_registries_are_loaded(tmp_path: Path):
    write_yaml(
        tmp_path / "scopes" / "custom.yaml",
        """
        version: 1
        metadata:
          id: custom-scopes
          name: Custom Scopes
        scopes:
          custom_py:
            include:
              - src/**/*.py
            exclude:
              - src/generated/**
        """,
    )
    write_yaml(
        tmp_path / "registries" / "custom.yaml",
        """
        version: 1
        metadata:
          id: custom-rules
          name: Custom Rules
          description: Test rules.
        rules:
          - id: sample.custom
            type: regex
            severity: warning
            enabled: true
            message: Sample rule.
            scopes:
              - custom_py
            patterns:
              - sample
        """,
    )
    config = project_config(
        registries=["registries/custom.yaml"],
        scopes=["scopes/custom.yaml"],
    )

    rules = ConfigManager().load_rule_definitions(tmp_path, config, profile_config())

    assert rules[0][ConfigKeys.INCLUDE] == ["src/**/*.py"]
    assert rules[0][ConfigKeys.EXCLUDE] == ["src/generated/**"]


def test_dt1_load_yaml_style_rejects_indentless_lists(tmp_path: Path):
    config_path = tmp_path / "bad.yaml"
    write_yaml(
        config_path,
        """
        version: 1
        project:
          name: sample
          root: .
          source_roots:
        - src
        rule_sets:
          common: false
          languages: []
          projects: []
        """,
    )

    with pytest.raises(ValueError, match="YAML list items must be indented"):
        ConfigManager().load_project_config(config_path)


def test_dt2_load_yaml_style_allows_template_list_indentation(tmp_path: Path):
    config_path = tmp_path / "good.yaml"
    write_yaml(
        config_path,
        """
        version: 1
        project:
          name: sample
          root: .
          source_roots:
            - src
        rule_sets:
          common: false
          languages: []
          projects: []
        """,
    )

    project = ConfigManager().load_project_config(config_path)

    assert project[ConfigKeys.PROJECT][ConfigKeys.SOURCE_ROOTS] == ["src"]


def test_profile_overrides_apply_before_project_overrides(tmp_path: Path):
    write_yaml(tmp_path / "registries" / "rules.yaml", registry_yaml("sample.override"))
    config = project_config(registries=["registries/rules.yaml"])
    config[ConfigKeys.OVERRIDES][ConfigKeys.SEVERITY] = {
        "sample.override": "info",
    }
    profile = profile_config(
        {
            ConfigKeys.SEVERITY: {
                "sample.override": "error",
            },
        }
    )

    rules = ConfigManager().load_rule_definitions(tmp_path, config, profile)

    assert rules[0][ConfigKeys.SEVERITY] == "info"


def test_common_rule_set_loads_new_scopes_without_duplicate_ids():
    config = project_config()
    config[ConfigKeys.RULE_SETS][ConfigKeys.COMMON] = True

    rules = ConfigManager().load_rule_definitions(Path(".").resolve(), config, profile_config())
    rule_ids = [rule[ConfigKeys.ID] for rule in rules]

    assert len(rule_ids) == len(set(rule_ids))
    assert "common.no_multiple_blank_lines" in rule_ids
    assert "common.no_committed_environment_file" in rule_ids
    assert "security.no_hardcoded_secret_assignment" in rule_ids


def test_common_scopes_expand_to_final_scope_names():
    config = project_config()
    config[ConfigKeys.RULE_SETS][ConfigKeys.COMMON] = True

    rules = ConfigManager().load_rule_definitions(Path(".").resolve(), config, profile_config())
    rules_by_id = {
        rule[ConfigKeys.ID]: rule
        for rule in rules
    }

    assert "**/*.py" in rules_by_id["common.max_file_lines"][ConfigKeys.INCLUDE]
    assert "**/*.env" in rules_by_id["security.no_hardcoded_secret_assignment"][
        ConfigKeys.INCLUDE
    ]


def test_source_manifest_is_required_for_builtin_resources(tmp_path: Path):
    config = project_config()
    config[ConfigKeys.RULE_SETS][ConfigKeys.COMMON] = True
    manager = ConfigManager(resource_locator=ResourceLocator(source_root=tmp_path))

    with pytest.raises(FileNotFoundError, match="Built-in manifest not found"):
        manager.load_rule_definitions(tmp_path, config, profile_config())


def test_env_file_rule_targets_nested_environment_files():
    config = project_config()
    config[ConfigKeys.RULE_SETS][ConfigKeys.COMMON] = True

    rules = ConfigManager().load_rule_definitions(Path(".").resolve(), config, profile_config())
    env_rule = next(
        rule
        for rule in rules
        if rule[ConfigKeys.ID] == "common.no_committed_environment_file"
    )

    assert "**/.env" in env_rule[ConfigKeys.INCLUDE]
    assert "**/.env.*" in env_rule[ConfigKeys.INCLUDE]
    assert "**/.env.example" in env_rule[ConfigKeys.EXCLUDE]


def test_memox_rule_set_loads_ported_project_rules():
    config = project_config()
    config[ConfigKeys.RULE_SETS][ConfigKeys.LANGUAGES] = ["flutter"]
    config[ConfigKeys.RULE_SETS][ConfigKeys.PROJECTS] = ["memox"]

    rules = ConfigManager().load_rule_definitions(Path(".").resolve(), config, profile_config())
    rules_by_id = {
        rule[ConfigKeys.ID]: rule
        for rule in rules
    }

    assert "memox.no_else" in rules_by_id
    assert "memox.provider_file_naming" in rules_by_id
    assert "memox.legacy_state_notifier" in rules_by_id
    assert "memox.domain_no_flutter_import" in rules_by_id
    assert "memox.presentation_no_dart_io_imports" in rules_by_id
    assert "lib/**/*.dart" in rules_by_id["memox.no_else"][ConfigKeys.INCLUDE]
