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
    build_class_doc,
    build_exported_object_doc,
    build_function_doc,
    documentable_object_from_export,
)
from generator.inspection import resolve_exports
from generator.models import (
    ClassDoc,
    DocumentableObject,
    ExportedObjectDoc,
    ExportedName,
    FunctionDoc,
)


def document_export(
    export: ExportedName,
) -> tuple[dict[str, dict[str, Any]], list[ExportedName]]:
    """Build a JSON-serializable mapping of docs data for one parsed export."""
    resolved, missing = resolve_exports(
        export.config_namespace,
        [export],
    )

    docs_map: dict[str, dict[str, Any]] = {}

    for resolved_export, obj in resolved:
        item = documentable_object_from_export(resolved_export, obj)
        docs_map[item.public_name] = asdict(build_public_doc_entry(item))

    return docs_map, missing


def build_public_doc_entry(
    item: DocumentableObject,
) -> FunctionDoc | ClassDoc | ExportedObjectDoc:
    """Build a docs-ready dataclass for one public object."""
    if item.kind == "class":
        return build_class_doc(item)

    if item.kind in {"function", "builtin", "method"}:
        return build_function_doc(item)

    return build_exported_object_doc(item)



def main(args: argparse.Namespace) -> None:
    """Document every export listed in JSON files under ``args.input_dir``."""
    print("Documenting public exports from package namespaces...")

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    for input_path in Path(args.input_dir).glob("*.json"):
        exports_data = json.loads(input_path.read_text(encoding="utf-8"))

        # Extract the namespace and name of the export
        for entry in exports_data:

            # Convert the dict entry to an ExportedName dataclass for easier handling
            export = ExportedName(**entry)

            print(f"Documenting {export.config_namespace}.{export.public_name}...")

            docs_map, missing = document_export(export)

            # Define output path as {namespace}.{public_name}.json to ensure uniqueness
            output_path = output_dir / f"{export.config_namespace}.{export.public_name}.json"
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
