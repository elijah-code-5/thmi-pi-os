#!/usr/bin/env python3
"""Zip every apps/<fullname>/ into dist/<fullname>_<version>.mpk and write dist/app_index.json.
usage: build_apps.py [REPO]   (REPO = owner/name used for download URLs)"""
import json, os, sys, zipfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
repo = sys.argv[1] if len(sys.argv) > 1 else "elijah-code-5/thmi-pi-os"
import subprocess; subprocess.check_call([sys.executable, os.path.join(ROOT, "tools", "sync_shared.py")])
out = os.path.join(ROOT, "dist")
os.makedirs(out, exist_ok=True)
index = []
for name in sorted(os.listdir(os.path.join(ROOT, "apps"))):
    d = os.path.join(ROOT, "apps", name)
    mf = os.path.join(d, "MANIFEST.JSON")
    if not os.path.isfile(mf):
        continue
    m = json.load(open(mf))
    assert m["fullname"] == name, name
    fn = "%s_%s.mpk" % (name, m["version"])
    path = os.path.join(out, fn)
    with zipfile.ZipFile(path, "w", zipfile.ZIP_STORED) as z:
        z.writestr(zipfile.ZipInfo(name + "/"), "")
        for dp, _, files in sorted(os.walk(d)):
            rel = os.path.relpath(dp, os.path.join(ROOT, "apps"))
            if rel != name:
                z.writestr(zipfile.ZipInfo(rel + "/"), "")
            for f in sorted(files):
                if f.endswith(".pyc"):
                    continue
                z.write(os.path.join(dp, f), rel + "/" + f)
    index.append({"fullname": name, "name": m["name"], "version": m["version"],
                  "description": m.get("short_description", ""), "size": os.path.getsize(path),
                  "url": "https://github.com/%s/releases/download/apps-latest/%s" % (repo, fn)})
json.dump({"apps": index}, open(os.path.join(out, "app_index.json"), "w"), indent=1)
print("built", [a["fullname"] for a in index])
