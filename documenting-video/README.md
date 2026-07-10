# documenting-video

Turn a video — a local file or a URL (YouTube, Loom, Vimeo, Teams recording, …) — into comprehensive **markdown documentation with inline screenshots** captured at the moments that matter.

Great for knowledge-transfers, demos, and recorded meetings: it reads the transcript, decides which moments are worth showing, captures those frames, and writes them into synthesized prose (not a raw transcript dump).

## What it does

1. **Resolve input** — local file, video URL (downloaded with `yt-dlp`), or an existing transcript.
2. **Transcribe** if needed (existing captions, or local Whisper).
3. **Detect screenshot-worthy moments** from the transcript (demos, diagrams, topic changes, "as you can see…").
4. **Capture frames** — either directly with **ffmpeg** (preferred for local files) or via a browser for web-hosted video.
5. **Assemble** a clean markdown document with screenshots placed at the right narrative points, plus a collapsible full transcript.

## Requirements

| Need | For | Install |
|---|---|---|
| **Python 3.8+** | scripts | preinstalled on macOS |
| **ffmpeg / ffprobe** | frame capture, audio extraction | `brew install ffmpeg` |
| **yt-dlp** | downloading video URLs | `brew install yt-dlp` *(or `pip install yt-dlp`)* |
| **openai-whisper** | local transcription when no captions exist *(optional)* | `pip install openai-whisper` |
| **A Chromium browser** | browser-based screenshot capture *(fallback only)* | needed only for web-hosted/DRM video you can't download |

> **Fast path:** if you have a local video file and ffmpeg, screenshots are extracted directly with ffmpeg — no browser required, and it avoids the flakiness of seeking inside web video players.

## Install

```bash
git clone https://github.com/quietpublish/skills.git
cp -R skills/documenting-video ~/.claude/skills/

brew install ffmpeg yt-dlp
pip install openai-whisper   # optional, only if you need local transcription
```

## Usage

```
/documenting-video <video-url-or-local-path>
```

It will ask for context (what the video is about, who's in it, where output should go), then produce a documentation folder containing the markdown, a `screenshots/` directory, and the transcript.

## Note

This skill is also invoked by **[meeting-wrapup](../meeting-wrapup/)** to capture screenshots for meeting summaries.
