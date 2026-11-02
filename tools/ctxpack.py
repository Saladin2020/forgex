#!/usr/bin/env python3
"""FORGEX context pack (stdlib only): load only what a task needs, under a per-mode token cap.

  ctxpack.py "<task>" [--path P ...] [--mode QUICK|STANDARD|GUARDED] [--kit DIR] [--policy FILE]
             [--out forgex/context-pack.md] [--json] [--print]
Run from the project root. Picks, in policy priority order: forgex/STATE.md (always), DECISIONS entries
whose Tags/title match the task's areas, kit cards by Tags, CODEMAP sections for touched dirs/areas,
golden examples by file kind. Tokens are ESTIMATES (chars/4). The bundle never exceeds the cap;
everything left out is listed with a reason. Policy: forgex/context-policy.json overrides the shipped one.
"""
import argparse, fnmatch, json, re, sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
PKG = HERE.parent  # references/ (shipped) or repo root (source)

def est(s): return (len(s) + 3) // 4

def glob_re(g):
    out, i = "", 0
    while i < len(g):
        if g.startswith("**/", i): out += "(?:.*/)?"; i += 3
        elif g.startswith("**", i): out += ".*"; i += 2
        elif g[i] == "*": out += "[^/]*"; i += 1
        elif g[i] == "?": out += "[^/]"; i += 1
        else: out += re.escape(g[i]); i += 1
    return re.compile("^" + out + "$")

def hit(path, globs): return any(glob_re(g).match(path) for g in globs)

def first(*cands):
    return next((Path(c) for c in cands if c and Path(c).exists()), None)

def load_policy(arg):
    p = first(arg, "forgex/context-policy.json", PKG / "config/context-policy.json")
    if not p: sys.exit("context-policy.json not found")
    return json.loads(p.read_text()), p

def kit_dir(arg):
    if arg: return Path(arg)
    cfg = PKG / "config/kit.json"
    name = json.loads(cfg.read_text()).get("kit") if cfg.exists() else None
    return first(PKG / "kit", PKG / "kits" / name if name else None, PKG / "house", PKG / "core/house")

def words(s): return " " + re.sub(r"[^a-z0-9ก-๙]+", " ", s.lower()) + " "

def areas_for(task, paths, pol):
    w, found = words(task), {}
    for a in pol["areas"]:
        why = [k for k in a["keywords"] if words(k) in w or (len(k) > 5 and k in w)]
        why += [p for p in paths if hit(p, a["paths"])]
        if why: found[a["area"]] = why
    return found

def guess_mode(areas, paths):
    risky = {"auth", "money", "db"} & set(areas)
    try:
        g = json.loads((PKG / "config/default-policy.json").read_text())["guardedGlobs"]
    except Exception: g = []
    if risky or any(hit(p, g) for p in paths): return "GUARDED"
    if len(paths) <= 1 and set(areas) <= {"ui"}: return "QUICK"
    return "STANDARD"

def tags_of(text):
    m = re.search(r"^\s*-\s*\**Tags:?\**:?\s*(.+)$", text, re.M | re.I)
    return {t.strip().lower() for t in m.group(1).split(",")} if m else set()

def decisions(areas, task):
    p = Path("forgex/DECISIONS.md")
    if not p.exists(): return [], []
    parts = re.split(r"(?m)^(?=## D-\d+)", p.read_text())
    keep, skip, w = [], [], words(task)
    for e in parts[1:]:
        head = e.splitlines()[0]; tg = tags_of(e)
        why = (tg & set(areas)) or {x for x in re.findall(r"[a-z]{4,}", head.lower()) if f" {x} " in w}
        (keep if why else skip).append((e.strip(), head, sorted(why)))
    return [("decisions", f"DECISIONS {h.split('·')[0].strip('# ').strip()}", e, f"tags/title match {', '.join(y)}") for e, h, y in keep], \
           [(f"DECISIONS {h.split('·')[0].strip('# ').strip()}", "no matching tag/area") for _, h, _ in skip]

def cards(kit, areas, task, cap):
    if not kit or not (kit / "blocks").is_dir(): return [], []
    scored, skip, w = [], [], words(task)
    for c in sorted((kit / "blocks").glob("*.md")):
        if c.name.startswith("_") or c.name == "INDEX.md": continue
        t = c.read_text(); tg = tags_of(t)
        s = 3 * len(tg & set(areas)) + sum(1 for x in tg if f" {x} " in w) + (2 if words(c.stem.replace("-", " ")).strip() in w else 0)
        (scored if s else skip).append((s, c, t) if s else (f"card {c.stem}", "tags not in task areas"))
    scored.sort(key=lambda x: -x[0])
    # Reserve a slot per area for its core card (primary = first tag), then fill by score.
    prim = lambda t: (re.search(r"Tags:?\**:?\s*([^,\n]+)", t) or [None, ""])[1].strip().lower()
    picked = []
    for ar in areas:
        core = next((x for x in scored if prim(x[2]) == ar and x not in picked), None)
        if core and len(picked) < cap: picked.append(core)
    picked += [x for x in scored if x not in picked][: cap - len(picked)]
    picked.sort(key=lambda x: -x[0])
    for s, c, _ in scored:
        if all(c != y[1] for y in picked): skip.append((f"card {c.stem}", f"over maxCards={cap} (score {s})"))
    core_names = {x[1] for x in picked if prim(x[2]) in areas}
    return [("cards", f"card {c.stem}", t.strip(), f"tag score {s}" + (" · area core card" if c in core_names else "")) for s, c, t in picked], skip

def codemap(paths, areas, pol):
    p = Path("forgex/CODEMAP.md")
    if not p.exists(): return [], [("CODEMAP", "forgex/CODEMAP.md missing (run codemap.py)")]
    secs = re.split(r"(?m)^(?=## )", p.read_text())
    keep, skip = [], []
    dirs = {str(Path(x).parent) for x in paths}
    kw = {k for a in areas for ar in pol["areas"] if ar["area"] == a for k in ar["keywords"] if len(k) > 3}
    for s in secs[1:]:
        d = s.splitlines()[0][3:].split(" (")[0].rstrip("/")
        if d == "Notes": keep.append(("codemap", "CODEMAP Notes", s.strip(), "notes")); continue
        if d in dirs: keep.append(("codemap", f"CODEMAP {d}/", s.strip(), "touched dir"))
        elif any(k in d.lower() for k in kw): keep.append(("codemap", f"CODEMAP {d}/", s.strip(), "area keyword in dir"))
        else: skip.append((f"CODEMAP {d}/", "unrelated dir"))
    return keep, skip

KIND_WORDS = {"form-page": ["page", "form"], "api-route": ["api", "endpoint", "route"], "server-action": ["action", "mutation"], "test": ["test", "spec"]}

def golden(kit, paths, task, pol):
    if not kit or not (kit / "golden").is_dir(): return [], []
    w, keep, skip = words(task), [], []
    for kind, globs in pol.get("goldenByKind", {}).items():
        f = kit / "golden" / f"{kind}.md"
        if not f.exists(): continue
        if any(hit(p, globs) for p in paths) or any(f" {k} " in w for k in KIND_WORDS.get(kind, [])):
            keep.append(("golden", f"golden {kind}", f.read_text().strip(), "file kind match"))
        else: skip.append((f"golden {kind}", "file kind not touched"))
    return keep, skip

def main():
    ap = argparse.ArgumentParser(); ap.add_argument("task"); ap.add_argument("--path", action="append", default=[])
    ap.add_argument("--mode", choices=["QUICK", "STANDARD", "GUARDED"]); ap.add_argument("--kit"); ap.add_argument("--policy")
    ap.add_argument("--out", default="forgex/context-pack.md"); ap.add_argument("--json", action="store_true"); ap.add_argument("--print", action="store_true")
    a = ap.parse_args()
    pol, pol_path = load_policy(a.policy); kit = kit_dir(a.kit)
    skipped = [(p, "policy skip list") for p in a.path if hit(p, pol.get("skip", []))]
    paths = [p for p in a.path if not hit(p, pol.get("skip", []))]
    areas = areas_for(a.task, paths, pol)
    mode = a.mode or guess_mode(areas, paths)
    cap = pol["budgets"][mode]; ncards = pol.get("maxCards", {}).get(mode, 3)
    cand = {"state": [], "decisions": [], "cards": [], "codemap": [], "golden": []}
    for g in pol["always"]:
        for f in sorted(Path(".").glob(g)) or []:
            cand["state"].append(("state", str(f), f.read_text().strip(), "always"))
        if not any(Path(".").glob(g)): skipped.append((g, "missing (run context.py init)"))
    for k, fn in (("decisions", lambda: decisions(areas, a.task)), ("cards", lambda: cards(kit, areas, a.task, ncards)),
                  ("codemap", lambda: codemap(paths, areas, pol)), ("golden", lambda: golden(kit, paths, a.task, pol))):
        if k in pol.get("skipKinds", {}).get(mode, []):
            items, sk = fn(); skipped += [(i[1], f"kind '{k}' skipped in {mode}") for i in items] + sk; continue
        items, sk = fn(); cand[k] = items; skipped += sk
    head = f"# FORGEX context pack · {mode} · cap {cap} est. tokens\nTask: {a.task}\nAreas: {', '.join(areas) or '-'}\n"
    used, chosen, body = est(head), [], []
    for k in pol["priority"]:
        for kind, label, text, why in cand.get(k, []):
            block = f"\n---\n## [{label}]\n{text}\n"; t = est(block)
            if used + t <= cap: used += t; chosen.append((label, t, why)); body.append(block)
            elif kind == "state" and cap - used > 60:
                room = (cap - used - 20) * 4; block = block[:room] + "\n…(truncated to budget)\n"; t = est(block)
                used += t; chosen.append((label + " (truncated)", t, why)); body.append(block)
            else: skipped.append((label, f"over budget ({t} est. tokens, {cap - used} left)"))
    bundle = head + "".join(body)
    assert est(bundle) <= cap, "budget invariant broken"
    out = Path(a.out); out.parent.mkdir(parents=True, exist_ok=True); out.write_text(bundle)
    rep = {"mode": mode, "capTokensEst": cap, "usedTokensEst": est(bundle), "areas": areas, "policy": str(pol_path),
           "kit": str(kit) if kit else None, "loaded": [{"item": l, "tokensEst": t, "why": w} for l, t, w in chosen],
           "skipped": [{"item": l, "why": w} for l, w in skipped], "bundle": str(out)}
    if a.json: print(json.dumps(rep, indent=2, ensure_ascii=False))
    else:
        print(f"mode {mode} · {rep['usedTokensEst']}/{cap} est. tokens (chars/4) · areas: {', '.join(areas) or '-'}")
        for l, t, w in chosen: print(f"  + {l:32} {t:5}  {w}")
        for l, w in skipped: print(f"  - {l:32}        {w}")
        print(f"bundle: {out}  (read only this file)")
    if a.print: print(bundle)

if __name__ == "__main__":
    main()
