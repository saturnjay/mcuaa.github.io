#!/bin/sh
# MCUAA local preview: starts a local server and opens the site in your browser.
# Usage:  sh tools/preview.sh   (or double-click)
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
PORT="${1:-8899}"
cd "$ROOT" || exit 1
python3 -m http.server "$PORT" &
SERVER_PID=$!
sleep 1
open "http://localhost:$PORT/"
echo "Preview running at http://localhost:$PORT/  (stop: kill $SERVER_PID)"
