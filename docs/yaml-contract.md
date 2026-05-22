# YAML Contract

Code Verification Guard uses YAML files as its rule contract:

- `guard-manifest.yaml`
- `code-verification-guard.yaml`
- `profiles/*.yaml`
- `scopes/*.yaml`
- `registries/**/*.yaml`

Built-in YAML files are loaded only from the vendored source tree. Do not keep a
second bundled copy under `code_verification_guard/resources`.

Architecture ownership:

- `guard-manifest.yaml` maps rule set names to scope and registry files.
- `profiles/*.yaml` defines runtime failure/reporting defaults and overrides.
- `scopes/*.yaml` defines reusable file target sets.
- `registries/**/*.yaml` defines concrete rules.
- `code-verification-guard.yaml` selects rule sets and project-specific
  overrides for the checked project.

Templates:

- YAML templates live in `templates/`.
- Copy the closest template before adding a new config, profile, scope,
  registry, or manifest rule-set entry.
- Keep list items indented under their parent key; this is the repository's
  required style even when YAML parsers would accept shorter forms.
