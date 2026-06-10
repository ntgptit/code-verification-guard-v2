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
          padding: const EdgeInsets.fromLTRB(
            16,
            12,
            16,
            8,
          ),
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


def test_icon_size_must_use_icon_tokens_and_not_cross_match(
    tmp_path: Path,
) -> None:
    source = """
    class SampleSwatch extends StatelessWidget {
      @override
      Widget build(BuildContext context) {
        return const Column(
          children: [
            Icon(Icons.check, size: IconSizeTokens.sm),
            SizedBox(width: SpacingTokens.xs),
            SizedBox(height: SpacingTokens.sm),
            Icon(Icons.close, size: 11),
          ],
        );
      }
    }
    """

    violations = _violations(
        "design.require_icon_size_token",
        tmp_path,
        source,
        relative_path="lib/presentation/features/sample/sample_screen.dart",
    )

    assert len(violations) == 1
    assert "size: 11" in violations[0].code_line


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
        "design.require_mx_icon_tile_size_token",
        tmp_path,
        bad_multiline,
        relative_path="lib/presentation/shared/dialogs/mx_folder_delete_dialog.dart",
    )
    assert _violations(
        "design.require_mx_icon_tile_size_token",
        tmp_path,
        bad_inline,
        relative_path="lib/presentation/shared/dialogs/mx_folder_delete_dialog.dart",
    )
    assert not _violations(
        "design.require_mx_icon_tile_size_token",
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
        "design.no_spacing_token_for_component_size",
        tmp_path,
        spacing_fail,
        relative_path="lib/presentation/shared/dialogs/mx_folder_delete_dialog.dart",
    )


def test_visual_box_size_must_use_component_tokens(tmp_path: Path) -> None:
    bad = """
    class SampleSwatch extends StatelessWidget {
      @override
      Widget build(BuildContext context) {
        return Container(
          width: 28,
          height: 28,
          child: const Icon(Icons.check, size: IconSizeTokens.sm),
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
    gap_layout = """
    class SampleSwatch extends StatelessWidget {
      @override
      Widget build(BuildContext context) {
        return const SizedBox(height: SpacingTokens.sm);
      }
    }
    """

    assert _violations(
        "design.require_visual_box_size_token",
        tmp_path,
        bad,
        relative_path="lib/presentation/features/sample/sample_screen.dart",
    )
    assert not _violations(
        "design.require_visual_box_size_token",
        tmp_path,
        good,
        relative_path="lib/presentation/features/sample/sample_screen.dart",
    )
    assert not _violations(
        "design.require_visual_box_size_token",
        tmp_path,
        gap_layout,
        relative_path="lib/presentation/features/sample/sample_screen.dart",
    )


def test_icon_size_spacing_token_is_forbidden(tmp_path: Path) -> None:
    bad_multiline = """
    Widget build(BuildContext context) => Icon(
      Icons.check,
      size: SpacingTokens.md,
    );
    """
    bad_inline = """
    Widget build(BuildContext context) => Icon(Icons.check, size: SpacingTokens.md);
    """
    good = """
    Widget build(BuildContext context) => Icon(Icons.check, size: IconSizeTokens.sm);
    """

    assert _violations(
        "design.no_spacing_token_for_icon_size",
        tmp_path,
        bad_multiline,
        relative_path="lib/presentation/shared/dialogs/mx_folder_delete_dialog.dart",
    )
    assert _violations(
        "design.no_spacing_token_for_icon_size",
        tmp_path,
        bad_inline,
        relative_path="lib/presentation/shared/dialogs/mx_folder_delete_dialog.dart",
    )
    assert not _violations(
        "design.no_spacing_token_for_icon_size",
        tmp_path,
        good,
        relative_path="lib/presentation/shared/dialogs/mx_folder_delete_dialog.dart",
    )


def test_border_width_spacing_token_is_forbidden(tmp_path: Path) -> None:
    bad = """
    class SampleCard extends StatelessWidget {
      @override
      Widget build(BuildContext context) {
        return DecoratedBox(
          decoration: BoxDecoration(
            border: Border.all(
              color: scheme.outlineVariant,
              width: SpacingTokens.xxs,
            ),
          ),
        );
      }
    }
    """
    bad_side = """
    class SampleCard extends StatelessWidget {
      @override
      Widget build(BuildContext context) {
        return DecoratedBox(
          decoration: BoxDecoration(
            border: BorderSide(
              color: dividerColor,
              width: 1,
            ),
          ),
        );
      }
    }
    """
    color_only = """
    class SampleCard extends StatelessWidget {
      @override
      Widget build(BuildContext context) {
        return DecoratedBox(
          decoration: BoxDecoration(
            border: Border.all(color: scheme.outlineVariant),
          ),
        );
      }
    }
    """
    side_color_only = """
    class SampleCard extends StatelessWidget {
      @override
      Widget build(BuildContext context) {
        return DecoratedBox(
          decoration: BoxDecoration(
            border: BorderSide(color: dividerColor),
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
        "design.no_spacing_token_for_border_width",
        tmp_path,
        bad,
        relative_path="lib/presentation/features/sample/sample_screen.dart",
    )
    assert not _violations(
        "design.no_spacing_token_for_border_width",
        tmp_path,
        good,
        relative_path="lib/presentation/features/sample/sample_screen.dart",
    )
    assert _violations(
        "design.require_border_token",
        tmp_path,
        bad_side,
        relative_path="lib/presentation/features/sample/sample_screen.dart",
    )
    assert not _violations(
        "design.no_spacing_token_for_border_width",
        tmp_path,
        color_only,
        relative_path="lib/presentation/features/sample/sample_screen.dart",
    )
    assert not _violations(
        "design.no_spacing_token_for_border_width",
        tmp_path,
        side_color_only,
        relative_path="lib/presentation/features/sample/sample_screen.dart",
    )
    assert not _violations(
        "design.require_border_token",
        tmp_path,
        color_only,
        relative_path="lib/presentation/features/sample/sample_screen.dart",
    )
    assert not _violations(
        "design.require_border_token",
        tmp_path,
        side_color_only,
        relative_path="lib/presentation/features/sample/sample_screen.dart",
    )


def test_divider_thickness_spacing_token_is_forbidden(tmp_path: Path) -> None:
    bad = """
    class SampleCard extends StatelessWidget {
      @override
      Widget build(BuildContext context) {
        return Column(
          children: const [
            Divider(thickness: SpacingTokens.xxs),
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
          ],
        );
      }
    }
    """

    assert _violations(
        "design.no_spacing_token_for_divider_thickness",
        tmp_path,
        bad,
        relative_path="lib/presentation/features/sample/sample_screen.dart",
    )
    assert not _violations(
        "design.no_spacing_token_for_divider_thickness",
        tmp_path,
        good,
        relative_path="lib/presentation/features/sample/sample_screen.dart",
    )


def test_shadow_token_is_required_inside_box_shadow(tmp_path: Path) -> None:
    bad = """
    class SampleCard extends StatelessWidget {
      @override
      Widget build(BuildContext context) {
        return Container(
          decoration: BoxDecoration(
            boxShadow: [
              BoxShadow(
                blurRadius: 8,
                spreadRadius: SpacingTokens.sm,
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
    global_shadow = """
    class SampleCard extends StatelessWidget {
      @override
      Widget build(BuildContext context) {
        return Foo(
          blurRadius: 12,
          spreadRadius: 4,
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
    assert not _violations(
        "design.require_shadow_token",
        tmp_path,
        global_shadow,
        relative_path="lib/presentation/features/sample/sample_screen.dart",
    )


def test_spacing_gap_sizedbox_with_token_is_allowed(tmp_path: Path) -> None:
    source = """
    class SampleCard extends StatelessWidget {
      @override
      Widget build(BuildContext context) {
        return const Column(
          children: [
            SizedBox(height: SpacingTokens.xxs),
          ],
        );
      }
    }
    """

    assert not _violations(
        "design.require_icon_size_token",
        tmp_path,
        source,
        relative_path="lib/presentation/features/sample/sample_screen.dart",
    )
    assert not _violations(
        "design.require_mx_icon_tile_size_token",
        tmp_path,
        source,
        relative_path="lib/presentation/features/sample/sample_screen.dart",
    )
    assert not _violations(
        "design.require_visual_box_size_token",
        tmp_path,
        source,
        relative_path="lib/presentation/features/sample/sample_screen.dart",
    )
    assert not _violations(
        "design.no_spacing_token_for_icon_size",
        tmp_path,
        source,
        relative_path="lib/presentation/features/sample/sample_screen.dart",
    )
    assert not _violations(
        "design.no_spacing_token_for_component_size",
        tmp_path,
        source,
        relative_path="lib/presentation/features/sample/sample_screen.dart",
    )
    assert not _violations(
        "design.no_spacing_token_for_border_width",
        tmp_path,
        source,
        relative_path="lib/presentation/features/sample/sample_screen.dart",
    )
    assert not _violations(
        "design.no_spacing_token_for_divider_thickness",
        tmp_path,
        source,
        relative_path="lib/presentation/features/sample/sample_screen.dart",
    )
    assert not _violations(
        "design.no_spacing_token_for_shadow",
        tmp_path,
        source,
        relative_path="lib/presentation/features/sample/sample_screen.dart",
    )


def test_raw_divider_dimensions_are_forbidden(tmp_path: Path) -> None:
    # Raw Divider usage in feature code (any constructor call, including raw
    # height/thickness values) is covered by memox.divider_usage; the former
    # design.require_divider_token rule was merged into it.
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
        "memox.divider_usage",
        tmp_path,
        bad,
        relative_path="lib/presentation/features/sample/sample_screen.dart",
    )
    assert not _violations(
        "memox.divider_usage",
        tmp_path,
        good,
        relative_path="lib/presentation/features/sample/sample_screen.dart",
    )
