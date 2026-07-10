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


def main():
    if len(sys.argv) != 2:
        print("Usage: python3 transcribe.py <directory>")
        print("Example: python3 transcribe.py /path/to/meeting-folder")
        sys.exit(1)

    target_dir = Path(sys.argv[1]).resolve()
    if not target_dir.is_dir():
        print(f"Error: directory not found: {target_dir}")
        sys.exit(1)

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
