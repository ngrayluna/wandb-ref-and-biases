"""


Example AST from parsing wand.public.apis __init__.py file.

```text
Module(
    body=[
        Assign(
            targets=[
                    Name(id='__all__', ctx=Store())],
            value=Tuple(
                    elts=[
                        Constant(value='Api'),
                        Constant(value='RetryingClient'),
                        Constant(value='requests'),
                        Constant(value='ArtifactCollection'),
                        Constant(value='ArtifactCollections'),
                ...),
        ...),
    ImportFrom(
        module='wandb.apis.public.api',
        names=[
            alias(name='Api'),
            alias(name='RetryingClient')],
        level=0),          
    ...,
)
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

    Args:
        path: The file path to the module to parse.

    Returns:
        A list of ExportedName objects representing the public API of the module.
    """
    path = Path(path)
    source = path.read_text(encoding="utf-8")

    # Parse the source into an AST
    module = ast.parse(source, filename=str(path))

    # Read source lines to find doc:exclude comments
    lines = source.splitlines()

    all_names: list[str] | None = None
    imported_names: dict[str, ExportedName] = {}

    # First pass: collect __all__ names and imported names.
    for node in module.body:

        # Check for __all__ assignment
        if _is_all_assignment(node):
            all_names = _extract_all_names(node, lines)
            continue

        # Check for "from x import y" statements to track imported names
        # and source info (i.e. module path).
        if isinstance(node, ast.ImportFrom):
            module_name = _format_importfrom_module(node)
            for alias in node.names:
                if alias.name == "*":
                    continue

                # For "from x import y as z", the public name is "z".
                # For "from x import y", the public name is "y".
                public_name = alias.asname or alias.name
                imported_names[public_name] = ExportedName(
                    public_name=public_name,
                    source_module=module_name,
                    source_name=alias.name,
                    declared_in_all=False,
                )

    # If __all__ doesn't exist, use imported names ("from x import y") 
    # as the source of truth
    if all_names is None:
        return [imported_names[name] for name in sorted(imported_names)]

    # If __all__ exists, use it as the source of truth and provide source module.
    exports: list[ExportedName] = []
    for name in all_names:
        imported_item = imported_names.get(name)
        exports.append(
            ExportedName(
                public_name=name,
                source_module=imported_item.source_module if imported_item else None,
                source_name=imported_item.source_name if imported_item else None,
                declared_in_all=True,
            )
        )

    return exports


def _is_all_assignment(node: ast.stmt) -> bool:
    """Detects __all__ = [...] assignments.

    First, check if node is an element of type `ast.Assign`. 
    If yes, check if target is of type `ast.Name` with id "__all__". 
    
    Returns True if both conditions are met, False otherwise.

    Args:
        node: An AST node to check for being an assignment to __all__.
    ```
    
    Returns:
        True if the node assigns to ``__all__``.
    """
    if not isinstance(node, ast.Assign):
        return False

    return any(
        isinstance(target, ast.Name) and target.id == "__all__"
        for target in node.targets
    )


def _extract_all_names(node: ast.Assign, lines: list[str]) -> list[str]:
    """Pulls string literals from the __all__ list/tuple. 
    
    Filters out entries annotated with ``doc:exclude``, and returns the
    resulting list of names.

    Args:
        node: The AST node representing the __all__ assignment.
        lines: The source lines of the module (read from the file e.g. __init__.py),
            used to check for doc:exclude comments

    Returns:
        A list of names extracted from the __all__ assignment, excluding any marked with doc:exclude.
    """
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
    """Check whether a ``doc:exclude`` marker appears on the source lines spanning *node*.

    Returns True if any line in the node's span contains "doc:exclude".

    Args:
        node: The AST node to check for doc:exclude comments.
        lines: The source lines (read from the file) of the module, used to
            check for doc:exclude comments.

    Returns:
        True if any line in the node's span contains "doc:exclude", False otherwise.
    """
    start = getattr(node, "lineno", None)
    if start is None:
        return False

    end = getattr(node, "end_lineno", start)

    # Use 1-based line numbers to index into lines (which is 0-based)
    return any("doc:exclude" in line for line in lines[start - 1 : end])


def _format_importfrom_module(node: ast.ImportFrom) -> str:
    """Reconstructs the module path from an ImportFrom node. 
    
    Preservers relative dots (e.g., ...foo.bar)

    Args:
        node: An AST node of type ast.ImportFrom, representing a "from x import y" statement.

    Returns:
        The module path as a string, including any relative dots.
    """
    return f'{"." * node.level}{node.module or ""}'