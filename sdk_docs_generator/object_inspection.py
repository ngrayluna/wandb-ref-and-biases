"""Import, inspect, and normalize Python objects for docs generation."""
from __future__ import annotations

import importlib
import inspect
from typing import Any

from sdk_docs_generator.docstrings_parser import check_lazydoc, parse_docstring
from sdk_docs_generator.models import (
    ArgumentDoc,
    DocumentableObject,
    ExportedName,
    MethodDoc,
    ParsedDocstring,
    PropertyDoc,
    ReturnDoc,
)


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


def documentable_object_from_export(
    export: ExportedName,
    obj: Any,
) -> DocumentableObject:
    """Build a documentable record from a resolved export."""
    return DocumentableObject(
        public_name=export.public_name,
        obj=obj,
        kind=get_object_kind(obj),
        defining_module=getattr(obj, "__module__", None),
        qualname=getattr(obj, "__qualname__", None),
        signature=safe_get_signature(obj),
        docstring=inspect.getdoc(obj),
        source_module=export.source_module,
        source_name=export.source_name,
        declared_in_all=export.declared_in_all,
        source_file=safe_get_source_file(obj),
        line_number=safe_get_line_number(obj),
        import_statement=build_import_statement(export),
    )


def collect_class_properties(cls: type[Any]) -> list[PropertyDoc]:
    """Collect public properties defined directly on a class."""
    properties: list[PropertyDoc] = []

    for name, member in cls.__dict__.items():
        if name.startswith("_"):
            continue

        if not isinstance(member, property):
            continue

        doc = inspect.getdoc(member.fget) or inspect.getdoc(member) or ""
        parsed = parse_docstring(doc)

        properties.append(
            PropertyDoc(
                name=name,
                description=parsed.description,
                returns=build_property_return_doc(member, parsed),
                internal_use=check_lazydoc(parsed.description),
            )
        )

    return properties


def collect_class_methods(cls: type[Any]) -> list[MethodDoc]:
    """Collect public methods from a class."""
    methods: list[MethodDoc] = []

    for name, member in inspect.getmembers(cls):
        if name.startswith("_"):
            continue

        if isinstance(member, property):
            continue

        if not is_documentable_method(member):
            continue

        parsed = parse_docstring(inspect.getdoc(member))
        arguments = build_argument_docs(member, parsed.arguments)
        returns = parsed.returns or build_default_return_docs(member)

        methods.append(
            MethodDoc(
                name=name,
                description=parsed.description,
                qualname=getattr(member, "__qualname__", name),
                signature=safe_get_signature(member),
                source_file=safe_get_source_file(member) or "",
                line_number=safe_get_line_number(member),
                arguments=arguments,
                returns=returns,
                examples=parsed.examples,
                raises=parsed.raises,
            )
        )

    return methods


def is_documentable_method(member: Any) -> bool:
    """Return True if a class member should be treated as a public method."""
    return (
        inspect.isfunction(member)
        or inspect.ismethod(member)
        or inspect.isbuiltin(member)
        or inspect.ismethoddescriptor(member)
    )


def build_argument_docs(
    obj: Any,
    parsed_args: list[ArgumentDoc],
) -> list[ArgumentDoc]:
    """Build argument docs from signature plus parsed docstring data."""
    parsed_by_name = {arg.name: arg for arg in parsed_args}

    try:
        signature = inspect.signature(obj)
    except (TypeError, ValueError):
        return parsed_args

    arguments: list[ArgumentDoc] = []

    for parameter in signature.parameters.values():
        if parameter.name in {"self", "cls"}:
            continue

        parsed = parsed_by_name.get(parameter.name)
        arguments.append(
            ArgumentDoc(
                name=parameter.name,
                description=parsed.description if parsed is not None else "",
                internal_use=parsed.internal_use if parsed is not None else False,
            )
        )

    return arguments


def build_default_return_docs(obj: Any) -> list[ReturnDoc]:
    """Build a fallback return doc from annotations when possible."""
    try:
        signature = inspect.signature(obj)
    except (TypeError, ValueError):
        return []

    annotation = signature.return_annotation
    if annotation is inspect.Signature.empty:
        return []

    return [
        ReturnDoc(
            type_name="return",
            description=format_annotation(annotation),
        )
    ]


def build_property_return_doc(
    prop: property,
    parsed: ParsedDocstring,
) -> str:
    """Build a property's return doc from docstring or getter annotation."""
    if parsed.returns:
        first_return = parsed.returns[0]
        return first_return.description or first_return.type_name

    if prop.fget is None:
        return ""

    fallback_returns = build_default_return_docs(prop.fget)
    if not fallback_returns:
        return ""

    first_return = fallback_returns[0]
    return first_return.description or first_return.type_name


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


def build_import_statement(export: ExportedName) -> str:
    """Reconstruct a readable import statement for a public export."""
    if export.source_module is None:
        return ""

    if export.source_name is None:
        if export.public_name == export.source_module.rsplit(".", 1)[-1]:
            return f"import {export.source_module}"
        return f"import {export.source_module} as {export.public_name}"

    if export.source_name == export.public_name:
        return f"from {export.source_module} import {export.source_name}"

    return (
        f"from {export.source_module} import "
        f"{export.source_name} as {export.public_name}"
    )


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
