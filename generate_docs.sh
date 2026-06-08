#!/usr/bin/env bash
# Generate both the Python SDK and CLI reference docs from a single release tag.
#
# This is a thin orchestrator over generate_python.sh and generate_cli.sh.
# Run either of those directly if you only need one set of docs.
#
# Usage:
#   ./generate_docs.sh [--tag TAG]
#
# Examples:
#   ./generate_docs.sh --tag v0.18.3
#   ./generate_docs.sh            # use the existing ../wandb checkout (local testing)
set -euo pipefail

RELEASE_TAG=""

while [[ $# -gt 0 ]]; do
  case "$1" in
    --tag)
      RELEASE_TAG="${2:?Missing value for --tag}"
      shift 2
      ;;
    -h|--help)
      grep '^#' "$0" | sed 's/^# \{0,1\}//'
      exit 0
      ;;
    *)
      echo "Error: unknown argument: $1" >&2
      exit 1
      ;;
  esac
done

HERE="$(dirname "$0")"

echo "=== Generating Python SDK reference docs ==="
if [[ -n "$RELEASE_TAG" ]]; then
  "$HERE/generate_python.sh" --tag "$RELEASE_TAG"
else
  "$HERE/generate_python.sh"
fi

echo "=== Generating CLI reference docs ==="
"$HERE/generate_cli.sh" "$RELEASE_TAG"

echo "=== Done ==="
