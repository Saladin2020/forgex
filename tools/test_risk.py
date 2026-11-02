#!/usr/bin/env python3
"""Shared risk classifier tests: core/risk/cases.json through classifier.py AND classifier.mjs (parity). Exit 1 on failure."""
import json, subprocess, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RISK = ROOT / "risk" if (ROOT / "risk").is_dir() else ROOT / "core/risk"
sys.path.insert(0, str(RISK))
from classifier import classify  # noqa: E402

cases = json.loads((RISK / "cases.json").read_text(encoding="utf-8"))
py = [classify(**{("extra_globs" if k == "extraGlobs" else k): v for k, v in c["in"].items()})["mode"] for c in cases]
js = json.loads(subprocess.run(["node", str(RISK / "parity.mjs")], capture_output=True, text=True, encoding="utf-8", check=True).stdout)
fail = 0
for c, p, j in zip(cases, py, js):
    good = p == j == c["mode"]; fail += not good
    print(("ok  " if good else "FAIL") + f" risk {c['name']}: want {c['mode']} py {p} js {j}")
print(f"\n{len(cases)} risk cases, py/js parity {'OK' if py == js else 'BROKEN'}" if not fail else f"\n{fail} failed"); sys.exit(1 if fail else 0)
