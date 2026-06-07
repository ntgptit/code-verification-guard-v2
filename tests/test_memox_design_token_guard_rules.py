"""Integration-style tests for MemoX design-token guard regex rules."""

from __future__ import annotations

from copy import deepcopy
from pathlib import Path

import yaml

from code_verification_guard.factory.rule_factory import RuleFactory

REGISTRY_DIR = (
    Path(__file__).parents[1] / "registries" / "projects" / "memox" / "rules"
)


def _rule_config(rule_id: str) -> dict:
    for registry_path in REGISTRY_DIR.glob("*-rules.yaml"):
        registry = yaml.safe_load(registry_path.read_text(encoding="utf-8"))
        for rule_config in registry.get("rules", []):
            if rule_config["id"] == rule_id:
                return deepcopy(rule_config)

    raise AssertionError(f"Rule not found: {rule_id}")


def _violations(
    rule_id: str,
    tmp_path: Path,
    source: str,
    *,
    relative_path: str,
    exclude: list[str] | None = None,
) -> list:
    source_path = tmp_path / relative_path
    source_path.parent.mkdir(parents=True, exist_ok=True)
    source_path.write_text(source, encoding="utf-8")

    rule_config = _rule_config(rule_id)
    rule_config.pop("scopes", None)
    rule_config["include"] = ["lib/**/*.dart"]
    rule_config["exclude"] = exclude or []
    rule_config["enabled"] = True

    return RuleFactory().create(rule_config).check(tmp_path)


def test_token_arithmetic_is_forbidden_in_feature_ui(tmp_path: Path) -> None:
    bad = """
    class SampleScreen extends StatelessWidget {
      @override
      Widget build(BuildContext context) {
        return SizedBox(height: SpacingTokens.xxs / 2);
      }
    }
    """
    good = """
    class SampleScreen extends StatelessWidget {
      @override
      Widget build(BuildContext context) {
        return const SizedBox(height: SpacingTokens.xxs);
      }
    }
    """
    token_file = """
    abstract final class SampleSpacingTokens {
      SampleSpacingTokens._();

      static const double hairline = SpacingTokens.xxs / 2;
    }
    """

    assert _violations(
        "design.no_token_arithmetic_in_ui",
        tmp_path,
        bad,
        relative_path="lib/presentation/features/sample/sample_screen.dart",
    )
    assert not _violations(
        "design.no_token_arithmetic_in_ui",
        tmp_path,
        good,
        relative_path="lib/presentation/features/sample/sample_screen.dart",
    )
    assert not _violations(
        "design.no_token_arithmetic_in_ui",
        tmp_path,
        token_file,
        relative_path="lib/core/theme/tokens/sample_spacing_tokens.dart",
        exclude=["lib/core/theme/tokens/**"],
    )


def test_spacing_token_is_forbidden_for_divider_border_and_stroke_properties(
    tmp_path: Path,
) -> None:
    bad = """
    class SampleCard extends StatelessWidget {
      @override
      Widget build(BuildContext context) {
        return Column(
          children: [
            Divider(thickness: SpacingTokens.xxs),
            SizedBox(
              height: SpacingTokens.xxs / 2,
              child: const ColoredBox(color: Colors.red),
            ),
            DecoratedBox(
              decoration: BoxDecoration(
                border: Border(
                  bottom: BorderSide(width: SpacingTokens.xs),
                ),
              ),
            ),
            CustomPaint(
              painter: _SamplePainter(strokeWidth: SpacingTokens.xs),
            ),
          ],
        );
      }
    }
    """
    good = """
    class SampleCard extends StatelessWidget {
      @override
      Widget build(BuildContext context) {
        return const Column(
          children: [
            MxDivider(),
            SizedBox(height: 1, child: ColoredBox(color: Colors.red)),
          ],
        );
      }
    }
    """

    assert _violations(
        "design.no_spacing_token_for_non_spacing_property",
        tmp_path,
        bad,
        relative_path="lib/presentation/features/sample/sample_screen.dart",
    )
    assert not _violations(
        "design.no_spacing_token_for_non_spacing_property",
        tmp_path,
        good,
        relative_path="lib/presentation/features/sample/sample_screen.dart",
    )


def test_raw_divider_dimensions_are_forbidden(tmp_path: Path) -> None:
    bad = """
    class SampleScreen extends StatelessWidget {
      @override
      Widget build(BuildContext context) {
        return Column(
          children: const [
            Divider(height: 1, thickness: 1),
            VerticalDivider(width: 1),
          ],
        );
      }
    }
    """
    good = """
    class SampleScreen extends StatelessWidget {
      @override
      Widget build(BuildContext context) {
        return const Column(
          children: [
            MxDivider(),
          ],
        );
      }
    }
    """

    assert _violations(
        "design.require_divider_token",
        tmp_path,
        bad,
        relative_path="lib/presentation/features/sample/sample_screen.dart",
    )
    assert not _violations(
        "design.require_divider_token",
        tmp_path,
        good,
        relative_path="lib/presentation/features/sample/sample_screen.dart",
    )
