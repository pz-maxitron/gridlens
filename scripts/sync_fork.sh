#!/bin/bash
# Keeps the pz-maxitron/gridlens fork's main in sync with upstream
# (open-energy-transition/gridlens), and keeps active working branches
# merged with the latest main so they don't accumulate conflicts.
#
# CANONICAL COPY: this file is the source of truth, kept in the repo for
# visibility/history. The actual executable run by the Hermes cron job
# ("gridlens-fork-sync") is a plain copy at
# ~/.hermes/scripts/gridlens_sync_fork.sh -- the cron sandbox requires
# scripts to live there (no symlinks). If you edit this file, copy it
# over the ~/.hermes/scripts/ version too.
#
# Runs entirely in an ISOLATED clone, never in the main
# ~/code/plexos-catalogue-web working directory -- that directory may
# have live uncommitted work (e.g. a long-running research agent) and
# must never have its branch switched out from under it.
#
# Silent on a no-op. Prints a summary when something actually changed,
# or a clear WARNING when a branch needs manual conflict resolution
# (never force-pushes or auto-resolves a real conflict).
#
# Branches to keep synced with main, besides main itself:
BRANCHES_TO_SYNC=("develop")

set -u
MAIN_REPO="$HOME/code/plexos-catalogue-web"
SYNC_DIR="$HOME/.cache/gridlens-sync-mirror"
export PATH="$HOME/.local/bin:$PATH"

if [ ! -d "$SYNC_DIR/.git" ]; then
  mkdir -p "$(dirname "$SYNC_DIR")"
  git clone --quiet "$MAIN_REPO" "$SYNC_DIR" 2>&1
  (cd "$SYNC_DIR" && \
    git remote set-url origin "$(git -C "$MAIN_REPO" remote get-url origin)" && \
    git remote add upstream "$(git -C "$MAIN_REPO" remote get-url upstream)" ) 2>&1
fi

cd "$SYNC_DIR" || { echo "WARNING: could not create/access sync mirror at $SYNC_DIR"; exit 1; }

SUMMARY=""
WARNED=0

git fetch upstream --quiet 2>&1
git fetch origin --quiet 2>&1

UPSTREAM_MAIN=$(git rev-parse upstream/main 2>/dev/null)
ORIGIN_MAIN=$(git rev-parse origin/main 2>/dev/null)

if [ -z "$UPSTREAM_MAIN" ] || [ -z "$ORIGIN_MAIN" ]; then
  echo "WARNING: could not resolve upstream/main or origin/main -- check remotes"
  exit 1
fi

if [ "$UPSTREAM_MAIN" != "$ORIGIN_MAIN" ]; then
  # Only fast-forward -- never force-push over diverged fork history.
  if git merge-base --is-ancestor "$ORIGIN_MAIN" "$UPSTREAM_MAIN"; then
    git push origin "upstream/main:refs/heads/main" --quiet 2>&1
    SUMMARY="${SUMMARY}Synced fork main: ${ORIGIN_MAIN:0:7} -> ${UPSTREAM_MAIN:0:7}\n"
  else
    echo "WARNING: fork main has diverged from upstream main (not a fast-forward). Not touching it -- needs manual review."
    WARNED=1
  fi
fi

for BRANCH in "${BRANCHES_TO_SYNC[@]}"; do
  if ! git ls-remote --exit-code --heads origin "$BRANCH" >/dev/null 2>&1; then
    continue
  fi
  git fetch origin "$BRANCH" --quiet 2>&1

  if git merge-base --is-ancestor upstream/main "origin/$BRANCH"; then
    continue  # branch already contains the latest main
  fi

  git checkout -B "$BRANCH" "origin/$BRANCH" --quiet 2>&1 || {
    echo "WARNING: could not check out '$BRANCH' in the sync mirror -- skipping this run."
    WARNED=1
    continue
  }

  if git merge upstream/main --no-edit --quiet 2>&1; then
    git push origin "$BRANCH:refs/heads/$BRANCH" --quiet 2>&1
    SUMMARY="${SUMMARY}Merged latest main into '${BRANCH}' and pushed (no conflicts).\n"
  else
    git merge --abort 2>&1
    echo "WARNING: merging main into '${BRANCH}' has a real conflict -- needs manual resolution (git checkout ${BRANCH} && git merge upstream/main). Left '${BRANCH}' untouched."
    WARNED=1
  fi
done

if [ -n "$SUMMARY" ]; then
  printf "%b" "$SUMMARY"
fi

exit 0
