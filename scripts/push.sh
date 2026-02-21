#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/.."

REPO="iotlodge/mcpfarm.ai"
REMOTE_URL="git@github.com:${REPO}.git"
BRANCH="${1:-main}"
MSG="${2:-}"

# ── Init git if needed ───────────────────────────────────────
if [ ! -d .git ]; then
    echo "Initializing git repository..."
    git init
    git branch -M main
fi

# ── Set remote if needed ─────────────────────────────────────
if ! git remote get-url origin > /dev/null 2>&1; then
    echo "Adding remote: $REMOTE_URL"
    git remote add origin "$REMOTE_URL"
fi

# ── Stage changes ────────────────────────────────────────────
# Exclude memory bank files from commits
echo "Staging changes..."
git add -A

# Unstage CLAUDE memory bank files
git reset HEAD -- 'CLAUDE-*.md' 2>/dev/null || true
git reset HEAD -- '.claude/' 2>/dev/null || true

# ── Show what's being committed ──────────────────────────────
echo ""
echo "Changes to commit:"
git diff --cached --stat
echo ""

STAGED=$(git diff --cached --name-only)
if [ -z "$STAGED" ]; then
    echo "Nothing to commit."
    exit 0
fi

# ── Commit ───────────────────────────────────────────────────
if [ -z "$MSG" ]; then
    echo "Enter commit message (or Ctrl+C to cancel):"
    read -r MSG
fi

if [ -z "$MSG" ]; then
    echo "No commit message provided. Aborting."
    exit 1
fi

git commit -m "$MSG"

# ── Push ─────────────────────────────────────────────────────
echo ""
echo "Pushing to origin/$BRANCH..."
git push -u origin "$BRANCH"

echo ""
echo "Pushed to github.com/$REPO ($BRANCH)"
