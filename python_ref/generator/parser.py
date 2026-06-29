"""Parse Python docstrings into docs-generator models."""
from __future__ import annotations

import inspect
import re
import textwrap

from generator.models import (
    ArgumentDoc,
    ParsedDocstring,
    RaisesDoc,
    ReturnDoc,
)


def parse_docstring(docstring: str | None) -> ParsedDocstring:
    """Parse a docstring into docs-oriented sections."""
    if not docstring:
        return ParsedDocstring()

    cleaned = inspect.cleandoc(docstring)
    lines = cleaned.splitlines()

    description_lines: list[str] = []
    args_lines: list[str] = []
    returns_lines: list[str] = []
    examples_lines: list[str] = []
    raises_lines: list[str] = []

    current_section = "description"

    for line in lines:
        stripped = line.strip()

        if stripped in {"Args:", "Arguments:", "Parameters:"}:
            current_section = "arguments"
            continue

        if stripped == "Returns:":
            current_section = "returns"
            continue

        if stripped in {"Examples:", "Example:"}:
            current_section = "examples"
            continue

        if stripped == "Raises:":
            current_section = "raises"
            continue

        if current_section == "description":
            description_lines.append(line)
        elif current_section == "arguments":
            args_lines.append(line)
        elif current_section == "returns":
            returns_lines.append(line)
        elif current_section == "examples":
            examples_lines.append(line)
        elif current_section == "raises":
            raises_lines.append(line)

    return ParsedDocstring(
        description=_normalize_block(description_lines),
        arguments=parse_argument_block(args_lines),
        returns=parse_return_block(returns_lines),
        examples=_normalize_block(examples_lines),
        raises=parse_raises_block(raises_lines),
    )


def parse_argument_block(lines: list[str]) -> list[ArgumentDoc]:
    """Parse an Args/Parameters-style block."""
    arguments: list[ArgumentDoc] = []
    current_name: str | None = None
    current_indent = 0
    current_description: list[str] = []

    for raw_line in lines:
        stripped = raw_line.rstrip().strip()
        indent = _line_indent(raw_line)

        if not stripped:
            continue

        if _looks_like_doc_field(stripped) and (
            current_name is None or indent <= current_indent
        ):
            if current_name is not None:
                description = _join_description_lines(current_description)
                arguments.append(
                    ArgumentDoc(
                        name=current_name,
                        description=description,
                        internal_use=check_lazydoc(description),
                    )
                )

            field_name, description = _split_doc_field(stripped)
            current_name = field_name
            current_indent = indent
            current_description = [description] if description else []
            continue

        if current_name is not None:
            current_description.append(
                _description_continuation(raw_line, current_indent)
            )

    if current_name is not None:
        description = _join_description_lines(current_description)
        arguments.append(
            ArgumentDoc(
                name=current_name,
                description=description,
                internal_use=check_lazydoc(description),
            )
        )

    return arguments


def parse_raises_block(lines: list[str]) -> list[RaisesDoc]:
    """Parse a Raises-style block."""
    raises: list[RaisesDoc] = []
    name: str | None = None
    description: list[str] = []

    for raw_line in lines:
        stripped = raw_line.rstrip().strip()

        if not stripped:
            continue

        if _looks_like_doc_field(stripped):
            if name is not None:
                raises.append(
                    RaisesDoc(
                        name=name,
                        description=_join_description_lines(description),
                    )
                )

            name, field_description = _split_doc_field(stripped)
            description = [field_description] if field_description else []
            continue

        if name is not None:
            description.append(stripped)

    if name is not None:
        raises.append(
            RaisesDoc(
                name=name,
                description=_join_description_lines(description),
            )
        )

    return raises


def parse_return_block(lines: list[str]) -> list[ReturnDoc]:
    """Parse a Returns-style block."""
    returns: list[ReturnDoc] = []
    current_name: str | None = None
    current_description: list[str] = []

    for raw_line in lines:
        stripped = raw_line.rstrip().strip()

        if not stripped:
            continue

        if _looks_like_doc_field(stripped):
            if current_name is not None or current_description:
                returns.append(
                    ReturnDoc(
                        type_name=current_name or "",
                        description=_join_description_lines(current_description),
                    )
                )

            field_name, description = _split_doc_field(stripped)
            current_name = field_name
            current_description = [description] if description else []
            continue

        if current_name is None and not current_description:
            current_description = [stripped]
            continue

        current_description.append(stripped)

    if current_name is not None or current_description:
        returns.append(
            ReturnDoc(
                type_name=current_name or "",
                description=_join_description_lines(current_description),
            )
        )

    return returns


def check_lazydoc(description: str) -> bool:
    """Return True if the description contains a lazydoc directive."""
    return "lazydoc" in description


def _looks_like_doc_field(line: str) -> bool:
    """Return True if a line looks like a simple doc field entry."""
    if ":" not in line:
        return False

    left, _right = line.split(":", 1)
    field_name = left.strip()
    return bool(
        re.fullmatch(
            r"\*{0,2}[A-Za-z_][\w.]*\s*(?:\([^)]*\))?\s*(?:=\s*[^:]+)?",
            field_name,
        )
    )


def _split_doc_field(line: str) -> tuple[str, str]:
    """Split a simple ``name: description`` doc line."""
    left, right = line.split(":", 1)
    name = left.strip()
    description = right.strip()

    if "(" in name:
        name = name.split("(", 1)[0].strip()
    elif "=" in name:
        name = name.split("=", 1)[0].strip()

    return name, description


def _normalize_block(lines: list[str]) -> str:
    """Normalize a free-text docstring block."""
    text = "\n".join(lines).strip()
    return textwrap.dedent(text).strip()


def _join_description_lines(lines: list[str]) -> str:
    """Join multiple description lines into readable prose."""
    parts = [part.rstrip() for part in lines if part.strip()]
    if any(_looks_like_markdown_list_item(part.strip()) for part in parts):
        return "\n".join(parts).strip()

    return " ".join(part.strip() for part in parts).strip()


def _looks_like_markdown_list_item(line: str) -> bool:
    """Return True if a line starts a markdown list item."""
    return line.startswith(("- ", "* ", "+ "))


def _line_indent(line: str) -> int:
    """Return the number of leading spaces in a line."""
    return len(line) - len(line.lstrip(" "))


def _description_continuation(line: str, field_indent: int) -> str:
    """Return continuation text relative to the parent doc field."""
    stripped = line.rstrip()
    content_indent = field_indent + 4
    if _line_indent(stripped) >= content_indent:
        return stripped[content_indent:]

    return stripped.strip()
