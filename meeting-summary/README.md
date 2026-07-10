# meeting-summary

Turn any meeting transcript into a clean, structured, scannable summary — topics discussed, key themes, decisions, action items, and notable moments — adapted to the kind of meeting it was.

Works with any transcript source (Deepgram JSON, VTT, SRT, or plain text) and any meeting type: workshop, retro, all-hands, open forum, standup, podcast.

## What it does

- Reads the transcript (and a speaker-confidence report, if one exists) and generates a `YYYY-MM-DD-summary.md`.
- Adapts the structure to the meeting type (e.g. retros organize by went-well / didn't / actions; standups by per-person updates).
- Attributes contributions to specific people when clear, captures the *why* behind discussions, and extracts action items and decisions.
- **Flags uncertain speaker attributions for you to confirm** before publishing — automated diarization is unreliable with shared microphones, so it won't silently guess.

## Requirements

**None beyond a transcript.** This skill is pure instructions — no scripts or external tools. It's most powerful when paired with a diarized transcript + confidence report (see [meeting-wrapup](../meeting-wrapup/)), but it works fine on a plain transcript.

## Install

```bash
git clone https://github.com/quietpublish/skills.git
cp -R skills/meeting-summary ~/.claude/skills/
```

## Usage

```
/meeting-summary /path/to/folder-or-transcript
```

Point it at a directory containing a transcript (it looks for `deepgram.json`, `*.vtt`, `*.srt`, or `*.txt`), or directly at a transcript file. It produces a dated summary markdown file.

## Note

This skill is also invoked automatically by **[meeting-wrapup](../meeting-wrapup/)** as its summarization step.
