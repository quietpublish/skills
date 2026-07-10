---
name: meeting-summary
description: Create a meeting summary from a transcript. Works with any meeting type — workshops, retros, all-hands, open forums, standups. Use after a meeting to generate the summary document.
argument-hint: "<directory> or <transcript-file>"
---

# Meeting Summary

You are creating a meeting summary from a transcript.

## Instructions

1. **Check for transcript sources** in the directory (priority order):
   - `deepgram.json` + `speaker-confidence-report.md` → proceed to step 2
   - `deepgram.json` only → run `python3 ~/.claude/skills/meeting-wrapup/scripts/analyze-speakers.py <directory>` first
   - `*.mp4` or `*.mp3` only → run `python3 ~/.claude/skills/meeting-wrapup/scripts/transcribe.py <directory>` (this chains analyze automatically)
   - `*.vtt` only → fallback to reading VTT directly (no confidence data available)
   - `*.srt` or `*.txt` → read directly as plain transcript
2. **Read the speaker confidence report** (`speaker-confidence-report.md`) — note the speaker map and all flagged passages
3. **Read the transcript** (`deepgram-transcript.md` for Deepgram-based, or VTT/SRT for fallback) — it may require multiple reads for long files
4. **Check for images** (`.png`, `.jpg`) in the same folder — board screenshots, slides, etc.
5. **Generate the summary** following the template below, adapted to the meeting type

## Summary Template

Create a file named `YYYY-MM-DD-summary.md` (using the meeting date).

```markdown
# [Meeting Name] Summary — YYYY-MM-DD

## Meeting Overview
- **Type**: [workshop / retro / all-hands / open forum / standup / etc.]
- **Duration**: ~XX minutes
- **Facilitator**: [Name]
- **Participants**: [List names mentioned in transcript]

---

## Topics Discussed

### 1. [Topic Title]
**Raised by**: [Name]

[2-3 paragraph summary of the discussion]

**Key points:**
- [Bullet point insights]

**Quotes/moments worth noting:**
- [Notable quotes if any]

---

### 2. [Next Topic]...

---

## Key Themes & Insights

1. **[Theme]** — [Brief explanation]
2. **[Theme]** — [Brief explanation]

---

## Action Items
- [ ] [Action] — *Owner: [Name]*
- [ ] [Action] — *Owner: [Name]*

---

## Follow-ups for Next Time
- [Items mentioned for future discussion]
```

## Adapting to Meeting Types

The template above is a starting point. Adapt based on what kind of meeting this is:

- **Open forum / discussion-based**: Use the full topic structure with votes, quotes, themes (like the template above)
- **Workshop / working session**: Focus on inputs, process, outputs, and decisions made
- **Retro / retrospective**: Organize by what went well, what didn't, and action items
- **All-hands / announcements**: Focus on announcements, Q&A, and key decisions
- **Standup / status update**: Brief per-person updates with blockers highlighted
- **Knowledge transfer / demo**: Focus on what was demonstrated, key learnings, and resources shared

When in doubt, let the transcript content guide the structure rather than forcing it into a template.

## Guidelines

- **Attribute contributions** to specific people when clear from transcript
- **Capture the "why"** not just the "what" of discussions
- **Note frameworks or models** that emerged
- **Keep summaries scannable** with clear headers and bullet points
- **Include humor or memorable moments** that capture the session's spirit
- **Extract action items** — who committed to doing what, by when
- **Note decisions made** — especially if they resolve prior open questions

## Speaker Attribution — Important

Hybrid meetings with in-room participants sharing a single conference room microphone make automated speaker identification unreliable:

- **Teams/Zoom VTT transcripts** only identify remote participants by name. In-room speakers appear as unnamed tags.
- **Deepgram diarization** assigns speaker numbers (Speaker 0, Speaker 1, etc.) but frequently misattributes when people talk over each other, speak in quick succession, or sit near each other by the shared mic.
- **Cross-referencing** VTT with Deepgram helps but is not sufficient — diarization errors can silently assign the wrong speaker to entire passages.

### Automated Confidence Flagging

The `analyze-speakers.py` script automatically:
- **Resolves speaker names** by cross-referencing Deepgram speaker numbers with VTT named entries
- **Flags low-confidence passages** where `speaker_confidence` < 0.50 or any word has confidence of 0.0
- **Marks `[LOW CONFIDENCE]`** in `deepgram-transcript.md` on flagged segments
- **Generates `speaker-confidence-report.md`** with a table of all flagged passages including timestamps, attributed speaker, confidence score, and text preview

When writing the summary, **use the confidence report as your primary guide** for which attributions need verification. Unidentified in-room speakers and any flagged passages should all be treated as uncertain.

**Before publishing, you MUST present ALL uncertain attributions to the user for manual confirmation.** Format them as a table with timestamps so the user can easily verify against the video:

| Timestamp | Current Attribution | Confidence | Quote/Content |
|---|---|---|---|
| 4:44 | Speaker 0 (unidentified) | 0.27 | "I have a small child, she's four years old..." |

Do NOT publish the summary with unverified attributions. Getting attribution wrong misrepresents what people said and undermines trust in the summary.

## After Creating

The summary serves as:
- A shareable record of the meeting
- Input for follow-up meetings or status updates
- Reference for action items and decisions

**Next steps**:
1. Run `/documenting-video` on the meeting video to extract screenshots at key moments. Screenshots are saved to `screenshots/` and can be referenced using `![Caption](screenshots/filename.png)`.
2. Build PDF with `~/.claude/skills/meeting-wrapup/scripts/build-pdf.sh <directory>` for offline sharing.
