#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
ADB_DIR="$ROOT_DIR/platform-tools"
ZIP_PATH="$ADB_DIR/platform-tools.zip"
URL_LINUX="https://dl.google.com/android/repository/platform-tools-latest-linux.zip"

mkdir -p "$ADB_DIR"
echo "Downloading Android platform-tools to $ADB_DIR..."
curl -L -o "$ZIP_PATH" "$URL_LINUX"
echo "Unzipping..."
unzip -o "$ZIP_PATH" -d "$ADB_DIR" >/dev/null
rm -f "$ZIP_PATH"

ADB_BIN="$ADB_DIR/platform-tools/adb"
if [ ! -x "$ADB_BIN" ]; then
  echo "ERROR: adb not found at $ADB_BIN after extraction." >&2
  exit 1
fi

echo "Done. Use this adb path (and optionally export ADB_PATH for the bot):"
echo "  $ADB_BIN"
echo "Example:"
echo "  export ADB_PATH=\"$ADB_BIN\""
echo "  source venv/bin/activate && python -m GramAddict run --config accounts/yourusername/config.yml"

