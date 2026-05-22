"""Rule type constants."""

from enum import StrEnum


class RuleType(StrEnum):
    """Supported rule implementation types."""
    REGEX = "regex"
    FILE_NAME = "file_name"
    MAX_LINES = "max_lines"
    MAX_BUILD_LINES = "max_build_lines"
    FORBIDDEN_IMPORT = "forbidden_import"
    IF_COMMENT = "if_comment"
    PYTHON_DOCSTRING = "python_docstring"
