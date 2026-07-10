# tui-screenshots

Capture **deterministic screenshots (and GIFs) of a terminal UI or CLI app** using [vhs](https://github.com/charmbracelet/vhs), a headless terminal recorder. Perfect for README/docs screenshots, demo GIFs, or iterating on a shot until it looks right.

Because vhs drives the app inside a scripted, headless terminal, captures are **repeatable** — the same `.tape` script always produces the same image. And since the output is a PNG/GIF, an agent can `Read` it back, *see* the result, and adjust timing/keys/sizing before re-running.

## Requirements

| Need | Install |
|---|---|
| **vhs** + **ffmpeg** + **ttyd** | `brew install vhs ffmpeg ttyd` (macOS) — Linux: see [vhs install docs](https://github.com/charmbracelet/vhs#installation) |

## Install

```bash
git clone https://github.com/quietpublish/skills.git
cp -R skills/tui-screenshots ~/.claude/skills/
brew install vhs ffmpeg ttyd
```

## Usage

Ask for a terminal capture and the skill takes over — e.g. *"screenshot the TUI,"* *"make a demo GIF of this CLI,"* *"regenerate the README screenshots."* It writes a `.tape` script, runs vhs, then reads the output back to verify and iterate.

## Note

This skill is standalone — it has no dependencies on the other skills in this collection.
