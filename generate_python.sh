#!/bin/bash
set -euo pipefail

# Shared repo setup (REPO_URL, REPO_DIR, prepare_repo).
source "$(dirname "$0")/lib/common.sh"

DOCS_REPO_DIR="../docs"
RELEASE_TAG=""

# Python SDK-specific variables
JSON_NAMESPACES_DIR="./artifacts/python_objects_found"
JSON_DOC_ENTRIES_DIR="./artifacts/python_docs_json"
TMP_MDX_OUTPUT_DIR="./artifacts/python_mdx_output"
MDX_OUTPUT_DIR="./generated/python"

clear_directory() {
  local dir="$1"

  if [[ -z "$dir" || "$dir" == "/" ]]; then
    echo "Refusing to clear unsafe directory: '$dir'" >&2
    exit 1
  fi

  mkdir -p "$dir"
  find "$dir" -mindepth 1 -maxdepth 1 -exec rm -rf {} +
}

replace_directory() {
  local dir="$1"

  if [[ -z "$dir" || "$dir" == "/" ]]; then
    echo "Refusing to replace unsafe directory: '$dir'" >&2
    exit 1
  fi

  rm -rf "$dir"
  mkdir -p "$dir"
}

usage() {
  cat <<EOF
Usage:
  $0 [--repo-dir PATH] [--tag TAG] [--json-namespaces-dir PATH] [--docs-repo PATH]

Examples:
  $0 --repo-dir ../wandb
  $0 --tag v0.17.0
  $0 --repo-dir /tmp/wandb --tag v0.17.0
  $0 --repo-dir ../wandb --json-namespaces-dir ./python_objects_found --docs-repo ../docs
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --repo-dir)
      REPO_DIR="${2:?Missing value for --repo-dir}"
      shift 2
      ;;
    --tag)
      RELEASE_TAG="${2:?Missing value for --tag}"
      shift 2
      ;;
    --json-namespaces-dir)
      JSON_NAMESPACES_DIR="${2:?Missing value for --json-namespaces-dir}"
      shift 2
      ;;
    --docs-repo)
      DOCS_REPO_DIR="${2:?Missing value for --docs-repo}"
      shift 2
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      echo "Error: unknown argument: $1" >&2
      usage >&2
      exit 1
      ;;
  esac
done

clear_directory "$JSON_NAMESPACES_DIR"
clear_directory "$JSON_DOC_ENTRIES_DIR"
clear_directory "$TMP_MDX_OUTPUT_DIR"
clear_directory "$MDX_OUTPUT_DIR"

# Clone/checkout the wandb repo and export PYTHONPATH (sets REPO_ROOT).
prepare_repo "$RELEASE_TAG" "$REPO_DIR"

# Run the Python scripts to generate the docs
python ./python_ref/get_python_objects.py --output-dir="$JSON_NAMESPACES_DIR"

python ./python_ref/get_info.py --input-dir="$JSON_NAMESPACES_DIR" --output-dir="$JSON_DOC_ENTRIES_DIR"

python ./python_ref/create_mdx_file.py --source-info "$JSON_DOC_ENTRIES_DIR/"  --output-dir="$TMP_MDX_OUTPUT_DIR"

python ./python_ref/sort_files.py --source-directory "$TMP_MDX_OUTPUT_DIR" --output "$MDX_OUTPUT_DIR"

python ./python_ref/rename_files.py --source-directory "$MDX_OUTPUT_DIR/"

# Copy static mdx files to the generated directory
cp -R python_ref/static_mdx/. "$MDX_OUTPUT_DIR"/
find "$MDX_OUTPUT_DIR" -name ".DS_Store" -delete

echo "Copying generated docs to $DOCS_REPO_DIR/models/ref/python/..."

DEST="$DOCS_REPO_DIR/models/ref/python"
replace_directory "$DEST"
cp -R "$MDX_OUTPUT_DIR"/. "$DEST"/
