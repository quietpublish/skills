#!/usr/bin/env python3
"""Analyze Deepgram word-level JSON to produce speaker-labeled transcripts
and confidence reports.

Usage:
    python3 analyze-speakers.py <directory> [--threshold 0.5]

Inputs:
    <directory>/deepgram.json  — Deepgram API response with word-level data
    <directory>/*.vtt          — Optional VTT for speaker name mapping

Outputs:
    <directory>/deepgram-transcript.md
    <directory>/speaker-confidence-report.md
"""

import argparse
import json
import re
import sys
from pathlib import Path
from statistics import mean


# ---------------------------------------------------------------------------
# VTT parsing
# ---------------------------------------------------------------------------

def parse_vtt_timestamp(ts: str) -> float:
    """Convert HH:MM:SS.mmm or MM:SS.mmm to seconds."""
    parts = ts.strip().split(":")
    if len(parts) == 3:
        h, m, s = parts
        return int(h) * 3600 + int(m) * 60 + float(s)
    elif len(parts) == 2:
        m, s = parts
        return int(m) * 60 + float(s)
    return 0.0


def parse_vtt(vtt_path: Path) -> list[dict]:
    """Parse a VTT file and return entries with named speakers.

    Returns a list of dicts:
        { "start": float, "end": float, "speaker": str, "text": str }

    Only entries with a real speaker name are returned (not @-prefixed or empty).
    """
    text = vtt_path.read_text(encoding="utf-8", errors="replace")
    entries = []

    # Split into cue blocks (separated by blank lines)
    blocks = re.split(r"\n\s*\n", text)

    for block in blocks:
        lines = block.strip().splitlines()
        if not lines:
            continue

        # Find the timestamp line
        ts_line = None
        ts_idx = None
        for i, line in enumerate(lines):
            if "-->" in line:
                ts_line = line
                ts_idx = i
                break

        if ts_line is None:
            continue

        # Parse timestamps
        match = re.match(
            r"(\d[\d:.]+)\s*-->\s*(\d[\d:.]+)", ts_line
        )
        if not match:
            continue

        start = parse_vtt_timestamp(match.group(1))
        end = parse_vtt_timestamp(match.group(2))

        # Collect text lines after the timestamp
        text_lines = lines[ts_idx + 1 :]
        full_text = " ".join(text_lines)

        # Extract speaker name from <v Name>...</v> tags
        speaker_match = re.search(r"<v\s+([^>]*)>", full_text)
        if not speaker_match:
            continue

        speaker_name = speaker_match.group(1).strip()

        # Skip unnamed or @-prefixed (in-room) speakers
        if not speaker_name or speaker_name.startswith("@"):
            continue

        # Strip tags to get plain text
        plain_text = re.sub(r"</?v[^>]*>", "", full_text).strip()

        entries.append(
            {
                "start": start,
                "end": end,
                "speaker": speaker_name,
                "text": plain_text,
            }
        )

    return entries


# ---------------------------------------------------------------------------
# Speaker segments
# ---------------------------------------------------------------------------

def build_segments(words: list[dict]) -> list[dict]:
    """Group contiguous words with the same speaker number into segments."""
    if not words:
        return []

    segments = []
    current = {
        "speaker": words[0]["speaker"],
        "start": words[0]["start"],
        "end": words[0]["end"],
        "words": [words[0]],
    }

    for w in words[1:]:
        if w["speaker"] == current["speaker"]:
            current["end"] = w["end"]
            current["words"].append(w)
        else:
            segments.append(_finalize_segment(current))
            current = {
                "speaker": w["speaker"],
                "start": w["start"],
                "end": w["end"],
                "words": [w],
            }

    segments.append(_finalize_segment(current))
    return segments


def _finalize_segment(raw: dict) -> dict:
    """Convert a raw accumulator into a final segment dict."""
    confidences = [
        w.get("speaker_confidence", 0.0) for w in raw["words"]
    ]
    return {
        "speaker": raw["speaker"],
        "start": raw["start"],
        "end": raw["end"],
        "text": " ".join(w.get("punctuated_word", w["word"]) for w in raw["words"]),
        "avg_confidence": mean(confidences) if confidences else 0.0,
        "word_count": len(raw["words"]),
        "has_zero_conf": any(c == 0.0 for c in confidences),
    }


def merge_consecutive(segments: list[dict], gap: float = 2.0) -> list[dict]:
    """Merge consecutive segments from the same speaker within *gap* seconds."""
    if not segments:
        return []

    merged = [segments[0].copy()]

    for seg in segments[1:]:
        prev = merged[-1]
        if (
            seg["speaker"] == prev["speaker"]
            and seg["start"] - prev["end"] <= gap
        ):
            total_words = prev["word_count"] + seg["word_count"]
            prev["avg_confidence"] = (
                prev["avg_confidence"] * prev["word_count"]
                + seg["avg_confidence"] * seg["word_count"]
            ) / total_words
            prev["end"] = seg["end"]
            prev["text"] = prev["text"] + " " + seg["text"]
            prev["word_count"] = total_words
            prev["has_zero_conf"] = prev["has_zero_conf"] or seg["has_zero_conf"]
        else:
            merged.append(seg.copy())

    return merged


# ---------------------------------------------------------------------------
# VTT cross-reference
# ---------------------------------------------------------------------------

def build_speaker_map(
    words: list[dict], vtt_entries: list[dict]
) -> dict[int, str]:
    """Map Deepgram speaker numbers to VTT speaker names."""
    if not vtt_entries or not words:
        return {}

    name_tallies: dict[str, dict[int, int]] = {}

    for entry in vtt_entries:
        vtt_start = entry["start"] - 1.0
        vtt_end = entry["end"] + 1.0
        name = entry["speaker"]

        if name not in name_tallies:
            name_tallies[name] = {}

        for w in words:
            if w["start"] >= vtt_start and w["start"] <= vtt_end:
                spk = w["speaker"]
                name_tallies[name][spk] = name_tallies[name].get(spk, 0) + 1

    candidates = []
    for name, tallies in name_tallies.items():
        total = sum(tallies.values())
        if total < 20:
            continue
        dominant_spk = max(tallies, key=tallies.get)
        dominant_count = tallies[dominant_spk]
        pct = dominant_count / total
        if pct > 0.70:
            candidates.append(
                {
                    "name": name,
                    "speaker": dominant_spk,
                    "count": dominant_count,
                    "total": total,
                    "pct": pct,
                }
            )

    speaker_map: dict[int, str] = {}
    candidates.sort(key=lambda c: c["pct"], reverse=True)

    for c in candidates:
        spk = c["speaker"]
        if spk not in speaker_map:
            speaker_map[spk] = c["name"]

    return speaker_map


# ---------------------------------------------------------------------------
# Formatting helpers
# ---------------------------------------------------------------------------

def fmt_time(seconds: float) -> str:
    """Format seconds as M:SS."""
    total_secs = int(seconds)
    m = total_secs // 60
    s = total_secs % 60
    return f"{m}:{s:02d}"


def speaker_label(
    speaker_num: int, speaker_map: dict[int, str]
) -> str:
    """Return a display label for a speaker."""
    if speaker_num in speaker_map:
        return speaker_map[speaker_num]
    return f"Speaker {speaker_num} (in-room)"


def is_flagged(segment: dict, threshold: float) -> bool:
    """Check if a segment should be flagged for low confidence."""
    return segment["avg_confidence"] < threshold or segment["has_zero_conf"]


# ---------------------------------------------------------------------------
# Output generation
# ---------------------------------------------------------------------------

def compute_speaker_stats(
    words: list[dict], speaker_map: dict[int, str], vtt_entries: list[dict]
) -> list[dict]:
    """Compute per-speaker statistics for the confidence report."""
    speaker_word_counts: dict[int, int] = {}
    for w in words:
        spk = w["speaker"]
        speaker_word_counts[spk] = speaker_word_counts.get(spk, 0) + 1

    name_tallies: dict[str, dict[int, int]] = {}
    for entry in vtt_entries:
        vtt_start = entry["start"] - 1.0
        vtt_end = entry["end"] + 1.0
        name = entry["speaker"]
        if name not in name_tallies:
            name_tallies[name] = {}
        for w in words:
            if w["start"] >= vtt_start and w["start"] <= vtt_end:
                spk = w["speaker"]
                name_tallies[name][spk] = name_tallies[name].get(spk, 0) + 1

    rows = []
    all_speakers = sorted(speaker_word_counts.keys())

    for spk in all_speakers:
        word_count = speaker_word_counts[spk]
        if spk in speaker_map:
            name = speaker_map[spk]
            for vname, tallies in name_tallies.items():
                if vname == name and spk in tallies:
                    total = sum(tallies.values())
                    pct = tallies[spk] / total * 100 if total else 0
                    rows.append(
                        {
                            "speaker": spk,
                            "name": name,
                            "match_pct": f"{pct:.0f}%",
                            "evidence": f"{word_count:,} words",
                        }
                    )
                    break
            else:
                rows.append(
                    {
                        "speaker": spk,
                        "name": name,
                        "match_pct": "—",
                        "evidence": f"{word_count:,} words",
                    }
                )
        else:
            rows.append(
                {
                    "speaker": spk,
                    "name": "(unidentified)",
                    "match_pct": "—",
                    "evidence": f"{word_count:,} words",
                }
            )

    return rows


def generate_transcript(
    segments: list[dict],
    speaker_map: dict[int, str],
    title: str,
    duration_minutes: float,
    total_speakers: int,
    identified_count: int,
    threshold: float,
) -> str:
    """Generate the deepgram-transcript.md content."""
    lines = []
    lines.append(f"# Transcript — {title}")
    lines.append("")

    vtt_note = f"{identified_count} identified via VTT" if identified_count else "none identified via VTT"
    lines.append(
        f"**Duration:** {duration_minutes:.0f} minutes | "
        f"**Speakers:** {total_speakers} detected ({vtt_note})"
    )
    lines.append("")
    lines.append("---")

    for seg in segments:
        lines.append("")
        label = speaker_label(seg["speaker"], speaker_map)
        time_str = fmt_time(seg["start"])
        conf_tag = " [LOW CONFIDENCE]" if is_flagged(seg, threshold) else ""

        lines.append(f"**{label}** [{time_str}]{conf_tag}:")
        lines.append("")
        lines.append(seg["text"])
        lines.append("")
        lines.append("---")

    return "\n".join(lines) + "\n"


def generate_report(
    segments: list[dict],
    words: list[dict],
    speaker_map: dict[int, str],
    speaker_stats: list[dict],
    total_speakers: int,
    identified_count: int,
    threshold: float,
) -> str:
    """Generate the speaker-confidence-report.md content."""
    lines = []
    lines.append("# Speaker Confidence Report")
    lines.append("")

    lines.append("## Speaker Map")
    lines.append("")
    lines.append("| Deepgram # | Resolved Name | Match % | Evidence |")
    lines.append("|---|---|---|---|")
    for row in speaker_stats:
        lines.append(
            f"| Speaker {row['speaker']} | {row['name']} "
            f"| {row['match_pct']} | {row['evidence']} |"
        )
    lines.append("")

    lines.append("## Overall Statistics")
    lines.append("")

    total_words = len(words)
    total_segments = len(segments)
    flagged = [s for s in segments if is_flagged(s, threshold)]
    flagged_count = len(flagged)
    flagged_pct = (flagged_count / total_segments * 100) if total_segments else 0

    lines.append(f"- Total words: {total_words:,}")
    lines.append(f"- Total segments: {total_segments:,}")
    lines.append(
        f"- Low-confidence segments (< {threshold:.2f}): "
        f"{flagged_count} ({flagged_pct:.0f}%)"
    )
    lines.append(
        f"- Speakers identified via VTT: {identified_count} of {total_speakers}"
    )
    lines.append("")

    lines.append("## Flagged Passages")
    lines.append("")
    if flagged:
        lines.append("Review these against the video before publishing.")
        lines.append("")
        lines.append("| # | Time | Speaker | Avg Conf | Text (first 80 chars) |")
        lines.append("|---|---|---|---|---|")
        for i, seg in enumerate(flagged, 1):
            label = speaker_label(seg["speaker"], speaker_map)
            time_str = fmt_time(seg["start"])
            text_preview = seg["text"][:80]
            if len(seg["text"]) > 80:
                text_preview += "..."
            lines.append(
                f"| {i} | {time_str} | {label} "
                f"| {seg['avg_confidence']:.2f} | {text_preview} |"
            )
    else:
        lines.append("No passages flagged. All segments meet the confidence threshold.")
    lines.append("")

    return "\n".join(lines) + "\n"


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="Analyze Deepgram word-level JSON for speaker-labeled transcripts."
    )
    parser.add_argument(
        "directory",
        help="Directory containing deepgram.json (absolute path)",
    )
    parser.add_argument(
        "--threshold",
        type=float,
        default=0.5,
        help="Speaker confidence threshold for flagging (default: 0.5)",
    )
    args = parser.parse_args()

    target_dir = Path(args.directory).resolve()

    if not target_dir.is_dir():
        print(f"Error: directory not found: {target_dir}", file=sys.stderr)
        sys.exit(1)

    # --- Load Deepgram JSON ---
    deepgram_path = target_dir / "deepgram.json"
    if not deepgram_path.exists():
        print(f"Error: deepgram.json not found in {target_dir}", file=sys.stderr)
        sys.exit(1)

    with open(deepgram_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    words = data["results"]["channels"][0]["alternatives"][0]["words"]

    if not words:
        print("Warning: no words found in Deepgram data.", file=sys.stderr)
        (target_dir / "deepgram-transcript.md").write_text(
            "# Transcript\n\nNo words found in Deepgram data.\n"
        )
        (target_dir / "speaker-confidence-report.md").write_text(
            "# Speaker Confidence Report\n\nNo words found in Deepgram data.\n"
        )
        print("Done (empty — no words in Deepgram data).")
        return

    # --- Build segments ---
    segments = build_segments(words)
    segments = merge_consecutive(segments, gap=2.0)

    # --- VTT cross-reference ---
    vtt_files = list(target_dir.glob("*.vtt"))
    vtt_entries = []
    speaker_map: dict[int, str] = {}

    if vtt_files:
        vtt_path = vtt_files[0]
        vtt_entries = parse_vtt(vtt_path)
        speaker_map = build_speaker_map(words, vtt_entries)
        print(f"VTT: {vtt_path.name} ({len(vtt_entries)} named entries)")
    else:
        print("No VTT file found — skipping speaker name cross-reference.")

    # --- Compute stats ---
    all_speakers = sorted(set(w["speaker"] for w in words))
    total_speakers = len(all_speakers)
    identified_count = len(speaker_map)

    duration_seconds = words[-1]["end"] - words[0]["start"]
    duration_minutes = duration_seconds / 60.0

    # Use directory name as title
    title = target_dir.name

    speaker_stats = compute_speaker_stats(words, speaker_map, vtt_entries)

    # --- Generate transcript ---
    transcript = generate_transcript(
        segments=segments,
        speaker_map=speaker_map,
        title=title,
        duration_minutes=duration_minutes,
        total_speakers=total_speakers,
        identified_count=identified_count,
        threshold=args.threshold,
    )
    transcript_path = target_dir / "deepgram-transcript.md"
    transcript_path.write_text(transcript, encoding="utf-8")

    # --- Generate confidence report ---
    report = generate_report(
        segments=segments,
        words=words,
        speaker_map=speaker_map,
        speaker_stats=speaker_stats,
        total_speakers=total_speakers,
        identified_count=identified_count,
        threshold=args.threshold,
    )
    report_path = target_dir / "speaker-confidence-report.md"
    report_path.write_text(report, encoding="utf-8")

    # --- Summary ---
    flagged_count = sum(1 for s in segments if is_flagged(s, args.threshold))

    print()
    print(f"Title:      {title}")
    print(f"Duration:   {duration_minutes:.0f} minutes")
    print(f"Words:      {len(words):,}")
    print(f"Segments:   {len(segments):,}")
    print(f"Speakers:   {total_speakers} detected, {identified_count} identified via VTT")
    if speaker_map:
        for spk, name in sorted(speaker_map.items()):
            print(f"            Speaker {spk} → {name}")
    print(f"Flagged:    {flagged_count} segments below {args.threshold} threshold")
    print()
    print(f"Written: {transcript_path}")
    print(f"Written: {report_path}")


if __name__ == "__main__":
    main()
