"""Pattern-level tests for MemoX UI async guard rules."""

from __future__ import annotations

import re

MOUNTED_LINE_PATTERNS = [
    r"\bif\s*\(\s*!?\s*(?!(?:ref|context)\.)mounted\b",
    r"\bif\s*\([^)]*[!&|]\s*!?\s*(?!(?:ref|context)\.)mounted\b",
    r"\bif\s*\(\s*!?\s*context\.mounted\b",
    r"\bif\s*\([^)]*[!&|]\s*!?\s*context\.mounted\b",
    r"^\s*[!&|]\s*!?\s*(?!(?:ref|context)\.)mounted\b",
    r"^\s*!?\s*(?!(?:ref|context)\.)mounted\s*[!&|]",
    r"^\s*[!&|]\s*!?\s*context\.mounted\b",
    r"^\s*!?\s*context\.mounted\s*[!&|]",
]

MOUNTED_MULTILINE_PATTERNS = [
    r"(?s)\bif\s*\([^;{]*?\b!?\s*(?!(?:ref|context)\.)mounted\b",
    r"(?s)\bif\s*\([^;{]*?\b!?\s*context\.mounted\b",
]

AD_HOC_GUARD_PATTERNS = [
    r"\b_(?:isCurrent(?:Request)?|isStillCurrent|isSameRequest|isAlive|canContinue)\s*\(",
    r"\b(?:canContinueUi|guardUi)\s*\(",
]

GUARD_REQUIRED_FILE_PATTERN = re.compile(
    r"(?s)^(?=.*extends\s+(?:Consumer)?State<)"
    r"(?=.*Future<[^>]*>\s+\w+\s*\([^)]*\)\s+async\s*\{[\s\S]*?\bawait\b)"
    r"(?!.*final\s+guard\s*=\s*Ui(?:Async|Mounted)Guard\s*\().+"
)

AWAIT_GUARD_BEFORE_UI_PATTERN = re.compile(
    r"(?s)await\s+[^;]+;\s*"
    r"(?!\s*if\s*\(\s*!guard\.canContinue\s*\)\s*\{\s*return;\s*\})"
    r"(?=[\s\S]{0,500}?(?:setState\s*\(|context\.(?:push|pop|replace|go|popRoute|goNamed|pushNamed)"
    r"|Navigator\.|ScaffoldMessenger|showDialog|MxBottomSheet|MxDialog|MxNameDialog"
    r"|MxConfirmationDialog|AppLocalizations\.of))"
)


def _any_match(patterns: list[str], text: str, *, multiline: bool = False) -> bool:
    flags = re.MULTILINE
    if multiline:
        flags |= re.DOTALL
    return any(re.search(pattern, text, flags) for pattern in patterns)


def test_mounted_line_patterns_flag_direct_checks() -> None:
    assert _any_match(MOUNTED_LINE_PATTERNS, "if (!mounted) return;", multiline=True)
    assert _any_match(MOUNTED_LINE_PATTERNS, "if (!context.mounted) return;", multiline=True)
    assert _any_match(
        MOUNTED_LINE_PATTERNS,
        "if (!mounted || !success) return;",
        multiline=True,
    )
    assert _any_match(
        MOUNTED_LINE_PATTERNS,
        "        !mounted ||\n",
        multiline=True,
    )


def test_mounted_line_patterns_ignore_ref_mounted() -> None:
    assert not _any_match(
        MOUNTED_LINE_PATTERNS,
        "if (!ref.mounted) return;",
        multiline=True,
    )


def test_mounted_line_patterns_allow_guard_setup() -> None:
    assert not _any_match(
        MOUNTED_LINE_PATTERNS,
        "isMounted: () => mounted,",
        multiline=True,
    )
    assert not _any_match(
        MOUNTED_LINE_PATTERNS,
        "isMounted: () => context.mounted,",
        multiline=True,
    )
    assert not _any_match(
        MOUNTED_LINE_PATTERNS,
        "if (!guard.canContinue) { return; }",
        multiline=True,
    )


def test_mounted_multiline_pattern_flags_split_conditions() -> None:
    source = """
    if (status != AnimationStatus.completed ||
        !mounted ||
        _answerState != _RecallAnswerState.hidden) {
      return;
    }
    """
    assert _any_match(MOUNTED_MULTILINE_PATTERNS, source)


def test_ad_hoc_guard_patterns_flag_custom_helpers() -> None:
    assert _any_match(AD_HOC_GUARD_PATTERNS, "if (!_isCurrentRequest(token)) return;")
    assert _any_match(AD_HOC_GUARD_PATTERNS, "if (!guardUi(token)) return;")


def test_guard_required_pattern_requires_ui_guard_in_file() -> None:
    missing_guard = """
    class _ExampleState extends State<Example> {
      Future<void> load() async {
        await Future<void>.value();
        setState(() {});
      }
    }
    """
    assert GUARD_REQUIRED_FILE_PATTERN.search(missing_guard)

    with_guard = """
    class _ExampleState extends State<Example> {
      Future<void> load() async {
        final guard = UiMountedGuard(isMounted: () => mounted);
        await Future<void>.value();
        if (!guard.canContinue) {
          return;
        }
      }
    }
    """
    assert not GUARD_REQUIRED_FILE_PATTERN.search(with_guard)


def test_await_guard_pattern_requires_can_continue_before_ui() -> None:
    bad = """
    final value = await load();
    setState(() {});
    """
    assert AWAIT_GUARD_BEFORE_UI_PATTERN.search(bad)

    good = """
    final value = await load();
    if (!guard.canContinue) {
      return;
    }
    context.popRoute();
    """
    assert not AWAIT_GUARD_BEFORE_UI_PATTERN.search(good)

    good_navigation_extension = """
    final success = await action();
    if (!guard.canContinue) {
      return;
    }
    context.goStudyResult(sessionId);
    """
    assert not AWAIT_GUARD_BEFORE_UI_PATTERN.search(good_navigation_extension)
