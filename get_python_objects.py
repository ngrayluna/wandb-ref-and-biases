"""
Get Python objects from a module.
"""

from __future__ import annotations

import ast
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True, slots=True)
class ExportedName:
    """A public name exported by a module."""

    public_name: str
    source_module: str | None = None
    source_name: str | None = None
    declared_in_all: bool = False


def parse_public_exports(path: str | Path) -> list[ExportedName]:
    """Parse a module file and return end-user-facing exported names.

    Policy:
    - If ``__all__`` exists, it is treated as authoritative.
    - Names in ``__all__`` marked with ``doc:exclude`` are omitted.
    - ``from x import y`` statements are used only to attach provenance to
      names already present in ``__all__``.
    - If ``__all__`` does not exist, fall back to names from
      ``from x import y`` statements.

    Notes:
    - Plain ``import x`` statements are ignored.
    - Star imports are ignored.
    - Dynamic ``__all__`` construction is not supported.
    - Relative imports are preserved as written.
    """
    path = Path(path)
    source = path.read_text(encoding="utf-8")
    module = ast.parse(source, filename=str(path))
    lines = source.splitlines()

    all_names: list[str] | None = None
    imported_names: dict[str, ExportedName] = {}

    # First pass: collect __all__ names and imported names.
    for node in module.body:
        if _is_all_assignment(node):
            all_names = _extract_all_names(node, lines)
            continue

        if isinstance(node, ast.ImportFrom):
            module_name = _format_importfrom_module(node)
            for alias in node.names:
                if alias.name == "*":
                    continue

                public_name = alias.asname or alias.name
                imported_names[public_name] = ExportedName(
                    public_name=public_name,
                    source_module=module_name,
                    source_name=alias.name,
                    declared_in_all=False,
                )

    # If __all__ doesn't exist, use imported names as the source of truth
    if all_names is None:
        return [imported_names[name] for name in sorted(imported_names)]

    # If __all__ exists, use it as the source of truth and enrich source info
    exports: list[ExportedName] = []
    for name in all_names:
        imported_item = imported_names.get(name)

        if imported_item is None:
            exports.append(
                ExportedName(
                    public_name=name,
                    source_module=None,
                    source_name=None,
                    declared_in_all=True,
                )
            )
            continue

        exports.append(
            ExportedName(
                public_name=imported_item.public_name,
                source_module=imported_item.source_module,
                source_name=imported_item.source_name,
                declared_in_all=True,
            )
        )

    return exports


def _is_all_assignment(node: ast.stmt) -> bool:
    """Return True if the node assigns to ``__all__``."""
    if not isinstance(node, ast.Assign):
        return False

    return any(
        isinstance(target, ast.Name) and target.id == "__all__"
        for target in node.targets
    )


def _extract_all_names(node: ast.Assign, lines: list[str]) -> list[str]:
    """Extract non-excluded string names from a simple ``__all__`` assignment."""
    value = node.value
    if not isinstance(value, (ast.List, ast.Tuple)):
        return []

    names: list[str] = []

    for element in value.elts:
        if not isinstance(element, ast.Constant) or not isinstance(element.value, str):
            continue

        if _node_has_doc_exclude(element, lines):
            continue

        names.append(element.value)

    return names


def _node_has_doc_exclude(node: ast.AST, lines: list[str]) -> bool:
    """Return True if any source line for the node contains ``doc:exclude``."""
    start = getattr(node, "lineno", None)
    end = getattr(node, "end_lineno", start)

    if start is None or end is None:
        return False

    return any("doc:exclude" in line for line in lines[start - 1 : end])


def _format_importfrom_module(node: ast.ImportFrom) -> str:
    """Return the module string for an ``ImportFrom`` node, preserving relativity."""
    return f'{"." * node.level}{node.module or ""}'