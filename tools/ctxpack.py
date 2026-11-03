#!/usr/bin/env python3
"""FORGEX context pack (stdlib only): load only what a task needs, under a per-mode token cap.

  ctxpack.py "<task>" [--path P ...] [--mode QUICK|STANDARD|GUARDED] [--kit DIR] [--policy FILE]
             [--out forgex/context-pack.md] [--json] [--print]
Run from the project root. Picks, in policy priority order: forgex/STATE.md (always), DECISIONS entries
whose Tags/title match the task's areas, kit cards by Tags, CODEMAP sections for touched dirs/areas,
golden examples by file kind. Tokens are ESTIMATES (chars/4). The bundle never exceeds the cap;
everything left out is listed with a reason. Mode comes from the shared risk classifier
(core/risk, same as validate.mjs). The pack starts with a YAML metadata header (id, versions, budget, selected,
skipped, warnings) that is not counted against the cap; --json reports headerTokensEst. Policy: forgex/context-policy.json overrides the shipped one.
"""
import argparse, hashlib, json, re, sys
from pathlib import Path
for _s in (sys.stdout, sys.stderr):  # Windows consoles (cp874/cp1252): never crash on Thai output
    try: _s.reconfigure(encoding="utf-8", errors="replace")
    except Exception: pass
sys.argv = [x.encode("utf-8", "surrogateescape").decode("utf-8", "replace") for x in sys.argv]  # non-UTF-8 POSIX locales

HERE = Path(__file__).resolve().parent
PKG = HERE.parent  # references/ (shipped) or repo root (source)
sys.path.insert(0, str(PKG / "risk" if (PKG / "risk").is_dir() else PKG / "core/risk"))
from classifier import classify, RULES  # noqa: E402  shared with validate.mjs (classifier.mjs)

def fail(msg): print(f"ctxpack: error: {msg}", file=sys.stderr); sys.exit(2)
def forgex_version():
    try: return json.loads((PKG / "package.json").read_text(encoding="utf-8"))["version"]
    except Exception: return "unknown"

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
    if not p: fail("context-policy.json not found")
    try: pol = json.loads(p.read_text(encoding="utf-8"))
    except (ValueError, OSError) as e: fail(f"invalid policy {p}: {e}")
    if not isinstance(pol, dict): fail(f"invalid policy {p}: not an object")
    miss = [k for k in ("budgets", "always", "priority", "areas") if k not in pol]
    if miss: fail(f"invalid policy {p}: missing {', '.join(miss)}")
    b = pol["budgets"]
    if not isinstance(b, dict) or any(not isinstance(b.get(m), int) or b[m] < 100 for m in RULES["modes"]):
        fail(f"invalid policy {p}: budgets need integer QUICK/STANDARD/GUARDED >= 100")
    if not isinstance(pol["areas"], list) or any(not isinstance(a, dict) or not {"area", "keywords", "paths"} <= a.keys() for a in pol["areas"]):
        fail(f"invalid policy {p}: each area needs area, keywords, paths")
    return pol, p

def kit_dir(arg):
    if arg: return Path(arg)
    cfg = PKG / "config/kit.json"
    name = json.loads(cfg.read_text(encoding="utf-8")).get("kit") if cfg.exists() else None
    return first(PKG / "kit", PKG / "kits" / name if name else None, PKG / "house", PKG / "core/house")

def words(s): return " " + re.sub(r"[^a-z0-9ก-๙]+", " ", s.lower()) + " "

def areas_for(task, paths, pol):
    w, found = words(task), {}
    for a in pol["areas"]:
        why = [k for k in a["keywords"] if words(k) in w or (len(k) > 5 and k in w)]
        why += [p for p in paths if hit(p, a["paths"])]
        if why: found[a["area"]] = why
    return found

def extra_globs():
    """Project forgex/policy.json and shipped default-policy guardedGlobs add to the shared rules (union = conservative)."""
    out = []
    for f in (Path("forgex/policy.json"), PKG / "config/default-policy.json"):
        try: out += json.loads(f.read_text(encoding="utf-8")).get("guardedGlobs", [])
        except Exception: pass
    return out

def check_paths(raw):
    """Normalise to project-relative POSIX paths; reject anything outside the project root."""
    root, out, warns = Path.cwd().resolve(), [], []
    for p in raw:
        q = Path(p); full = (q if q.is_absolute() else root / q).resolve()
        try: rel = full.relative_to(root).as_posix()
        except ValueError: fail(f"path outside project root: {p}")
        if not full.exists(): warns.append(f"path not found (still used for risk): {rel}")
        out.append(rel)
    return out, warns

def tags_of(text):
    m = re.search(r"^\s*-\s*\**Tags:?\**:?\s*(.+)$", text, re.M | re.I)
    return {t.strip().lower() for t in m.group(1).split(",")} if m else set()

def decisions(areas, task):
    """v2.8: select by Tags (tag in task areas, or tag word in the task). Untagged legacy entries fall back to title
    words and are flagged (validate.py --context makes Tags mandatory)."""
    p = Path("forgex/DECISIONS.md")
    if not p.exists(): return [], []
    parts = re.split(r"(?m)^(?=## D-\d+)", p.read_text(encoding="utf-8"))
    keep, skip, w = [], [], words(task)
    for e in parts[1:]:
        head = e.splitlines()[0]; tg = tags_of(e)
        if tg: why = sorted(tg & set(areas) | {x for x in tg if words(x) in w}); how = "tag match"
        else: why = sorted({x for x in re.findall(r"[a-z]{4,}", head.lower()) if f" {x} " in w}); how = "UNTAGGED title-word fallback"
        lab = f"DECISIONS {head.split('·')[0].strip('# ').strip()}"
        if why: keep.append(("decisions", lab, e.strip(), f"{how} {', '.join(why)}"))
        else: skip.append((lab, "no matching tag/area" if tg else "untagged (add '- Tags:'), no title match"))
    return keep, skip

UI_WORDS = ("page", "screen", "component", "ui", "form", "หน้า", "ปุ่ม", "ฟอร์ม")
def is_ui_task(task, paths, pol):
    """Creates or changes a page/UI: a page/component path, the ui area, or a UI word in the task."""
    w = words(task); page_globs = pol.get("goldenByKind", {}).get("form-page", []) + ["**/components/**", "**/*.css"]
    return any(hit(p, page_globs) for p in paths) or any((f" {k} " in w) if k.isascii() else (k in task) for k in UI_WORDS)

STYLE_TAGS = {"ui", "design", "style", "token", "tokens", "theme"}

def cards(kit, areas, task, cap, ui=False):
    if not kit or not (kit / "blocks").is_dir(): return [], []
    scored, skip, w = [], [], words(task)
    for c in sorted((kit / "blocks").glob("*.md")):
        if c.name.startswith("_") or c.name == "INDEX.md": continue
        t = c.read_text(encoding="utf-8"); tg = tags_of(t)
        s = 3 * len(tg & set(areas)) + sum(1 for x in tg if f" {x} " in w) + (2 if words(c.stem.replace("-", " ")).strip() in w else 0)
        (scored if s else skip).append((s, c, t) if s else (f"card {c.stem}", "tags not in task areas" if tg else "untagged card (add '- **Tags:**')"))
    scored.sort(key=lambda x: -x[0])
    # Reserve a slot per area for its core card (primary = first tag), then fill by score.
    prim = lambda t: (re.search(r"Tags:?\**:?\s*([^,\n]+)", t) or [None, ""])[1].strip().lower()
    picked = []
    if ui and cap > 0:  # UI task: always keep one style/design card, even if risk areas would take every slot
        allc = [(3, c, c.read_text(encoding="utf-8")) for c in sorted((kit / "blocks").glob("*.md")) if not c.name.startswith("_") and c.name != "INDEX.md"]
        sty = next((x for x in scored if tags_of(x[2]) & STYLE_TAGS), None) or next((x for x in allc if tags_of(x[2]) & STYLE_TAGS), None)
        if sty:
            if sty not in scored: scored.append(sty); skip[:] = [s for s in skip if s[0] != f"card {sty[1].stem}"]
            picked.append(sty)
    # Allocation rule: risk areas (auth, money, db) first, then policy order; one core slot each until the cap is full.
    order = sorted(areas, key=lambda x: (x not in ("auth", "money", "db"), list(areas).index(x)))
    for ar in order:
        core = next((x for x in scored if prim(x[2]) == ar and x not in picked), None)
        if core and len(picked) < cap: picked.append(core)
    picked += [x for x in scored if x not in picked][: cap - len(picked)]
    picked.sort(key=lambda x: -x[0])
    for s, c, t in scored:
        if all(c != y[1] for y in picked):
            core = prim(t) in areas
            skip.append((f"card {c.stem}", f"{'core card ' if core else ''}over maxCards={cap} (score {s})"))
    core_names = {x[1] for x in picked if prim(x[2]) in areas}
    sty_c = picked[0][1] if ui and picked and tags_of(picked[0][2]) & STYLE_TAGS else None
    return [("cards", f"card {c.stem}", t.strip(), f"tag score {s}" + (" · area core card" if c in core_names else "") + (" · UI style slot" if c == sty_c else "")) for s, c, t in picked], skip

sys.path.insert(0, str(HERE))
import codemap as cmap  # noqa: E402
import tokens  # noqa: E402  tokenizer adapter (tiktoken if installed, else chars/4 flagged estimate)
# codemap  sharded JSON index + import graph + symbol index (v2.8)

def codemap(paths, areas, pol, task="", hops=2, max_related=12):
    """v2.8: forgex/codemap/*.json -> touched files, 1-2 hop import neighbours, symbols named in the task.
    Falls back to v2.7 CODEMAP.md sections (touched dir / area keyword) when no JSON index exists."""
    cm = cmap.load(".")
    notes = []
    mdp = Path("forgex/CODEMAP.md")
    if mdp.exists() and "## Notes" in (t := mdp.read_text(encoding="utf-8")):
        notes = [("codemap", "CODEMAP Notes", "## Notes" + t.split("## Notes", 1)[1].rstrip(), "notes")]
    if cm:
        line = lambda f, why: f"- `{f}`" + (f": {', '.join((cmap.shard_entry(cm, f) or {}).get('symbols', [])[:6])}" if (cmap.shard_entry(cm, f) or {}).get("symbols") else "") + f"  ({why})"
        keep, skip = [], []
        touched = [p for p in paths if cmap.shard_entry(cm, p) is not None]
        if touched: keep.append(("codemap", "CODEMAP touched", "\n".join(line(f, "touched") for f in touched), "touched files (index)"))
        rel = sorted(cmap.related(cm, touched, hops).items(), key=lambda x: (x[1], x[0]))
        if rel:
            shown = rel[:max_related]
            keep.append(("codemap", "CODEMAP related (import graph)", "\n".join(line(f, f"{h} hop") for f, h in shown), f"import graph ≤{hops} hops: {len(rel)} files"))
            if len(rel) > max_related: skip.append((f"CODEMAP related +{len(rel) - max_related}", f"over maxRelated={max_related}"))
        sh = cmap.symbol_hits(cm, task)
        if sh:
            keep.append(("codemap", "CODEMAP symbols", "\n".join(f"- `{k}` → {', '.join(v[:3])}" for k, v in sh.items()), f"symbols named in task: {', '.join(list(sh)[:4])}"))
        if not keep: skip.append(("CODEMAP index", "no touched/related file or named symbol"))
        return keep + notes, skip
    if not mdp.exists(): return [], [("CODEMAP", "forgex/codemap/index.json missing (run codemap.py)")]
    secs = re.split(r"(?m)^(?=## )", mdp.read_text(encoding="utf-8"))
    keep, skip = [], []
    dirs = {str(Path(x).parent) for x in paths}
    kw = {k for a in areas for ar in pol["areas"] if ar["area"] == a for k in ar["keywords"] if len(k) > 3}
    for s in secs[1:]:
        d = s.splitlines()[0][3:].split(" (")[0].rstrip("/")
        if d == "Notes": keep.append(("codemap", "CODEMAP Notes", s.strip(), "notes")); continue
        if d in dirs: keep.append(("codemap", f"CODEMAP {d}/", s.strip(), "touched dir (legacy CODEMAP.md)"))
        elif any(k in d.lower() for k in kw): keep.append(("codemap", f"CODEMAP {d}/", s.strip(), "area keyword in dir (legacy CODEMAP.md)"))
        else: skip.append((f"CODEMAP {d}/", "unrelated dir"))
    return keep, skip

def roadmap_items():
    """v2.9: only the current slice + the next ready one from forgex/roadmap.json, never the whole roadmap."""
    if not Path("forgex/roadmap.json").exists(): return [], []
    import roadmap as rm
    try: r = rm.load()
    except Exception as e: return [], [("roadmap", f"unreadable forgex/roadmap.json ({e})")]
    cur, nxt = rm.current_and_next(r)
    if not cur: return [], [("roadmap", "all slices done")]
    out = [("roadmap", f"roadmap {cur['id']} (current)", rm.slice_text(cur, "Current slice"), "current slice")]
    if nxt: out.append(("roadmap", f"roadmap {nxt['id']} (next)", rm.slice_text(nxt, "Next slice"), "next ready slice"))
    rest = len(r["slices"]) - len(out)
    return out, ([(f"roadmap +{rest} slices", "only current + next are loaded")] if rest else [])

KIND_WORDS = {"form-page": ["page", "form"], "api-route": ["api", "endpoint", "route"], "server-action": ["action", "mutation"], "test": ["test", "spec"]}

def design(kit, ui):
    """Kit DESIGN.md (tokens, fonts, shapes) for any UI task."""
    f = kit / "DESIGN.md" if kit else None
    if not f or not f.exists(): return [], []
    if not ui: return [], [("design DESIGN.md", "not a UI task")]
    return [("design", "design DESIGN.md", f.read_text(encoding="utf-8").strip(), "UI task: design tokens always loaded")], []

def golden(kit, paths, task, pol, ui=False):
    """Score = 3 per touched path matching the kind's globs + 1 per kind word in the task; keep if >= goldenMinScore."""
    if not kit or not (kit / "golden").is_dir(): return [], []
    w, keep, skip, need = words(task), [], [], pol.get("goldenMinScore", 2)
    for kind, globs in pol.get("goldenByKind", {}).items():
        f = kit / "golden" / f"{kind}.md"
        if not f.exists(): continue
        ph = sum(1 for p in paths if hit(p, globs)); kw = [k for k in KIND_WORDS.get(kind, []) if f" {k} " in w]
        s = 3 * ph + len(kw) + (need if ui and kind == "form-page" and ph else 0)
        why = f"golden score {s} (paths {ph}, words {','.join(kw) or '-'}; min {need})"
        if s >= need: keep.append(("golden", f"golden {kind}", f.read_text(encoding="utf-8").strip(), why))
        else: skip.append((f"golden {kind}", why))
    return keep, skip

def yq(s): return json.dumps(str(s), ensure_ascii=False)

def meta_header(m):
    L = ["---", "forgexContextPack:", f"  id: {m['id']}", f"  forgexVersion: {yq(m['forgexVersion'])}",
         f"  policyVersion: {yq(m['policyVersion'])}", f"  policy: {yq(m['policy'])}", f"  mode: {m['mode']}",
         "  modeReasons: [" + ", ".join(yq(r) for r in m["modeReasons"]) + "]",
         f"  budget: {{capTokensEst: {m['cap']}, usedTokensEst: {m['used']}, estimator: \"chars/4\", headerExcluded: true}}",
         "  selected:"] + [f"    - {{item: {yq(l)}, tokensEst: {t}, why: {yq(w)}}}" for l, t, w in m["selected"]] + \
        ["  skipped:"] + [f"    - {{item: {yq(l)}, why: {yq(w)}}}" for l, w in m["skipped"]] + \
        ["  warnings: [" + ", ".join(yq(x) for x in m["warnings"]) + "]", "---", ""]
    return "\n".join(L)

def main():
    ap = argparse.ArgumentParser(); ap.add_argument("task"); ap.add_argument("--path", action="append", default=[])
    ap.add_argument("--mode", choices=["QUICK", "STANDARD", "GUARDED"]); ap.add_argument("--kit"); ap.add_argument("--policy")
    ap.add_argument("--out", default="forgex/context-pack.md"); ap.add_argument("--json", action="store_true"); ap.add_argument("--print", action="store_true")
    a = ap.parse_args()
    pol, pol_path = load_policy(a.policy); kit = kit_dir(a.kit)
    allp, warnings = check_paths(a.path)
    skipped = [(p, "policy skip list") for p in allp if hit(p, pol.get("skip", []))]
    paths = [p for p in allp if not hit(p, pol.get("skip", []))]
    areas = areas_for(a.task, paths, pol)
    if not areas: warnings.append("no area matched (no tags/keywords): only STATE, touched CODEMAP and golden by path")
    risk = classify(mode=a.mode, paths=allp, areas=list(areas), extra_globs=extra_globs(), task=a.task)
    mode = risk["mode"]; warnings += risk["warnings"]
    auto = classify(paths=allp, areas=list(areas), extra_globs=extra_globs(), task=a.task)["mode"]  # classifierMode (no explicit floor)
    cap = pol["budgets"][mode]; ncards = pol.get("maxCards", {}).get(mode, 3)
    cand = {"state": [], "roadmap": [], "decisions": [], "cards": [], "codemap": [], "golden": []}
    for g in pol["always"]:
        for f in sorted(Path(".").glob(g)) or []:
            cand["state"].append(("state", str(f), f.read_text(encoding="utf-8").strip(), "always"))
        if not any(Path(".").glob(g)): skipped.append((g, "missing (run context.py init)"))
    ui = is_ui_task(a.task, paths, pol)
    cand["design"] = []
    for k, fn in (("roadmap", roadmap_items), ("decisions", lambda: decisions(areas, a.task)), ("cards", lambda: cards(kit, areas, a.task, ncards, ui)), ("design", lambda: design(kit, ui)),
                  ("codemap", lambda: codemap(paths, areas, pol, a.task, pol.get("graphHops", 2), pol.get("maxRelated", 12))), ("golden", lambda: golden(kit, paths, a.task, pol, ui))):
        if k in pol.get("skipKinds", {}).get(mode, []):
            items, sk = fn(); skipped += [(i[1], f"kind '{k}' skipped in {mode}") for i in items] + sk; continue
        items, sk = fn(); cand[k] = items; skipped += sk
    head = f"# FORGEX context pack · {mode} · cap {cap} est. tokens\nTask: {a.task}\nAreas: {', '.join(areas) or '-'}\n"
    used, chosen, body = est(head), [], []
    prio = list(pol["priority"]) + [k for k in ("roadmap", "design") if k not in pol["priority"]]
    for k in prio:
        for kind, label, text, why in cand.get(k, []):
            block = f"\n---\n## [{label}]\n{text}\n"; t = est(block)
            if used + t <= cap: used += t; chosen.append((label, t, why)); body.append(block)
            elif kind == "state" and cap - used > 60:
                room = (cap - used - 20) * 4; block = block[:room] + "\n…(truncated to budget)\n"; t = est(block)
                used += t; chosen.append((label + " (truncated)", t, why)); body.append(block)
            else: skipped.append((label, f"over budget ({t} est. tokens, {cap - used} left)"))
    content = head + "".join(body)
    assert est(content) <= cap, "budget invariant broken"
    pid = "cp-" + hashlib.sha1(content.encode()).hexdigest()[:10]
    meta = {"id": pid, "forgexVersion": forgex_version(), "policyVersion": pol.get("version", "unknown"), "policy": str(pol_path),
            "mode": mode, "modeReasons": risk["reasons"], "cap": cap, "used": est(content), "selected": chosen, "skipped": skipped, "warnings": warnings}
    bundle = meta_header(meta) + content
    out = Path(a.out); out.parent.mkdir(parents=True, exist_ok=True); out.write_text(bundle, encoding="utf-8")
    tk = tokens.count(bundle)
    rep = {"packId": pid, "classifierMode": auto, "explicitMode": a.mode, "tokensIn": tk["tokens"], "tokenMethod": tk["method"], "tokenEstimate": tk["estimate"], "forgexVersion": meta["forgexVersion"], "policyVersion": meta["policyVersion"], "estimator": "chars/4",
           "modeReasons": risk["reasons"], "warnings": warnings, "headerTokensEst": est(bundle) - est(content), "mode": mode, "capTokensEst": cap, "usedTokensEst": est(content), "areas": areas, "policy": str(pol_path),
           "kit": str(kit) if kit else None, "loaded": [{"item": l, "tokensEst": t, "why": w} for l, t, w in chosen],
           "skipped": [{"item": l, "why": w} for l, w in skipped], "bundle": str(out)}
    if a.json: print(json.dumps(rep, indent=2, ensure_ascii=False))
    else:
        print(f"pack {pid} · mode {mode} (classifier {auto}) · bundle {tk['tokens']} tokens ({tk['method']}) · {rep['usedTokensEst']}/{cap} est. tokens (chars/4) · areas: {', '.join(areas) or '-'}")
        for r in risk["reasons"]: print(f"  risk: {r}")
        for x in warnings: print(f"  warning: {x}")
        for l, t, w in chosen: print(f"  + {l:32} {t:5}  {w}")
        for l, w in skipped: print(f"  - {l:32}        {w}")
        print(f"bundle: {out}  (read only this file)")
    if a.print: print(bundle)

if __name__ == "__main__":
    main()
