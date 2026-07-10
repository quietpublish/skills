#!/usr/bin/env bash
#
# link-into-claude.sh
# ---------------------------------------------------------------------------
# Symlink every skill in this repo into ~/.claude/skills/ so the repo is the
# single source of truth: edits are live in Claude Code AND version-controlled
# here. Run again any time you add a skill — it's idempotent.
#
# Any pre-existing real directory is backed up (not deleted) to
# ~/.claude/.skill-backups/ before it's replaced with a symlink.
# ---------------------------------------------------------------------------
set -euo pipefail

REPO_DIR="$(cd "$(dirname "$0")" && pwd)"
DEST="${CLAUDE_SKILLS_DIR:-$HOME/.claude/skills}"
BACKUP_DIR="$HOME/.claude/.skill-backups"

mkdir -p "$DEST"

linked=0; already=0; backed_up=0
for src in "$REPO_DIR"/*/; do
  src="${src%/}"
  [ -f "$src/SKILL.md" ] || continue        # only real skills
  skill="$(basename "$src")"
  link="$DEST/$skill"

  if [ -L "$link" ] && [ "$(readlink "$link")" = "$src" ]; then
    echo "  ✓ already linked: $skill"
    already=$((already + 1))
    continue
  fi

  if [ -e "$link" ] || [ -L "$link" ]; then
    mkdir -p "$BACKUP_DIR"
    backup="$BACKUP_DIR/${skill}.$(date +%Y%m%d-%H%M%S)"
    mv "$link" "$backup"
    echo "  • backed up existing $skill -> $backup"
    backed_up=$((backed_up + 1))
  fi

  ln -s "$src" "$link"
  echo "  linked: $skill -> $src"
  linked=$((linked + 1))
done

echo
echo "Done: $linked linked, $already already linked, $backed_up backed up."
echo "Source of truth is now: $REPO_DIR"
