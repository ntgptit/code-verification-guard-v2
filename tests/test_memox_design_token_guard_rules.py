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


def test_edge_insets_must_use_spacing_tokens_or_zero(tmp_path: Path) -> None:
    bad = """
    class SampleHeader extends StatelessWidget {
      @override
      Widget build(BuildContext context) {
        final localHeaderPadding = 12.0;
        return Padding(
          padding: const EdgeInsets.fromLTRB(16, 12, 16, 8),
          child: Container(
            padding: EdgeInsets.symmetric(horizontal: localHeaderPadding),
            margin: EdgeInsets.only(left: SpacingTokens.md + 2),
          ),
        );
      }
    }
    """
    good = """
    class SampleHeader extends StatelessWidget {
      @override
      Widget build(BuildContext context) {
        return const Padding(
          padding: EdgeInsets.zero,
          child: Padding(
            padding: EdgeInsets.symmetric(horizontal: SpacingTokens.md),
            child: SizedBox.shrink(),
          ),
        );
      }
    }
    """

    assert _violations(
        "design.require_spacing_token_for_edge_insets",
        tmp_path,
        bad,
        relative_path="lib/presentation/features/sample/sample_screen.dart",
    )
    assert not _violations(
        "design.require_spacing_token_for_edge_insets",
        tmp_path,
        good,
        relative_path="lib/presentation/features/sample/sample_screen.dart",
    )


def test_visual_component_sizes_must_use_component_tokens(tmp_path: Path) -> None:
    bad = """
    class SampleSwatch extends StatelessWidget {
      @override
      Widget build(BuildContext context) {
        return Container(
          width: 28,
          height: 28,
          child: const Icon(Icons.check, size: 14),
        );
      }
    }
    """
    good = """
    class SampleSwatch extends StatelessWidget {
      @override
      Widget build(BuildContext context) {
        return Container(
          width: ComponentSizeTokens.controlSm,
          height: ComponentSizeTokens.controlSm,
          child: const Icon(Icons.check, size: IconSizeTokens.sm),
        );
      }
    }
    """

    assert _violations(
        "design.require_component_size_token",
        tmp_path,
        bad,
        relative_path="lib/presentation/features/sample/sample_screen.dart",
    )
    assert not _violations(
        "design.require_component_size_token",
        tmp_path,
        good,
        relative_path="lib/presentation/features/sample/sample_screen.dart",
    )


def test_mx_icon_tile_size_must_use_component_tokens(tmp_path: Path) -> None:
    bad_multiline = """
    Widget _buildHeader(ColorScheme scheme) => MxIconTile(
      icon: Icons.folder_delete_outlined,
      color: scheme.error,
      size: 48,
    );
    """
    bad_inline = """
    Widget _buildHeader(ColorScheme scheme) => MxIconTile(icon: Icons.folder_delete_outlined, color: scheme.error, size: 48);
    """
    good = """
    Widget _buildHeader(ColorScheme scheme) => MxIconTile(
      icon: Icons.folder_delete_outlined,
      color: scheme.error,
      size: IconSizeTokens.md,
    );
    """
    arithmetic_fail = """
    Widget _buildHeader(ColorScheme scheme) => MxIconTile(
      icon: Icons.folder_delete_outlined,
      color: scheme.error,
      size: SpacingTokens.xs + SpacingTokens.sm,
    );
    """
    spacing_fail = """
    Widget _buildHeader(ColorScheme scheme) => MxIconTile(
      icon: Icons.folder_delete_outlined,
      color: scheme.error,
      size: SpacingTokens.xs,
    );
    """

    assert _violations(
        "design.require_component_size_token",
        tmp_path,
        bad_multiline,
        relative_path="lib/presentation/shared/dialogs/mx_folder_delete_dialog.dart",
    )
    assert _violations(
        "design.require_component_size_token",
        tmp_path,
        bad_inline,
        relative_path="lib/presentation/shared/dialogs/mx_folder_delete_dialog.dart",
    )
    assert not _violations(
        "design.require_component_size_token",
        tmp_path,
        good,
        relative_path="lib/presentation/shared/dialogs/mx_folder_delete_dialog.dart",
    )
    assert _violations(
        "design.no_token_arithmetic_in_ui",
        tmp_path,
        arithmetic_fail,
        relative_path="lib/presentation/shared/dialogs/mx_folder_delete_dialog.dart",
    )
    assert _violations(
        "design.no_spacing_token_for_non_spacing_property",
        tmp_path,
        spacing_fail,
        relative_path="lib/presentation/shared/dialogs/mx_folder_delete_dialog.dart",
    )


def test_border_widths_must_use_border_tokens(tmp_path: Path) -> None:
    bad = """
    class SampleCard extends StatelessWidget {
      @override
      Widget build(BuildContext context) {
        return DecoratedBox(
          decoration: BoxDecoration(
            border: Border.all(width: 1),
          ),
        );
      }
    }
    """
    good = """
    class SampleCard extends StatelessWidget {
      @override
      Widget build(BuildContext context) {
        return DecoratedBox(
          decoration: BoxDecoration(
            border: Border.all(width: BorderTokens.width),
          ),
        );
      }
    }
    """

    assert _violations(
        "design.require_border_token",
        tmp_path,
        bad,
        relative_path="lib/presentation/features/sample/sample_screen.dart",
    )
    assert not _violations(
        "design.require_border_token",
        tmp_path,
        good,
        relative_path="lib/presentation/features/sample/sample_screen.dart",
    )


def test_shadow_properties_must_use_shadow_tokens(tmp_path: Path) -> None:
    bad = """
    class SampleCard extends StatelessWidget {
      @override
      Widget build(BuildContext context) {
        return Container(
          decoration: BoxDecoration(
            boxShadow: [
              BoxShadow(
                blurRadius: 8,
                spreadRadius: 2,
              ),
            ],
          ),
        );
      }
    }
    """
    good = """
    class SampleCard extends StatelessWidget {
      @override
      Widget build(BuildContext context) {
        return Container(
          decoration: BoxDecoration(
            boxShadow: [
              BoxShadow(
                blurRadius: 0,
                spreadRadius: ShadowTokens.spreadSm,
              ),
            ],
          ),
        );
      }
    }
    """

    assert _violations(
        "design.require_shadow_token",
        tmp_path,
        bad,
        relative_path="lib/presentation/features/sample/sample_screen.dart",
    )
    assert not _violations(
        "design.require_shadow_token",
        tmp_path,
        good,
        relative_path="lib/presentation/features/sample/sample_screen.dart",
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
            Container(width: SpacingTokens.xs, height: SpacingTokens.xs),
            Icon(Icons.check, size: SpacingTokens.xs),
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
            BoxShadow(
              blurRadius: SpacingTokens.xs,
              spreadRadius: SpacingTokens.xs,
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
            SizedBox(height: SpacingTokens.xxs),
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
