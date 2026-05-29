"""Import, inspect, and normalize Python objects for docs generation."""
from __future__ import annotations

import importlib
import inspect
import re
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


# Stabilize parameter defaults whose repr embeds a volatile memory address. — and drop the trailing —.
_MEMORY_ADDRESS_RE = re.compile(r"\s+at\s+0x[0-9a-fA-F]+")
_IDENTIFIER_RE = re.compile(r"^[A-Za-z_]\w*$")


class _StableRepr:
    def __init__(self, text: str) -> None:
        self.text = text

    def __repr__(self) -> str:
        return self.text


def _annotation_identifier(annotation: Any) -> str | None:
    """Return a stable identifier for an annotation, if possible."""
    if isinstance(annotation, str) and _IDENTIFIER_RE.match(annotation):
        return annotation
    return None

def _stable_default(parameter: inspect.Parameter) -> Any:
    """Return a stable representation for a parameter default value."""
    default = parameter.default

    if default is inspect.Parameter.empty:
        return default

    # Handles sentinels like: anonymous: 'DoNotSet' = <object object at 0x...>
    if type(default) is object:
        return _StableRepr(_annotation_identifier(parameter.annotation) or "object()")

    # Handles defaults like: <function exclude_wandb_fn at 0x...>
    if inspect.isroutine(default):
        name = getattr(default, "__qualname__", None) or getattr(default, "__name__", None)
        if name:
            return _StableRepr(name)

    # Backstop for arbitrary reprs that still contain memory addresses.
    rendered = repr(default)
    if _MEMORY_ADDRESS_RE.search(rendered):
        return _StableRepr(_MEMORY_ADDRESS_RE.sub("", rendered))

    return default


def safe_get_signature(obj: Any) -> str | None:
    """Return a deterministic string signature for an object, if available."""
    try:
        signature = inspect.signature(obj)
    except (TypeError, ValueError):
        return None

    parameters = [
        parameter.replace(default=_stable_default(parameter))
        for parameter in signature.parameters.values()
    ]

    rendered = str(signature.replace(parameters=parameters))
    return _MEMORY_ADDRESS_RE.sub("", rendered)


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
