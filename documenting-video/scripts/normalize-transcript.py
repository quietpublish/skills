#!/usr/bin/env python3
"""
normalize-transcript.py

Parses multiple transcript formats into a unified JSON format.

Supported formats:
  - YouTube pb3 JSON (.json with wireMagic: "pb3" or events[].segs)
  - Whisper JSON output (segments[].start/end/text)
  - SRT subtitle files (.srt)
  - VTT subtitle files (.vtt)
  - Plain text with [HH:MM:SS] or [MM:SS] timestamp prefixes

Output format:
  [{ "start": 0.0, "end": 5.0, "text": "..." }, ...]

Usage:
  python3 normalize-transcript.py <input_file> <output_file>
  python3 normalize-transcript.py transcript.srt output.json
"""

import json
import re
import sys
from pathlib import Path


def parse_srt_timestamp(ts: str) -> float:
    """Convert SRT timestamp (HH:MM:SS,mmm) to seconds."""
    ts = ts.strip().replace(",", ".")
    parts = ts.split(":")
    if len(parts) == 3:
        return float(parts[0]) * 3600 + float(parts[1]) * 60 + float(parts[2])
    if len(parts) == 2:
        return float(parts[0]) * 60 + float(parts[1])
    return float(parts[0])


def parse_vtt_timestamp(ts: str) -> float:
    """Convert VTT timestamp (HH:MM:SS.mmm or MM:SS.mmm) to seconds."""
    ts = ts.strip()
    parts = ts.split(":")
    if len(parts) == 3:
        return float(parts[0]) * 3600 + float(parts[1]) * 60 + float(parts[2])
    if len(parts) == 2:
        return float(parts[0]) * 60 + float(parts[1])
    return float(parts[0])


def strip_html_tags(text: str) -> str:
    """Remove HTML/VTT tags from text."""
    return re.sub(r"<[^>]+>", "", text)


def parse_srt(content: str) -> list[dict]:
    """Parse SRT subtitle format."""
    segments = []
    blocks = re.split(r"\n\s*\n", content.strip())

    for block in blocks:
        lines = block.strip().split("\n")
        if len(lines) < 2:
            continue

        # Find the timestamp line (contains " --> ")
        ts_line = None
        text_start = 0
        for i, line in enumerate(lines):
            if " --> " in line:
                ts_line = line
                text_start = i + 1
                break

        if not ts_line:
            continue

        start_str, end_str = ts_line.split(" --> ")
        # Remove position metadata after timestamp
        end_str = re.split(r"\s+", end_str.strip())[0]

        text = " ".join(lines[text_start:]).strip()
        text = strip_html_tags(text)
        text = re.sub(r"\s+", " ", text).strip()

        if text:
            segments.append({
                "start": round(parse_srt_timestamp(start_str), 3),
                "end": round(parse_srt_timestamp(end_str), 3),
                "text": text,
            })

    return segments


def parse_vtt(content: str) -> list[dict]:
    """Parse WebVTT subtitle format."""
    segments = []

    # Remove WEBVTT header and metadata
    content = re.sub(r"^WEBVTT.*?\n\n", "", content, flags=re.DOTALL)
    # Remove NOTE blocks
    content = re.sub(r"NOTE\s.*?\n\n", "", content, flags=re.DOTALL)
    # Remove STYLE blocks
    content = re.sub(r"STYLE\s.*?\n\n", "", content, flags=re.DOTALL)

    blocks = re.split(r"\n\s*\n", content.strip())

    for block in blocks:
        lines = block.strip().split("\n")
        if len(lines) < 2:
            continue

        # Find the timestamp line
        ts_line = None
        text_start = 0
        for i, line in enumerate(lines):
            if " --> " in line:
                ts_line = line
                text_start = i + 1
                break

        if not ts_line:
            continue

        parts = ts_line.split(" --> ")
        start_str = parts[0].strip()
        end_str = re.split(r"\s+", parts[1].strip())[0]

        text = " ".join(lines[text_start:]).strip()
        text = strip_html_tags(text)
        text = re.sub(r"\s+", " ", text).strip()

        if text:
            segments.append({
                "start": round(parse_vtt_timestamp(start_str), 3),
                "end": round(parse_vtt_timestamp(end_str), 3),
                "text": text,
            })

    return segments


def parse_youtube_json(data: dict) -> list[dict]:
    """Parse YouTube JSON3 / pb3 caption format."""
    segments = []

    # Format 1: wireMagic pb3 with events[].segs
    if "wireMagic" in data or "events" in data:
        events = data.get("events", [])
        for event in events:
            start_ms = event.get("tStartMs", 0)
            duration_ms = event.get("dDurationMs", 0)
            segs = event.get("segs", [])

            text = "".join(seg.get("utf8", "") for seg in segs).strip()
            text = text.replace("\n", " ")

            if text and text != "\n":
                segments.append({
                    "start": round(start_ms / 1000.0, 3),
                    "end": round((start_ms + duration_ms) / 1000.0, 3),
                    "text": text,
                })

    # Format 2: Array of objects with start/dur/text (yt-dlp json3 output)
    elif isinstance(data, list):
        for item in data:
            if "start" in item and "text" in item:
                segments.append({
                    "start": round(float(item["start"]), 3),
                    "end": round(float(item.get("end", item["start"] + item.get("dur", 0))), 3),
                    "text": item["text"].strip(),
                })

    return segments


def parse_whisper_json(data: dict) -> list[dict]:
    """Parse Whisper JSON output format."""
    segments = []

    whisper_segments = data.get("segments", [])
    for seg in whisper_segments:
        text = seg.get("text", "").strip()
        if text:
            segments.append({
                "start": round(float(seg["start"]), 3),
                "end": round(float(seg["end"]), 3),
                "text": text,
            })

    return segments


def parse_timestamped_text(content: str) -> list[dict]:
    """Parse plain text with [HH:MM:SS] or [MM:SS] timestamp prefixes."""
    segments = []
    # Match patterns like [0:00], [00:00], [0:00:00], [00:00:00], (0:00), etc.
    pattern = r"[\[\(](\d{1,2}(?::\d{2}){1,2})[\]\)]"
    lines = content.strip().split("\n")

    timestamps = []
    texts = []

    for line in lines:
        match = re.match(r"\s*" + pattern + r"\s*(.*)", line)
        if match:
            ts_str = match.group(1)
            text = match.group(2).strip()
            parts = ts_str.split(":")
            if len(parts) == 3:
                seconds = int(parts[0]) * 3600 + int(parts[1]) * 60 + float(parts[2])
            else:
                seconds = int(parts[0]) * 60 + float(parts[1])
            timestamps.append(seconds)
            texts.append(text)
        elif texts:
            # Continuation line -- append to previous
            texts[-1] += " " + line.strip()

    for i, (ts, text) in enumerate(zip(timestamps, texts)):
        end = timestamps[i + 1] if i + 1 < len(timestamps) else ts + 5.0
        text = re.sub(r"\s+", " ", text).strip()
        if text:
            segments.append({
                "start": round(ts, 3),
                "end": round(end, 3),
                "text": text,
            })

    return segments


def detect_and_parse(file_path: str) -> list[dict]:
    """Detect format and parse transcript file."""
    path = Path(file_path)
    content = path.read_text(encoding="utf-8")
    ext = path.suffix.lower()

    # SRT
    if ext == ".srt":
        return parse_srt(content)

    # VTT
    if ext == ".vtt" or content.strip().startswith("WEBVTT"):
        return parse_vtt(content)

    # JSON formats
    if ext in (".json", ".json3"):
        data = json.loads(content)

        # Already in our output format
        if isinstance(data, list) and data and all(
            "start" in d and "end" in d and "text" in d for d in data[:3]
        ):
            return data

        # Whisper output
        if isinstance(data, dict) and "segments" in data:
            return parse_whisper_json(data)

        # YouTube JSON3
        if isinstance(data, dict) and ("wireMagic" in data or "events" in data):
            return parse_youtube_json(data)

        # Array of objects with start/text
        if isinstance(data, list) and data and "start" in data[0]:
            return parse_youtube_json(data)

    # Plain text with timestamps
    if ext in (".txt", "") or re.search(r"[\[\(]\d{1,2}:\d{2}", content[:200]):
        result = parse_timestamped_text(content)
        if result:
            return result

    raise ValueError(
        f"Could not detect transcript format for {file_path}. "
        f"Supported: .srt, .vtt, .json (YouTube/Whisper), .txt (timestamped)"
    )


def merge_short_segments(segments: list[dict], min_duration: float = 1.0) -> list[dict]:
    """Merge very short segments into their neighbors."""
    if not segments:
        return segments

    merged = [segments[0]]
    for seg in segments[1:]:
        prev = merged[-1]
        # Merge if previous segment is very short and contiguous
        if prev["end"] >= seg["start"] - 0.1 and (seg["start"] - prev["start"]) < min_duration:
            prev["end"] = seg["end"]
            prev["text"] = prev["text"] + " " + seg["text"]
        else:
            merged.append(seg)

    # Clean up merged text
    for seg in merged:
        seg["text"] = re.sub(r"\s+", " ", seg["text"]).strip()

    return merged


def main():
    if len(sys.argv) < 3:
        print(f"Usage: {sys.argv[0]} <input_file> <output_file>")
        print(f"       {sys.argv[0]} transcript.srt output.json")
        sys.exit(1)

    input_file = sys.argv[1]
    output_file = sys.argv[2]

    if not Path(input_file).exists():
        print(f"Error: Input file not found: {input_file}")
        sys.exit(1)

    segments = detect_and_parse(input_file)
    segments = merge_short_segments(segments)

    # Summary
    if segments:
        duration = segments[-1]["end"]
        print(f"Parsed {len(segments)} segments")
        print(f"Duration: {duration:.1f}s ({duration/60:.1f} min)")
        print(f"First: [{segments[0]['start']:.1f}s] {segments[0]['text'][:60]}...")
        print(f"Last:  [{segments[-1]['start']:.1f}s] {segments[-1]['text'][:60]}...")
    else:
        print("Warning: No segments parsed from input file")

    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(segments, f, indent=2, ensure_ascii=False)

    print(f"Output written to: {output_file}")


if __name__ == "__main__":
    main()
