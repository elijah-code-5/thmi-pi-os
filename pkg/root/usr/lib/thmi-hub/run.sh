#!/bin/sh
# Starts the T-HMI server for the current user. Everything it needs lives in your home folder.
H="${XDG_DATA_HOME:-$HOME/.local/share}/thmi-hub"
C="${XDG_CONFIG_HOME:-$HOME/.config}/thmi-hub"
mkdir -p "$H/bin" "$H/data" "$C" "$HOME/Music" "$HOME/THMI-Files"
[ -f "$C/config.json" ] || printf '{\n  "music_dir": "%s/Music",\n  "files_dir": "%s/THMI-Files",\n  "services": []\n}\n' "$HOME" "$HOME" > "$C/config.json"
# YouTube support: keep the official yt-dlp current (re-checked every 3 days, never blocks start-up)
case "$(uname -m)" in aarch64|arm64) F=yt-dlp_linux_aarch64;; *) F=yt-dlp_linux;; esac
if [ ! -x "$H/bin/yt-dlp" ] || [ -n "$(find "$H/bin/yt-dlp" -mtime +3 2>/dev/null)" ]; then
  ( curl -fsSL --retry 2 -o "$H/bin/yt-dlp.new" "https://github.com/yt-dlp/yt-dlp/releases/latest/download/$F" \
    && chmod 755 "$H/bin/yt-dlp.new" && mv "$H/bin/yt-dlp.new" "$H/bin/yt-dlp" ) >/dev/null 2>&1 &
fi
export THMI_DATA="$H/data" THMI_BASE="$C" HUB_CONFIG="$C/config.json" THMI_PKG=1
export STREAM_DISPLAY="${DISPLAY:-:0}"
export PATH="$H/bin:$PATH"
exec python3 /usr/lib/thmi-hub/hub.py
