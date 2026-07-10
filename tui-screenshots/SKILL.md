---
name: tui-screenshots
description: Capture deterministic screenshots (or GIFs) of a terminal UI / CLI app using vhs, a headless terminal recorder. Use when asked to screenshot a TUI, capture an image of a CLI app, record a terminal session, make a demo GIF, regenerate README/docs screenshots, or produce terminal output as an image. Triggers on: screenshot the TUI, capture the app, terminal recording, vhs tape, demo gif, record the CLI, capture terminal as image.
---

# Capturing TUI Screenshots with vhs

[vhs](https://github.com/charmbracelet/vhs) drives a program inside a **headless terminal** and captures stills (PNG) and/or an animated GIF from a `.tape` script. Because it's headless and scripted, captures are **deterministic and repeatable** — ideal for docs/README screenshots and for iterating until a shot looks right.

**The key advantage for Claude:** after capturing, you can `Read` the PNG (it's an image) to *see* the result, then adjust timing/keys/sizing and re-run. Always do this verify-and-iterate loop — don't assume the first capture is right.

## Prerequisites

vhs needs `ffmpeg` and `ttyd`. Check, and install if missing:

```bash
command -v vhs >/dev/null || brew install vhs ffmpeg ttyd   # macOS
# Linux: see https://github.com/charmbracelet/vhs#installation
```

## Workflow

1. **Write a `.tape`** describing the session (launch the app, drive keys, capture).
2. **Run it:** `vhs path/to/file.tape` → writes the `Output` GIF and any `Screenshot` PNGs.
3. **Read each PNG** to verify layout, content, and that keys landed on the right screen.
4. **Iterate:** adjust `Sleep` durations, key sequences, or terminal size; re-run.
5. **Clean up** any backend you started for the capture.

## Tape language — essentials

```tape
Output "demo.gif"            # REQUIRED, even if you only want Screenshots. Quote the path.
Set Shell "bash"
Set Width 1540               # pixels — wider = more columns
Set Height 880               # pixels
Set FontSize 14
Set Padding 12

Type "myapp --some-flag"     # types into the shell
Enter
Sleep 3s                     # let the app boot + initial data load (be generous)

Ctrl+G                       # key chords: Ctrl+<X>, also Tab, Enter, Escape, Up/Down/Left/Right, Space
Sleep 2s
Screenshot "docs/screenshots/panel.png"   # capture a still NOW. Quote the path.

Tab
Sleep 800ms
Enter
Sleep 1500ms
Screenshot "docs/screenshots/detail.png"
```

### Gotchas (these will bite)
- **Quote every path.** `Screenshot "out.png"` and `Output "out.gif"` — bare paths fail to parse.
- **`Output` is mandatory** even for screenshot-only tapes (send the GIF to `/tmp` if you don't want it).
- **Sleep generously.** TUIs need time to boot and to finish async loads (HTTP fetches, file watches) before a key or screenshot. A screenshot fired too early catches a half-loaded/reflowed screen. When a shot looks wrong, bumping `Sleep` is the first fix.
- **`Screenshot` captures the frame at that instant** — place one after each navigation step you want to document. Multiple `Screenshot` lines in one tape are fine.
- **`cwd`** is wherever you invoke `vhs` from; relative paths in `Type`/`Screenshot` resolve from there. Invoke from the repo root.

### Sizing for TUIs
Many TUIs want a wide terminal (~120 columns). `Set Width 1540 / Height 880 / FontSize 14` is a good starting point for a dense two-pane layout. If content truncates, widen; if text is too small, raise `FontSize` and widen proportionally. Capture, `Read`, adjust.

## Apps that need a backend / server / env

vhs runs in its own shell, so host env vars and background processes don't carry in. Two options:

- **Start the dependency on the host first** (background it), then run vhs; the app inside vhs reaches it over localhost/sockets:
  ```bash
  mybackend --addr :8088 >/tmp/backend.log 2>&1 &
  trap 'kill $! 2>/dev/null' EXIT
  vhs demo.tape
  ```
- **Or set env in the tape** by typing it into the launch command: `Type "MYAPP_API=http://127.0.0.1:8088 myapp"`. (vhs also has `Set Env`/`Env` in newer versions.)

For reproducibility, wrap the whole thing in a script (build app + start backend + `vhs tape` + cleanup) and a `make` target, and commit the `.tape`.

## Animated GIF instead of stills

Drop the `Screenshot` lines and let `Output "demo.gif"` record the full driven session — great for an animated README demo. Keep the session short and the final `Sleep` long enough to land on a clean ending frame.

## Recipe checklist
- [ ] vhs/ffmpeg/ttyd present
- [ ] backend started (if needed) + cleanup trap
- [ ] tape: Output + Set size + launch + Sleep + keys + Screenshot (all paths quoted)
- [ ] run `vhs`, then **Read every PNG** and verify
- [ ] iterate on Sleep/keys/size; commit the tape + a regen script/`make` target
