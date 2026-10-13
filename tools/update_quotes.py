#!/usr/bin/env python3
"""Refresh src/typerace/quotes.json from Monkeytype's English quote collection.

    python3 tools/update_quotes.py
"""
import json
import os
import sys
import urllib.request

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
from typerace.app import typable  # noqa: E402

URL = "https://raw.githubusercontent.com/monkeytypegame/monkeytype/master/frontend/static/quotes/english.json"
OUT = os.path.join(os.path.dirname(__file__), "..", "src", "typerace", "quotes.json")

with urllib.request.urlopen(URL, timeout=30) as r:
    raw = json.load(r)["quotes"]
quotes = [[f"mt{q['id']}", t, q.get("source", "")] for q in raw if (t := typable(q["text"]))]
with open(OUT, "w") as f:
    json.dump(quotes, f, ensure_ascii=True, separators=(",", ":"))
print(f"{len(quotes)} of {len(raw)} quotes written to {os.path.normpath(OUT)}")
