"""Build docs-ready dataclass records from inspected Python objects."""
from __future__ import annotations

import inspect
from typing import Any

from generator.parser import check_lazydoc, parse_docstring
from generator.inspection import (
    format_annotation,
    get_object_kind,
    is_documentable_method,
    safe_get_line_number,
    safe_get_signature,
    safe_get_source_file,
)
from generator.models import (
    ArgumentDoc,
    AttributeDoc,
    ClassDoc,
    DocumentableObject,
    ExportedName,
    FunctionDoc,
    MethodDoc,
    ParsedDocstring,
    PropertyDoc,
    ReturnDoc,
)


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

def build_pydantic_argument_docs(cls: type[Any]) -> list[ArgumentDoc]:
    """Build argument docs from Pydantic model field descriptions."""
    model_fields = getattr(cls, "model_fields", None)
    if not model_fields:
        return []

    try:
        signature = inspect.signature(cls)
    except (TypeError, ValueError):
        return []

    signature_names = set(signature.parameters)
    arguments: list[ArgumentDoc] = []

    for field_name, field in model_fields.items():
        public_name = _pydantic_public_field_name(field_name, field, signature_names)
        if public_name not in signature_names:
            continue

        description = getattr(field, "description", None) or ""
        arguments.append(
            ArgumentDoc(
                name=public_name,
                description=description,
                internal_use=check_lazydoc(description),
            )
        )

    return arguments

def _pydantic_public_field_name(
    field_name: str,
    field: Any,
    signature_names: set[str],
) -> str:
    """Return the constructor-facing name for a Pydantic model field.

    Pydantic fields can be exposed under an alias that differs from the Python
    attribute name. Prefer the first field alias that appears in the class
    signature so argument docs attach to the name users actually pass.
    """
    for candidate in (
        getattr(field, "validation_alias", None),
        getattr(field, "alias", None),
        getattr(field, "serialization_alias", None),
        field_name,
    ):
        if isinstance(candidate, str) and candidate in signature_names:
            return candidate

    return field_name

def collect_class_argument_docs(cls: type[Any], parsed_class: ParsedDocstring) -> list[ArgumentDoc]:
    """Collect class argument docs from the best available source."""
    pydantic_arguments = build_pydantic_argument_docs(cls)
    if pydantic_arguments:
        return pydantic_arguments

    init_docstring = inspect.getdoc(cls.__init__)
    parsed_init = parse_docstring(init_docstring)
    if parsed_init.arguments:
        return parsed_init.arguments

    return parsed_class.arguments


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


def collect_class_properties(cls: type[Any]) -> list[PropertyDoc]:
    """Collect public properties defined directly on a class."""
    properties: list[PropertyDoc] = []

    # This only documents properties defined directly on the class. Use
    # inspect.getmembers(cls) here if inherited properties should be included.
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

    return sorted(properties, key=lambda prop: prop.name.casefold())


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


def build_function_doc(item: DocumentableObject) -> FunctionDoc:
    """Build a docs-ready record for a public function-like object."""
    parsed = parse_docstring(item.docstring)
    returns = parsed.returns or build_default_return_docs(item.obj)

    return FunctionDoc(
        name=item.public_name,
        qualname=item.qualname or item.public_name,
        defining_module=item.defining_module,
        kind=item.kind,
        description=parsed.description,
        examples=parsed.examples,
        source_file=item.source_file or "",
        line_number=item.line_number,
        import_statement=item.import_statement,
        signature=item.signature,
        arguments=build_argument_docs(item.obj, parsed.arguments),
        returns=returns,
        raises=parsed.raises,
        internal_use=check_lazydoc(parsed.description),
    )


def build_class_doc(item: DocumentableObject) -> ClassDoc:
    """Build a docs-ready record for a public class."""

    # Find out how the class is documented: Pydantic model fields, __init__ docstring, or class docstring.
    parsed = parse_docstring(item.docstring)
    arguments = collect_class_argument_docs(item.obj, parsed)

    return ClassDoc(
        public_name=item.public_name,
        qualname=item.qualname or item.public_name,
        defining_module=item.defining_module,
        internal_use=check_lazydoc(parsed.description),
        kind=item.kind,
        description=parsed.description,
        examples=parsed.examples,
        source_file=item.source_file or "",
        line_number=item.line_number,
        import_statement=item.import_statement,
        signature=item.signature,
        arguments=build_argument_docs(item.obj, arguments),
        properties=collect_class_properties(item.obj),
        methods=collect_class_methods(item.obj),
        raises=parsed.raises,
    )


def build_attribute_doc(item: DocumentableObject) -> AttributeDoc:
    """Build a docs-ready record for a public attribute-like export."""
    parsed = parse_docstring(item.docstring)

    return AttributeDoc(
        name=item.public_name,
        description=parsed.description,
        kind=item.kind,
        source_file=item.source_file or "",
        line_number=item.line_number,
        import_statement=item.import_statement,
        internal_use=check_lazydoc(parsed.description),
    )
