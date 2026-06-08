# Shared setup for the wandb reference-doc generators.
#
# This file is meant to be *sourced*, not executed:
#   source "$(dirname "$0")/lib/common.sh"
#
# It provides the wandb repo coordinates and a prepare_repo() function that
# clones/updates the repo, checks out a release tag (or uses the local repo
# as-is for testing), and exports PYTHONPATH so the generator scripts can
# import the wandb package.

REPO_URL="https://github.com/wandb/wandb.git"
REPO_DIR="${REPO_DIR:-../wandb}"

# Populated by prepare_repo().
REPO_ROOT=""

# prepare_repo [RELEASE_TAG] [REPO_DIR]
#
# With a release tag: clone (full) if needed, fetch tags, and checkout the tag.
# Without a tag: use the existing local repo as-is (useful for local testing);
# errors out if it is not a Git repository.
#
# On success, sets the global REPO_ROOT and exports PYTHONPATH to include it.
prepare_repo() {
  local release_tag="${1:-}"
  local repo_dir="${2:-$REPO_DIR}"

  if [[ -n "$release_tag" ]]; then
    if [[ -d "$repo_dir/.git" ]]; then
      echo "Fetching tags in $repo_dir..."
      git -C "$repo_dir" fetch --tags origin
    else
      echo "Cloning $REPO_URL into $repo_dir..."
      mkdir -p "$(dirname "$repo_dir")"
      git clone "$REPO_URL" "$repo_dir"
    fi

    echo "Checking out $release_tag..."
    git -C "$repo_dir" checkout --force "$release_tag"
  else
    echo "No release tag specified. Using existing $repo_dir/ for local testing..."
    if [[ ! -d "$repo_dir/.git" ]]; then
      echo "Error: $repo_dir is not a Git repository." >&2
      echo "Pass a release tag to clone/check out a release, or ensure the wandb repo exists locally." >&2
      return 1
    fi
  fi

  REPO_ROOT="$(git -C "$repo_dir" rev-parse --show-toplevel)"

  if [[ ! -d "$REPO_ROOT/wandb" ]]; then
    echo "Error: expected Python package directory not found: $REPO_ROOT/wandb" >&2
    return 1
  fi

  # Put the repo root on PYTHONPATH so generator scripts can import wandb.
  export PYTHONPATH="$REPO_ROOT${PYTHONPATH:+:$PYTHONPATH}"
}
