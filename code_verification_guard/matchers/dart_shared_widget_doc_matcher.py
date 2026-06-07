"""Dart shared widget documentation matcher implementation."""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

from code_verification_guard.constants.config_keys import ConfigKeys
from code_verification_guard.matchers.base_matcher import BaseMatcher
from code_verification_guard.models.scan_context import ScanContext
from code_verification_guard.models.violation import Violation
from code_verification_guard.rules.base_rule import BaseRule
from code_verification_guard.scanner.rule_file_reader import RuleFile


@dataclass(frozen=True)
class _DartClassBlock:
    """A parsed Dart class block and its immediate doc block."""

    class_name: str
    base_class: str | None
    start_line: int
    end_line: int
    code_line: str
    doc_lines: list[tuple[int, str]]
    field_names: set[str]


class DartSharedWidgetDocMatcher(BaseMatcher):
    """Checks Dart shared widget classes for structured doc comments."""

    SECTION_MARKERS = {
        "Purpose:": "purpose",
        "Use when:": "use_when",
        "Do not use when:": "do_not_use_when",
        "Category:": "category",
        "Public API:": "public_api",
        "States:": "states",
        "Variants:": "variants",
        "Expected contracts:": "expected_contracts",
    }

    CLASS_PATTERN = re.compile(r"^\s*class\s+(?P<class_name>[A-Za-z_]\w*)\b")
    EXTENDS_PATTERN = re.compile(r"\bextends\s+(?P<base_class>[A-Za-z_]\w*)\b")
    FIELD_PATTERN = re.compile(
        r"^\s*(?:late\s+)?final\s+(?:[A-Za-z_][\w<>, ?]*\s+)?(?P<field_name>[A-Za-z_]\w*)\s*(?:[=;,{])"
    )
    PUBLIC_API_ITEM_PATTERN = re.compile(r"^\s*-\s+(?P<field_name>[A-Za-z_]\w*)\s*:")

    def match(self, rule: BaseRule, context: ScanContext) -> list[Violation]:
        """Return Dart shared-widget documentation violations."""
        check = rule.rule_config.get(ConfigKeys.CHECK)
        if not check:
            return []

        base_classes = tuple(rule.rule_config.get(ConfigKeys.WIDGET_BASE_CLASSES, []))
        state_field_names = set(rule.rule_config.get(ConfigKeys.STATE_FIELD_NAMES, []))
        variant_field_names = set(rule.rule_config.get(ConfigKeys.VARIANT_FIELD_NAMES, []))
        allowed_values = set(rule.rule_config.get(ConfigKeys.ALLOWED_VALUES, []))
        known_contracts = tuple(rule.rule_config.get(ConfigKeys.KNOWN_CONTRACTS, []))
        only_categories = set(rule.rule_config.get(ConfigKeys.ONLY_CATEGORIES, []))

        violations: list[Violation] = []
        for rule_file in rule.target_rule_files(context.project_root):
            violations.extend(
                self._check_file(
                    rule=rule,
                    rule_file=rule_file,
                    check=check,
                    base_classes=base_classes,
                    state_field_names=state_field_names,
                    variant_field_names=variant_field_names,
                    allowed_values=allowed_values,
                    known_contracts=known_contracts,
                    only_categories=only_categories,
                )
            )

        return violations

    def _check_file(
        self,
        rule: BaseRule,
        rule_file: RuleFile,
        check: str,
        base_classes: tuple[str, ...],
        state_field_names: set[str],
        variant_field_names: set[str],
        allowed_values: set[str],
        known_contracts: tuple[str, ...],
        only_categories: set[str],
    ) -> list[Violation]:
        """Check one Dart file for shared widget doc violations."""
        violations: list[Violation] = []
        index = 0

        while index < len(rule_file.lines):
            line = rule_file.lines[index]
            class_match = self.CLASS_PATTERN.match(line)
            if class_match is None:
                index += 1
                continue

            block = self._parse_class_block(rule_file.lines, index, class_match)
            if block is None:
                index += 1
                continue

            index = block.end_line

            if block.class_name.startswith("_"):
                continue

            if base_classes and block.base_class not in base_classes:
                continue

            doc_lines = block.doc_lines
            if not doc_lines:
                if check == "required":
                    violations.append(
                        self._create_violation(
                            rule=rule,
                            file_path=rule_file.path,
                            block=block,
                        )
                    )
                continue

            doc_sections = self._parse_sections(doc_lines)
            summary_line = self._summary_line(doc_lines)

            if check == "required":
                continue

            if check == "summary_required":
                if summary_line is None or self._is_section_marker(summary_line):
                    violations.append(self._create_violation(rule, rule_file.path, block))
                continue

            if check == "purpose_required":
                if not doc_sections.get("purpose"):
                    violations.append(self._create_violation(rule, rule_file.path, block))
                continue

            if check == "use_when_required":
                if not doc_sections.get("use_when"):
                    violations.append(self._create_violation(rule, rule_file.path, block))
                continue

            if check == "do_not_use_when_required":
                category_value = self._first_non_empty_line(doc_sections.get("category", []))
                if only_categories and category_value not in only_categories:
                    continue

                if not doc_sections.get("do_not_use_when"):
                    violations.append(self._create_violation(rule, rule_file.path, block))
                continue

            if check == "category_required":
                if not self._first_non_empty_line(doc_sections.get("category", [])):
                    violations.append(self._create_violation(rule, rule_file.path, block))
                continue

            if check == "category_allowed_value":
                category_lines = doc_sections.get("category", [])
                category_value = self._first_non_empty_line(category_lines)
                if not category_value or category_value not in allowed_values:
                    violations.append(self._create_violation(rule, rule_file.path, block))
                continue

            if check == "public_api_required":
                if not self._has_public_api_item(doc_sections.get("public_api", [])):
                    violations.append(self._create_violation(rule, rule_file.path, block))
                continue

            if check == "states_required_when_state_field_exists":
                if block.field_names & state_field_names and not doc_sections.get("states"):
                    violations.append(self._create_violation(rule, rule_file.path, block))
                continue

            if check == "variants_required_when_variant_field_exists":
                if block.field_names & variant_field_names and not doc_sections.get("variants"):
                    violations.append(self._create_violation(rule, rule_file.path, block))
                continue

            if check == "expected_contracts_required":
                if not self._has_known_contract(doc_sections.get("expected_contracts", []), known_contracts):
                    violations.append(self._create_violation(rule, rule_file.path, block))
                continue

        return violations

    def _parse_class_block(
        self,
        lines: list[str],
        start_index: int,
        class_match: re.Match[str],
    ) -> _DartClassBlock | None:
        """Parse one Dart class block and its immediate documentation."""
        header_end = start_index
        while header_end < len(lines) and "{" not in lines[header_end]:
            header_end += 1

        if header_end >= len(lines):
            return None

        header_lines = lines[start_index : header_end + 1]
        base_class = self._base_class_name(" ".join(line.strip() for line in header_lines))
        depth = self._brace_delta(header_lines)
        field_names: set[str] = set()
        end_index = header_end
        scan_index = header_end + 1

        while scan_index < len(lines) and depth > 0:
            line = lines[scan_index]
            if depth == 1:
                field_match = self.FIELD_PATTERN.match(line)
                if field_match:
                    field_names.add(field_match.group("field_name"))

            depth += self._brace_delta([line])
            end_index = scan_index
            scan_index += 1

        doc_lines = self._doc_lines(lines, start_index)
        return _DartClassBlock(
            class_name=class_match.group("class_name"),
            base_class=base_class,
            start_line=start_index + 1,
            end_line=end_index + 1,
            code_line=lines[start_index].strip(),
            doc_lines=doc_lines,
            field_names=field_names,
        )

    def _doc_lines(self, lines: list[str], class_start_index: int) -> list[tuple[int, str]]:
        """Return the immediate Dart doc block before a class declaration."""
        doc_start = class_start_index
        while doc_start > 0 and self._is_doc_line(lines[doc_start - 1]):
            doc_start -= 1

        if doc_start == class_start_index:
            return []

        return [
            (line_index + 1, self._strip_doc_prefix(lines[line_index]))
            for line_index in range(doc_start, class_start_index)
        ]

    def _parse_sections(self, doc_lines: list[tuple[int, str]]) -> dict[str, list[str]]:
        """Parse named doc sections from a Dart doc block."""
        sections: dict[str, list[str]] = {value: [] for value in self.SECTION_MARKERS.values()}
        current_section: str | None = None

        for _, line in doc_lines:
            stripped = line.strip()
            if stripped in self.SECTION_MARKERS:
                current_section = self.SECTION_MARKERS[stripped]
                continue

            if current_section is not None:
                sections[current_section].append(line)

        return sections

    def _summary_line(self, doc_lines: list[tuple[int, str]]) -> str | None:
        """Return the first non-empty line in a Dart doc block."""
        for _, line in doc_lines:
            if line.strip():
                return line.strip()

        return None

    def _first_non_empty_line(self, lines: list[str]) -> str | None:
        """Return the first non-empty line from a section."""
        for line in lines:
            stripped = line.strip()
            if stripped:
                return stripped

        return None

    def _has_public_api_item(self, lines: list[str]) -> bool:
        """Return whether the Public API section lists at least one field."""
        return any(self.PUBLIC_API_ITEM_PATTERN.match(line) for line in lines)

    def _has_known_contract(self, lines: list[str], known_contracts: tuple[str, ...]) -> bool:
        """Return whether the Expected contracts section mentions a known contract."""
        section_text = "\n".join(lines)
        return any(re.search(rf"\b{re.escape(contract)}\b", section_text) for contract in known_contracts)

    def _create_violation(
        self,
        rule: BaseRule,
        file_path: Path,
        block: _DartClassBlock,
    ) -> Violation:
        """Create a class-scoped violation."""
        return rule.create_violation(
            file_path=file_path,
            class_name=block.class_name,
            line_number=block.start_line,
            code_line=block.code_line,
        )

    def _base_class_name(self, header_text: str) -> str | None:
        """Return the base class name used by a Dart class declaration."""
        match = self.EXTENDS_PATTERN.search(header_text)
        if match is None:
            return None

        return match.group("base_class")

    def _is_doc_line(self, line: str) -> bool:
        """Return whether a line is part of a Dart doc comment block."""
        return line.lstrip().startswith("///")

    def _strip_doc_prefix(self, line: str) -> str:
        """Strip the Dart doc prefix from a line."""
        stripped = line.lstrip()
        if stripped.startswith("///"):
            return stripped[3:].lstrip()
        return stripped

    def _is_section_marker(self, line: str) -> bool:
        """Return whether a line starts a named doc section."""
        return line.strip() in self.SECTION_MARKERS

    def _brace_delta(self, lines: list[str]) -> int:
        """Return the brace delta for one or more lines."""
        return sum(line.count("{") - line.count("}") for line in lines)
