"""Fault-injection probes for the memox-v8 design-system ratchets.

Every design-system rule ships three proofs: a positive synthetic probe (the
rule goes red on the thing it bans), a comment false-positive probe (prose that
names the thing stays green), and the live-tree scan the gate's guard step
performs. The first two live here.
"""

from __future__ import annotations

from copy import deepcopy
from pathlib import Path

import yaml

from code_verification_guard.factory.rule_factory import RuleFactory

REGISTRY_PATH = (
    Path(__file__).parents[1]
    / "registries"
    / "projects"
    / "memox-v8"
    / "rules"
    / "memox-design-system-rules.yaml"
)


def _rule_config(rule_id: str) -> dict:
    registry = yaml.safe_load(REGISTRY_PATH.read_text(encoding="utf-8"))
    for rule_config in registry.get("rules", []):
        if rule_config["id"] == rule_id:
            return deepcopy(rule_config)

    raise AssertionError(f"Rule not found: {rule_id}")


def _violations(rule_id: str, tmp_path: Path, source: str) -> list:
    source_path = (
        tmp_path / "lib" / "features" / "deck" / "presentation" / "screens" / "sample_screen.dart"
    )
    source_path.parent.mkdir(parents=True, exist_ok=True)
    source_path.write_text(source, encoding="utf-8")

    rule_config = _rule_config(rule_id)
    rule_config.pop("scopes", None)
    rule_config["include"] = ["lib/**/*.dart"]
    rule_config["exclude"] = []
    rule_config["enabled"] = True

    return RuleFactory().create(rule_config).check(tmp_path)


SCREEN_CHROME = "memox_v8.design_system.no_raw_screen_chrome"
CHOICE_CHIP = "memox_v8.design_system.no_raw_choice_chip"


def test_no_raw_screen_chrome_goes_red_on_a_raw_app_bar(tmp_path: Path) -> None:
    bad = """
    return Scaffold(
      appBar: AppBar(title: Text(title)),
      body: child,
    );
    """
    assert _violations(SCREEN_CHROME, tmp_path, bad)


def test_no_raw_screen_chrome_goes_red_on_a_sliver_app_bar(tmp_path: Path) -> None:
    bad = """
    slivers: <Widget>[
      SliverAppBar(pinned: true, title: Text(title)),
    ],
    """
    assert _violations(SCREEN_CHROME, tmp_path, bad)


def test_no_raw_screen_chrome_ignores_prose_and_themes(tmp_path: Path) -> None:
    good = """
    // MxAppShell owns the chrome; a raw AppBar( here would route around it.
    /// A doc comment that says SliverAppBar( is still prose.
    final AppBarTheme theme = AppBarTheme(centerTitle: false);
    return MxAppShell(appBar: MxAppBar(title: title), body: child);
    """
    assert not _violations(SCREEN_CHROME, tmp_path, good)


def test_no_raw_choice_chip_goes_red_on_a_raw_choice_chip(tmp_path: Path) -> None:
    bad = """
    ChoiceChip(label: Text(label), selected: isSelected, onSelected: onPick),
    ChoiceChip.elevated(label: Text(label), selected: false),
    """
    assert _violations(CHOICE_CHIP, tmp_path, bad)


def test_no_raw_choice_chip_leaves_the_allowed_chips_alone(tmp_path: Path) -> None:
    good = """
    // MxFilterChip owns the pick-one chip, so features never build a ChoiceChip(.
    Chip(label: Text(tag.name), onDeleted: remove),
    ActionChip(avatar: const Icon(Icons.add), label: Text(add), onPressed: open),
    MxFilterChip(label: label, isSelected: isSelected, onSelected: onPick),
    """
    assert not _violations(CHOICE_CHIP, tmp_path, good)


SHEET_ROUTE = "memox_v8.design_system.no_raw_sheet_route"
LOADING = "memox_v8.design_system.no_raw_loading_indicator"
RESTYLE = "memox_v8.design_system.no_text_restyle"


def test_no_raw_sheet_route_goes_red_on_a_raw_route(tmp_path: Path) -> None:
    bad = """
    final chosen = await showModalBottomSheet<DeckListSort>(
      context: context,
      builder: (sheetContext) => MxBottomSheet(child: options),
    );
    showBottomSheet(context: context, builder: (_) => child);
    """
    assert _violations(SHEET_ROUTE, tmp_path, bad)


def test_no_raw_sheet_route_leaves_the_owner_and_prose_alone(tmp_path: Path) -> None:
    good = """
    // showMxBottomSheet owns the route; a raw showModalBottomSheet( bypasses it.
    final chosen = await showMxBottomSheet<DeckListSort>(
      context,
      builder: (sheetContext) => MxBottomSheet(child: options),
    );
    """
    assert not _violations(SHEET_ROUTE, tmp_path, good)


def test_no_raw_loading_indicator_goes_red_on_a_bare_spinner(tmp_path: Path) -> None:
    bad = """
    child: const CircularProgressIndicator(),
    child: LinearProgressIndicator(),
    child: CircularProgressIndicator.adaptive(),
    """
    assert _violations(LOADING, tmp_path, bad)


def test_no_raw_loading_indicator_leaves_the_family_and_prose_alone(tmp_path: Path) -> None:
    good = """
    // A bare CircularProgressIndicator( announces nothing.
    child: MxSpinner(semanticLabel: label),
    child: MxSkeletonList(semanticLabel: label),
    """
    assert not _violations(LOADING, tmp_path, good)


def test_no_text_restyle_sees_all_four_spellings_across_lines(tmp_path: Path) -> None:
    for bad in (
        "style: context.texts.bodySmall?.copyWith(color: colors.error),",
        "style: context.textStyles.rowTitle.copyWith(color: colors.onSurfaceVariant),",
        "style: Theme.of(context).textTheme.bodySmall?.copyWith(color: c),",
        """
    style: AppTypography.withWeight(
      context.texts.labelMedium!,
      FontWeight.w600,
    ).copyWith(
      color: ink,
    ),
    """,
    ):
        assert _violations(RESTYLE, tmp_path, bad), bad


def test_no_text_restyle_accepts_named_styles_and_prose(tmp_path: Path) -> None:
    good = """
    // texts.bodySmall!.copyWith( is the spelling this rule refuses.
    style: context.textStyles.rowTitle,
    style: AppTypography.withWeight(
      context.texts.labelMedium!,
      FontWeight.w600,
    ),
    """
    assert not _violations(RESTYLE, tmp_path, good)


def test_no_text_restyle_sees_the_hint_style(tmp_path: Path) -> None:
    # `MxTextStyles.inputHint` is a resolved style like the others; a
    # `.copyWith(` on it is the same restyle, however the styles are reached.
    assert _violations(
        RESTYLE,
        tmp_path,
        "final s = context.textStyles.inputHint.copyWith(color: Colors.red);\n",
    )
    violations = _violations(
        RESTYLE,
        tmp_path,
        "final s = MxTextStyles(texts, scheme).inputHint.copyWith(color: ink);\n",
    )
    assert len(violations) == 1


def test_no_text_restyle_leaves_the_hint_style_alone(tmp_path: Path) -> None:
    good = """
    hintStyle: MxTextStyles(texts, scheme).inputHint,
    style: context.textStyles.inputHint,
    """
    assert not _violations(RESTYLE, tmp_path, good)
