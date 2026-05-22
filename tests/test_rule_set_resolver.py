from pathlib import Path
from textwrap import dedent

import yaml

from code_verification_guard.config.rule_set_resolver import RuleSetResolver
from code_verification_guard.constants.config_keys import ConfigKeys


def write_yaml(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(dedent(content).strip() + "\n", encoding="utf-8")


def test_manifest_resolves_selected_rule_sets(tmp_path: Path):
    tool_root = tmp_path / "tool"
    manifest_path = tool_root / "guard-manifest.yaml"
    write_yaml(
        manifest_path,
        """
        version: 1
        rule_sets:
          common:
            scopes:
              - scopes/common.yaml
            registries:
              - registries/common.yaml
          python:
            scopes:
              - scopes/python.yaml
            registries:
              - registries/python.yaml
          memox:
            scopes:
              - scopes/flutter.yaml
            registries:
              - registries/memox.yaml
        """,
    )

    resolver = RuleSetResolver(tool_root)
    resolved = resolver.resolve(
        tmp_path / "project",
        {
            ConfigKeys.RULE_SETS: {
                ConfigKeys.COMMON: True,
                ConfigKeys.LANGUAGES: ["python"],
                ConfigKeys.PROJECTS: ["memox"],
            },
            ConfigKeys.SCOPES: [],
            ConfigKeys.REGISTRIES: [],
        },
    )

    assert tool_root / "scopes/common.yaml" in resolved[ConfigKeys.SCOPES]
    assert tool_root / "scopes/python.yaml" in resolved[ConfigKeys.SCOPES]
    assert tool_root / "scopes/flutter.yaml" in resolved[ConfigKeys.SCOPES]
    assert tool_root / "registries/common.yaml" in resolved[ConfigKeys.REGISTRIES]
    assert tool_root / "registries/python.yaml" in resolved[ConfigKeys.REGISTRIES]
    assert tool_root / "registries/memox.yaml" in resolved[ConfigKeys.REGISTRIES]


def test_builtin_manifest_common_loads_all_common_registries():
    manifest = yaml.safe_load(Path("guard-manifest.yaml").read_text(encoding="utf-8"))
    common_registries = manifest[ConfigKeys.RULE_SETS][ConfigKeys.COMMON][
        ConfigKeys.REGISTRIES
    ]

    assert common_registries == [
        "registries/common/common-code-rules.yaml",
        "registries/common/common-security-rules.yaml",
        "registries/common/common-naming-rules.yaml",
        "registries/common/common-convention-rules.yaml",
        "registries/common/common-file-rules.yaml",
    ]
