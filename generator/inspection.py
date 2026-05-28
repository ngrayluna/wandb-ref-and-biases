"""Import, inspect, and normalize Python objects for docs generation."""
from __future__ import annotations

import importlib
import inspect
from typing import Any

from generator.models import ExportedName


def resolve_exports(
    package_name: str,
    exports: list[ExportedName],
) -> tuple[list[tuple[ExportedName, Any]], list[ExportedName]]:
    """Resolve parsed exports against the imported package namespace."""
    module = importlib.import_module(package_name)

    resolved: list[tuple[ExportedName, Any]] = []
    missing: list[ExportedName] = []

    for export in exports:
        if hasattr(module, export.public_name):
            resolved.append((export, getattr(module, export.public_name)))
        else:
            missing.append(export)

    return resolved, missing


def is_documentable_method(member: Any) -> bool:
    """Return True if a class member should be treated as a public method."""
    return (
        inspect.isfunction(member)
        or inspect.ismethod(member)
        or inspect.isbuiltin(member)
        or inspect.ismethoddescriptor(member)
    )


def safe_get_signature(obj: Any) -> str | None:
    """Return a string signature for an object, if available."""
    try:
        return str(inspect.signature(obj))
    except (TypeError, ValueError):
        return None


def safe_get_source_file(obj: Any) -> str | None:
    """Return a source file path for an object, if available."""
    try:
        source_file = inspect.getsourcefile(obj) or inspect.getfile(obj)
    except (TypeError, OSError):
        return None

    return source_file


def safe_get_line_number(obj: Any) -> int | None:
    """Return the line number for an object, if available."""
    try:
        _source_lines, line_number = inspect.getsourcelines(obj)
    except (TypeError, OSError):
        return None

    return line_number


def format_annotation(annotation: Any) -> str:
    """Return a readable string for a type annotation."""
    if isinstance(annotation, str):
        return annotation

    if hasattr(annotation, "__name__"):
        return str(annotation.__name__)

    return str(annotation)


def get_object_kind(obj: Any) -> str:
    """Return a stable, human-readable kind for an object."""
    if inspect.isclass(obj):
        return "class"
    if inspect.isfunction(obj):
        return "function"
    if inspect.ismethod(obj):
        return "method"
    if inspect.isbuiltin(obj):
        return "builtin"
    return "attribute"
