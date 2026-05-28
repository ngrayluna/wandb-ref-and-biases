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

from generator.builder import (
    build_attribute_doc,
    build_class_doc,
    build_function_doc,
    documentable_object_from_export,
)
from generator.inspection import resolve_exports
from generator.models import (
    AttributeDoc,
    ClassDoc,
    DocumentableObject,
    ExportedName,
    FunctionDoc,
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
        return build_class_doc(item)

    if item.kind in {"function", "builtin", "method"}:
        return build_function_doc(item)

    return build_attribute_doc(item)



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
