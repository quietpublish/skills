#!/usr/bin/env python3
"""Transcribe a meeting recording using Deepgram's Nova-3 model.

Usage: python3 transcribe.py <directory>
Example: python3 transcribe.py /path/to/meeting-folder

Reads DEEPGRAM_API_KEY from:
  1. Environment variable
  2. .env.local in the target directory
  3. .env.local in the current working directory
  4. ~/.config/deepgram/.env

If only an .mp4 exists in the directory, extracts audio to .mp3 first.
Saves the full Deepgram response as deepgram.json, then auto-runs analyze.
"""

import os
import subprocess
import sys
import time
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent


def load_api_key(target_dir: Path):
    """Load DEEPGRAM_API_KEY from env var or .env files."""
    # 1. Environment variable
    key = os.environ.get("DEEPGRAM_API_KEY")
    if key:
        return key

    # 2. Search for .env.local files
    search_paths = [
        target_dir / ".env.local",
        Path.cwd() / ".env.local",
        Path.home() / ".config" / "deepgram" / ".env",
    ]

    for env_file in search_paths:
        if env_file.exists():
            for line in env_file.read_text().splitlines():
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                if line.startswith("DEEPGRAM_API_KEY="):
                    value = line.split("=", 1)[1].strip()
                    if len(value) >= 2 and value[0] in ('"', "'") and value[-1] == value[0]:
                        value = value[1:-1]
                    if value:
                        return value

    print("Error: DEEPGRAM_API_KEY not found.")
    print("Set it as an environment variable, or create .env.local with:")
    print("  DEEPGRAM_API_KEY=your_key_here")
    print(f"Searched: {', '.join(str(p) for p in search_paths)}")
    print("\nNo key? Transcribe offline instead:  python3 transcribe.py --local <directory>")
    sys.exit(1)


def find_audio(target_dir):
    """Find or extract an mp3 from the target directory."""
    mp3_files = list(target_dir.glob("*.mp3"))
    if mp3_files:
        print(f"Found audio: {mp3_files[0].name}")
        return mp3_files[0]

    mp4_files = list(target_dir.glob("*.mp4"))
    if not mp4_files:
        print(f"Error: no .mp3 or .mp4 found in {target_dir}")
        sys.exit(1)

    mp4_path = mp4_files[0]
    mp3_path = mp4_path.with_suffix(".mp3")
    print(f"No mp3 found. Extracting audio from {mp4_path.name}...")

    result = subprocess.run(
        [
            "ffmpeg", "-i", str(mp4_path),
            "-vn", "-codec:a", "libmp3lame", "-q:a", "4",
            "-y", str(mp3_path),
        ],
        capture_output=True,
        text=True,
    )

    if result.returncode != 0:
        print(f"Error: ffmpeg failed:\n{result.stderr}")
        sys.exit(1)

    size_mb = mp3_path.stat().st_size / (1024 * 1024)
    print(f"Extracted: {mp3_path.name} ({size_mb:.1f} MB)")
    return mp3_path


def transcribe(api_key, audio_path):
    """Send audio to Deepgram and return the response."""
    try:
        from deepgram import DeepgramClient
        from deepgram.core.api_error import ApiError
    except ImportError:
        print("Error: deepgram-sdk not installed.")
        print("Install with: pip install deepgram-sdk")
        sys.exit(1)

    file_size_mb = audio_path.stat().st_size / (1024 * 1024)
    print(f"\nSending {audio_path.name} ({file_size_mb:.1f} MB) to Deepgram Nova-3...")
    print("This may take 2-5 minutes for a 50-minute recording.")

    client = DeepgramClient(api_key=api_key)
    start_time = time.time()

    try:
        with open(audio_path, "rb") as f:
            response = client.listen.v1.media.transcribe_file(
                request=f.read(),
                model="nova-3",
                smart_format=True,
                diarize=True,
                utterances=True,
                paragraphs=True,
            )
    except ApiError as e:
        print(f"\nError: Deepgram API error: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\nError: transcription failed: {e}")
        sys.exit(1)

    elapsed = time.time() - start_time
    print(f"Transcription complete in {elapsed:.0f}s.")
    return response


def save_response(response, output_path):
    """Save Deepgram response as JSON."""
    output_path.write_text(response.model_dump_json(indent=2))
    size_mb = output_path.stat().st_size / (1024 * 1024)
    print(f"\nSaved: {output_path} ({size_mb:.1f} MB)")


def print_summary(response):
    """Print a summary of the transcription results."""
    metadata = response.metadata
    results = response.results

    duration_secs = metadata.duration
    minutes = int(duration_secs // 60)
    seconds = int(duration_secs % 60)

    word_count = 0
    speaker_set = set()
    for channel in results.channels:
        for alt in channel.alternatives:
            if alt.words:
                for word in alt.words:
                    word_count += 1
                    if word.speaker is not None:
                        speaker_set.add(word.speaker)

    print(f"\n--- Summary ---")
    print(f"  Duration:  {minutes}m {seconds}s")
    print(f"  Words:     {word_count:,}")
    print(f"  Speakers:  {len(speaker_set)}")


def run_analyze(target_dir):
    """Auto-run the analyze script."""
    analyze_script = SCRIPT_DIR / "analyze-speakers.py"
    if not analyze_script.exists():
        print(f"\nNote: analyze script not found at {analyze_script}, skipping.")
        return

    print(f"\nRunning analyze script...")
    result = subprocess.run(
        ["/usr/bin/python3", str(analyze_script), str(target_dir)],
    )
    if result.returncode != 0:
        print("Warning: analyze script exited with errors.")


# ---------------------------------------------------------------------------
# Local transcription (offline fallback via OpenAI Whisper — no API, no cloud)
# ---------------------------------------------------------------------------

def _fmt_ts(seconds: float) -> str:
    total = int(seconds)
    return f"{total // 60}:{total % 60:02d}"


def transcribe_local(audio_path, model_size: str):
    """Transcribe locally with Whisper. No diarization (single stream)."""
    try:
        import whisper
    except ImportError:
        print("Error: openai-whisper is not installed (needed for --local).")
        print("Install with: pip install openai-whisper")
        print("Or use Deepgram instead by setting DEEPGRAM_API_KEY.")
        sys.exit(1)

    file_size_mb = audio_path.stat().st_size / (1024 * 1024)
    print(f"\nTranscribing {audio_path.name} ({file_size_mb:.1f} MB) locally with "
          f"Whisper '{model_size}'.")
    print("This runs entirely offline and can take several minutes on CPU.")

    start_time = time.time()
    model = whisper.load_model(model_size)
    result = model.transcribe(str(audio_path), verbose=False)
    print(f"Local transcription complete in {time.time() - start_time:.0f}s.")
    return result


def write_local_outputs(result, target_dir, audio_name: str):
    """Write a transcript + stub confidence report so the rest of the pipeline
    flows. Local mode has no speaker diarization or confidence data."""
    segments = result.get("segments", []) or []

    tlines = [
        f"# Transcript — {target_dir.name}",
        "",
        f"**Source:** {audio_name} | **Transcription:** local Whisper "
        "(offline; **no speaker diarization**)",
        "",
        "> Local transcription produces a single undifferentiated stream — there is **no**",
        "> speaker attribution or confidence scoring. Assign speakers manually from context,",
        "> or set `DEEPGRAM_API_KEY` and re-run for diarized output.",
        "",
        "---",
        "",
    ]
    for seg in segments:
        tlines.append(f"**[{_fmt_ts(seg.get('start', 0.0))}]**")
        tlines.append("")
        tlines.append((seg.get("text") or "").strip())
        tlines.append("")
    transcript_path = target_dir / "deepgram-transcript.md"
    transcript_path.write_text("\n".join(tlines) + "\n", encoding="utf-8")

    rlines = [
        "# Speaker Confidence Report",
        "",
        "## Speaker Map",
        "",
        "Local Whisper transcription — **no diarization was performed**; speakers were "
        "not separated.",
        "",
        "## Notes",
        "",
        "- No confidence data (local, offline transcription).",
        "- All text is a single stream — attribute speakers manually before publishing.",
        f"- Segments: {len(segments):,}",
        "",
    ]
    (target_dir / "speaker-confidence-report.md").write_text(
        "\n".join(rlines) + "\n", encoding="utf-8"
    )

    print(f"\nWritten: {transcript_path}")
    print(f"Written: {target_dir / 'speaker-confidence-report.md'}")
    print(f"Segments: {len(segments):,}")


def run_local(target_dir, model_size: str):
    audio_path = find_audio(target_dir)
    result = transcribe_local(audio_path, model_size)
    write_local_outputs(result, target_dir, audio_path.name)
    print("\nDone (local transcription — no diarization).")


USAGE = ("Usage: python3 transcribe.py [--local [--model SIZE]] <directory>\n"
         "  Default: transcribe via Deepgram (needs DEEPGRAM_API_KEY).\n"
         "  --local: transcribe offline with Whisper (no API; no diarization).\n"
         "  --model: Whisper size (default: base). tiny|base|small|medium|large")


def main():
    args = sys.argv[1:]
    use_local = False
    model_size = "base"
    positional = []
    i = 0
    while i < len(args):
        a = args[i]
        if a in ("--local", "--offline"):
            use_local = True
        elif a == "--model":
            i += 1
            if i >= len(args):
                print("Error: --model requires a value (tiny|base|small|medium|large).")
                sys.exit(1)
            model_size = args[i]
        elif a in ("-h", "--help"):
            print(USAGE)
            sys.exit(0)
        else:
            positional.append(a)
        i += 1

    if len(positional) != 1:
        print(USAGE)
        sys.exit(1)

    target_dir = Path(positional[0]).resolve()
    if not target_dir.is_dir():
        print(f"Error: directory not found: {target_dir}")
        sys.exit(1)

    if use_local:
        run_local(target_dir, model_size)
        return

    output_path = target_dir / "deepgram.json"

    # Check for existing output
    if output_path.exists():
        if sys.stdin.isatty():
            answer = input(f"{output_path.name} already exists. Overwrite? [y/N] ")
            if answer.lower() not in ("y", "yes"):
                print("Aborted.")
                sys.exit(0)
        else:
            print(f"{output_path.name} already exists, overwriting.")

    api_key = load_api_key(target_dir)
    audio_path = find_audio(target_dir)
    response = transcribe(api_key, audio_path)
    save_response(response, output_path)
    print_summary(response)
    run_analyze(target_dir)

    print("\nDone.")


if __name__ == "__main__":
    main()
