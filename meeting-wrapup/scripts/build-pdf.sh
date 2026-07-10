#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
TEMPLATES_DIR="$SCRIPT_DIR/../templates"

usage() {
  echo "Usage: $0 [--html] <directory> [summary-file]"
  echo "  Builds summary.pdf by default."
  echo "  --html      Also build a self-contained summary.html (opt-in; off by default)."
  echo "  --pdf-only  Explicitly build only the PDF (the default)."
  echo "Examples:"
  echo "  $0 /path/to/meeting"
  echo "  $0 --html /path/to/meeting"
  echo "  $0 /path/to/meeting meeting-summary.md"
}

# --- Parse flags & arguments ---
# HTML output is OPT-IN. By default only the PDF is produced.
BUILD_HTML=false
POSITIONAL=()
while [ $# -gt 0 ]; do
  case "$1" in
    --html)     BUILD_HTML=true ;;
    --pdf-only) BUILD_HTML=false ;;
    -h|--help)  usage; exit 0 ;;
    --*)        echo "Error: unknown option: $1"; usage; exit 1 ;;
    *)          POSITIONAL+=("$1") ;;
  esac
  shift
done
# Restore positionals (bash 3.2-safe expansion of a possibly-empty array under `set -u`).
set -- ${POSITIONAL[@]+"${POSITIONAL[@]}"}

if [ $# -lt 1 ]; then
  usage
  exit 1
fi

TARGET_DIR="$(cd "$1" && pwd)"

if [ ! -d "$TARGET_DIR" ]; then
  echo "Error: directory not found: $TARGET_DIR"
  exit 1
fi

# --- Find the summary markdown ---
if [ $# -ge 2 ]; then
  MD_FILE="$TARGET_DIR/$2"
else
  # Look for *-session-summary.md, *-summary.md, or summary.md
  MD_FILE=""
  for pattern in "*-session-summary.md" "*-summary.md" "summary.md"; do
    matches=("$TARGET_DIR"/$pattern)
    if [ -f "${matches[0]}" ]; then
      MD_FILE="${matches[0]}"
      break
    fi
  done

  if [ -z "$MD_FILE" ] || [ ! -f "$MD_FILE" ]; then
    echo "Error: no summary markdown found in $TARGET_DIR"
    echo "Looked for: *-session-summary.md, *-summary.md, summary.md"
    echo "You can specify a file: $0 $1 your-file.md"
    exit 1
  fi
fi

echo "Source: $MD_FILE"

# --- CSS paths ---
WEB_CSS="$TEMPLATES_DIR/web.css"
PRINT_CSS="$TEMPLATES_DIR/print.css"

# --- Strip YAML frontmatter (Pandoc shouldn't render it) ---
CLEAN_MD="$TARGET_DIR/.pandoc-input.md"
tr -d '\r' < "$MD_FILE" > "$CLEAN_MD"
FIRST_LINE=$(head -1 "$CLEAN_MD")
if [ "$FIRST_LINE" = "---" ]; then
  FRONTMATTER_END=$(tail -n +2 "$CLEAN_MD" | grep -n '^---$' | head -1 | cut -d: -f1)
  tail -n +"$((FRONTMATTER_END + 2))" "$CLEAN_MD" > "$CLEAN_MD.tmp"
  mv "$CLEAN_MD.tmp" "$CLEAN_MD"
fi

# --- Generate HTML (opt-in via --html) ---
if [ "$BUILD_HTML" = true ]; then
  echo ""
  echo "Generating HTML..."
  if pandoc "$CLEAN_MD" \
    --standalone \
    --embed-resources \
    --resource-path="$TARGET_DIR" \
    --css="$WEB_CSS" \
    --toc --toc-depth=2 \
    -o "$TARGET_DIR/summary.html"; then
    SIZE=$(du -h "$TARGET_DIR/summary.html" | cut -f1)
    echo "  HTML: $TARGET_DIR/summary.html ($SIZE)"
  else
    echo "  HTML generation failed."
  fi
fi

# --- Generate PDF ---
echo ""
echo "Generating PDF..."
if pandoc "$CLEAN_MD" \
  --standalone \
  --resource-path="$TARGET_DIR" \
  --css="$PRINT_CSS" \
  --pdf-engine=weasyprint \
  -o "$TARGET_DIR/summary.pdf"; then
  SIZE=$(du -h "$TARGET_DIR/summary.pdf" | cut -f1)
  echo "  PDF:  $TARGET_DIR/summary.pdf ($SIZE)"
else
  echo "  PDF generation failed."
fi

# --- Clean up temp file ---
rm -f "$CLEAN_MD"

echo ""
echo "Done."
