# meeting-wrapup

Turn a meeting recording into a polished, shareable summary — **transcript → speaker-attributed summary → screenshots → PDF** — with two checkpoints where the workflow pauses for your review.

It's built for any recorded session: podcasts, workshops, retros, all-hands, open forums, standups.

## Example output

See a real summary this skill produced: **[example-summary.pdf](example/example-summary.pdf)** — generated live during an episode of *Reflective Practice Radio* (transcript → speaker-attributed summary → embedded screenshots → PDF).

## What it does

| Phase | Output |
|---|---|
| **1. Transcribe & analyze** | Sends audio to Deepgram (Nova-3, diarized), producing `deepgram.json`, a readable `deepgram-transcript.md`, and a `speaker-confidence-report.md` that flags low-confidence speaker attributions. |
| **🛑 Checkpoint 1** | You verify the flagged attributions and review the draft summary. |
| **2. Summarize** | Generates `YYYY-MM-DD-summary.md` using the `meeting-summary` skill's template, adapted to the meeting type. |
| **3. Screenshots** *(optional)* | Captures frames from the video (via the `documenting-video` skill) and places them at the relevant points in the summary. |
| **🛑 Checkpoint 2** | You review the final summary before the PDF is built. |
| **4. Build PDF** | Produces `summary.pdf` (and `summary.html` only if you pass `--html`). |

The workflow degrades gracefully: no audio → use an existing transcript; no video → skip screenshots; no pandoc/WeasyPrint → the markdown summary is still the deliverable.

## Companion skills (required)

`meeting-wrapup` calls these — install them alongside it:

- **[meeting-summary](../meeting-summary/)** — generates the summary document.
- **[documenting-video](../documenting-video/)** — captures the screenshots.

## Requirements

| Need | For | Install |
|---|---|---|
| **Python 3.8+** | all scripts | preinstalled on macOS; else your package manager |
| **`deepgram-sdk`** | transcription | `pip install deepgram-sdk` |
| **A Deepgram API key** | transcription | free credits at [deepgram.com](https://deepgram.com/) |
| **`openai-whisper`** | offline transcription *(optional; no key needed)* | `pip install openai-whisper` |
| **ffmpeg** | audio extraction + screenshots | `brew install ffmpeg` |
| **pandoc + WeasyPrint** | PDF export *(optional)* | `brew install pandoc weasyprint` |
| **A Chromium browser** | screenshot fallback *(optional)* | only if a video isn't local/ffmpeg-able |

## Install

```bash
# 1. Copy this skill + its companions into your Claude Code skills directory
git clone https://github.com/quietpublish/skills.git
cp -R skills/meeting-wrapup    ~/.claude/skills/
cp -R skills/meeting-summary   ~/.claude/skills/
cp -R skills/documenting-video ~/.claude/skills/

# 2. Dependencies
pip install deepgram-sdk
brew install ffmpeg              # required
brew install pandoc weasyprint  # optional, for PDF export
```

## Set up your Deepgram key

Put your key in a `.env.local` file **in the meeting folder** (or export it as an environment variable):

```bash
# <meeting-folder>/.env.local
DEEPGRAM_API_KEY=your_key_here
```

The transcription script looks for the key in this order: `DEEPGRAM_API_KEY` env var → `.env.local` in the meeting folder → `.env.local` in the current directory → `~/.config/deepgram/.env`. **Never commit `.env.local`.**

## Usage

Drop a recording into a folder and run the skill against that folder (or the file):

```
/meeting-wrapup /path/to/meeting-folder
```

Up front it asks a couple of questions (meeting type, how to attribute speakers), then runs the pipeline, pausing at the two checkpoints for your input. You can walk away between checkpoints — it waits for you.

## Output

In the meeting folder you'll get:

```
deepgram.json                  # raw transcription response
deepgram-transcript.md         # readable, speaker-labeled transcript
speaker-confidence-report.md   # speaker map + flagged low-confidence passages
YYYY-MM-DD-summary.md          # the summary (with inline screenshots, if captured)
screenshots/                   # captured frames (if the video had visuals)
summary.pdf                    # print-ready PDF (Phase 4)
summary.html                   # only if you build with --html
```

## Notes

- **HTML is opt-in.** `build-pdf.sh` produces only the PDF by default; pass `--html` to also emit a self-contained `summary.html`.
- **Screenshots prefer ffmpeg.** For a local video file, frames are extracted directly with ffmpeg (deterministic, fast). The browser-based capture path is a fallback for web-hosted/DRM video.
- **Reuses existing transcripts.** If you already have a transcript (e.g. from a tool like MacWhisper), drop it in the folder — the workflow will offer to use it and skip the Deepgram step.
- **Offline transcription.** No Deepgram key, or a private/secure meeting? Run `transcribe.py --local` to transcribe on-device with Whisper (`pip install openai-whisper`) — no cloud, no cost. Trade-off: **no speaker diarization or confidence scoring** (a single stream you attribute manually).
