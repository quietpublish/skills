---
name: meeting-wrapup
description: Full post-meeting workflow — transcribe, summarize, screenshot, and build PDF for any meeting recording. Two checkpoints pause for human review. Use for any recorded meeting, workshop, or session.
argument-hint: "<directory> (e.g., /path/to/meeting-folder)"
---

# Meeting Wrapup

You are running the full post-meeting pipeline for a recorded meeting. This orchestrates transcription, summary generation, screenshot capture, and PDF generation — with two human checkpoints.

Use the directory from `$ARGUMENTS`. If no argument is given, ask the user which directory contains the meeting files.

**Before starting**, ask the user (if not already provided):
1. What kind of meeting was this? (standup, retro, workshop, all-hands, open forum, etc.)
2. Who facilitated?
3. Any known participants?

---

## Phase 1: Transcribe & Analyze

**Goal:** Get a transcript with speaker names resolved and low-confidence passages flagged.

1. **First, check for an already-prepared transcript** before transcribing anything:
   - `deepgram.json` present → reuse it; run `analyze-speakers.py` only if the `deepgram-transcript.md` / `speaker-confidence-report.md` outputs are missing. Skip re-transcription.
   - A user-supplied transcript (`.vtt`, `.srt`, `.txt`, or a transcript-style `.md` such as MacWhisper output) present → **ask the user** whether to use it and skip Deepgram. This holds **even if a video is also present** — do not silently re-transcribe when a transcript already exists.
   - Reusing a plain transcript means **no Deepgram confidence data** — note that, then proceed to Phase 2 reading it directly.

2. Otherwise, look in the directory for audio/video files (`.mp4`, `.mp3`).

3. **If audio/video exists (and no transcript is being reused):**
   - Run the transcription pipeline:
     ```bash
     /usr/bin/python3 ~/.claude/skills/meeting-wrapup/scripts/transcribe.py <directory>
     ```
   - **Offline / no API key:** add `--local` (`transcribe.py --local <directory>`) to transcribe on-device with Whisper instead of Deepgram — private and free, but **no speaker diarization or confidence data** (a single stream to attribute manually). Requires `pip install openai-whisper`.
   - This chains `analyze-speakers.py` automatically, producing:
     - `deepgram.json` — raw Deepgram response
     - `deepgram-transcript.md` — readable transcript with `[LOW CONFIDENCE]` markers
     - `speaker-confidence-report.md` — speaker map and flagged passages table
   - Report to the user: number of speakers detected, names resolved, flagged segment count.

4. **If no audio/video but a `.vtt`/`.srt`/`.txt` transcript exists:**
   - Note fallback mode: "No audio file found. Using the provided transcript (no Deepgram confidence data available)."
   - Speaker attribution quality will be limited — VTT only identifies remote participants.

5. **If neither exists:**
   - Stop and tell the user: "No transcript source found. Drop a `.mp4`, `.mp3`, or a transcript (`.vtt`/`.srt`/`.txt`) into the folder and re-run."

---

## Phase 2: Generate Summary

**Goal:** Produce a draft meeting summary following the meeting-summary skill's template and guidelines.

1. **Read** `~/.claude/skills/meeting-summary/SKILL.md` for the full summary template, guidelines, and speaker attribution rules.
2. Follow those instructions to generate the summary. Specifically:
   - Read the speaker confidence report (if available) to know which attributions need verification
   - Read the transcript (`deepgram-transcript.md` or `.vtt`)
   - Check for any screenshots or images already in the folder
   - Generate the summary adapted to the meeting type
3. Save the summary as `<directory>/YYYY-MM-DD-summary.md` (using the meeting date).

---

## CHECKPOINT 1: Attribution Review

**STOP HERE and wait for the user.**

Present the following for review:

1. **Speaker confidence summary** — How many speakers were detected, which names were resolved, how many flagged passages.

2. **Flagged attributions table** — All uncertain attributions with timestamps so the user can verify against the video:

   | Timestamp | Current Attribution | Confidence | Quote/Content |
   |---|---|---|---|
   | MM:SS | Speaker name or number | score | Brief text preview |

   If using VTT fallback (no Deepgram data), note that in-room speakers could not be identified and list any passages attributed to unnamed speakers.

3. **Draft summary** — The full summary text for review.

Ask: **"Please review the flagged attributions and the draft summary. Let me know any corrections, then I'll proceed to screenshots."**

Wait for the user to respond. Apply any corrections they provide before moving on.

---

## Phase 3: Screenshots (optional)

**Goal:** Capture screenshots from the meeting video to add visual context to the summary.

1. Check if a `.mp4` file exists in the directory.

2. **If video exists:**
   - Ask the user: "Video file found. Want me to capture screenshots with `/documenting-video`?" (Skip if they decline.)
   - Invoke `/documenting-video` on the meeting video. The video is local, so use its **ffmpeg fast path** (direct frame extraction at each timestamp) rather than the browser player — it's deterministic and avoids the web-player fragility.
   - After screenshots are captured in `screenshots/`, review the summary and place screenshot references at relevant points using markdown image syntax:
     ```markdown
     ![Caption describing what's shown](screenshots/filename.png)
     ```
   - Match screenshots to the discussion topics they illustrate.

3. **If no video exists:**
   - Note: "No video file found — skipping screenshot capture."
   - If there are already screenshots in the `screenshots/` directory, offer to place those in the summary.

---

## CHECKPOINT 2: Final Review

**STOP HERE and wait for the user.**

Present the final summary (with screenshots placed, if any) and ask:

**"Here's the final summary. Ready to build the PDF?"**

If the user wants changes, apply them. If they approve, proceed to Phase 4.

---

## Phase 4: Build PDF

**Goal:** Build a print-ready PDF for offline sharing. HTML is **optional (opt-in)** — do not generate it automatically.

By default the script produces **only** `summary.pdf`. Pass `--html` only when the user explicitly wants a self-contained `summary.html` as well (e.g., for web sharing).

```bash
# PDF only (default)
~/.claude/skills/meeting-wrapup/scripts/build-pdf.sh <directory>

# Also produce HTML (only if the user asks)
~/.claude/skills/meeting-wrapup/scripts/build-pdf.sh --html <directory>
```

Verify output:
- `summary.pdf` — print-ready PDF (always, unless PDF generation fails)
- `summary.html` — self-contained HTML with embedded images (**only** when `--html` was passed)

If PDF generation fails (WeasyPrint or Pandoc not installed), note it and offer `--html` as an alternative deliverable.

Report the file sizes and confirm completion.

---

## Graceful Degradation

This skill should complete as much as possible even when tools are missing:

- **No audio file** → skip transcription, use VTT fallback
- **No VTT either** → stop (can't generate summary without a transcript)
- **No video** → skip screenshot phase entirely
- **WeasyPrint not installed** → PDF can't be built; offer `--html` (HTML uses Pandoc only, not WeasyPrint) as an alternative deliverable
- **Pandoc not installed** → neither PDF nor HTML can be built; the markdown summary is the deliverable
- **User declines screenshots** → skip Phase 3, go straight to Checkpoint 2
- **No Deepgram API key** → transcribe offline with `transcribe.py --local` (Whisper; `pip install openai-whisper`). Note it yields **no diarization or confidence data** — a single stream to attribute manually.

Always tell the user what was skipped and why.
