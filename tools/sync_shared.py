#!/usr/bin/env python3
"""Copy shared/*.py into every app that imports them (each .mpk must be self-contained)."""
import os, shutil, re
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
shared = [f for f in os.listdir(os.path.join(ROOT, "shared")) if f.endswith(".py")]
for app in sorted(os.listdir(os.path.join(ROOT, "apps"))):
    d = os.path.join(ROOT, "apps", app)
    if not os.path.isdir(d):
        continue
    src = "".join(open(os.path.join(d, f)).read() for f in os.listdir(d) if f.endswith(".py") and f not in shared)
    for f in shared:
        mod = f[:-3]
        if re.search(r"^\s*(import|from)\s+%s\b" % mod, src, re.M) or (mod == "thmi_net" and "thmi_ui" in src):
            shutil.copy(os.path.join(ROOT, "shared", f), os.path.join(d, f))
print("shared synced")
