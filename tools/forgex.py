#!/usr/bin/env python3
"""FORGEX command entry (stdlib). Light planning + harvest + style capture (v2.9).

  forgex.py plan "<goal>" | plan --check | next | slice done <id> [--check-cmd "<cmd>"]
  forgex.py harvest <sliceId> | harvest --confirm <draft> --kit <personal kit dir>
  forgex.py style capture <image-or-url ...> [--out forgex/style] [--no-fetch]
Planning is only for new projects/features with >3 slices; QUICK and single tasks skip it.
"""
import sys
from pathlib import Path
for _s in (sys.stdout, sys.stderr):
    try: _s.reconfigure(encoding="utf-8", errors="replace")
    except Exception: pass
sys.argv = [x.encode("utf-8", "surrogateescape").decode("utf-8", "replace") for x in sys.argv]
sys.path.insert(0, str(Path(__file__).resolve().parent))

def main():
    a = sys.argv[1:]
    if not a: sys.exit(__doc__)
    c, rest = a[0], a[1:]
    if c in ("plan", "next", "slice"):
        import roadmap; {"plan": roadmap.cmd_plan, "next": roadmap.cmd_next, "slice": roadmap.cmd_slice}[c](rest)
    elif c == "harvest": import harvest; harvest.main(rest)
    elif c == "style": import style; style.main(rest)
    else: sys.exit(__doc__)

if __name__ == "__main__":
    main()
