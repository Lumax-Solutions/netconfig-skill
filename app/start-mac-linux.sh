#!/usr/bin/env bash
# NetConfig Assistant - start the app and open it in your browser.
cd "$(dirname "$0")" || exit 1
if command -v python3 >/dev/null 2>&1; then exec python3 netconfig_app.py "$@"; fi
if command -v python >/dev/null 2>&1; then exec python netconfig_app.py "$@"; fi
echo "Python 3 is needed. macOS: install from https://www.python.org/downloads/  Linux: sudo apt install python3"
read -r -p "Press Enter to close" _
