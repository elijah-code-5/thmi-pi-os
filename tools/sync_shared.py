#!/usr/bin/env python3
"""Copy shared/*.py into every app that imports them (each .mpk must be self-contained), including shared->shared imports."""
import os, shutil, re
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SH = os.path.join(ROOT, "shared")
shared = {f[:-3]: open(os.path.join(SH, f)).read() for f in os.listdir(SH) if f.endswith(".py")}


def imports(src):
    return {m for m in shared if re.search(r"^\s*(import|from)\s+%s\b" % m, src, re.M)}


for app in sorted(os.listdir(os.path.join(ROOT, "apps"))):
    d = os.path.join(ROOT, "apps", app)
    if not os.path.isdir(d):
        continue
    for f in os.listdir(d):                       # drop stale copies first
        if f.endswith(".py") and f[:-3] in shared:
            os.remove(os.path.join(d, f))
    src = "".join(open(os.path.join(d, f)).read() for f in os.listdir(d) if f.endswith(".py"))
    need, todo = set(), imports(src)
    while todo:
        m = todo.pop()
        if m not in need:
            need.add(m)
            todo |= imports(shared[m])
    for m in need:
        shutil.copy(os.path.join(SH, m + ".py"), os.path.join(d, m + ".py"))
print("shared synced")
