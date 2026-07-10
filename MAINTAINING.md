# Maintaining this repo

Notes for the maintainer (not needed by people just installing a skill).

## Source of truth & the symlink flow

**This repo is the single source of truth for these skills.** On the maintainer's machine, each skill folder in `~/.claude/skills/` is a **symlink** into this repo, so:

- Editing a skill (from the repo *or* through `~/.claude/skills/…`) edits the same files.
- Changes are **live in Claude Code immediately** and **version-controlled** at the same time.
- Publishing = `git commit` + `git push`. No copying, no drift.

Set it up (idempotent — safe to re-run):

```bash
./link-into-claude.sh
```

It symlinks every folder here that contains a `SKILL.md` into `~/.claude/skills/`. Any pre-existing **real** directory is backed up (not deleted) to `~/.claude/.skill-backups/<skill>.<timestamp>` first.

## Adding a new skill

1. Create `<skill-name>/` with a `SKILL.md` (plus `scripts/`, `templates/`, `references/` as needed).
2. Add `<skill-name>/README.md` — what it does, dependencies, install, usage.
3. Add a row to the skills table in the top-level [`README.md`](README.md).
4. Add its dependencies to [`INSTALL.md`](INSTALL.md).
5. Run `./link-into-claude.sh` to link it live.
6. Run the pre-publish checklist below, then commit + push.

## Pre-publish checklist ✅

This is a **public** repo. Before pushing, from the repo root:

```bash
# Secrets / personal paths (should print nothing). Extend the pattern with your own
# employer, usernames, client names, and internal tool names before running.
grep -rniE "/Users/|@gmail|password|api[_-]?key|token|secret|sk-[A-Za-z0-9]{16,}|ghp_[A-Za-z0-9]{20,}|-----BEGIN" . --exclude-dir=.git
```

- ✅ No secrets, tokens, or `.env` files (`.gitignore` covers the common ones — but verify).
- ✅ No hardcoded personal paths or private info in *content* (grep matches on file *paths* are fine).
- ✅ No work/client-specific skills (they don't belong in a public share).
- ✅ **Don't republish third-party skills** (e.g. skills copied from someone else's pack) without their license and attribution. Only publish skills that are yours to share.

## Reverting a skill to a plain directory

Symlinks live under `~/.claude/skills/`; originals are backed up under `~/.claude/.skill-backups/`. To detach a skill from the repo:

```bash
rm ~/.claude/skills/<skill>                        # remove the symlink (NOT the repo)
cp -R ./<skill> ~/.claude/skills/<skill>           # restore a plain copy from the repo
# or restore a pre-symlink backup from ~/.claude/.skill-backups/
```
