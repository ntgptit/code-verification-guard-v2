# Agent Source Architecture Notes

## Source-Only Layout

The tool is source-only. It is intended to be copied or unzipped into a project
and run from that vendored source tree.

Root YAML resources are the only built-in rule source:

```text
guard-manifest.yaml
profiles/
scopes/
registries/
```

Do not add a second packaged resource copy under `code_verification_guard/`.
If root resources are changed, no sync step is required.

The runnable source bundle is composed of:

```text
code_verification_guard/   Python engine only
guard/                     Local CLI entrypoint
guard-manifest.yaml        Built-in rule set manifest
profiles/                  Built-in runtime profiles
scopes/                    Built-in reusable scopes
registries/                Built-in rule registries
code-verification-guard.yaml
```

The Python engine must stay generic. Concrete project, language, framework, and
convention rules belong in root YAML files unless a new generic matcher or
loader capability is needed.

## File Hygiene

Do not commit generated/cache/build artifacts:

```text
.pytest_cache/
.mypy_cache/
.ruff_cache/
.tox/
.nox/
__pycache__/
*.pyc
build/
dist/
*.egg-info/
.coverage
htmlcov/
```

The zip script must include the source bundle and exclude these files.

## CLI Contract

The following commands must keep working:

```powershell
python guard\run.py --help
python guard\run.py check --project .
```

The installed `code-verification-guard` console script is not a supported
distribution path for this source-only workflow.

## Documentation Contract

When adding a new rule set, update `guard-manifest.yaml`, related `scopes/*.yaml`, related `registries/**/*.yaml`, and README or docs if behavior is user-facing.

When adding a new matcher type, document the matcher type name, required YAML fields, supported optional fields, example registry usage, and limitations.
