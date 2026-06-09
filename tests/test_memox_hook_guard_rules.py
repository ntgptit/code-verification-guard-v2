from __future__ import annotations

from copy import deepcopy
from hashlib import sha1
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


def _violations(rule_id: str, tmp_path: Path, relative_path: str, source: str) -> list:
    case_root = tmp_path / sha1(f"{relative_path}\n{source}".encode("utf-8")).hexdigest()
    source_path = case_root / relative_path
    source_path.parent.mkdir(parents=True, exist_ok=True)
    source_path.write_text(source, encoding="utf-8")

    rule_config = _rule_config(rule_id)
    rule_config.pop("scopes", None)
    rule_config["enabled"] = True

    return RuleFactory().create(rule_config).check(case_root)


def test_hook_boundary_blocks_hooks_outside_presentation(tmp_path: Path) -> None:
    domain_source = """
    import 'package:flutter_hooks/flutter_hooks.dart';

    class DomainThing {
      void build() {
        useState(0);
      }
    }
    """
    data_source = """
    class DataThing {
      void build() {
        useState(0);
      }
    }
    """
    router_source = """
    import 'package:hooks_riverpod/hooks_riverpod.dart';

    class AppRouter extends HookWidget {
      const AppRouter({super.key});
    }
    """
    presentation_source = """
    import 'package:hooks_riverpod/hooks_riverpod.dart';

    class SampleScreen extends HookWidget {
      const SampleScreen({super.key});
    }
    """

    assert _violations(
        "memox.hooks_presentation_only",
        tmp_path,
        "lib/domain/sample.dart",
        domain_source,
    )
    assert _violations(
        "memox.hooks_presentation_only",
        tmp_path,
        "lib/data/sample.dart",
        data_source,
    )
    assert _violations(
        "memox.hooks_presentation_only",
        tmp_path,
        "lib/app/router/router.dart",
        router_source,
    )
    assert not _violations(
        "memox.hooks_presentation_only",
        tmp_path,
        "lib/presentation/features/sample/sample_screen.dart",
        presentation_source,
    )


def test_shared_hook_declarations_must_use_mx_prefix(tmp_path: Path) -> None:
    bad = """
    String useSharedTextValue(TextEditingController controller) {
      useListenable(controller);
      return controller.text;
    }
    """
    good = """
    String useMxSharedTextValue(TextEditingController controller) {
      useListenable(controller);
      return controller.text;
    }
    """
    safe_calls_only = """
    class SampleWidget extends StatelessWidget {
      @override
      Widget build(BuildContext context) {
        final controller = useTextEditingController();
        useListenable(controller);
        return const SizedBox.shrink();
      }
    }
    """

    assert _violations(
        "memox.shared_hook_custom_names_use_mx_prefix",
        tmp_path,
        "lib/presentation/shared/hooks/mx_text_controller_hooks.dart",
        bad,
    )
    assert not _violations(
        "memox.shared_hook_custom_names_use_mx_prefix",
        tmp_path,
        "lib/presentation/shared/hooks/mx_text_controller_hooks.dart",
        good,
    )
    assert not _violations(
        "memox.shared_hook_custom_names_use_mx_prefix",
        tmp_path,
        "lib/presentation/shared/hooks/mx_text_controller_hooks.dart",
        safe_calls_only,
    )


def test_search_field_rule_requires_shared_search_hook_for_owned_controller(
    tmp_path: Path,
) -> None:
    bad = """
    class SampleSearchScreen extends HookConsumerWidget {
      const SampleSearchScreen({super.key});

      @override
      Widget build(BuildContext context, WidgetRef ref) {
        final controller = useTextEditingController();
        return MxSearchField(
          controller: controller,
          onChanged: (value) => ref.read(searchQueryProvider.notifier).set(value),
        );
      }
    }
    """
    good = bad.replace(
        "final controller = useTextEditingController();\n",
        "final search = useMxSearchController(ref);\n",
    ).replace(
        "controller: controller,\n          onChanged: (value) => ref.read(searchQueryProvider.notifier).set(value),\n",
        "controller: search.controller,\n          onChanged: search.onChanged,\n",
    )
    shared_widget = """
    class MxSearchField extends StatelessWidget {
      const MxSearchField({super.key});

      @override
      Widget build(BuildContext context) => const SizedBox.shrink();
    }
    """

    assert _violations(
        "memox.mx_search_field_uses_shared_search_hook",
        tmp_path,
        "lib/presentation/features/sample/sample_screen.dart",
        bad,
    )
    assert not _violations(
        "memox.mx_search_field_uses_shared_search_hook",
        tmp_path,
        "lib/presentation/features/sample/sample_screen.dart",
        good,
    )
    assert not _violations(
        "memox.mx_search_field_uses_shared_search_hook",
        tmp_path,
        "lib/presentation/shared/widgets/inputs/mx_search_field.dart",
        shared_widget,
    )


def test_text_value_rule_requires_shared_text_hooks_for_manual_listeners(
    tmp_path: Path,
) -> None:
    bad = """
    class SampleTextField extends HookWidget {
      const SampleTextField({super.key});

      @override
      Widget build(BuildContext context) {
        final controller = useTextEditingController();
        useListenable(controller);
        return TextField(controller: controller);
      }
    }
    """
    with_mx_text_value = bad.replace(
        "        useListenable(controller);\n",
        "        final value = useMxTextValue(controller);\n",
    )
    with_mx_text_submit_state = bad.replace(
        "        useListenable(controller);\n",
        "        final submitState = useMxTextSubmitState(controller);\n",
    )
    with_mx_search_controller = bad.replace(
        "        useListenable(controller);\n",
        "        final search = useMxSearchController(ref);\n",
    )

    assert _violations(
        "memox.text_controller_value_uses_shared_text_hook",
        tmp_path,
        "lib/presentation/features/sample/sample_screen.dart",
        bad,
    )
    assert not _violations(
        "memox.text_controller_value_uses_shared_text_hook",
        tmp_path,
        "lib/presentation/features/sample/sample_screen.dart",
        with_mx_text_value,
    )
    assert not _violations(
        "memox.text_controller_value_uses_shared_text_hook",
        tmp_path,
        "lib/presentation/features/sample/sample_screen.dart",
        with_mx_text_submit_state,
    )
    assert not _violations(
        "memox.text_controller_value_uses_shared_text_hook",
        tmp_path,
        "lib/presentation/features/sample/sample_screen.dart",
        with_mx_search_controller,
    )


def test_submit_hook_rule_flags_manual_disabled_submit_state(
    tmp_path: Path,
) -> None:
    bad = """
    class SampleForm extends HookWidget {
      const SampleForm({super.key});

      @override
      Widget build(BuildContext context) {
        final controller = useTextEditingController();
        final canSubmit = controller.text.trim().isNotEmpty;
        return Column(
          children: [
            TextField(controller: controller),
            FilledButton(
              onPressed: canSubmit ? () {} : null,
              child: const Text('Save'),
            ),
          ],
        );
      }
    }
    """
    good = bad.replace(
        "        final canSubmit = controller.text.trim().isNotEmpty;\n",
        "        final submitState = useMxTextSubmitState(controller);\n",
    ).replace(
        "              onPressed: canSubmit ? () {} : null,\n",
        "              onPressed: submitState.canSubmit ? () {} : null,\n",
    )

    assert _violations(
        "memox.text_submit_state_uses_shared_submit_hook",
        tmp_path,
        "lib/presentation/features/sample/sample_screen.dart",
        bad,
    )
    assert not _violations(
        "memox.text_submit_state_uses_shared_submit_hook",
        tmp_path,
        "lib/presentation/features/sample/sample_screen.dart",
        good,
    )


def test_focus_hook_rule_flags_manual_post_frame_focus(tmp_path: Path) -> None:
    bad = """
    class SampleScreen extends HookConsumerWidget {
      const SampleScreen({super.key});

      @override
      Widget build(BuildContext context, WidgetRef ref) {
        WidgetsBinding.instance.addPostFrameCallback((_) {
          focusNode.requestFocus();
        });
        return const SizedBox.shrink();
      }
    }
    """
    good = bad.replace(
        "        WidgetsBinding.instance.addPostFrameCallback((_) {\n"
        "          focusNode.requestFocus();\n"
        "        });\n",
        "        useMxRequestFocusAfterFrame(focusNode);\n",
    )

    assert _violations(
        "memox.post_frame_focus_uses_shared_focus_hook",
        tmp_path,
        "lib/presentation/features/sample/sample_screen.dart",
        bad,
    )
    assert not _violations(
        "memox.post_frame_focus_uses_shared_focus_hook",
        tmp_path,
        "lib/presentation/features/sample/sample_screen.dart",
        good,
    )


def test_generic_safety_cases_stay_compliant(tmp_path: Path) -> None:
    safe_screen = """
    class SampleScreen extends StatelessWidget {
      const SampleScreen({super.key});

      @override
      Widget build(BuildContext context) {
        return const SizedBox.shrink();
      }
    }
    """
    controlled_widget = """
    class MxSearchField extends StatelessWidget {
      const MxSearchField({super.key});

      @override
      Widget build(BuildContext context) {
        return const SizedBox.shrink();
      }
    }
    """

    assert not _violations(
        "memox.hooks_presentation_only",
        tmp_path,
        "lib/presentation/features/sample/sample_screen.dart",
        safe_screen,
    )
    assert not _violations(
        "memox.mx_search_field_uses_shared_search_hook",
        tmp_path,
        "lib/presentation/shared/widgets/inputs/mx_search_field.dart",
        controlled_widget,
    )
    assert not _violations(
        "memox.text_controller_value_uses_shared_text_hook",
        tmp_path,
        "lib/presentation/features/sample/sample_screen.dart",
        safe_screen,
    )
    assert not _violations(
        "memox.text_submit_state_uses_shared_submit_hook",
        tmp_path,
        "lib/presentation/features/sample/sample_screen.dart",
        safe_screen,
    )
    assert not _violations(
        "memox.post_frame_focus_uses_shared_focus_hook",
        tmp_path,
        "lib/presentation/features/sample/sample_screen.dart",
        safe_screen,
    )
