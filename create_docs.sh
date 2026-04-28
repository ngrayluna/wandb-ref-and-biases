#!/bin/bash
#!/usr/bin/env bash
set -euo pipefail

REPO_URL="https://github.com/wandb/wandb.git"
REPO_DIR="./.repos/wandb"
RELEASE_TAG=""
OUTPUT_DIR="./objects_found"

usage() {
  cat <<EOF
Usage:
  $0 [--repo-dir PATH] [--tag TAG] [--output-dir PATH]

Examples:
  $0 --repo-dir ../wandb
  $0 --tag v0.17.0
  $0 --repo-dir /tmp/wandb --tag v0.17.0
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
    --output-dir)
      OUTPUT_DIR="${2:?Missing value for --output-dir}"
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

export PYTHONPATH="$REPO_ROOT${PYTHONPATH:+:$PYTHONPATH}"


python get_python_objects.py --output-dir=./objects_found

python get_info.py --input-dir=./objects_found --output-dir=./docs_json

python create_mdx_file.py --source-info ./docs_json/  --output-dir ./mdx_output

python sort_files.py --source-directory mdx_output/ --output ./python