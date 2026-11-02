#!/usr/bin/env python3
"""FORGEX context files (stdlib only). Run from project root.

  context.py init                      -> creates forgex/STATE.md, forgex/DECISIONS.md (never overwrites)
  context.py decide "<decision>" --why "<why>" [--alt "<option>" ...] [--supersedes D-3] [--tag auth --tag db]
"""
import argparse, datetime, re, sys
from pathlib import Path
for _s in (sys.stdout, sys.stderr):  # Windows consoles (cp874/cp1252): never crash on Thai output
    try: _s.reconfigure(encoding="utf-8", errors="replace")
    except Exception: pass
sys.argv = [x.encode("utf-8", "surrogateescape").decode("utf-8", "replace") for x in sys.argv]  # non-UTF-8 POSIX locales

HERE = Path(__file__).resolve().parent
TPL = next(p for p in (HERE.parent / "templates", HERE.parent / "core/templates") if p.is_dir())
OUT = Path("forgex")

def init():
    OUT.mkdir(exist_ok=True)
    for name in ("STATE.md", "DECISIONS.md"):
        dst = OUT / name
        if dst.exists():
            print(f"exists: {dst}")
        else:
            dst.write_text((TPL / name).read_text(encoding="utf-8")); print(f"created: {dst}")

def decide(a):
    p = OUT / "DECISIONS.md"
    if not p.exists(): sys.exit("run `context.py init` first")
    text = p.read_text(encoding="utf-8")
    n = 1 + max([int(x) for x in re.findall(r"^## D-(\d+)", text, re.M)] or [0])
    one = lambda s: " ".join(s.split())
    lines = [f"\n## D-{n} · {datetime.date.today().isoformat()} · {one(a.decision)}", f"- Why: {one(a.why)}"]
    if a.alt: lines.append("- Rejected: " + "; ".join(one(x) for x in a.alt))
    if a.tag: lines.append("- Tags: " + ", ".join(t.strip().lower() for t in a.tag))
    if a.supersedes: lines.append(f"- Supersedes: {a.supersedes}")
    p.write_text(text.rstrip("\n") + "\n" + "\n".join(lines) + "\n", encoding="utf-8"); print(f"added D-{n}")

ap = argparse.ArgumentParser(); sub = ap.add_subparsers(dest="cmd", required=True)
sub.add_parser("init")
d = sub.add_parser("decide"); d.add_argument("decision"); d.add_argument("--why", required=True)
d.add_argument("--alt", action="append"); d.add_argument("--supersedes"); d.add_argument("--tag", action="append")
a = ap.parse_args()
init() if a.cmd == "init" else decide(a)
