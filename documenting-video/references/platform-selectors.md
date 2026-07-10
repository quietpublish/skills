# Platform-Specific Video Player APIs

Quick reference for controlling video players via `evaluate_script` in Chrome DevTools MCP.

---

## HTML5 `<video>` (Universal)

Works on any page with a native `<video>` element (most platforms under the hood).

### Find video element
```javascript
() => {
  const video = document.querySelector('video');
  if (!video) return { found: false };
  return {
    found: true,
    duration: video.duration,
    currentTime: video.currentTime,
    paused: video.paused,
    width: video.videoWidth,
    height: video.videoHeight,
    src: video.currentSrc?.substring(0, 100)
  };
}
```

### Seek + pause + wait for frame
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
    setTimeout(() => resolve({ success: true, timeout: true, time: video.currentTime }), 3000);
  });
}
```

### Blank frame detection
```javascript
() => {
  const video = document.querySelector('video');
  const canvas = document.createElement('canvas');
  canvas.width = video.videoWidth;
  canvas.height = video.videoHeight;
  const ctx = canvas.getContext('2d');
  ctx.drawImage(video, 0, 0);
  const samples = [];
  for (let row = 0; row < 3; row++) {
    for (let col = 0; col < 3; col++) {
      const x = Math.floor((col + 0.5) * canvas.width / 3);
      const y = Math.floor((row + 0.5) * canvas.height / 3);
      const pixel = ctx.getImageData(x, y, 1, 1).data;
      samples.push({ r: pixel[0], g: pixel[1], b: pixel[2] });
    }
  }
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

### Hide player controls
```javascript
() => {
  const video = document.querySelector('video');
  video.controls = false;
  // Also try to hide via CSS
  const style = document.createElement('style');
  style.textContent = `
    video::-webkit-media-controls { display: none !important; }
    video::-webkit-media-controls-enclosure { display: none !important; }
  `;
  document.head.appendChild(style);
  return { controlsHidden: true };
}
```

---

## YouTube

YouTube uses an iframe embed with its own JS API. The `<video>` element is inside the iframe.

### Direct page (youtube.com/watch?v=...)

The `<video>` element is accessible directly:
```javascript
() => {
  const video = document.querySelector('video.html5-main-video') || document.querySelector('video');
  return video ? { found: true, duration: video.duration } : { found: false };
}
```

### YouTube Player API (when available)
```javascript
() => {
  // YouTube exposes a player object on the page
  const player = document.querySelector('#movie_player');
  if (player && player.seekTo) {
    player.seekTo(TIMESTAMP, true);
    player.pauseVideo();
    return { success: true, api: 'youtube-player' };
  }
  return { success: false };
}
```

### YouTube iframe embed
```javascript
() => {
  const iframe = document.querySelector('iframe[src*="youtube"]');
  if (iframe) {
    // Use postMessage API
    iframe.contentWindow.postMessage(JSON.stringify({
      event: 'command',
      func: 'seekTo',
      args: [TIMESTAMP, true]
    }), '*');
    iframe.contentWindow.postMessage(JSON.stringify({
      event: 'command',
      func: 'pauseVideo',
      args: []
    }), '*');
    return { success: true, api: 'youtube-iframe-postmessage' };
  }
  return { success: false };
}
```

### Dismiss YouTube overlays
```javascript
() => {
  // Skip ads button
  const skipBtn = document.querySelector('.ytp-skip-ad-button, .ytp-ad-skip-button-modern');
  if (skipBtn) skipBtn.click();
  // Dismiss annotations
  document.querySelectorAll('.ytp-ce-element').forEach(el => el.style.display = 'none');
  // Hide end screen
  const endScreen = document.querySelector('.ytp-endscreen-content');
  if (endScreen) endScreen.style.display = 'none';
  return { cleaned: true };
}
```

---

## Vimeo

### Direct page (vimeo.com/...)
```javascript
() => {
  const video = document.querySelector('video');
  if (video) return { found: true, duration: video.duration };
  // Vimeo sometimes nests video in a player div
  const player = document.querySelector('.vp-video video');
  if (player) return { found: true, duration: player.duration };
  return { found: false };
}
```

### Vimeo Player API (via embed)
```javascript
() => {
  const iframe = document.querySelector('iframe[src*="vimeo"]');
  if (iframe) {
    iframe.contentWindow.postMessage(JSON.stringify({
      method: 'setCurrentTime',
      value: TIMESTAMP
    }), '*');
    iframe.contentWindow.postMessage(JSON.stringify({
      method: 'pause'
    }), '*');
    return { success: true, api: 'vimeo-postmessage' };
  }
  return { success: false };
}
```

---

## Loom

Loom uses a custom player but with a standard `<video>` element underneath.

### Find Loom video
```javascript
() => {
  const video = document.querySelector('video[data-testid="video-player"]')
    || document.querySelector('video');
  if (video) {
    return { found: true, duration: video.duration, src: video.src?.substring(0, 80) };
  }
  return { found: false };
}
```

### Loom-specific: dismiss overlays
```javascript
() => {
  // Dismiss CTA overlays, share prompts, etc.
  document.querySelectorAll('[data-testid*="cta"], [class*="CallToAction"]').forEach(el => {
    el.style.display = 'none';
  });
  // Hide transcript sidebar if open
  const sidebar = document.querySelector('[data-testid="transcript-sidebar"]');
  if (sidebar) sidebar.style.display = 'none';
  return { cleaned: true };
}
```

---

## Microsoft Teams / Stream

Teams recordings hosted on SharePoint/Stream use a standard video player.

### Find video
```javascript
() => {
  const video = document.querySelector('video')
    || document.querySelector('.vjs-tech')  // Video.js based
    || document.querySelector('[data-testid="videoPlayer"] video');
  if (video) {
    return { found: true, duration: video.duration };
  }
  return { found: false };
}
```

### Note on auth
Teams/Stream videos typically require authentication. The user must:
1. Open the video URL in the browser and sign in
2. Use `list_pages` to find the authenticated page
3. Use `select_page` to select it
4. Then proceed with the standard `<video>` API

---

## Google Drive / Meet Recordings

### Find video in Google Drive player
```javascript
() => {
  // Google Drive video player
  const video = document.querySelector('video.html5-video-container video')
    || document.querySelector('video');
  if (video) {
    return { found: true, duration: video.duration };
  }
  return { found: false };
}
```

---

## Fallback: Keyboard Controls

When JavaScript APIs don't work (CORS, sandboxed iframes, DRM), use keyboard shortcuts via `press_key`:

| Action | Key | Notes |
|---|---|---|
| Play/Pause | `Space` or `k` (YouTube) | Must focus player first |
| Seek forward 5s | `ArrowRight` | |
| Seek backward 5s | `ArrowLeft` | |
| Seek forward 10s | `l` (YouTube) | |
| Seek backward 10s | `j` (YouTube) | |
| Jump to start | `Home` or `0` | |
| Jump to % | `1`-`9` | 10%-90% of duration |
| Fullscreen | `f` | Useful for cleaner screenshots |

**Strategy for keyboard-based seeking:**
1. Press `Home` or `0` to go to start
2. Calculate target position as percentage of duration
3. Use number keys (1-9) for rough positioning
4. Fine-tune with `ArrowRight`/`ArrowLeft` (5s increments)
5. Pause with `Space`
6. Wait 1s for frame to settle
7. Take screenshot

---

## Detection Strategy

When starting screenshot capture, try detection in this order:

1. **Direct `<video>` query** -- works 90% of the time
2. **Platform-specific selector** -- for known platforms (YouTube, Vimeo, etc.)
3. **iframe inspection** -- check for embedded players
4. **`take_snapshot` a11y tree** -- find video-related elements by role
5. **Keyboard fallback** -- last resort, least precise
