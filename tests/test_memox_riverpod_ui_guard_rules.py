"""Integration-style tests for MemoX Riverpod/UI guard regex rules."""

from __future__ import annotations

from copy import deepcopy
from pathlib import Path

import yaml

from code_verification_guard.factory.rule_factory import RuleFactory

REGISTRY_DIR = Path(__file__).parents[1] / "registries" / "projects" / "memox"


def _rule_config(rule_id: str) -> dict:
    for registry_path in REGISTRY_DIR.glob("*.yaml"):
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

    assert _violations("memox.widget_callback_ref_watch_usage", tmp_path, bad)
    assert not _violations("memox.widget_callback_ref_watch_usage", tmp_path, good)


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

    assert _violations("memox.infrastructure_provider_keep_alive_required", tmp_path, bad)
    assert not _violations("memox.infrastructure_provider_keep_alive_required", tmp_path, good)


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
        "memox.infrastructure_provider_keep_alive_required",
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

    assert _violations("memox.provider_state_object_too_large", tmp_path, bad)
    assert not _violations("memox.provider_state_object_too_large", tmp_path, good)


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

    assert _violations("memox.no_broad_provider_invalidation", tmp_path, bad)
    assert not _violations("memox.no_broad_provider_invalidation", tmp_path, good)


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

    assert _violations("memox.command_provider_repository_ref_read", tmp_path, bad)
    assert not _violations("memox.command_provider_repository_ref_read", tmp_path, good)


def test_command_provider_repository_rule_allows_reactive_build(
    tmp_path: Path,
) -> None:
    source = """
    Future<TtsSettings> build() async {
      final repository = await ref.watch(ttsSettingsRepositoryProvider.future);
      return repository.watch();
    }
    """

    assert not _violations("memox.command_provider_repository_ref_read", tmp_path, source)


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

    assert _violations("memox.long_collection_uses_builder", tmp_path, bad)
    assert not _violations("memox.long_collection_uses_builder", tmp_path, good)


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

    assert _violations("memox.heavy_collection_work_in_build", tmp_path, bad)
    assert not _violations("memox.heavy_collection_work_in_build", tmp_path, good)


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

    assert _violations("memox.screen_async_value_when_section_split", tmp_path, bad)
    assert not _violations("memox.screen_async_value_when_section_split", tmp_path, good)


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

    assert _violations("memox.watch_state_side_effect_requires_listen", tmp_path, bad)
    assert not _violations("memox.watch_state_side_effect_requires_listen", tmp_path, good)
