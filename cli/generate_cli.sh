#!/bin/bash
# Generate markdown reference documentation for wandb CLI commands.
#
# This script:
#   1. Clones/updates the wandb/wandb repo to ./wandb/
#   2. Checks out the specified release tag
#   3. Generates markdown docs using md-click from the checked-out source
#   4. Formats the docs with tables and GitHub source links
#
# Output is written to ./output/ directory.
#
# Usage: ./generate_cli.sh [release_tag]
# Example: ./generate_cli.sh v0.18.3
# Note: If you want to specify a different output directory for the .mdx files,
# you can provide it as a second argument:
# Example: ./generate_cli.sh v0.18.3 docs/models/ref/cli
#
# If no release_tag is provided, the script uses the existing ./wandb/
# directory as-is (useful for local testing). GitHub source links will
# point to the 'main' branch.

set -e  # Exit on error

RELEASE_TAG="${1:-}"
REPO_URL="https://github.com/wandb/wandb.git"
REPO_DIR="wandb"

OUTPUT_JSON="source_info.json"
OUTPUT_DIR="cli_output"
MDX_OUTPUT_DIR="${2:-output}"

if [ -n "$RELEASE_TAG" ]; then
    # Clone or update the wandb repository
    if [ -d "$REPO_DIR" ]; then
        echo "Updating existing wandb repository..."
        git -C "$REPO_DIR" fetch --tags
    else
        echo "Cloning wandb repository..."
        git clone --depth 1 --no-checkout "$REPO_URL" "$REPO_DIR"
        git -C "$REPO_DIR" fetch --tags --depth 1
    fi

    # Checkout the specified release tag
    echo "Checking out $RELEASE_TAG..."
    git -C "$REPO_DIR" checkout "$RELEASE_TAG" --force
else
    echo "No release tag specified. Using existing $REPO_DIR/ directory for local testing..."
    if [ ! -d "$REPO_DIR" ]; then
        echo "Error: $REPO_DIR/ directory not found. Either provide a release tag or ensure the wandb repo exists locally."
        exit 1
    fi
fi

# Set PYTHONPATH to use the checked-out repo
export PYTHONPATH="$PWD/$REPO_DIR:$PYTHONPATH"

# Create output directory if it doesn't exist
# If it does exist, clear it out to avoid stale files from previous runs
if [ -d "$OUTPUT_DIR" ]; then
    rm -rf "$OUTPUT_DIR"/*
else
    mkdir -p "$OUTPUT_DIR"
fi

# Generate source info JSON (for source links in docs)
python get_public_commands.py --output-json "$OUTPUT_JSON"

# Extract command names from JSON and create .mdx files
if [ -n "$RELEASE_TAG" ]; then
    python create_mdx_file.py --source-info "$OUTPUT_JSON" --output-dir "$OUTPUT_DIR" --release-tag "$RELEASE_TAG"
else
    python create_mdx_file.py --source-info "$OUTPUT_JSON" --output-dir "$OUTPUT_DIR"
fi

python sort_markdown.py --output-markdown "$OUTPUT_DIR" --source-info "$OUTPUT_JSON"

if [ -n "$MDX_OUTPUT_DIR" ]; then
    # Copy .mdx files to the specified output directory.
    mkdir -p "$MDX_OUTPUT_DIR"
    cp -r "$OUTPUT_DIR"/* "$MDX_OUTPUT_DIR/"
    echo "Copied .mdx files to $MDX_OUTPUT_DIR/."
fi