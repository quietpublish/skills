# documenting-video

Transform video recordings (knowledge transfers, demos, meetings) into comprehensive markdown documentation with inline screenshots.

## Invocation

User says: `/documenting-video`, "document this video", "turn this recording into docs", "create documentation from this video"

## Inputs

The user provides one or more of:
- A video URL (YouTube, Loom, Vimeo, Teams recording, or any web-hosted video)
- A local video file path
- An existing transcript file (`.srt`, `.vtt`, `.json`, `.txt`)
- A transcript + video combination (skip transcription, keep video for screenshots)

## Workflow

### Phase 1: Input Resolution & Setup

#### Step 1 - Determine Input Type

Ask the user (if not already provided):
1. What is the video source? (URL, local file, or transcript)
2. What is this video about? (brief context for better section titles)
3. Who are the participants? (for attribution)
4. Where should the output go? (directory path, default: `./docs/video-docs/{slugified-title}`)

Classify the input:
- **Video URL** → will download with `yt-dlp`
- **Local video file** → verify exists with `ffprobe`
- **Existing transcript** (`.srt`, `.vtt`, `.json`, `.txt`) → normalize only
- **Transcript + video** → skip transcription, use video for screenshots

#### Step 2 - Install Dependencies

Check and install required tools:

```bash
# Check for yt-dlp
which yt-dlp || pip3 install yt-dlp

# Check for whisper (only if transcription needed)
python3 -c "import whisper" 2>/dev/null || pip3 install openai-whisper

# ffmpeg/ffprobe are required -- prompt user to install via brew if missing
which ffmpeg || echo "ERROR: ffmpeg is required. Install with: brew install ffmpeg"
which ffprobe || echo "ERROR: ffprobe is required. Install with: brew install ffmpeg"
```

#### Step 3 - Acquire Transcript

Choose the transcription path based on input:

**Path A - YouTube/Vimeo with captions available:**
```bash
# Try to get existing captions first (free, fast, accurate)
yt-dlp --write-auto-sub --sub-lang en --sub-format json3 --skip-download -o "{output_dir}/transcript" "{URL}"
```
This produces a file like `transcript.en.json3`. Note the `.json3` extension -- the normalize
script handles this. Normalize with `normalize-transcript.py`.

> **Optimization:** If you'll also need the video for screenshots, start the video download
> as a **background task** in parallel with caption download and transcript normalization.
> The video download is the slowest step and can run concurrently:
> ```bash
> # Background: download video (slow)
> yt-dlp -f "bestvideo[height<=1080]+bestaudio/best[height<=1080]" --merge-output-format mp4 -o "{output_dir}/video.mp4" "{URL}" &
> # Foreground: download captions (fast), normalize, analyze transcript
> yt-dlp --write-auto-sub --sub-lang en --sub-format json3 --skip-download -o "{output_dir}/transcript" "{URL}"
> ```

**Path B - No captions / local file / captions unavailable:**
```bash
# Extract audio
ffmpeg -i "{video_path}" -vn -acodec pcm_s16le -ar 16000 -ac 1 "{output_dir}/audio.wav"

# Transcribe with whisper -- model selection by duration:
#   < 30 min  → medium (best quality)
#   30-90 min → small (good balance)
#   > 90 min  → base (fastest, acceptable quality)
python3 -c "
import whisper
model = whisper.load_model('{model_size}')
result = model.transcribe('{output_dir}/audio.wav', verbose=False)
import json
with open('{output_dir}/transcript-raw.json', 'w') as f:
    json.dump(result, f, indent=2)
"
```

**Path C - Existing transcript provided:**
```bash
python3 ~/.claude/skills/documenting-video/scripts/normalize-transcript.py "{transcript_path}" "{output_dir}/transcript-raw.json"
```

After any path, verify the transcript was generated:
```bash
python3 -c "
import json
with open('{output_dir}/transcript-raw.json') as f:
    data = json.load(f)
print(f'Transcript loaded: {len(data)} segments')
print(f'Duration: {data[-1][\"end\"]:.1f}s ({data[-1][\"end\"]/60:.1f} min)')
print(f'First line: {data[0][\"text\"][:80]}...')
"
```

### Phase 2: Intelligent Moment Detection

#### Step 4 - Analyze Transcript for Screenshot-Worthy Moments

Read the normalized transcript JSON (`transcript-raw.json`) and analyze it to identify moments worth capturing as screenshots.

**Detection patterns -- look for these signals in the transcript text:**

| Category | Transcript Signals | Priority |
|---|---|---|
| Visual Reference | "as you can see", "if you look at", "let me show you", "on the screen" | Critical |
| Demonstration | "let me demonstrate", "I'll walk through", "watch what happens", "let me show" | Critical |
| Diagram/Architecture | "this diagram shows", "the architecture", "the flow is", "this chart" | Critical |
| Topic Change | "moving on to", "next thing is", "so now let's", "the next topic" | High |
| Code/Config Shown | "this code", "the configuration", "in this file", "this function", "this class" | High |
| UI Navigation | "go to", "navigate to", "click on", "open the", "in the settings" | High |
| Error/Issue | "this error", "you'll see this warning", "the problem is", "this bug" | High |
| Key Concept | "important thing here is", "what you need to know", "the key takeaway" | Medium |

**Density control rules:**
- Minimum 15-second gap between any two screenshots
- Target density: ~1 screenshot per 2-3 minutes for mixed content
- Screen-share heavy content → ~1 screenshot per 1.5-2 minutes (bias toward MORE)
- Talking-head content → ~1 screenshot per 3-4 minutes (bias toward FEWER)
- Maximum cap: 50 screenshots (even for very long videos)
- If video duration is unknown or no video is available, skip screenshot capture entirely

**Output format** -- produce a JSON array:
```json
[
  {
    "timestamp": 45.2,
    "timestamp_display": "0:45",
    "category": "visual_reference",
    "context": "Speaker points to architecture diagram on screen",
    "suggested_caption": "System architecture overview showing microservices layout",
    "priority": "critical"
  }
]
```

Save this to `{output_dir}/moments.json`.

### Phase 3: Screenshot Capture via Chrome DevTools MCP

> **Prerequisite:** Chrome DevTools MCP server must be connected and a browser must be open.
> **Skip this phase** if: no video URL/file is available, or the user opts out of screenshots.

> **CRITICAL LESSON (learned from production use):** Web-based video players (especially YouTube)
> crash after rapid repeated seeks. The player silently enters an error state and all subsequent
> screenshots capture "Something went wrong" screens instead of video frames. **Always prefer
> downloading the video and playing it locally via a simple HTML page.**

> **FAST PATH — local video + ffmpeg (PREFERRED when available):** If you have a local video file
> and `ffmpeg` is installed, skip the browser entirely and extract frames directly at each moment's
> timestamp. It's deterministic, faster, and immune to the player-crash issues above:
> ```bash
> ffmpeg -nostdin -loglevel error -ss <SECONDS> -i "<video>" -frames:v 1 -q:v 2 -y "<out>.png"
> ```
> Then `Read` each PNG to confirm it shows real content (not a transition/black frame); nudge the
> timestamp by ±0.5s and re-extract if a frame is blank. Use the browser method below **only** for
> web-hosted or DRM-protected video you can't download, or when you specifically need the player/page
> chrome captured in-frame.

#### Step 5 - Prepare Browser and Video Source (fallback: web-hosted/DRM video)

**5a. Download video for local playback (STRONGLY PREFERRED):**

For YouTube, Vimeo, Loom, and most web videos, download first to avoid player instability:
```bash
# Download video file (best quality up to 1080p)
yt-dlp -f "bestvideo[height<=1080]+bestaudio/best[height<=1080]" --merge-output-format mp4 -o "{output_dir}/video.mp4" "{URL}"
```

Then create a minimal HTML page for local playback:
```bash
cat > "{output_dir}/player.html" << 'PLAYER_EOF'
<!DOCTYPE html>
<html><body style="margin:0;background:#000;display:flex;align-items:center;justify-content:center;height:100vh">
<video id="v" src="video.mp4" preload="auto" style="max-width:100%;max-height:100vh"></video>
</body></html>
PLAYER_EOF
```

Start a local server **with range request support** and navigate to it:
```bash
python3 ~/.claude/skills/documenting-video/scripts/serve.py 8765 "{output_dir}" &
SERVER_PID=$!
```

> **CRITICAL:** Do NOT use `python3 -m http.server` -- it does not support range requests,
> which means the browser cannot seek within the video (`video.seekable` will be empty).
> The custom `serve.py` script handles `Range` headers and returns `206 Partial Content`
> responses, enabling full seeking.

Then `navigate_page` to `http://localhost:8765/player.html`

**5b. Fallback: Use web player directly (only if download fails):**

If `yt-dlp` fails (DRM, authentication, etc.), navigate to the URL directly.
Be aware that web players may crash after 4-6 rapid seeks. If this happens,
reload the page between captures (see Step 6c).

**5c. Set up the browser:**

1. Resize the page for consistent screenshots:
   - Use `resize_page` to set dimensions to **1920x1080**

2. Find the video element:
   - Use `take_snapshot` with `verbose: true` to get page elements -- the default snapshot
     often only shows `RootWebArea` on the minimal player.html page and won't reveal the
     `<video>` element UID needed for targeted screenshots
   - Use `evaluate_script` to locate the video element:
     ```javascript
     () => {
       const video = document.querySelector('video');
       if (!video) return { found: false };
       return {
         found: true,
         duration: video.duration,
         width: video.videoWidth,
         height: video.videoHeight,
         paused: video.paused,
         src: video.currentSrc?.substring(0, 100)
       };
     }
     ```
   - If no `<video>` element found, check for iframes and try platform-specific approaches (see `references/platform-selectors.md`)

3. Pause the video and dismiss any overlays:
   ```javascript
   () => {
     const video = document.querySelector('video');
     video.pause();
     // Try to dismiss cookie banners, play buttons, etc.
     document.querySelectorAll('[class*="overlay"], [class*="cookie"], [class*="consent"]').forEach(el => {
       if (el.offsetParent !== null) el.style.display = 'none';
     });
     return { paused: true };
   }
   ```

#### Step 6 - Screenshot Capture Loop

For each moment in `moments.json`, execute this sequence:

**6a. Seek to timestamp:**
```javascript
(TIMESTAMP) => {
  const video = document.querySelector('video');
  video.currentTime = TIMESTAMP;
  video.pause();
  return new Promise(resolve => {
    video.addEventListener('seeked', () => {
      if ('requestVideoFrameCallback' in video) {
        video.requestVideoFrameCallback(() => resolve({ success: true, time: video.currentTime }));
      } else {
        setTimeout(() => resolve({ success: true, time: video.currentTime }), 500);
      }
    }, { once: true });
    // Fallback timeout -- seeked event rarely fires in practice, even with local playback.
    // The 3s timeout IS the primary mechanism; seeked is just a bonus if it happens to work.
    setTimeout(() => resolve({ success: true, timeout: true, time: video.currentTime }), 3000);
  });
}
```

**6b. Player health check (CRITICAL -- do this BEFORE every capture):**

Web players (especially YouTube) silently crash after repeated seeks, showing error overlays
instead of video. The canvas-based blank detection does NOT catch these -- error screens have
text and icons that produce normal pixel variance.

```javascript
() => {
  const video = document.querySelector('video');
  // Check for error state on the video element itself
  const hasError = video.error !== null;
  const networkState = video.networkState; // 3 = NETWORK_NO_SOURCE
  const readyState = video.readyState;    // 0 = HAVE_NOTHING
  // Check for error overlay text in the page
  const pageText = document.body.innerText.toLowerCase();
  const hasErrorText = pageText.includes('something went wrong')
    || pageText.includes('error')
    || pageText.includes('unavailable')
    || pageText.includes('refresh or try again');
  return {
    healthy: !hasError && readyState >= 2 && !hasErrorText,
    error: video.error?.message || null,
    networkState,
    readyState,
    hasErrorText
  };
}
```

**If the player is unhealthy:**
1. **Local playback:** Reload the page (`navigate_page` type=reload), wait for load, re-seek
2. **Web player (YouTube etc.):** Reload the page, wait for video to load, skip any ads again, then re-seek
3. If still unhealthy after reload: note in output and skip remaining captures

**6c. Pacing -- add delay between seeks:**

> **CRITICAL:** Do NOT rapid-fire seeks. Wait at least 1-2 seconds between seek operations.
> YouTube's player crashes after ~5 rapid seeks. Local HTML5 video is more resilient but
> still benefits from pacing.

After each successful capture, wait 1 second before proceeding to the next moment.

**6d. Quality check -- detect blank/black frames:**
```javascript
() => {
  const video = document.querySelector('video');
  const canvas = document.createElement('canvas');
  canvas.width = video.videoWidth;
  canvas.height = video.videoHeight;
  const ctx = canvas.getContext('2d');
  ctx.drawImage(video, 0, 0);

  // Sample 3x3 grid of pixels
  const samples = [];
  for (let row = 0; row < 3; row++) {
    for (let col = 0; col < 3; col++) {
      const x = Math.floor((col + 0.5) * canvas.width / 3);
      const y = Math.floor((row + 0.5) * canvas.height / 3);
      const pixel = ctx.getImageData(x, y, 1, 1).data;
      samples.push({ r: pixel[0], g: pixel[1], b: pixel[2] });
    }
  }

  // Calculate variance across samples
  const avgR = samples.reduce((s, p) => s + p.r, 0) / 9;
  const avgG = samples.reduce((s, p) => s + p.g, 0) / 9;
  const avgB = samples.reduce((s, p) => s + p.b, 0) / 9;
  const variance = samples.reduce((s, p) =>
    s + (p.r - avgR) ** 2 + (p.g - avgG) ** 2 + (p.b - avgB) ** 2, 0) / 9;

  return {
    isBlank: variance < 50 && avgR < 30 && avgG < 30 && avgB < 30,
    isLowVariance: variance < 100,
    variance: Math.round(variance),
    avgColor: { r: Math.round(avgR), g: Math.round(avgG), b: Math.round(avgB) }
  };
}
```

Note: This canvas check catches black/blank frames but does NOT catch player error overlays.
That's why the health check in 6b is essential.

**6e. Retry logic for blank frames:**
- If `isBlank` or `isLowVariance`: wait 500ms, retry (up to 3 times)
- After 3 retries: nudge timestamp by +0.5s and try once more
- After all retries fail: skip this moment and note it in the output

**6f. Capture screenshot:**
- Use `take_screenshot` with `filePath` set to `{output_dir}/screenshots/{NN}-{timestamp}-{category}-{short-desc}.png`
- Try to target the `<video>` element UID first (cleaner capture without player chrome)
- Fall back to viewport screenshot if element targeting fails

**6g. Post-capture verification (IMPORTANT):**

After capturing each screenshot, read it back with the `Read` tool to visually confirm it
contains actual video content. If it shows an error screen, player chrome, or is otherwise
unusable:
1. Delete the bad screenshot
2. Reload the page if needed (health check from 6b)
3. Re-seek and re-capture
4. If still bad after 2 attempts, skip and note in output

**Filename convention:** `{NN}-{MMmSSs}-{category}-{slugified-description}.png`
- Example: `03-02m15s-demo-creating-new-branch.png`

#### Step 7 - Edge Case Handling

| Scenario | Detection | Recovery |
|---|---|---|
| **Player crash after rapid seeks** | Health check returns `hasErrorText: true` or `readyState: 0` | Reload page, re-seek. **Best prevention: download video and play locally (Step 5a)** |
| Auth-required video | `yt-dlp` fails with 403/login | Ask user to open & authenticate in browser, then use `list_pages` + `select_page` to find the page |
| iframe-embedded player | No `<video>` in top-level DOM | Check iframes; for YouTube embeds use postMessage API; fall back to keyboard controls (Space, arrows) |
| Very long video (>2hr) | Duration check from ffprobe | Reduce screenshot density; offer to split document by detected topic sections |
| No audio track | `ffprobe` shows no audio stream | Skip transcription; require user-provided transcript |
| Player controls overlay | Controls visible in screenshots | Wait 3s for auto-hide; target `<video>` element UID directly; use CSS to hide controls |
| DRM-protected video | Cannot seek or capture | Inform user; offer transcript-only documentation mode |
| Error screen captured as screenshot | Post-capture `Read` shows error overlay | Delete bad file, reload page, re-seek, re-capture |
| `seeked` event never fires | All seeks return `timeout: true` | Rely on 3s fallback timeout; consider switching to local playback |

After all screenshots are captured, clean up temporary files:
```bash
# Stop the local server
kill $SERVER_PID 2>/dev/null
# Or if PID was lost:
pkill -f "serve.py 8765" 2>/dev/null

# Remove temp files (keep only final outputs)
rm -f "{output_dir}/player.html"
rm -f "{output_dir}/video.mp4"
rm -f "{output_dir}/moments.json"
rm -f "{output_dir}/transcript.en.json3"  # raw YouTube caption file
rm -f "{output_dir}/audio.wav"            # whisper audio extraction
```

### Phase 4: Document Assembly

#### Step 8 - Create Output Structure

Ensure the output directory contains:
```
{output_dir}/
├── {document-name}.md          # Final comprehensive document
├── screenshots/                # All captured screenshots (from Phase 3)
├── transcript.md               # Full timestamped transcript (readable)
└── transcript-raw.json         # Raw normalized transcript data
```

Generate the readable `transcript.md` from `transcript-raw.json`.

> **IMPORTANT: YouTube caption deduplication.** YouTube json3 captions produce heavily
> overlapping segments -- each segment starts before the previous one ends. If you naively
> concatenate or merge by non-overlap, you get one giant block of duplicated text.
> **Solution:** Skip every other segment (take even-indexed ones only) and add timestamp
> markers every ~15 seconds. This produces clean, readable output.

```python
# Deduplication approach for overlapping YouTube captions:
for i, seg in enumerate(segments):
    if i % 2 != 0:  # Skip odd segments (they overlap with even ones)
        continue
    # Add [M:SS] timestamp every ~15 seconds
    # Write seg["text"]
```

For Whisper-generated transcripts (non-overlapping), simply output each segment with its timestamp.

Target format:
```markdown
# Transcript: {Video Title}

**Duration:** {HH:MM:SS}

---

[0:00] First segment of text...

[0:15] Next segment of text...

...
```

#### Step 9 - Generate Markdown Document

Use the following template and guidelines to generate the final document.

**Template:**

```markdown
# {Document Title}

> **Source:** {Video title or URL}  |  **Duration:** {HH:MM:SS}  |  **Date:** {video date or today}
> **Participants:** {names if known}  |  **Generated:** {today's date} via documenting-video skill

---

## Table of Contents

- [Overview](#overview)
- [{Section 1 Title}](#{anchor})
- [{Section 2 Title}](#{anchor})
- ...
- [Key Takeaways](#key-takeaways)
- [Action Items](#action-items)

---

## Overview

{2-4 sentence synthesis of the entire video. What was covered, why it matters, and who should read this.}

---

## {Section Title}

{Synthesized prose covering this topic. NOT verbatim transcript -- rewrite as clear technical writing.}

![{Caption}](screenshots/{filename}.png)
*{Caption}: {What this screenshot shows and why it matters}*

{Continue synthesized prose...}

> **Key point:** {Important callout extracted from this section}

```{language}
{Any code, commands, or configuration mentioned verbally -- formatted as proper code blocks}
```

| {Header} | {Header} |
|---|---|
| {data} | {data} |

---

## Key Takeaways

1. **{Takeaway title}**: {1-2 sentence explanation}
2. **{Takeaway title}**: {1-2 sentence explanation}
3. ...

## Action Items

- [ ] {Action item} *(Owner: {name if known})*
- [ ] {Action item}

---

<details>
<summary>Full Transcript (click to expand)</summary>

{Full timestamped transcript from transcript.md}

</details>
```

**Writing guidelines -- these are CRITICAL:**

1. **Synthesize, don't transcribe.** The main body must be rewritten as clear technical prose. Never paste transcript text verbatim into sections.
2. **Screenshots at narrative points.** Place each screenshot exactly where the content it shows is discussed in the prose.
3. **Spoken lists become tables.** When the speaker lists items, comparisons, or options, convert to a markdown table.
4. **Spoken commands become code blocks.** Any CLI commands, code snippets, URLs, file paths, or configuration mentioned verbally should be extracted into fenced code blocks with appropriate language tags.
5. **Section structure from topics.** Create sections based on major topic shifts detected in Phase 2, not based on arbitrary time divisions.
6. **Full transcript at the end.** The complete timestamped transcript goes in a collapsible `<details>` section at the bottom.
7. **Document must stand alone.** A reader should be able to understand the content without watching the video.

### Phase 5: Review & Polish

#### Step 10 - Self-Review Checklist

Before presenting the document, verify:

- [ ] **Visually verify every screenshot** by reading each .png file -- confirm they show actual video content, not error screens, player chrome, or blank frames
- [ ] All screenshot file paths in markdown match actual files in `screenshots/` directory
- [ ] Table of Contents anchors match actual section headings (lowercase, hyphens, no special chars)
- [ ] No verbatim transcript text appears in the main body sections
- [ ] All code blocks have language tags (```bash, ```javascript, ```python, etc.)
- [ ] All URLs mentioned in the video are clickable markdown links
- [ ] Document reads as coherent technical writing, not a transcript summary
- [ ] Screenshots are ordered chronologically and placed at relevant narrative points
- [ ] Key takeaways and action items are populated (not empty sections)
- [ ] Metadata header is complete (source, duration, date, participants)

Fix any issues found during this review.

#### Step 11 - Present Results to User

Display a summary:

```
Documentation complete!

  Document:     {output_dir}/{document-name}.md
  Screenshots:  {N} captured in {output_dir}/screenshots/
  Transcript:   {output_dir}/transcript.md
  Raw data:     {output_dir}/transcript-raw.json

  Video duration:  {HH:MM:SS}
  Sections:        {N}
  Screenshots:     {N} captured ({M} skipped due to blank frames)

Would you like me to:
- Adjust any section titles or content?
- Add more screenshots at specific timestamps?
- Split this into multiple documents by topic?
- Remove or replace any screenshots?
```

## Error Handling Reference

| Error | Detection | Recovery |
|---|---|---|
| **Player crash from rapid seeks** | Health check: `hasErrorText: true`, `readyState: 0`, or page shows "Something went wrong" | **Primary fix:** Download video and use local playback (Step 5a). **If using web player:** Reload page, wait, re-seek. Add 1-2s delay between seeks |
| **Error screen captured as screenshot** | Post-capture `Read` of .png shows error text instead of video | Delete bad file, reload page, re-seek, re-capture. Canvas blank-frame detection does NOT catch these -- must visually verify |
| `yt-dlp` fails (auth/404) | Non-zero exit code | Prompt user for local file or ask them to open video in browser |
| `yt-dlp` not installable | pip3 fails | Ask user to install manually: `brew install yt-dlp` |
| Whisper OOM | Python MemoryError | Fall back to smaller model: `medium` → `small` → `base` |
| No `<video>` element found | `evaluate_script` returns `found: false` | Try `take_snapshot` to find player UID; try iframe detection; fall back to keyboard controls |
| Blank frame captured | Quality check returns `isBlank: true` | Retry 3x with 500ms delays; nudge timestamp +0.5s; skip and note in output |
| Player controls in screenshot | Visual overlap detection | Target `<video>` element UID; wait 3s for auto-hide; inject CSS `video::-webkit-media-controls { display: none !important; }` |
| ffmpeg not installed | `which ffmpeg` fails | Tell user: `brew install ffmpeg` |
| Chrome DevTools MCP not connected | Tool calls fail | Skip screenshot phase; produce transcript-only documentation |
| Transcript normalizer fails | Python script error | Show raw transcript to Claude for manual parsing |
| `seeked` event never fires | Seek returns `timeout: true` for every attempt | Normal behavior -- the 3s fallback timeout IS the primary seek mechanism in practice, even with local playback. Do not treat `timeout: true` as an error |

## Dependencies

- `yt-dlp` -- video download (installed via pip3)
- `openai-whisper` -- speech-to-text (installed via pip3)
- `ffmpeg` / `ffprobe` -- audio extraction and video analysis (must be pre-installed)
- Chrome DevTools MCP -- browser automation for screenshots
- Python 3.8+ -- script execution
