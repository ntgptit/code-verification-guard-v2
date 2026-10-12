# memox-v8 ruleset

The main guard for the memox-v8 repository. It owns every check
`flutter analyze` cannot express.

```bash
python code-verification-guard-v2/guard/run.py check --project . --ruleset memox-v8
```

## Why this ruleset exists separately from `memox`

`memox` is the one other MemoX ruleset beside it. It stays for one reason — the
guard's own test suite exercises its rule engine through that ruleset — and it
does not fit this repository:

| Ruleset | Why it does not apply |
|---|---|
| `memox` | Flutter, but a layer-first tree (`lib/presentation/features/**`, `lib/data/datasources/**`). memox-v8 is **feature-first**: `lib/features/<feature>/{domain,data,presentation}`. Every scope path differs, so the rules would silently match nothing. |

No ruleset for another tree is vendored beside them: it would be easy to run
the wrong one, and a ruleset that matches nothing reports a clean pass.

## What it replaces

V8 runs neither `custom_lint` nor `riverpod_lint`: `pubspec.yaml` has neither,
so `flutter analyze` checks no Riverpod usage.

`memox-state-management-rules.yaml` makes those checks. The rule that matters
most is `memox.state_management.no_ref_read_in_build`: `ref.read` inside
`build()` reads without subscribing, so the widget silently stops updating. It
surfaces as "the data is stale" and is very hard to trace back to that line.

## Files

| File | Covers |
|---|---|
| `memox-architecture-rules.yaml` | Layer boundaries (ADR-010, ADR-011), a domain free of infrastructure, one database connection site, deferred dependencies (ADR-001, ADR-002) |
| `memox-state-management-rules.yaml` | Riverpod 3 usage — the riverpod_lint replacement |
| `memox-error-handling-rules.yaml` | Swallowed exceptions, `print`, Failure mapping |
| `memox-design-token-rules.yaml` | No raw colour / text style / spacing in product UI |
| `memox-design-system-rules.yaml` | Features compose the Mx shared widgets; weights, text styles and colour roles go through the theme |
| `memox-i18n-rules.yaml` | No user-visible string outside ARB |
| `memox-data-model-rules.yaml` | The root through `root_id` (BR-DECK-003), no ambient clock in domain, the schedule apart from the card (ADR-004), the stored review kind (BR-SRS-015), buttons from `supportedActions` (ADR-003) |
| `memox-privacy-rules.yaml` | Card content never logged, no secrets, app-private storage |
| `memox-naming-rules.yaml` | snake_case and role suffixes |
| `memox-testing-rules.yaml` | No skipped or focused tests |

## Scope discipline

Design-token and i18n rules run on `ui_surfaces` — `lib/features/*/presentation`
plus `lib/shared` — and deliberately **not** on:

- `lib/core/theme/**`, where raw values are legitimately *defined*; linting it
  would flag the definition as the crime
- `lib/app/**`, the composition root and the debug-only widget gallery, which
  are not product UI. The typography rules still cover it
  (`typography_ui_surfaces`).

## A `rule_without_targets` warning is a finding — do not silence it

A rule whose scope matches no file checks nothing and passes green. The engine
reports it as `guard.config.rule_without_targets`, and both profiles fail on
warnings, so it cannot pass unnoticed. A rule that waits for a layer V8 has not
built yet says so with `targets_pending` in `config/overrides.yaml`.

## Adding a rule

1. Put it in the file whose domain it belongs to; keep the
   `memox.<domain>.<name>` id convention.
2. Prefer an existing scope over a per-rule `include:`.
3. Write the message so it says *why*, not just *what* — the message is the only
   thing the person who trips it will read.
4. **Fault-inject it.** Write a file that violates it, confirm the guard exits 1
   and names your rule, delete the file, confirm exit 0. A rule that has never
   fired is not known to work.
