"""Integration-style tests for MemoX Riverpod/UI guard regex rules."""

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


def _violations(rule_id: str, tmp_path: Path, source: str) -> list:
    source_path = tmp_path / "lib" / "presentation" / "features" / "sample" / "sample_screen.dart"
    source_path.parent.mkdir(parents=True, exist_ok=True)
    source_path.write_text(source, encoding="utf-8")

    rule_config = _rule_config(rule_id)
    rule_config.pop("scopes", None)
    rule_config["include"] = ["lib/**/*.dart"]
    rule_config["exclude"] = []
    rule_config["enabled"] = True

    return RuleFactory().create(rule_config).check(tmp_path)


def test_existing_callback_ref_watch_rule_flags_ui_callbacks(tmp_path: Path) -> None:
    bad = """
    class Sample extends ConsumerWidget {
      @override
      Widget build(BuildContext context, WidgetRef ref) {
        return FilledButton(
          onPressed: () { ref.watch(sampleProvider.notifier).save(); },
          child: const Text('Save'),
        );
      }
    }
    """
    good = bad.replace("ref.watch", "ref.read")

    assert _violations("memox.state_management.no_ref_watch_in_callbacks", tmp_path, bad)
    assert not _violations("memox.state_management.no_ref_watch_in_callbacks", tmp_path, good)


def test_feature_screens_must_not_return_raw_scaffold(tmp_path: Path) -> None:
    bad = """
    class DeckScreen extends StatelessWidget {
      @override
      Widget build(BuildContext context) {
        return Scaffold(body: DeckListSection());
      }
    }
    """
    good = """
    class DeckScreen extends StatelessWidget {
      @override
      Widget build(BuildContext context) {
        return const MxScaffold(body: DeckListSection());
      }
    }
    """

    assert _violations("memox.screen_shell.no_raw_scaffold", tmp_path, bad)
    assert not _violations("memox.screen_shell.no_raw_scaffold", tmp_path, good)


def test_feature_screens_should_use_mx_screen_shell_when_returning_top_shell(
    tmp_path: Path,
) -> None:
    bad = """
    class DeckScreen extends StatelessWidget {
      @override
      Widget build(BuildContext context) {
        return CustomScrollView(slivers: []);
      }
    }
    """
    good = """
    class DeckScreen extends StatelessWidget {
      @override
      Widget build(BuildContext context) {
        return const MxListScaffold(body: DeckListSection());
      }
    }
    """

    assert _violations("memox.screen_shell.use_mx_scaffold_family", tmp_path, bad)
    assert not _violations(
        "memox.screen_shell.use_mx_scaffold_family",
        tmp_path,
        good,
    )


def test_widget_repository_provider_access_is_forbidden_in_screens(
    tmp_path: Path,
) -> None:
    bad = """
    class DeckScreen extends ConsumerWidget {
      @override
      Widget build(BuildContext context, WidgetRef ref) {
        final repository = ref.read(deckRepositoryProvider);
        return MxScaffold(body: Text('${repository.hashCode}'));
      }
    }
    """
    good = """
    class DeckSection extends ConsumerWidget {
      @override
      Widget build(BuildContext context, WidgetRef ref) {
        final state = ref.watch(deckListProvider);
        return DeckListView(state: state);
      }
    }
    """

    assert _violations("memox.architecture.widget_no_repository_provider_access", tmp_path, bad)
    assert not _violations("memox.architecture.widget_no_repository_provider_access", tmp_path, good)


def test_infrastructure_provider_keep_alive_rule_flags_plain_riverpod(
    tmp_path: Path,
) -> None:
    bad = """
    @riverpod
    Future<DeckRepository> deckRepository(Ref ref) async => DeckRepositoryImpl();
    """
    good = """
    @Riverpod(keepAlive: true)
    Future<DeckRepository> deckRepository(Ref ref) async => DeckRepositoryImpl();
    """

    assert _violations("memox.state_management.infrastructure_provider_keep_alive", tmp_path, bad)
    assert not _violations("memox.state_management.infrastructure_provider_keep_alive", tmp_path, good)


def test_infrastructure_provider_keep_alive_rule_ignores_use_cases(
    tmp_path: Path,
) -> None:
    source = """
    @riverpod
    Future<AuthorizeGoogleDriveUseCase> authorizeGoogleDriveUseCase(
      Ref ref,
    ) async => AuthorizeGoogleDriveUseCase();

    @riverpod
    Future<PersistGoogleAccountAuthResultUseCase>
    persistGoogleAccountAuthResultUseCase(Ref ref) async =>
        PersistGoogleAccountAuthResultUseCase();
    """

    assert not _violations(
        "memox.state_management.infrastructure_provider_keep_alive",
        tmp_path,
        source,
    )


def test_large_provider_state_object_rule_flags_many_fields(tmp_path: Path) -> None:
    bad = """
    final class BigState {
      const BigState();
      final String a;
      final String b;
      final String c;
      final String d;
      final String e;
      final String f;
      final String g;
      final String h;
    }
    """
    good = """
    final class SmallState {
      const SmallState();
      final String a;
      final String b;
      final String c;
    }
    """

    assert _violations("memox.state_management.provider_state_max_fields", tmp_path, bad)
    assert not _violations("memox.state_management.provider_state_max_fields", tmp_path, good)


def test_broad_provider_invalidation_rule_allows_family_refresh(
    tmp_path: Path,
) -> None:
    bad = """
    Future<void> save() async {
      ref.invalidate(libraryOverviewProvider);
    }
    """
    good = """
    Future<void> save(String deckId) async {
      ref.invalidate(flashcardListQueryProvider(deckId));
    }
    """

    assert _violations("memox.state_management.no_broad_provider_invalidation", tmp_path, bad)
    assert not _violations("memox.state_management.no_broad_provider_invalidation", tmp_path, good)


def test_command_provider_repository_access_prefers_read(tmp_path: Path) -> None:
    bad = """
    Future<void> save() async {
      final repository = ref.watch(deckRepositoryProvider);
      await repository.save();
    }
    """
    good = """
    Future<void> save() async {
      final repository = ref.read(deckRepositoryProvider);
      await repository.save();
    }
    """

    assert _violations("memox.state_management.command_no_repository_ref_watch", tmp_path, bad)
    assert not _violations("memox.state_management.command_no_repository_ref_watch", tmp_path, good)


def test_command_provider_repository_rule_allows_reactive_build(
    tmp_path: Path,
) -> None:
    source = """
    Future<TtsSettings> build() async {
      final repository = await ref.watch(ttsSettingsRepositoryProvider.future);
      return repository.watch();
    }
    """

    assert not _violations("memox.state_management.command_no_repository_ref_watch", tmp_path, source)


def test_data_driven_lists_should_use_builder(tmp_path: Path) -> None:
    bad = """
    Widget build(BuildContext context) {
      return ListView(children: items.map((item) => Text(item.name)).toList());
    }
    """
    good = """
    Widget build(BuildContext context) {
      return ListView.builder(
        itemCount: items.length,
        itemBuilder: (context, index) => Text(items[index].name),
      );
    }
    """

    assert _violations("memox.performance.long_lists_use_builder", tmp_path, bad)
    assert not _violations("memox.performance.long_lists_use_builder", tmp_path, good)


def test_heavy_collection_work_in_build_is_flagged(tmp_path: Path) -> None:
    bad = """
    Widget build(BuildContext context) {
      final visible = widget.items.where((item) => item.enabled).toList();
      return Text('${visible.length}');
    }
    """
    good = """
    Widget build(BuildContext context) {
      return Text('${widget.visibleCount}');
    }
    """

    assert _violations("memox.performance.no_heavy_collection_work_in_build", tmp_path, bad)
    assert not _violations("memox.performance.no_heavy_collection_work_in_build", tmp_path, good)


def test_screen_async_value_when_rule_flags_inline_screen_branching(
    tmp_path: Path,
) -> None:
    bad = """
    Widget build(BuildContext context, WidgetRef ref) {
      return ref.watch(sampleProvider).when(
        data: Text.new,
        loading: CircularProgressIndicator.new,
        error: (error, stack) => Text('$error'),
      );
    }
    """
    good = """
    Widget build(BuildContext context, WidgetRef ref) {
      return AppAsyncBuilder(value: ref.watch(sampleProvider));
    }
    """

    assert _violations("memox.state_management.screen_async_when_section_split", tmp_path, bad)
    assert not _violations("memox.state_management.screen_async_when_section_split", tmp_path, good)


def test_screen_part_of_screen_library_is_forbidden(tmp_path: Path) -> None:
    bad = """
    part of 'learning_settings_screen.dart';

    class LearningSettingsPartsScreen extends StatelessWidget {
      @override
      Widget build(BuildContext context) => const SizedBox.shrink();
    }
    """
    good = """
    class LearningSettingsPartsScreen extends StatelessWidget {
      @override
      Widget build(BuildContext context) => const SizedBox.shrink();
    }
    """
    widget_part = """
    part of 'audio_speech_settings_content.dart';

    class AudioSpeechSettingsContentVoicePart extends StatelessWidget {
      @override
      Widget build(BuildContext context) => const SizedBox.shrink();
    }
    """

    assert _violations("memox.coding.no_screen_part_of_split", tmp_path, bad)
    assert not _violations("memox.coding.no_screen_part_of_split", tmp_path, good)
    assert not _violations("memox.coding.no_screen_part_of_split", tmp_path, widget_part)


def test_intrinsic_layout_requires_review(tmp_path: Path) -> None:
    bad = """
    Widget build(BuildContext context) {
      return IntrinsicHeight(child: Row(children: cards));
    }
    """
    good = """
    Widget build(BuildContext context) {
      return SizedBox(height: MxSpace.xxl, child: Row(children: cards));
    }
    """

    assert _violations("memox.performance.intrinsic_layout_requires_review", tmp_path, bad)
    assert not _violations("memox.performance.intrinsic_layout_requires_review", tmp_path, good)


def test_scrollable_shrinkwrap_requires_review(tmp_path: Path) -> None:
    bad = """
    Widget build(BuildContext context) {
      return ListView.builder(
        shrinkWrap: true,
        itemBuilder: (context, index) => Text(items[index].name),
      );
    }
    """
    good = """
    Widget build(BuildContext context) {
      return Expanded(
        child: ListView.builder(
          itemBuilder: (context, index) => Text(items[index].name),
        ),
      );
    }
    """

    assert _violations("memox.performance.shrinkwrap_requires_review", tmp_path, bad)
    assert not _violations("memox.performance.shrinkwrap_requires_review", tmp_path, good)


def test_raw_future_stream_builders_should_use_async_surfaces(
    tmp_path: Path,
) -> None:
    bad = """
    Widget build(BuildContext context) {
      return FutureBuilder<DeckState>(
        future: loadDeck(),
        builder: (context, snapshot) => Text('${snapshot.data}'),
      );
    }
    """
    good = """
    Widget build(BuildContext context, WidgetRef ref) {
      return AppAsyncBuilder(value: ref.watch(deckProvider));
    }
    """

    assert _violations("memox.state_management.no_raw_future_stream_builder", tmp_path, bad)
    assert not _violations(
        "memox.state_management.no_raw_future_stream_builder",
        tmp_path,
        good,
    )


def test_watch_driven_side_effects_should_use_ref_listen(tmp_path: Path) -> None:
    bad = """
    Widget build(BuildContext context, WidgetRef ref) {
      final state = ref.watch(sampleProvider);
      if (state.showSavedMessage) {
        ScaffoldMessenger.of(context).showSnackBar(const SnackBar(content: Text('Saved')));
      }
      return const SizedBox.shrink();
    }
    """
    good = """
    Widget build(BuildContext context, WidgetRef ref) {
      ref.listen(sampleProvider, (previous, next) {
        if (next.showSavedMessage) {
          MxSnackbar.success(context, message: 'Saved');
        }
      });
      return const SizedBox.shrink();
    }
    """

    assert _violations("memox.state_management.side_effects_use_ref_listen", tmp_path, bad)
    assert not _violations("memox.state_management.side_effects_use_ref_listen", tmp_path, good)


def test_template_screen_shell_ref_watch_is_staged_to_mx_templates(
    tmp_path: Path,
) -> None:
    bad = """
    class DeckScreen extends ConsumerWidget {
      @override
      Widget build(BuildContext context, WidgetRef ref) {
        final decks = ref.watch(deckListProvider);
        return MxListScaffold(body: DeckListSection(decks: decks));
      }
    }
    """
    good = """
    class DeckScreen extends StatelessWidget {
      @override
      Widget build(BuildContext context) {
        return const MxListScaffold(body: DeckListSection());
      }
    }

    class DeckListSection extends ConsumerWidget {
      @override
      Widget build(BuildContext context, WidgetRef ref) {
        final decks = ref.watch(deckListProvider);
        return DeckListView(decks: decks);
      }
    }
    """
    base_scaffold = bad.replace("MxListScaffold", "MxScaffold")

    assert _violations("memox.screen_shell.template_shell_no_ref_watch", tmp_path, bad)
    assert not _violations(
        "memox.screen_shell.template_shell_no_ref_watch",
        tmp_path,
        good,
    )
    assert _violations(
        "memox.screen_shell.template_shell_no_ref_watch",
        tmp_path,
        base_scaffold,
    )


def test_section_widgets_may_watch_provider_state(tmp_path: Path) -> None:
    source = """
    class DeckScreen extends StatelessWidget {
      @override
      Widget build(BuildContext context) {
        return const MxListScaffold(body: DeckListSection());
      }
    }

    class DeckListSection extends ConsumerWidget {
      @override
      Widget build(BuildContext context, WidgetRef ref) {
        final decks = ref.watch(deckListProvider);
        return DeckListView(decks: decks);
      }
    }
    """

    assert not _violations("memox.screen_shell.template_shell_no_ref_watch", tmp_path, source)


def test_template_screen_shell_ref_watch_escape_hatch_requires_reason(
    tmp_path: Path,
) -> None:
    allowed = """
    class DeckScreen extends ConsumerWidget {
      @override
      Widget build(BuildContext context, WidgetRef ref) {
        // guard:allow-screen-watch -- reason: route-owned permission state.
        final permission = ref.watch(deckPermissionProvider);
        return MxListScaffold(body: PermissionGate(permission: permission));
      }
    }
    """
    missing_reason = allowed.replace(" -- reason: route-owned permission state.", "")

    assert not _violations(
        "memox.screen_shell.template_shell_no_ref_watch",
        tmp_path,
        allowed,
    )
    assert _violations(
        "memox.screen_shell.watch_escape_hatch_requires_reason",
        tmp_path,
        missing_reason,
    )
    assert not _violations(
        "memox.screen_shell.watch_escape_hatch_requires_reason",
        tmp_path,
        allowed,
    )


def test_feature_screen_raw_padding_radius_color_is_flagged(tmp_path: Path) -> None:
    bad = """
    class DeckScreen extends StatelessWidget {
      @override
      Widget build(BuildContext context) {
        return MxScaffold(
          body: Padding(
            padding: EdgeInsets.all(16),
            child: DecoratedBox(
              decoration: BoxDecoration(
                color: Colors.red,
                borderRadius: BorderRadius.circular(12),
              ),
            ),
          ),
        );
      }
    }
    """
    good = """
    class DeckScreen extends StatelessWidget {
      @override
      Widget build(BuildContext context) {
        return const MxListScaffold(body: DeckListSection());
      }
    }
    """

    assert _violations("memox.screen_shell.no_raw_padding_radius_color", tmp_path, bad)
    assert not _violations(
        "memox.screen_shell.no_raw_padding_radius_color",
        tmp_path,
        good,
    )


def test_feature_screen_tokenized_edge_insets_are_allowed(tmp_path: Path) -> None:
    tokenized = """
    class StudyResultScreen extends StatelessWidget {
      @override
      Widget build(BuildContext context) {
        return Padding(
          padding: const EdgeInsets.symmetric(vertical: MxSpace.xs),
          child: const SizedBox.shrink(),
        );
      }
    }
    """

    assert not _violations(
        "memox.screen_shell.no_raw_padding_radius_color",
        tmp_path,
        tokenized,
    )


def test_base_screen_raw_layout_values_require_review_marker(tmp_path: Path) -> None:
    bad = """
    class MxListScaffold extends StatelessWidget {
      @override
      Widget build(BuildContext context) {
        return Padding(padding: EdgeInsets.all(16), child: body);
      }
    }
    """
    good = """
    class MxListScaffold extends StatelessWidget {
      @override
      Widget build(BuildContext context) {
        return Padding(
          padding: EdgeInsets.all(16),
          // guard:layout-value-reviewed -- reason: mirrors Material minimum inset.
          child: body,
        );
      }
    }
    """

    assert _violations("memox.screen_shell.base_template_no_hardcoded_layout_values", tmp_path, bad)
    assert not _violations(
        "memox.screen_shell.base_template_no_hardcoded_layout_values",
        tmp_path,
        good,
    )
