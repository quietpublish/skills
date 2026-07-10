# Installing quietpublish/skills

This document is written so a **coding agent** (or a human) can install these skills end to end. If you use a coding agent, point it here:

> **Prompt your agent:** *"Follow the INSTALL.md in https://github.com/quietpublish/skills to install the `meeting-wrapup` skill and its companions into `~/.claude/skills/`, then install and verify the dependencies."*

Everything below is explicit and idempotent — safe to re-run.

---

## Where skills live

Claude Code loads personal skills from **`~/.claude/skills/<skill-name>/`**. Installing a skill = putting its folder there (by copy or symlink).

## Step 1 — Get the repo

```bash
git clone https://github.com/quietpublish/skills.git
cd skills
```

## Step 2 — Install the skill folder(s)

Pick the skills you want. `meeting-wrapup` requires `meeting-summary` **and** `documenting-video`.

**Copy (simple):**
```bash
mkdir -p ~/.claude/skills
cp -R meeting-wrapup meeting-summary documenting-video ~/.claude/skills/   # the meeting bundle
# or an individual standalone skill:
cp -R tui-screenshots ~/.claude/skills/
```

**Or symlink (if you want to track the repo as the source of truth):**
```bash
./link-into-claude.sh    # symlinks every skill in this repo into ~/.claude/skills/
```

## Step 3 — Install dependencies

Only install what the skills you chose need.

### meeting-wrapup (+ meeting-summary + documenting-video)
```bash
pip install deepgram-sdk          # required — cloud transcription
brew install ffmpeg               # required — audio extraction + screenshots
brew install pandoc weasyprint    # optional — PDF export
pip install openai-whisper        # optional — offline transcription (no API key)
brew install yt-dlp               # optional — only if documenting video URLs
```

### tui-screenshots
```bash
brew install vhs ffmpeg ttyd
```

### meeting-summary
No dependencies — it works on a transcript alone.

> **Linux / non-Homebrew:** install `ffmpeg`, `pandoc`, `weasyprint`, `vhs`, `ttyd`, `yt-dlp` with your platform's package manager instead of `brew`.

## Step 4 — Configure (meeting-wrapup only)

`meeting-wrapup` transcribes with [Deepgram](https://deepgram.com/) by default. Put your key in a `.env.local` **in the meeting folder** (never commit it):

```bash
echo 'DEEPGRAM_API_KEY=your_key_here' > /path/to/meeting-folder/.env.local
```

No key? Skip this and use offline mode: `transcribe.py --local` (Whisper), or drop in a transcript you already have.

## Step 5 — Verify

In Claude Code, the skills should now be invocable by name:

- `/meeting-wrapup <folder-with-a-recording>`
- `/documenting-video <video-url-or-path>`
- `/meeting-summary <folder-or-transcript>`
- `/tui-screenshots` (or ask it to "screenshot the TUI")

If a skill doesn't appear, confirm its folder exists at `~/.claude/skills/<name>/` and contains a `SKILL.md`.

---

## Agent instructions (copy-paste)

```
Install skills from https://github.com/quietpublish/skills by following its INSTALL.md:
1. git clone the repo.
2. Copy (or symlink via link-into-claude.sh) these skill folders into ~/.claude/skills/:
   meeting-wrapup, meeting-summary, documenting-video.
3. Install dependencies: `pip install deepgram-sdk`, `brew install ffmpeg`, and
   (optional) `brew install pandoc weasyprint`, `pip install openai-whisper`.
4. Tell me to add my DEEPGRAM_API_KEY to a .env.local in my meeting folder.
5. Confirm the skills are installed and list how to invoke them.
```
