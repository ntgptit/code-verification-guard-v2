# Agent YAML Contract

## Golden Rule

For normal rule additions, do not modify Python code. Add or update YAML only:

- `scopes/*.yaml`
- `registries/**/*.yaml`
- `profiles/*.yaml`
- `registries/projects/<ruleset>/*.yaml`
- `registries/projects/<ruleset>/guard-manifest.yaml`
- `registries/projects/<ruleset>/config/*.yaml`
- `registries/projects/<ruleset>/rules/*.yaml`
- project-level `code-verification-guard.yaml`

Only modify Python code when adding a new generic capability such as a matcher type, reporter type, resource loading behavior, registry behavior, CLI command, or validation mechanism.

## YAML Architecture

Do not put inline rules inside `code-verification-guard.yaml`.

`code-verification-guard.yaml` is legacy project config. New reusable policy
bundles should prefer `registries/projects/<ruleset>/guard-manifest.yaml`.

Rules must be defined only in registry files. Scopes must be defined only in scope files. Profiles must only override behavior and must not define new rules.

## Templates

YAML templates are stored under `templates/`. Use them as the source format
when adding new YAML files:

- `templates/code-verification-guard.yaml` for project config.
- `templates/registry.yaml` for `registries/**/*.yaml`.
- `templates/scope.yaml` for `scopes/*.yaml`.
- `templates/profile.yaml` for `profiles/*.yaml`.
- `templates/guard-manifest-rule-set.yaml` for adding a manifest rule set.

Keep the template style: list items must be indented under their key, for
example:

```yaml
scopes:
  - sample_source
patterns:
  - "\\bsample\\b"
```

Do not use indentless lists such as:

```yaml
scopes:
- sample_source
```

## Manifest Rules

Do not hardcode registry paths in Python core.

Rule set mapping for the new flow must be declared in
`registries/projects/<ruleset>/guard-manifest.yaml`. The manifest maps config
files and rule registry files relative to the ruleset root.

Shared common/language rule sets should be selected with `rule_sets` in the
ruleset manifest. Project-owned registries should live under
`registries/projects/<ruleset>/rules/`.

If a new language/framework/project rule set is needed, update `guard-manifest.yaml`.

## Rule Quality

Avoid weak or noisy rules. A rule must have a stable ID, clear severity, clear message, clear scope, low false-positive risk, and a fix hint when possible.

Every rule ID must use namespace format:

```text
common.no_trailing_whitespace
security.no_private_key
python.no_bare_except
flutter.no_hardcoded_color
memox.no_raw_card
```

Do not use vague IDs such as `rule1`, `check_something`, or `no_bad_code`.

Project rules should stay pattern-based and generic. Do not encode class-specific
or file-specific allowlists when a reusable regex, scope, or matcher can express
the policy safely. For MemoX, hook usage is presentation-only: local search
controller state should use `useMxSearchController`, local text controller
value or submit state should use `useMxTextValue` or
`useMxTextSubmitState`, and post-frame focus lifecycle should use
`useMxRequestFocusAfterFrame`. Warning rules may be promoted later once the
codebase has migrated, but controlled/stateless design-system widgets should
not be converted to hooks just to satisfy the guard.

## Scope Rules

Prefer scopes over repeated include/exclude patterns.

Use direct `include` only for file-specific rules such as:

```text
.env
.env.*
.DS_Store
Thumbs.db
*.tmp
*.bak
```

For source-code scanning, define and reuse scopes.

## Allowed Change Strategy

When fixing issues:

1. Prefer fixing source code.
2. If the issue is a false positive, improve the rule, matcher, scope, or exclude strategy.
3. If the issue is project-specific, use project overrides.
4. If the issue is environment-specific, use profiles.
5. Do not hardcode project-specific exceptions in Python core.
