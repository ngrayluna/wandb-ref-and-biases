"""
Find and inspect public objects from the package namespace, parse their
docstrings, and build structured docsdata for use in MDX generation.

Usage
    python get_info.py
"""
from __future__ import annotations
import argparse
import json

import importlib
import inspect
import textwrap
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any


# ---------------------------------------------------------------------------
# Export discovery models
# ---------------------------------------------------------------------------

@dataclass(frozen=True, slots=True)
class ExportedName:
    """A public name exported by a package module."""

    public_name: str
    source_module: str | None = None
    source_name: str | None = None
    declared_in_all: bool = False

# ---------------------------------------------------------------------------
# Public docs models
# ---------------------------------------------------------------------------

@dataclass(frozen=True, slots=True)
class ArgumentDoc:
    """Documentation for a callable argument."""

    name: str
    description: str = ""
    internal_use: bool = False


@dataclass(frozen=True, slots=True)
class ReturnDoc:
    """Documentation for a return value."""

    type_name: str = ""
    description: str = ""


@dataclass(frozen=True, slots=True)
class PropertyDoc:
    """Documentation for a documented property or attribute."""

    name: str
    description: str = ""
    returns: str = ""
    internal_use: bool = False


@dataclass(frozen=True, slots=True)
class MethodDoc:
    """Documentation for a public method."""

    name: str
    description: str = ""
    qualname: str = ""
    signature: str | None = None
    source_file: str = ""
    line_number: int | None = None
    arguments: list[ArgumentDoc] = field(default_factory=list)
    returns: list[ReturnDoc] = field(default_factory=list)
    examples: str = ""


@dataclass(frozen=True, slots=True)
class FunctionDoc:
    """Documentation for a public function."""

    name: str
    qualname: str = ""
    defining_module: str | None = None
    kind: str = ""
    description: str = ""
    examples: str = ""
    source_file: str = ""
    line_number: int | None = None
    import_statement: str = ""
    signature: str | None = None
    arguments: list[ArgumentDoc] = field(default_factory=list)
    returns: list[ReturnDoc] = field(default_factory=list)
    internal_use: bool = False


@dataclass(frozen=True, slots=True)
class ClassDoc:
    """Documentation for a public class."""

    public_name: str
    qualname: str = ""
    defining_module: str | None = None
    internal_use: bool = False
    kind: str = ""
    description: str = ""
    examples: str = ""
    source_file: str = ""
    line_number: int | None = None
    import_statement: str = ""
    signature: str | None = None
    arguments: list[ArgumentDoc] = field(default_factory=list)
    properties: list[PropertyDoc] = field(default_factory=list)
    methods: list[MethodDoc] = field(default_factory=list)
    



@dataclass(frozen=True, slots=True)
class AttributeDoc:
    """Documentation for a public attribute-like export."""

    name: str
    kind: str = ""
    description: str = ""
    source_file: str = ""
    line_number: int | None = None
    import_statement: str = ""



@dataclass(frozen=True, slots=True)
class DocumentableObject:
    """A normalized, inspect-derived representation of a public object."""

    public_name: str
    obj: Any
    kind: str
    defining_module: str | None
    qualname: str | None
    signature: str | None
    docstring: str | None
    source_module: str | None
    source_name: str | None
    declared_in_all: bool
    source_file: str | None
    line_number: int | None
    import_statement: str

    @classmethod
    def from_export(cls, export: ExportedName, obj: Any) -> "DocumentableObject":
        """Build a documentable record from a resolved export."""
        source_file = _safe_get_source_file(obj)
        line_number = _safe_get_line_number(obj)

        return cls(
            public_name=export.public_name,
            obj=obj,
            kind=_get_object_kind(obj),
            defining_module=getattr(obj, "__module__", None),
            qualname=getattr(obj, "__qualname__", None),
            signature=_safe_get_signature(obj),
            docstring=inspect.getdoc(obj),
            source_module=export.source_module,
            source_name=export.source_name,
            declared_in_all=export.declared_in_all,
            source_file=source_file,
            line_number=line_number,
            import_statement=_build_import_statement(export),
        )


#######

def resolve_exports(
    package_name: str,
    exports: list[ExportedName],
) -> tuple[list[tuple[ExportedName, Any]], list[ExportedName]]:
    """Resolve parsed exports against the imported package namespace.
    
    In other words, attempt to find the actual Python objects corresponding
    to the exported names, so we can inspect them for docs generation.

    Args:
    - package_name: The name of the package to import for resolution.
    - exports: Records to resolve; only ``public_name`` is used for
          lookup, other fields pass through unchanged.

    Returns:
        ``(resolved, missing)``:
        - ``resolved``: ``(ExportedName, object)`` pairs for names found.
        - ``missing``: ``ExportedName`` records not present on the package.

    Example:
        >>> resolve_exports("wandb", [ExportedName(public_name="Api")])
        ([(ExportedName(public_name='Api', ...), <class '...Api'>)], [])    
    """
    module = importlib.import_module(package_name)

    resolved: list[tuple[ExportedName, Any]] = []
    missing: list[ExportedName] = []

    for export in exports:
        if hasattr(module, export.public_name):
            resolved.append(
                (export, getattr(module, export.public_name))
            )
        else:
            missing.append(export)

    return resolved, missing


# ---------------------------------------------------------------------------
# Public docs generation
# ---------------------------------------------------------------------------


def document_exports(
    object_name: str,
    package_name: str,
) -> tuple[dict[str, dict[str, Any]], list[ExportedName]]:
    """Build a JSON-serializable mapping of public docs data.

    Args:
        object_name: Public name as it appears on the package namespace                                                                                                                  
            (e.g. ``"Api"``, not ``"wandb.apis.public.api.Api"``).
        package_name: Dotted import path of the package exporting it.
    
    Returns:
        ``(docs_map, missing)``:
        - ``docs_map``: ``{public_name: doc_dict}``, empty if unresolved.
        - ``missing``: unresolved ``ExportedName`` records, empty if successfully resolved.

    Example:
        >>> docs_map, _ = document_exports("Api", "wandb")
        >>> docs_map["Api"]["kind"]                                                                                                                                                          
        'class'    
    """
    resolved, missing = resolve_exports(package_name, [ExportedName(public_name=object_name)])
    documentable_objects = [
        DocumentableObject.from_export(export, obj)
        for export, obj in resolved
    ]


    docs_map: dict[str, dict[str, Any]] = {}
    for item in documentable_objects:
        docs_map[item.public_name] = asdict(build_public_doc_entry(item))

    return docs_map, missing


def build_public_doc_entry(
    item: DocumentableObject,
) -> FunctionDoc | ClassDoc  | AttributeDoc:
    """Build a docs-ready dataclass for one public object."""
    if item.kind == "class":
        return _build_class_doc(item)

    if item.kind in {"function", "builtin", "method"}:
        return _build_function_doc(item)

    return _build_attribute_doc(item)


def _build_function_doc(item: DocumentableObject) -> FunctionDoc:
    """Build a docs-ready record for a public function-like object."""
    parsed = _parse_docstring(item.docstring)

    arguments = _build_argument_docs(
        obj=item.obj,
        parsed_args=parsed.arguments,
    )

    returns = parsed.returns or _build_default_return_docs(item.obj)

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
        arguments=arguments,
        returns=returns,
        internal_use=_check_lazydoc(parsed.description)
    )


def _build_class_doc(item: DocumentableObject) -> ClassDoc:
    """Build a docs-ready record for a public class."""
    parsed = _parse_docstring(item.docstring)
    properties = _collect_class_properties(item.obj)
    methods = _collect_class_methods(item.obj)

    return ClassDoc(
        public_name=item.public_name,
        qualname=item.qualname or item.public_name,
        defining_module=item.defining_module,
        internal_use=_check_lazydoc(parsed.description),
        kind=item.kind,
        description=parsed.description,
        examples=parsed.examples,
        source_file=item.source_file or "",
        line_number=item.line_number,
        import_statement=item.import_statement,
        signature=item.signature,
        arguments=_build_argument_docs(
            obj=item.obj,
            parsed_args=parsed.arguments,
        ),
        properties=properties,
        methods=methods,
    )


def _build_attribute_doc(item: DocumentableObject) -> AttributeDoc:
    """Build a docs-ready record for a public attribute-like export."""
    parsed = _parse_docstring(item.docstring)

    return AttributeDoc(
        name=item.public_name,
        description=parsed.description,
        kind=item.kind,
        source_file=item.source_file or "",
        line_number=item.line_number,
        import_statement=item.import_statement,
        internal_use=_check_lazydoc(parsed.description)
    )


# ---------------------------------------------------------------------------
# Class member collection
# ---------------------------------------------------------------------------

## Note: inspect.getmembers(cls) may include inherited members we don't want.
def _collect_class_properties(cls: type[Any]) -> list[PropertyDoc]:
    """Collect public properties defined directly on a class."""
    properties: list[PropertyDoc] = []

    for name, member in cls.__dict__.items():
        if name.startswith("_"):
            continue

        if not isinstance(member, property):
            continue

        doc = inspect.getdoc(member.fget) or inspect.getdoc(member) or ""
        parsed = _parse_docstring(doc)

        properties.append(
            PropertyDoc(
                name=name,
                description=parsed.description,
                returns=_build_property_return_doc(member, parsed),
                internal_use=_check_lazydoc(parsed.description)
            )
        )

    return properties

# Note: inspect.getmembers(cls) may include inherited members we don't want.
# Note[2]: It might give already-bound/transformed objects, not the raw descriptor from the class dictionary.
def _collect_class_methods(cls: type[Any]) -> list[MethodDoc]:
    """Collect public methods from a class."""
    methods: list[MethodDoc] = []

    # Future: for name, member in cls.__dict__.items():
    for name, member in inspect.getmembers(cls):
        if name.startswith("_"):
            continue

        if isinstance(member, property):
            continue

        if not _is_documentable_method(member):
            continue

        doc = inspect.getdoc(member)
        parsed = _parse_docstring(doc)
        arguments = _build_argument_docs(member, parsed.arguments)
        returns = parsed.returns or _build_default_return_docs(member)

        methods.append(
            MethodDoc(
                name=name,
                description=parsed.description,
                qualname=getattr(member, "__qualname__", name),
                signature=_safe_get_signature(member),
                source_file=_safe_get_source_file(member) or "",
                line_number=_safe_get_line_number(member),
                arguments=arguments,
                returns=returns,
                examples=parsed.examples,
            )
        )

    return methods


def _is_documentable_method(member: Any) -> bool:
    """Return True if a class member should be treated as a public method."""
    return (
        inspect.isfunction(member)
        or inspect.ismethod(member)
        or inspect.isbuiltin(member)
        or inspect.ismethoddescriptor(member)
    )


# ---------------------------------------------------------------------------
# Docstring parsing
# ---------------------------------------------------------------------------

@dataclass(frozen=True, slots=True)
class ParsedDocstring:
    """A light-weight parsed docstring."""

    description: str = ""
    examples: str = ""
    arguments: list[ArgumentDoc] = field(default_factory=list)
    returns: list[ReturnDoc] = field(default_factory=list)


def _parse_docstring(docstring: str | None) -> ParsedDocstring:
    """Parse a docstring into a small set of docs-oriented sections.

    Supported headings:
    - Args:
    - Arguments:
    - Parameters:
    - Returns:
    - Examples:
    """
    if not docstring:
        return ParsedDocstring()

    cleaned = inspect.cleandoc(docstring)
    lines = cleaned.splitlines()

    description_lines: list[str] = []
    args_lines: list[str] = []
    returns_lines: list[str] = []
    examples_lines: list[str] = []

    current_section = "description"

    for line in lines:
        stripped = line.strip()

        if stripped in {"Args:", "Arguments:", "Parameters:"}:
            current_section = "arguments"
            continue

        if stripped == "Returns:":
            current_section = "returns"
            continue

        if stripped == "Examples:":
            current_section = "examples"
            continue

        if current_section == "description":
            description_lines.append(line)
        elif current_section == "arguments":
            args_lines.append(line)
        elif current_section == "returns":
            returns_lines.append(line)
        elif current_section == "examples":
            examples_lines.append(line)

    return ParsedDocstring(
        description=_normalize_block(description_lines),
        examples=_normalize_block(examples_lines),
        arguments=_parse_argument_block(args_lines),
        returns=_parse_return_block(returns_lines),
    )


def _parse_argument_block(lines: list[str]) -> list[ArgumentDoc]:
    """Parse an Args/Parameters-style block.

    Expected style:
        name: Description
        name (type): Description
            Continued description.
    """
    arguments: list[ArgumentDoc] = []
    current_name: str | None = None
    current_description: list[str] = []

    for raw_line in lines:
        line = raw_line.rstrip()
        stripped = line.strip()

        if not stripped:
            continue

        if _looks_like_doc_field(stripped):
            if current_name is not None:
                arguments.append(
                    ArgumentDoc(
                        name=current_name,
                        description=_join_description_lines(current_description),
                        internal_use=_check_lazydoc(_join_description_lines(current_description))
                    )
                )

            field_name, description = _split_doc_field(stripped)
            current_name = field_name
            current_description = [description] if description else []
            continue

        if current_name is not None:
            current_description.append(stripped)

    if current_name is not None:
        arguments.append(
            ArgumentDoc(
                name=current_name,
                description=_join_description_lines(current_description),
                internal_use=_check_lazydoc(_join_description_lines(current_description))
            )
        )

    return arguments


def _parse_return_block(lines: list[str]) -> list[ReturnDoc]:
    """Parse a Returns-style block.

    Expected styles:
        Description
        name: Description
        type: Description
            Continued description.
    """
    returns: list[ReturnDoc] = []
    current_name: str | None = None
    current_description: list[str] = []

    for raw_line in lines:
        line = raw_line.rstrip()
        stripped = line.strip()

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


def _looks_like_doc_field(line: str) -> bool:
    """Return True if a line looks like a simple doc field entry."""
    if ":" not in line:
        return False

    left, _right = line.split(":", 1)
    return bool(left.strip())


def _split_doc_field(line: str) -> tuple[str, str]:
    """Split a simple ``name: description`` doc line."""
    left, right = line.split(":", 1)
    name = left.strip()
    description = right.strip()

    if "(" in name:
        name = name.split("(", 1)[0].strip()

    return name, description


def _normalize_block(lines: list[str]) -> str:
    """Normalize a free-text docstring block."""
    text = "\n".join(lines).strip()
    return textwrap.dedent(text).strip()


def _join_description_lines(lines: list[str]) -> str:
    """Join multiple description lines into readable prose."""
    return " ".join(part.strip() for part in lines if part.strip()).strip()


# ---------------------------------------------------------------------------
# Signature and source helpers
# ---------------------------------------------------------------------------


def _build_argument_docs(
    obj: Any,
    parsed_args: list[ArgumentDoc],
) -> list[ArgumentDoc]:
    """Build argument docs from signature plus parsed docstring data.

    Preference:
    - preserve argument order from the signature
    - fill descriptions from parsed docstring data when available
    """
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
        description = parsed.description if parsed is not None else ""

        arguments.append(
            ArgumentDoc(
                name=parameter.name,
                description=description,
            )
        )

    return arguments


def _build_default_return_docs(obj: Any) -> list[ReturnDoc]:
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
            description=_format_annotation(annotation),
        )
    ]

def _build_property_return_doc(
    prop: property,
    parsed: ParsedDocstring,
) -> str:
    """Build a property's return doc from docstring or getter annotation."""
    if parsed.returns:
        first_return = parsed.returns[0]
        return first_return.description or first_return.type_name

    if prop.fget is None:
        return ""

    fallback_returns = _build_default_return_docs(prop.fget)
    if not fallback_returns:
        return ""

    first_return = fallback_returns[0]
    return first_return.description or first_return.type_name

def _safe_get_signature(obj: Any) -> str | None:
    """Return a string signature for an object, if available."""
    try:
        return str(inspect.signature(obj))
    except (TypeError, ValueError):
        return None


def _safe_get_source_file(obj: Any) -> str | None:
    """Return a source file path for an object, if available."""
    try:
        source_file = inspect.getsourcefile(obj) or inspect.getfile(obj)
    except (TypeError, OSError):
        return None

    return source_file


def _safe_get_line_number(obj: Any) -> int | None:
    """Return the line number for an object, if available."""
    try:
        _source_lines, line_number = inspect.getsourcelines(obj)
    except (TypeError, OSError):
        return None

    return line_number


def _build_import_statement(export: ExportedName) -> str:
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


def _format_annotation(annotation: Any) -> str:
    """Return a readable string for a type annotation."""
    if isinstance(annotation, str):
        return annotation

    if hasattr(annotation, "__name__"):
        return str(annotation.__name__)

    return str(annotation)


def _check_lazydoc(description: str) -> bool:
    """Return True if the description contains a lazydoc directive."""
    return "lazydoc" in description

def _get_object_kind(obj: Any) -> str:
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


# ---------------------------------------------------------------------------
# Example usage
# ---------------------------------------------------------------------------


def main(args):
    filename = args.input_file

    # Read in JSON file. See sdk_exports.json for expected format.
    with open(filename, "r", encoding="utf-8") as f:
        exports_data = json.load(f)


    # Iterate over the exports and document them, writing out a JSON file for each. 
    for entry in exports_data:
        
        public_export = entry["public_name"]
        namespace = entry["config_namespace"]

        print(f"\nDocumenting {namespace}.{public_export}...")

        docs_map, missing = document_exports(
            object_name=public_export,
            package_name=namespace,
        )

        output_path = Path(args.output_dir) / f"{namespace}.{public_export}.json"
        output_path.write_text(
            json.dumps(docs_map, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )

        if missing:
            print("\nMissing exports:")
            for export in missing:
                print(f"  - {export.public_name}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Get object information.")
    parser.add_argument("--output-dir", required=False, default="./docs_json", help="Directory to write output JSON files.")
    parser.add_argument("--input-file", help="Path to input JSON file with exports to document.")
    main(parser.parse_args())
