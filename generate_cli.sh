#!/bin/bash
# Generate markdown reference documentation for wandb CLI commands.
#
# If no release_tag is provided,use ../wandb/ directory as-is (useful
# for local testing). Note that in this case, GitHub source links
# point to 'main' branch.

set -e  # Exit on error

# Shared repo setup (REPO_URL, REPO_DIR, prepare_repo).
source "$(dirname "$0")/lib/common.sh"

DOCS_REPO_DIR="../docs"
RELEASE_TAG="${1:-}"

OUTPUT_JSON="./artifacts/cli_source_info.json"
TMP_OUTPUT_DIR="./artifacts/cli_mdx_output"
MDX_OUTPUT_DIR="${2:-./generated/cli}"

usage() {
  cat <<EOF
Usage: 
    $0 [release_tag] [output_dir]
Example:
    $0 v0.18.3
    $0 v0.18.3 docs/models/ref/cli
EOF
}

# Clone/checkout the wandb repo and export PYTHONPATH (sets REPO_ROOT).
prepare_repo "$RELEASE_TAG" "$REPO_DIR"

# Create output directory if it doesn't exist
# If it does exist, clear it out to avoid stale files from previous runs
if [ -d "$TMP_OUTPUT_DIR" ]; then
    rm -rf "$TMP_OUTPUT_DIR"/*
else
    mkdir -p "$TMP_OUTPUT_DIR"
fi

if [ -d "$MDX_OUTPUT_DIR" ]; then
    rm -rf "$MDX_OUTPUT_DIR"/*
else        
    mkdir -p "$MDX_OUTPUT_DIR" 
fi

# Generate source info JSON (for source links in docs)
python ./cli_ref/get_public_commands.py --output-json "$OUTPUT_JSON"

# Extract command names from JSON and create .mdx files
if [ -n "$RELEASE_TAG" ]; then
    python ./cli_ref/create_mdx_file.py --source-info "$OUTPUT_JSON" --output-dir "$TMP_OUTPUT_DIR" --release-tag "$RELEASE_TAG"
else
    python ./cli_ref/create_mdx_file.py --source-info "$OUTPUT_JSON" --output-dir "$TMP_OUTPUT_DIR"
fi

python ./cli_ref/sort_markdown.py --output-markdown "$TMP_OUTPUT_DIR" --source-info "$OUTPUT_JSON"


# Store in temporary directory first, then copy to final output dir to avoid partial output in case of errors
cp -r "$TMP_OUTPUT_DIR"/* "$MDX_OUTPUT_DIR/"

# Copy generated .mdx files to the docs repo
echo "Copying .mdx files to $DOCS_REPO_DIR/models/ref/cli/"
cp -r "$MDX_OUTPUT_DIR"/* "$DOCS_REPO_DIR/models/ref/cli/"