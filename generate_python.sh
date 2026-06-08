#!/usr/bin/env bash
set -euo pipefail

REPO_URL="https://github.com/wandb/wandb.git"
REPO_DIR="../wandb"
DOCS_REPO_DIR="../docs"
RELEASE_TAG=""

# Python SDK-specific variables
JSON_NAMESPACES_DIR="./artifacts/python_objects_found"
JSON_DOC_ENTRIES_DIR="./artifacts/python_docs_json"
TMP_MDX_OUTPUT_DIR="./artifacts/python_mdx_output"
MDX_OUTPUT_DIR="./generated/python"


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

# Check directories exist, if they do remove contents, if they don't create them
if [ -d "$JSON_NAMESPACES_DIR" ]; then
    rm -rf "$JSON_NAMESPACES_DIR"/*
else
    mkdir -p "$JSON_NAMESPACES_DIR"
fi

if [ -d "$JSON_DOC_ENTRIES_DIR" ]; then
    rm -rf "$JSON_DOC_ENTRIES_DIR"/*
else
    mkdir -p "$JSON_DOC_ENTRIES_DIR"
fi

if [ -d "$TMP_MDX_OUTPUT_DIR" ]; then
    rm -rf "$TMP_MDX_OUTPUT_DIR"/*
else
    mkdir -p "$TMP_MDX_OUTPUT_DIR"
fi

if [ -d "$MDX_OUTPUT_DIR" ]; then
    rm -rf "$MDX_OUTPUT_DIR"/*
else
    mkdir -p "$MDX_OUTPUT_DIR"
fi



if [[ -n "$RELEASE_TAG" ]]; then
  if [[ -d "$REPO_DIR/.git" ]]; then
    echo "Fetching tags in $REPO_DIR..."
    git -C "$REPO_DIR" fetch --tags origin
  else
    echo "Cloning $REPO_URL into $REPO_DIR..."
    mkdir -p "$(dirname "$REPO_DIR")"
    git clone "$REPO_URL" "$REPO_DIR"
  fi

  echo "Checking out $RELEASE_TAG..."
  git -C "$REPO_DIR" checkout --force "$RELEASE_TAG"
else
  echo "Using local repo at $REPO_DIR..."

  if [[ ! -d "$REPO_DIR/.git" ]]; then
    echo "Error: $REPO_DIR is not a Git repository." >&2
    echo "Pass --repo-dir PATH for local testing, or --tag TAG to clone/check out a release." >&2
    exit 1
  fi
fi

# Get the absolute path to the repo root
REPO_ROOT="$(git -C "$REPO_DIR" rev-parse --show-toplevel)"

if [[ ! -d "$REPO_ROOT/wandb" ]]; then
  echo "Error: expected Python package directory not found: $REPO_ROOT/wandb" >&2
  exit 1
fi

# Set PYTHONPATH to include the repo root so that the scripts can import the package modules
export PYTHONPATH="$REPO_ROOT${PYTHONPATH:+:$PYTHONPATH}"

# Run the Python scripts to generate the docs
python ./python_ref/get_python_objects.py --output-dir="$JSON_NAMESPACES_DIR"

python ./python_ref/get_info.py --input-dir="$JSON_NAMESPACES_DIR" --output-dir="$JSON_DOC_ENTRIES_DIR"

python ./python_ref/create_mdx_file.py --source-info "$JSON_DOC_ENTRIES_DIR/"  --output-dir="$TMP_MDX_OUTPUT_DIR"

python ./python_ref/sort_files.py --source-directory "$TMP_MDX_OUTPUT_DIR" --output "$MDX_OUTPUT_DIR"

python ./python_ref/rename_files.py --source-directory "$MDX_OUTPUT_DIR/"

# echo "Copying generated docs to $DOCS_REPO_DIR/models/ref/python/..."

# cp -r $MDX_OUTPUT_DIR/* $DOCS_REPO_DIR/models/ref/python/