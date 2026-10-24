#!/bin/sh
# Builds the Debian package here. (The Arch package is built by CI inside an Arch container from pkg/arch/PKGBUILD.)
set -e
ROOT=$(cd "$(dirname "$0")/.." && pwd); OUT=${1:-$ROOT/dist}; V=${VERSION:-1.0.0}
mkdir -p "$OUT"; S=$(mktemp -d)
cp -a "$ROOT/pkg/root/." "$S/"
install -Dm644 "$ROOT/brain/hub.py" "$S/usr/lib/thmi-hub/hub.py"
mkdir -p "$S/DEBIAN"
cat > "$S/DEBIAN/control" <<EOT
Package: thmi-hub
Version: $V
Architecture: all
Maintainer: elijah-code-5 <noreply@users.noreply.github.com>
Depends: python3, mpv, ffmpeg, curl
Recommends: nodejs
Description: T-HMI Hub server (YouTube, podcasts, music, your own services)
 Runs as your own user, only when you start it (or if you run: thmi-hub enable).
EOT
cp "$ROOT/pkg/debian/postinst" "$S/DEBIAN/postinst"; chmod 755 "$S/DEBIAN/postinst"
dpkg-deb --root-owner-group --build "$S" "$OUT/thmi-hub_${V}_all.deb"
cp "$OUT/thmi-hub_${V}_all.deb" "$OUT/thmi-hub_all.deb"
