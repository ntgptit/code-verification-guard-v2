# Decision Tables: registry_and_scanner_test

Test file: `tests/test_file_scanner.py`
Test file: `tests/test_config_manager.py`
Test file: `tests/test_rule_registry.py`
Test file: `tests/test_rule_runner.py`

## Decision table: collectFiles

| ID | Branch / condition | Given | When | Then | Coverage |
| --- | --- | --- | --- | --- | --- |
| DT1 | file is under a default excluded directory | cache and dependency directories contain files | scanner collects `**/*` | only source files outside excluded paths are returned | C0+C1 |
| DT2 | file is a root coverage artifact | `.coverage` exists at project root | scanner collects `**/*` | `.coverage` is not returned | C0+C1 |

## Decision table: loadResources

| ID | Branch / condition | Given | When | Then | Coverage |
| --- | --- | --- | --- | --- | --- |
| DT1 | source manifest is missing | config manager receives a source root with no manifest | built-in rules are loaded | bundled resource rules are available | C0+C1 |
