"""
Find and inspect public objects from package namespaces, parse their
docstrings, and build structured docs data for use in MDX generation.

Usage:
    python get_info.py --input-dir=./objects_found --output-dir=./docs_json

Output:
    A JSON file containing the structured docs data for each public object.
"""
from __future__ import annotations

import argparse
import json
from dataclasses import asdict
from pathlib import Path
from typing import Any

from sdk_docs_generator.docstrings_parser import check_lazydoc, parse_docstring
from sdk_docs_generator.models import (
    AttributeDoc,
    ClassDoc,
    DocumentableObject,
    ExportedName,
    FunctionDoc,
)
from sdk_docs_generator.object_inspection import (
    build_argument_docs,
    build_default_return_docs,
    collect_class_methods,
    collect_class_properties,
    documentable_object_from_export,
    resolve_exports,
)


def document_exports(
    object_name: str,
    package_name: str,
) -> tuple[dict[str, dict[str, Any]], list[ExportedName]]:
    """Build a JSON-serializable mapping of public docs data."""
    resolved, missing = resolve_exports(
        package_name,
        [ExportedName(public_name=object_name)],
    )
    documentable_objects = [
        documentable_object_from_export(export, obj)
        for export, obj in resolved
    ]

    docs_map: dict[str, dict[str, Any]] = {}

    for item in documentable_objects:
        docs_map[item.public_name] = asdict(build_public_doc_entry(item))

    return docs_map, missing


def build_public_doc_entry(
    item: DocumentableObject,
) -> FunctionDoc | ClassDoc | AttributeDoc:
    """Build a docs-ready dataclass for one public object."""
    if item.kind == "class":
        return _build_class_doc(item)

    if item.kind in {"function", "builtin", "method"}:
        return _build_function_doc(item)

    return _build_attribute_doc(item)


def _build_function_doc(item: DocumentableObject) -> FunctionDoc:
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


def _build_class_doc(item: DocumentableObject) -> ClassDoc:
    """Build a docs-ready record for a public class."""
    parsed = parse_docstring(item.docstring)

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
        arguments=build_argument_docs(item.obj, parsed.arguments),
        properties=collect_class_properties(item.obj),
        methods=collect_class_methods(item.obj),
        raises=parsed.raises,
    )


def _build_attribute_doc(item: DocumentableObject) -> AttributeDoc:
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


def main(args: argparse.Namespace) -> None:
    """Document every export listed in JSON files under ``args.input_dir``."""
    print("Documenting public exports from package namespaces...")

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    for input_path in Path(args.input_dir).glob("*.json"):
        exports_data = json.loads(input_path.read_text(encoding="utf-8"))

        # Extract the namespace and name of the export
        for entry in exports_data:
            public_export = entry["public_name"]
            namespace = entry["config_namespace"]

            print(f"Documenting {namespace}.{public_export}...")

            docs_map, missing = document_exports(
                object_name=public_export,
                package_name=namespace,
            )

            output_path = output_dir / f"{namespace}.{public_export}.json"
            output_path.write_text(
                json.dumps(docs_map, indent=2, ensure_ascii=False) + "\n",
                encoding="utf-8",
            )

            if missing:
                print("\nMissing exports:")
                for export in missing:
                    print(f"  - {export.public_name}")

    print("Documentation extraction complete.\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Get object information.")
    parser.add_argument(
        "--output-dir",
        required=False,
        default="./docs_json",
        help="Directory to write output JSON files.",
    )
    parser.add_argument(
        "--input-dir",
        required=True,
        help="Directory containing export JSON files to document.",
    )
    main(parser.parse_args())
