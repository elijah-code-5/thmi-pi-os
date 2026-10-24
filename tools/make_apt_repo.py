#!/usr/bin/env python3
"""usage: make_apt_repo.py DIR  -> writes Packages, Packages.gz and Release next to the versioned .deb in DIR (a 'flat' apt repository)."""
import gzip, hashlib, os, subprocess, sys, time
d = sys.argv[1]
debs = sorted(f for f in os.listdir(d) if f.startswith("thmi-hub_") and f.endswith("_all.deb") and f != "thmi-hub_all.deb")
pk = subprocess.run(["dpkg-scanpackages", ".", "/dev/null"], cwd=d, capture_output=True, text=True, check=True).stdout
# only the newest deb listed
newest = debs[-1]
blocks = [b for b in pk.strip().split("\n\n") if newest in b]
open(os.path.join(d, "Packages"), "w").write("\n\n".join(blocks) + "\n")
with open(os.path.join(d, "Packages"), "rb") as f, gzip.open(os.path.join(d, "Packages.gz"), "wb") as g:
    g.write(f.read())
lines = ["Origin: thmi-pi-os", "Label: thmi-pi-os", "Suite: stable", "Codename: stable", "Architectures: all", "Components: main",
         "Date: " + time.strftime("%a, %d %b %Y %H:%M:%S UTC", time.gmtime()), "SHA256:"]
for n in ("Packages", "Packages.gz"):
    b = open(os.path.join(d, n), "rb").read()
    lines.append(" %s %d %s" % (hashlib.sha256(b).hexdigest(), len(b), n))
open(os.path.join(d, "Release"), "w").write("\n".join(lines) + "\n")
print("repo ok:", newest)
