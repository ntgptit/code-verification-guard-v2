"""Default values used by guard configuration and rules."""

from code_verification_guard.constants.severity import Severity


class Defaults:
    """Default configuration values for the guard."""
    SCHEMA_VERSION = 1
    CONFIG_FILE_NAME = "code-verification-guard.yaml"
    MANIFEST_FILE_NAME = "guard-manifest.yaml"
    DEFAULT_PROFILE = "local"
    REGISTRIES_DIRECTORY = "registries"
    SCOPES_DIRECTORY = "scopes"
    PROFILES_DIRECTORY = "profiles"
    PROJECTS_DIRECTORY = "projects"

    PROJECT_PATH = "."
    DEFAULT_RULE_ENABLED = True
    DEFAULT_REGEX_MODE = "line"
    REGEX_FILE_MODE = "file"
    REGEX_LINE_MODE = "line"

    DEFAULT_SEVERITY = Severity.ERROR
    DEFAULT_FAIL_ON = [Severity.ERROR]

    DEFAULT_INCLUDE_PATTERNS = ["**/*"]
    DEFAULT_DART_INCLUDE_PATTERNS = ["**/*.dart"]
    DEFAULT_COMMENT_PREFIXES = ["#", "//", "/*", "*", "*/"]
    DEFAULT_EXCLUDED_PATH_PARTS = {
        ".git",
        ".hg",
        ".svn",
        ".venv",
        "venv",
        "env",
        "node_modules",
        "__pycache__",
        ".pytest_cache",
        ".mypy_cache",
        ".ruff_cache",
        ".tox",
        ".nox",
        ".coverage",
        "build",
        "dist",
        ".dart_tool",
    }

    DEFAULT_REPORT_FORMAT = "console"

    MAX_BUILD_LINES = 80
    MAX_FILE_LINES = 400
