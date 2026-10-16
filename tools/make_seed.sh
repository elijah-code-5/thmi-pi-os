#!/bin/sh
# usage: make_seed.sh PATH_TO_MPOS_UNIX_BINARY OUT.img.gz   -> filesystem image with all apps in apps/
set -e
HERE=$(cd "$(dirname "$0")" && pwd); ROOT=$(dirname "$HERE")
python3 "$ROOT/tools/sync_shared.py"
STAGE=$(mktemp -d); mkdir -p "$STAGE/apps"
for d in "$ROOT"/apps/*/; do cp -r "$d" "$STAGE/apps/$(basename "$d")"; done
find "$STAGE" -name __pycache__ -prune -exec rm -rf {} +
IMG=$(mktemp)
"$1" -X heapsize=48M "$HERE/mkfs_image.py" "$STAGE" "$IMG" | tee /dev/stderr | grep -q "IMAGE OK"
gzip -9 -c "$IMG" > "$2"
