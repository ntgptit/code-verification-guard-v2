"""Tests for the memox-v8 raw-spacing rule and every spelling it catches.

Besides ``EdgeInsets.*`` and ``SizedBox(width|height:`` with a bare number, the
rule catches ``Gap(8)``, the ``spacing:``/``runSpacing:`` parameters of
Row/Column/Wrap, and ``EdgeInsetsDirectional``; each is pinned here in both
directions: the raw literal fires, the token form does not. Loading the rule
from the registry YAML rather than re-declaring the pattern is what makes these
tests guard the rule itself, not a copy of it.
"""

from __future__ import annotations

from copy import deepcopy
from pathlib import Path

import yaml

from code_verification_guard.factory.rule_factory import RuleFactory

_RULES = (
    Path(__file__).parents[1]
    / "registries"
    / "projects"
    / "memox-v8"
    / "rules"
    / "memox-design-token-rules.yaml"
)
_RULE_ID = "memox.design_token.no_raw_spacing_literal"


def _rule_config() -> dict:
    registry = yaml.safe_load(_RULES.read_text(encoding="utf-8"))
    for rule_config in registry.get("rules", []):
        if rule_config["id"] == _RULE_ID:
            return deepcopy(rule_config)
    raise AssertionError(f"Rule not found: {_RULE_ID} in {_RULES}")


def _violations(tmp_path: Path, source: str) -> list:
    source_path = tmp_path / "lib" / "shared" / "widgets" / "sample_widget.dart"
    source_path.parent.mkdir(parents=True, exist_ok=True)
    source_path.write_text(source, encoding="utf-8")

    rule_config = _rule_config()
    rule_config.pop("scopes", None)
    rule_config["include"] = ["lib/**/*.dart"]
    rule_config["exclude"] = []
    rule_config["enabled"] = True

    return RuleFactory().create(rule_config).check(tmp_path)


# --------------------------------------------------------------------------
# The original patterns still bite.
# --------------------------------------------------------------------------


def test_raw_edge_insets_and_sized_box_are_flagged(tmp_path: Path) -> None:
    source = "\n".join(
        [
            "final a = EdgeInsets.all(15);",
            "final b = SizedBox(height: 20);",
        ]
    )
    assert len(_violations(tmp_path, source)) == 2


# --------------------------------------------------------------------------
# The widened patterns: Gap, spacing:/runSpacing:, EdgeInsetsDirectional.
# --------------------------------------------------------------------------


def test_raw_gap_is_flagged_and_token_gap_is_not(tmp_path: Path) -> None:
    assert _violations(tmp_path, "final g = Gap(8);")
    assert not _violations(tmp_path, "final g = Gap(AppSpacing.sm);")


def test_raw_spacing_parameter_is_flagged_and_token_is_not(
    tmp_path: Path,
) -> None:
    raw = "\n".join(
        [
            "final c = Column(spacing: 8, children: const []);",
            "final w = Wrap(runSpacing: 12, children: const []);",
        ]
    )
    token = "\n".join(
        [
            "final c = Column(spacing: AppSpacing.sm, children: const []);",
            "final w = Wrap(runSpacing: AppSpacing.md, children: const []);",
        ]
    )
    assert len(_violations(tmp_path, raw)) == 2
    assert not _violations(tmp_path, token)


def test_raw_edge_insets_directional_is_flagged(tmp_path: Path) -> None:
    raw = "final p = EdgeInsetsDirectional.only(start: 16);"
    token = "final p = EdgeInsetsDirectional.only(start: AppSpacing.lg);"
    assert _violations(tmp_path, raw)
    assert not _violations(tmp_path, token)


def test_text_style_letter_spacing_does_not_cross_match(tmp_path: Path) -> None:
    # `letterSpacing:` is typography, owned by the no_raw_text_style rule; the
    # spacing rule must not double-report it. Case matters: the pattern says
    # `spacing:`, not `Spacing:`.
    assert not _violations(
        tmp_path, "final s = base.copyWith(letterSpacing: 1.2);"
    )
