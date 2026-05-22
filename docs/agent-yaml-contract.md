# Agent YAML Contract

## Golden Rule

For normal rule additions, do not modify Python code. Add or update YAML only:

- `scopes/*.yaml`
- `registries/**/*.yaml`
- `profiles/*.yaml`
- `guard-manifest.yaml`
- project-level `code-verification-guard.yaml`

Only modify Python code when adding a new generic capability such as a matcher type, reporter type, resource loading behavior, registry behavior, CLI command, or validation mechanism.

## YAML Architecture

Do not put inline rules inside `code-verification-guard.yaml`.

`code-verification-guard.yaml` is only for project metadata, selected profile, selected rule sets, custom registries, custom scopes, overrides, failure policy, and report options.

Rules must be defined only in registry files. Scopes must be defined only in scope files. Profiles must only override behavior and must not define new rules.

## Manifest Rules

Do not hardcode registry paths in Python core.

Rule set mapping must be declared in `guard-manifest.yaml`. The manifest maps rule set names to scope files and registry files.

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
