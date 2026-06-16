"""Integration-style tests for MemoX Flutter convention guard regex rules."""

from __future__ import annotations

from copy import deepcopy
from pathlib import Path

import yaml

from code_verification_guard.factory.rule_factory import RuleFactory

REGISTRY_PATH = (
    Path(__file__).parents[1]
    / "registries"
    / "projects"
    / "memox"
    / "rules"
    / "memox-flutter-convention-rules.yaml"
)


def _rule_config(rule_id: str) -> dict:
    registry = yaml.safe_load(REGISTRY_PATH.read_text(encoding="utf-8"))
    for rule_config in registry.get("rules", []):
        if rule_config["id"] == rule_id:
            return deepcopy(rule_config)

    raise AssertionError(f"Rule not found: {rule_id}")


def _violations(rule_id: str, tmp_path: Path, relative_path: str, source: str) -> list:
    source_path = tmp_path / relative_path
    source_path.parent.mkdir(parents=True, exist_ok=True)
    source_path.write_text(source, encoding="utf-8")

    rule_config = _rule_config(rule_id)
    rule_config.pop("scopes", None)
    rule_config["include"] = ["lib/**/*.dart"]
    rule_config["exclude"] = []
    rule_config["enabled"] = True

    return RuleFactory().create(rule_config).check(tmp_path)


def test_legacy_key_constructor_rule_flags_super_key_constructor(
    tmp_path: Path,
) -> None:
    bad = """
    class SampleTile extends StatelessWidget {
      const SampleTile({Key? key}) : super(key: key);

      @override
      Widget build(BuildContext context) => const SizedBox.shrink();
    }
    """
    good = """
    class SampleTile extends StatelessWidget {
      const SampleTile({super.key});

      @override
      Widget build(BuildContext context) => const SizedBox.shrink();
    }
    """

    assert _violations(
        "memox.flutter_convention.no_legacy_key_constructor",
        tmp_path,
        "lib/presentation/features/sample/widgets/sample_tile.dart",
        bad,
    )
    assert not _violations(
        "memox.flutter_convention.no_legacy_key_constructor",
        tmp_path,
        "lib/presentation/features/sample/widgets/sample_tile.dart",
        good,
    )


def test_widget_constructor_named_params_rule_flags_positional_constructor(
    tmp_path: Path,
) -> None:
    bad = """
    class SampleCard extends StatelessWidget {
      const SampleCard(this.title, {super.key});

      final String title;

      @override
      Widget build(BuildContext context) => Text(title);
    }
    """
    good = """
    class SampleCard extends StatelessWidget {
      const SampleCard({required this.title, super.key});

      final String title;

      @override
      Widget build(BuildContext context) => Text(title);
    }
    """

    assert _violations(
        "memox.flutter_convention.widget_constructor_named_params",
        tmp_path,
        "lib/presentation/features/sample/widgets/sample_card.dart",
        bad,
    )
    assert not _violations(
        "memox.flutter_convention.widget_constructor_named_params",
        tmp_path,
        "lib/presentation/features/sample/widgets/sample_card.dart",
        good,
    )


def test_widget_constructor_named_params_rule_allows_implicit_and_empty_constructors(
    tmp_path: Path,
) -> None:
    implicit = """
    class DashboardBody extends ConsumerWidget {
      @override
      Widget build(BuildContext context) => const SizedBox.shrink();
    }
    """
    empty = """
    class SampleCard extends StatelessWidget {
      const SampleCard();

      @override
      Widget build(BuildContext context) => const SizedBox.shrink();
    }
    """

    assert not _violations(
        "memox.flutter_convention.widget_constructor_named_params",
        tmp_path,
        "lib/presentation/features/dashboard/widgets/dashboard_screen_body.dart",
        implicit,
    )
    assert not _violations(
        "memox.flutter_convention.widget_constructor_named_params",
        tmp_path,
        "lib/presentation/features/sample/widgets/sample_card.dart",
        empty,
    )


def test_widget_constructor_should_be_const_rule_flags_missing_const(
    tmp_path: Path,
) -> None:
    bad = """
    class SampleCard extends StatelessWidget {
      SampleCard({super.key, required this.title});

      final String title;

      @override
      Widget build(BuildContext context) => Text(title);
    }
    """
    good = """
    class SampleCard extends StatelessWidget {
      const SampleCard({super.key, required this.title});

      final String title;

      @override
      Widget build(BuildContext context) => Text(title);
    }
    """

    assert _violations(
        "memox.flutter_convention.widget_constructor_should_be_const",
        tmp_path,
        "lib/presentation/features/sample/widgets/sample_card.dart",
        bad,
    )
    assert not _violations(
        "memox.flutter_convention.widget_constructor_should_be_const",
        tmp_path,
        "lib/presentation/features/sample/widgets/sample_card.dart",
        good,
    )


def test_stateful_widget_in_features_rule_flags_stateful_widget_and_state_class(
    tmp_path: Path,
) -> None:
    bad = """
    class SampleScreen extends StatefulWidget {
      const SampleScreen({super.key});

      @override
      State<SampleScreen> createState() => _SampleScreenState();
    }

    class _SampleScreenState extends State<SampleScreen> {
      @override
      Widget build(BuildContext context) => const SizedBox.shrink();
    }
    """
    good = """
    class SampleScreen extends HookConsumerWidget {
      const SampleScreen({super.key});

      @override
      Widget build(BuildContext context, WidgetRef ref) => const SizedBox.shrink();
    }
    """

    assert _violations(
        "memox.flutter_convention.no_stateful_widget_in_features",
        tmp_path,
        "lib/presentation/features/sample/screens/sample_screen.dart",
        bad,
    )
    assert not _violations(
        "memox.flutter_convention.no_stateful_widget_in_features",
        tmp_path,
        "lib/presentation/features/sample/screens/sample_screen.dart",
        good,
    )


def test_set_state_rule_flags_widget_mutation(tmp_path: Path) -> None:
    bad = """
    class SampleScreen extends StatefulWidget {
      const SampleScreen({super.key});

      @override
      State<SampleScreen> createState() => _SampleScreenState();
    }

    class _SampleScreenState extends State<SampleScreen> {
      void _increment() {
        setState(() {});
      }

      @override
      Widget build(BuildContext context) => const SizedBox.shrink();
    }
    """
    good = """
    class SampleScreen extends HookConsumerWidget {
      const SampleScreen({super.key});

      @override
      Widget build(BuildContext context, WidgetRef ref) => const SizedBox.shrink();
    }
    """

    assert _violations(
        "memox.flutter_convention.no_set_state",
        tmp_path,
        "lib/presentation/features/sample/screens/sample_screen.dart",
        bad,
    )
    assert not _violations(
        "memox.flutter_convention.no_set_state",
        tmp_path,
        "lib/presentation/features/sample/screens/sample_screen.dart",
        good,
    )


def test_build_context_field_rule_flags_persistent_context_storage(
    tmp_path: Path,
) -> None:
    bad = """
    class SampleState extends State<SampleScreen> {
      late BuildContext context;

      @override
      Widget build(BuildContext context) => const SizedBox.shrink();
    }
    """
    good = """
    class SampleScreen extends StatelessWidget {
      const SampleScreen({super.key});

      @override
      Widget build(BuildContext context) {
        final BuildContext localContext = context;
        return const SizedBox.shrink();
      }
    }
    """

    assert _violations(
        "memox.flutter_convention.no_build_context_fields",
        tmp_path,
        "lib/presentation/features/sample/screens/sample_screen.dart",
        bad,
    )
    assert not _violations(
        "memox.flutter_convention.no_build_context_fields",
        tmp_path,
        "lib/presentation/features/sample/screens/sample_screen.dart",
        good,
    )


def test_private_widget_builder_method_rule_flags_screen_helpers(
    tmp_path: Path,
) -> None:
    bad = """
    class SampleScreen extends StatelessWidget {
      const SampleScreen({super.key});

      @override
      Widget build(BuildContext context) {
        return Column(
          children: <Widget>[
            _buildHeader(context),
          ],
        );
      }

      Widget _buildHeader(BuildContext context) => const SizedBox.shrink();
    }
    """
    good = """
    class SampleScreen extends StatelessWidget {
      const SampleScreen({super.key});

      @override
      Widget build(BuildContext context) {
        return const SampleHeader();
      }
    }

    class SampleHeader extends StatelessWidget {
      const SampleHeader({super.key});

      @override
      Widget build(BuildContext context) => const SizedBox.shrink();
    }
    """

    assert _violations(
        "memox.flutter_convention.no_private_widget_builder_methods_in_screens",
        tmp_path,
        "lib/presentation/features/sample/screens/sample_screen.dart",
        bad,
    )
    assert not _violations(
        "memox.flutter_convention.no_private_widget_builder_methods_in_screens",
        tmp_path,
        "lib/presentation/features/sample/screens/sample_screen.dart",
        good,
    )


def test_mutable_children_list_rule_flags_add_calls_in_build(
    tmp_path: Path,
) -> None:
    bad = """
    class SampleCard extends StatelessWidget {
      const SampleCard({super.key});

      @override
      Widget build(BuildContext context) {
        final children = <Widget>[];
        children.add(const Text('A'));
        return Column(children: children);
      }
    }
    """
    good = """
    class SampleCard extends StatelessWidget {
      const SampleCard({super.key});

      @override
      Widget build(BuildContext context) {
        return const Column(
          children: <Widget>[
            Text('A'),
          ],
        );
      }
    }
    """

    assert _violations(
        "memox.flutter_convention.no_mutable_children_list_in_build",
        tmp_path,
        "lib/presentation/features/sample/widgets/sample_card.dart",
        bad,
    )
    assert not _violations(
        "memox.flutter_convention.no_mutable_children_list_in_build",
        tmp_path,
        "lib/presentation/features/sample/widgets/sample_card.dart",
        good,
    )


def test_global_key_review_rule_flags_feature_keys(tmp_path: Path) -> None:
    bad = """
    class SampleScreen extends StatelessWidget {
      const SampleScreen({super.key});

      final GlobalKey<FormState> formKey = GlobalKey<FormState>();

      @override
      Widget build(BuildContext context) => const SizedBox.shrink();
    }
    """
    good = """
    class SampleScreen extends StatelessWidget {
      const SampleScreen({super.key});

      @override
      Widget build(BuildContext context) => const SizedBox.shrink();
    }
    """

    assert _violations(
        "memox.flutter_convention.global_key_requires_review",
        tmp_path,
        "lib/presentation/features/sample/screens/sample_screen.dart",
        bad,
    )
    assert not _violations(
        "memox.flutter_convention.global_key_requires_review",
        tmp_path,
        "lib/presentation/features/sample/screens/sample_screen.dart",
        good,
    )


def test_non_null_assertion_review_rule_flags_bang_usage(tmp_path: Path) -> None:
    bad = """
    class SampleCard extends StatelessWidget {
      const SampleCard({super.key, required this.title});

      final String? title;

      @override
      Widget build(BuildContext context) {
        return Text(title!.trim());
      }
    }
    """
    good = """
    class SampleCard extends StatelessWidget {
      const SampleCard({super.key, required this.title});

      final String? title;

      @override
      Widget build(BuildContext context) {
        if (title == null) {
          return const SizedBox.shrink();
        }
        return Text(title.trim());
      }
    }
    """

    assert _violations(
        "memox.flutter_convention.non_null_assertion_requires_review",
        tmp_path,
        "lib/presentation/features/sample/widgets/sample_card.dart",
        bad,
    )
    assert not _violations(
        "memox.flutter_convention.non_null_assertion_requires_review",
        tmp_path,
        "lib/presentation/features/sample/widgets/sample_card.dart",
        good,
    )


def test_non_null_assertion_review_rule_ignores_type_check_operators(
    tmp_path: Path,
) -> None:
    source = """
    class SampleCard extends StatelessWidget {
      const SampleCard({super.key});

      @override
      Widget build(BuildContext context) {
        if (value is! int || name is! String) {
          return const SizedBox.shrink();
        }
        return const SizedBox.shrink();
      }
    }
    """

    assert not _violations(
        "memox.flutter_convention.non_null_assertion_requires_review",
        tmp_path,
        "lib/presentation/features/sample/widgets/sample_card.dart",
        source,
    )


def test_non_null_assertion_review_rule_skips_data_repositories(tmp_path: Path) -> None:
    """Drift `row.read(col)!` / `(await dao.find(id))!` are idiomatic in the data
    repository layer, so the rule's real scope must exclude it while still flagging
    presentation code."""
    drift_idiom = """
    Future<FlashcardRow> findFlashcard(String id) async {
      return (await _dao.findFlashcard(id))!;
    }
    """
    presentation_bang = """
    class SampleCard extends StatelessWidget {
      const SampleCard({super.key, required this.title});

      final String? title;

      @override
      Widget build(BuildContext context) => Text(title!);
    }
    """

    rule_config = _rule_config("memox.flutter_convention.non_null_assertion_requires_review")
    rule = RuleFactory().create(rule_config)

    repo_path = tmp_path / "lib/data/repositories/flashcard_repo_impl.dart"
    repo_path.parent.mkdir(parents=True, exist_ok=True)
    repo_path.write_text(drift_idiom, encoding="utf-8")

    ui_path = tmp_path / "lib/presentation/features/sample/widgets/sample_card.dart"
    ui_path.parent.mkdir(parents=True, exist_ok=True)
    ui_path.write_text(presentation_bang, encoding="utf-8")

    violations = rule.check(tmp_path)
    flagged = {str(v.file_path) for v in violations}

    assert str(ui_path) in flagged
    assert str(repo_path) not in flagged


def test_future_delayed_rule_flags_ui_delay_smells(tmp_path: Path) -> None:
    bad = """
    class SampleScreen extends StatelessWidget {
      const SampleScreen({super.key});

      @override
      Widget build(BuildContext context) {
        Future.delayed(const Duration(milliseconds: 300));
        return const SizedBox.shrink();
      }
    }
    """
    good = """
    class SampleScreen extends HookConsumerWidget {
      const SampleScreen({super.key});

      @override
      Widget build(BuildContext context, WidgetRef ref) {
        ref.listen(sampleProvider, (previous, next) {});
        return const SizedBox.shrink();
      }
    }
    """

    assert _violations(
        "memox.flutter_convention.no_future_delayed_in_ui",
        tmp_path,
        "lib/presentation/features/sample/screens/sample_screen.dart",
        bad,
    )
    assert not _violations(
        "memox.flutter_convention.no_future_delayed_in_ui",
        tmp_path,
        "lib/presentation/features/sample/screens/sample_screen.dart",
        good,
    )
