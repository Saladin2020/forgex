#!/usr/bin/env python3
"""FORGEX harvest (stdlib): after a slice is done, SUGGEST reusable code as a personal-kit card draft.

  forgex.py harvest <sliceId>                       -> forgex/harvest/<slice>-<name>.md drafts (nothing else changes)
  forgex.py harvest --confirm <draft.md> --kit DIR  -> copies ONE draft into DIR/blocks/ + INDEX line (human said yes)
Never automatic, never public: --confirm refuses core/house, references/house, or any dir without kit.json/private-terms.txt
(a personal kit). The agent shows the drafts and asks; only the person confirms.
"""
import json, re, sys
from pathlib import Path
HERE = Path(__file__).resolve().parent; sys.path.insert(0, str(HERE))
import codemap as cmap  # noqa: E402

def drafts(sid):
    r = json.loads(Path("forgex/roadmap.json").read_text(encoding="utf-8"))
    s = next((x for x in r["slices"] if x["id"] == sid), None)
    if not s: sys.exit(f"harvest: slice {sid} not found")
    if s.get("status") != "done": sys.exit(f"harvest: slice {sid} is not done yet (forgex.py slice done {sid} first)")
    out = []
    for f in s.get("files", []):
        p = Path(f)
        if not p.exists() or p.suffix not in cmap.CODE: continue
        syms = cmap.symbols(f, p.read_text(encoding="utf-8", errors="ignore"))
        if not syms: continue
        name = re.sub(r"[^a-z0-9]+", "-", p.stem.lower()).strip("-") or "block"
        tags = ", ".join(dict.fromkeys([t for t in (s.get("mode") == "GUARDED" and "security", p.parent.name.lower()) if t and t not in (".", "")])) or "misc"
        d = Path("forgex/harvest") / f"{sid}-{name}.md"; d.parent.mkdir(parents=True, exist_ok=True)
        d.write_text(f"# {name}  (DRAFT from slice {sid}; confirm before adding to your kit)\n- **Tags:** {tags}\n- **What:** {s.get('title', '')} ({', '.join(syms[:4])})\n"
                     f"- **From:** <repo>:{f}\n- **Reuse:** import/call {', '.join(syms[:3])}; copy the shape, adapt names\n- **Gotchas:** ? (not yet reused in a 2nd app)\n", encoding="utf-8")
        out.append(d)
    return out

def personal(kit):
    k = kit.resolve(); s = k.as_posix()
    if re.search(r"/(core|references)/house(/|$)", s): return False
    return (k / "kit.json").exists() or (k / "private-terms.txt").exists()

def confirm(draft, kit):
    kit = Path(kit)
    if not personal(kit): sys.exit(f"harvest: refused: {kit} is not a personal kit (needs kit.json or private-terms.txt; never core/house)")
    t = Path(draft).read_text(encoding="utf-8")
    name = re.sub(r"^\w+-", "", Path(draft).stem, count=1)
    dst = kit / "blocks" / f"{name}.md"
    if dst.exists(): sys.exit(f"harvest: {dst} exists; merge by hand")
    dst.parent.mkdir(parents=True, exist_ok=True)
    dst.write_text(re.sub(r"\s+\(DRAFT[^)]*\)", "", t, count=1), encoding="utf-8")
    idx = kit / "blocks/INDEX.md"; what = re.search(r"\*\*What:\*\*\s*(.+)", t)
    with idx.open("a", encoding="utf-8") as fh: fh.write(f"- `{name}`: {what.group(1) if what else name}\n")
    print(f"added card {dst} (+INDEX line). Personal kit only; never shipped public.")

def main(args):
    if "--confirm" in args:
        i = args.index("--confirm"); kit = args[args.index("--kit") + 1] if "--kit" in args else sys.exit("harvest --confirm needs --kit DIR")
        return confirm(args[i + 1], kit)
    if not args: sys.exit(__doc__)
    ds = drafts(args[0])
    print("\n".join(f"draft: {d}" for d in ds) if ds else "harvest: nothing reusable found (no exported symbols in slice files)")
    if ds: print("Show these to the person. Only if they say yes: forgex.py harvest --confirm <draft> --kit <personal kit dir>")
