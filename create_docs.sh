#!/usr/bin/env bash
set -euo pipefail

REPO_URL="https://github.com/wandb/wandb.git"
REPO_DIR="../wandb"
DOCS_REPO_DIR="../docs"
RELEASE_TAG=""

# Python SDK-specific variables
JSON_NAMESPACES_DIR="./objects_found"
JSON_DOC_ENTRIES_DIR="./docs_json"
TMP_MDX_OUTPUT_DIR="./mdx_output"
MDX_OUTPUT_DIR="./python"


## CLI-specific variables
CLI_OUTPUT_JSON="source_info.json"
CLI_OUTPUT_DIR="cli"


usage() {
  cat <<EOF
Usage:
  $0 [--repo-dir PATH] [--tag TAG] [--json-namespaces-dir PATH] [--docs-repo PATH]

Examples:
  $0 --repo-dir ../wandb
  $0 --tag v0.17.0
  $0 --repo-dir /tmp/wandb --tag v0.17.0
  $0 --repo-dir ../wandb --json-namespaces-dir ./docs_json --docs-repo ../docs
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

REPO_ROOT="$(git -C "$REPO_DIR" rev-parse --show-toplevel)"

if [[ ! -d "$REPO_ROOT/wandb" ]]; then
  echo "Error: expected Python package directory not found: $REPO_ROOT/wandb" >&2
  exit 1
fi

# Set PYTHONPATH to include the repo root so that the scripts can import the package modules
export PYTHONPATH="$REPO_ROOT${PYTHONPATH:+:$PYTHONPATH}"

# Run the Python scripts to generate the docs
python get_python_objects.py --output-dir="$JSON_NAMESPACES_DIR"

python get_info.py --input-dir="$JSON_NAMESPACES_DIR" --output-dir="$JSON_DOC_ENTRIES_DIR"

python create_mdx_file.py --source-info "$JSON_DOC_ENTRIES_DIR/"  --output-dir="$TMP_MDX_OUTPUT_DIR"

python sort_files.py --source-directory "$TMP_MDX_OUTPUT_DIR" --output "$MDX_OUTPUT_DIR"

python rename_files.py --source-directory "$MDX_OUTPUT_DIR/"

echo "Copying generated docs to $DOCS_REPO_DIR/models/ref/python/..."

cp -r ./python/* $DOCS_REPO_DIR/models/ref/python/

echo "Generating CLI docs..."

# Create output directory if it doesn't exist
# If it does exist, clear it out to avoid stale files from previous runs
if [ -d "$CLI_OUTPUT_DIR" ]; then
    rm -rf "$CLI_OUTPUT_DIR"/*
else
    mkdir -p "$CLI_OUTPUT_DIR"
fi

# Generate source info JSON (for source links in docs)
python get_public_commands.py --output-json "$CLI_OUTPUT_JSON"

# Extract command names from JSON and create .mdx files
if [ -n "$RELEASE_TAG" ]; then
    python create_mdx_file.py --source-info "$CLI_OUTPUT_JSON" --output-dir "$CLI_OUTPUT_DIR" --release-tag "$RELEASE_TAG"
else
    python create_mdx_file.py --source-info "$CLI_OUTPUT_JSON" --output-dir "$CLI_OUTPUT_DIR"
fi

python sort_markdown.py --output-markdown "$CLI_OUTPUT_DIR" --source-info "$CLI_OUTPUT_JSON"