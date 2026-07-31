# Main directory for the Python SDK generator. Contains scripts to parse Python source files, extract public API information, and generate MDX documentation files.
"""
Sorts generated MDX files into categories based on their metadata.

Usage:
    python sort_files.py --source-directory mdx_output/ --output ./python
"""
import argparse
import os
import glob
import frontmatter


def create_directories(root_directory: str) -> None:
    """Create category directories under the root directory."""
    categories = ["data-types", "experiments", "functions","automations", "custom-charts", "public-api"]
    for category in categories:
        os.makedirs(os.path.join(root_directory, category), exist_ok=True)

def sort_logic(kind: str, namespace: str) -> str:
    """Determine category for an MDX file based on its metadata.
    
    TODO: Sorting logic could be improved. E.g. functions sorting looks for sdk
    global functions. This may not cover all cases and could be refined further.
    """

    if kind == "function" and (
    namespace.startswith("wandb.sdk.") or namespace == "wandb.wandb_agent"):
        return "functions"
    if "wandb.sdk.data_types" in namespace:
        return "data-types"
    if kind == "class" and "wandb.sdk" in namespace:
        return "experiments"
    if "wandb.automations" in namespace:
        return "automations"
    if "wandb.custom_charts" in namespace:
        return "custom-charts"
    if "wandb.apis.public" in namespace:
        return "public-api"
    if "wandb.plot" in namespace:
        return "custom-charts"


def build_destination_path(output: str, category: str, filename: str, metadata: dict) -> str:
    """Build the output path for a generated MDX file."""
    basename = os.path.basename(filename)

    if metadata.get("page_kind") in {"class-properties", "class-methods"}:
        parent_slug = metadata.get("parent_slug", "")
        if parent_slug:
            return os.path.join(output, category, parent_slug, basename)

    return os.path.join(output, category, basename)



def main(args):

    print("Sorting MDX files into categories...")

    root_directory = args.output
    # Step 1. Created directory for each category (e.g. data_types, experiments, automations, public_api)
    create_directories(root_directory)

    # Step 2. Read each mdx file, extract metadata, and move to appropriate directory
    for filename in glob.glob(os.path.join(args.source_directory, '*.mdx')):

        frontmatter_data = frontmatter.load(filename)        
        metadata = frontmatter_data.metadata
        kind = metadata.get("kind", "")
        namespace = metadata.get("namespace", "")

        category = sort_logic(kind=kind, namespace=namespace)

        # Create destination path and move file
        if category is None:
            continue
        
        destination_path = build_destination_path(args.output, category, filename, metadata)
        os.makedirs(os.path.dirname(destination_path), exist_ok=True)
        os.rename(filename, destination_path)
        destination_dir = os.path.relpath(os.path.dirname(destination_path), args.output)
        print(f"Moved {os.path.basename(filename)} to {destination_dir}/")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Sort MDX files into categories based on metadata.")
    parser.add_argument("--output", required=True, help="Root directory to store categorized MDX files.")
    parser.add_argument("--source-directory", required=True, help="Directory containing MDX files to sort.")
    args = parser.parse_args()
    main(args)
