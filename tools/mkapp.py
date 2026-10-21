#!/usr/bin/env python3
"""usage: mkapp.py fullname "Name" "short" category ClassName file.py ["long"]  -> writes apps/<fullname>/MANIFEST.JSON"""
import json, os, sys
fullname, name, short, cat, cls, entry = sys.argv[1:7]
long_ = sys.argv[7] if len(sys.argv) > 7 else short
root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
d = os.path.join(root, "apps", fullname)
os.makedirs(d, exist_ok=True)
mf = os.path.join(d, "MANIFEST.JSON")
ver = "1.0.0"
if os.path.exists(mf):
    ver = json.load(open(mf)).get("version", ver)
json.dump({"name": name, "publisher": "T-HMI Hub", "short_description": short, "long_description": long_, "fullname": fullname,
           "version": ver, "category": cat, "activities": [{"entrypoint": entry, "classname": cls, "intent_filters": [{"action": "main", "category": "launcher"}]}]},
          open(mf, "w"))
