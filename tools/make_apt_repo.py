#!/usr/bin/env python3
"""usage: make_apt_repo.py DIR  -> writes Packages, Packages.gz and Release next to the versioned .deb in DIR (a 'flat' apt repository)."""
import gzip, hashlib, os, subprocess, sys, time
d = sys.argv[1]
debs = sorted(f for f in os.listdir(d) if f.startswith("thmi-hub_") and f.endswith("_all.deb") and f != "thmi-hub_all.deb")
import shutil, tempfile
newest = debs[-1]
tmp = tempfile.mkdtemp()                      # scan only the versioned file (the stable-name copy would be a duplicate)
shutil.copy(os.path.join(d, newest), tmp)
pk = subprocess.run(["dpkg-scanpackages", ".", "/dev/null"], cwd=tmp, capture_output=True, text=True, check=True).stdout
blocks = [x for x in pk.strip().split("\n\n") if x.strip()]
assert blocks, "no package found"
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
