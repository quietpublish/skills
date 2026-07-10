# quietpublish / skills

A small, growing collection of **[Claude Code](https://claude.com/claude-code) Agent Skills** — self-contained workflows you can drop into any agent that supports skills and run by name.

Each skill is a folder with a `SKILL.md` (the instructions the agent follows) plus any scripts, templates, and references it needs. They're designed to be **portable and vendor-agnostic** — the same markdown + scripts work in Claude Code, and the patterns port to other agent runtimes.

## Skills

| Skill | What it does | Docs |
|---|---|---|
| **[meeting-wrapup](meeting-wrapup/)** | Full post-meeting pipeline: transcribe a recording → speaker-attributed summary → screenshots → PDF, with two human review checkpoints. | [README](meeting-wrapup/README.md) |
| **[meeting-summary](meeting-summary/)** | Turn any meeting transcript into a clean, structured summary. Standalone, or used by `meeting-wrapup`. | [README](meeting-summary/README.md) |
| **[documenting-video](documenting-video/)** | Turn a video (file or URL) into markdown documentation with inline screenshots captured at the right moments. Standalone, or used by `meeting-wrapup`. | [README](documenting-video/README.md) |

> `meeting-wrapup` orchestrates the other two, so if you install it, install all three.

## Installing a skill

Claude Code loads personal skills from `~/.claude/skills/<skill-name>/`. To install any skill here, copy its folder there.

**Option A — clone and copy:**
```bash
git clone https://github.com/quietpublish/skills.git
cp -R skills/meeting-wrapup    ~/.claude/skills/
cp -R skills/meeting-summary   ~/.claude/skills/
cp -R skills/documenting-video ~/.claude/skills/
```

**Option B — let your agent install it.** Point your coding agent at this repo and say, for example:

> Install the `meeting-wrapup` skill (and its companions `meeting-summary` and `documenting-video`) from `https://github.com/quietpublish/skills` into `~/.claude/skills/`, then set up the dependencies listed in each skill's README.

Then follow that skill's README to install its dependencies and invoke it (e.g. `/meeting-wrapup`).

## Requirements at a glance

Requirements vary per skill — see each skill's README for specifics. Across the collection you may need:

- **Python 3.8+**
- **[ffmpeg](https://ffmpeg.org/)** / ffprobe — audio extraction, frame capture
- **[Deepgram](https://deepgram.com/)** API key — transcription (`meeting-wrapup`)
- **[pandoc](https://pandoc.org/)** + **[WeasyPrint](https://weasyprint.org/)** — PDF export (optional)
- **[yt-dlp](https://github.com/yt-dlp/yt-dlp)**, **[openai-whisper](https://github.com/openai/whisper)** — video download / local transcription (optional, `documenting-video`)
- A Chromium browser — only for `documenting-video`'s browser screenshot fallback

## License

[MIT](LICENSE) — free to use, modify, and share. Attribution appreciated but not required.
