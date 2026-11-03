#!/usr/bin/env python3
"""FORGEX feedback loop (stdlib, v2.10): end-of-work rating, end-of-project review, prune suggestions.

  forgex.py rate --scope milestone|project|quick --id <M1|name> <first-try|1-2|many|skip> [--log forgex/log.jsonl]
  forgex.py review [--kit DIR] [--history FILE] [--log forgex/log.jsonl]   -> forgex/REVIEW.md + forgex/review.json
  forgex.py review --accept <id> | --skip <id> [--kit DIR]                 -> records your choice for one item
  forgex.py prune --kit DIR [--stale-days 180]                               -> duplicate/stale card suggestions only
  forgex.py prune --confirm <card> --kit DIR                                 -> moves ONE card to DIR/pruned/ (+INDEX line out)
Rating: asked only when a milestone or the project closes, never for QUICK; one choice; `skip` logs rating=null and
never blocks; off via "feedback": {"rating": false} in forgex/context-policy.json (or the shipped config).
Review and prune only SUGGEST. Nothing in a kit changes unless the person accepts an item and runs its command;
prune never deletes (moves to pruned/, reversible) and refuses anything that is not a personal kit.
"""
import datetime, json, re, sys
from pathlib import Path
HERE = Path(__file__).resolve().parent; sys.path.insert(0, str(HERE))
import tokens, harvest  # noqa: E402

RATINGS = {"first-try": "passed first try", "1-2": "1-2 fix rounds", "many": "many fixes", "skip": None}
DEFAULT = {"rating": True, "review": True, "staleDays": 180}

def feedback_cfg():
    for p in (Path("forgex/context-policy.json"), HERE.parent / "config/context-policy.json"):
        if p.exists():
            try: return {**DEFAULT, **(json.loads(p.read_text(encoding="utf-8")).get("feedback") or {})}
            except Exception: pass
    return dict(DEFAULT)

def rows(log):
    p = Path(log)
    return [json.loads(x) for x in p.read_text(encoding="utf-8").splitlines() if x.strip()] if p.exists() else []

def append(log, e):
    p = Path(log); p.parent.mkdir(parents=True, exist_ok=True)
    with p.open("a", encoding="utf-8") as fh: fh.write(json.dumps(e, ensure_ascii=False) + "\n")

def prompt_text(scope, sid):
    """What roadmap/close prints at milestone/project close. Empty when disabled or QUICK."""
    if scope not in ("milestone", "project") or not feedback_cfg()["rating"]: return ""
    return (f"{scope} {sid} closed. Rate it (one choice, or skip): forgex.py rate --scope {scope} --id {sid} first-try|1-2|many|skip"
            + ("\nThen: forgex.py review (suggestions only; you accept or skip each)" if feedback_cfg()["review"] else ""))

def cmd_rate(a):
    opt = lambda k, d=None: a[a.index(k) + 1] if k in a and a.index(k) + 1 < len(a) else d
    scope, sid, log = opt("--scope", "milestone"), opt("--id", "-"), opt("--log", "forgex/log.jsonl")
    vals = {opt(k) for k in ("--scope", "--id", "--log")}
    choice = next((x for x in a if x in RATINGS and x not in vals), None)
    if scope == "quick": print("rate: not asked for QUICK tasks; nothing logged"); return
    if scope not in ("milestone", "project"): sys.exit("rate: --scope milestone|project")
    if not feedback_cfg()["rating"]: print("rate: disabled in config (feedback.rating=false); nothing logged"); return
    if choice is None: choice = "skip"  # no answer never blocks
    e = {"ts": datetime.datetime.now().astimezone().isoformat(timespec="seconds"), "kind": "rating", "scope": scope, "task": sid,
         "rating": None if choice == "skip" else choice, "skipped": choice == "skip"}
    append(log, e); print(json.dumps(e, ensure_ascii=False))

# ---------- cards / prune ----------
STOP = set("a an the and or of to in on for with by from is are be use uses via per into".split())
def card_info(p):
    t = p.read_text(encoding="utf-8", errors="ignore")
    g = lambda k: (re.search(rf"\*\*{k}:\*\*\s*(.+)", t) or [None, ""])[1].strip()
    words = {w for w in re.findall(r"[a-z0-9ก-๙]+", (p.stem.replace("-", " ") + " " + g("What") + " " + g("Reuse")).lower()) if w not in STOP and len(w) > 1}
    return {"card": p.stem, "path": p, "what": g("What"), "tags": g("Tags"), "used": g("Used"), "gotchas": g("Gotchas"), "words": words}

def kit_cards(kit):
    b = Path(kit) / "blocks"
    return [card_info(c) for c in sorted(b.glob("*.md")) if not c.name.startswith("_") and c.name != "INDEX.md"] if b.is_dir() else []

def jacc(a, b): return len(a & b) / len(a | b) if a | b else 0.0

def prune_suggestions(kit, stale_days=None, today=None):
    stale_days = stale_days or feedback_cfg()["staleDays"]; today = today or datetime.date.today()
    cs = kit_cards(kit); out = []
    for i, x in enumerate(cs):
        for y in cs[i + 1:]:
            s = jacc(x["words"], y["words"])
            if s >= 0.5: out.append({"kind": "duplicate", "card": y["card"], "of": x["card"], "score": round(s, 2),
                                    "why": f"`{y['card']}` overlaps `{x['card']}` ({round(s * 100)}% same words); merge into one, prune the other"})
    for c in cs:
        d = None
        if c["used"]:
            try: d = datetime.date.fromisoformat(c["used"][:10])
            except ValueError: d = None
        if d is None: d = datetime.date.fromtimestamp(c["path"].stat().st_mtime)
        age = (today - d).days
        if age > stale_days and (c["gotchas"].startswith("?") or not c["used"] or "?" in c["what"]):
            out.append({"kind": "stale", "card": c["card"], "age": age, "why": f"`{c['card']}` not used for {age} days and still unverified (`?`)"})
        elif age > stale_days * 2:
            out.append({"kind": "stale", "card": c["card"], "age": age, "why": f"`{c['card']}` not used for {age} days"})
    return out

def prune_confirm(card, kit):
    kit = Path(kit)
    if not harvest.personal(kit): sys.exit(f"prune: refused: {kit} is not a personal kit (needs kit.json or private-terms.txt; never core/house)")
    name = Path(card).stem; src = kit / "blocks" / f"{name}.md"
    if not src.exists(): sys.exit(f"prune: {src} not found")
    dst = kit / "pruned" / f"{name}.md"; dst.parent.mkdir(exist_ok=True)
    if dst.exists(): dst = dst.with_name(f"{name}.{datetime.datetime.now():%Y%m%d%H%M%S}.md")
    src.rename(dst)
    idx = kit / "blocks/INDEX.md"
    if idx.exists():
        idx.write_text("".join(l for l in idx.read_text(encoding="utf-8").splitlines(True) if not re.match(rf"\s*-\s*`{re.escape(name)}`", l)), encoding="utf-8")
    print(f"pruned (moved, not deleted): {src} -> {dst}. Undo: move it back and re-add the INDEX line.")

def cmd_prune(a):
    kit = a[a.index("--kit") + 1] if "--kit" in a else sys.exit("prune needs --kit DIR")
    if "--confirm" in a: return prune_confirm(a[a.index("--confirm") + 1], kit)
    sd = int(a[a.index("--stale-days") + 1]) if "--stale-days" in a else None
    s = prune_suggestions(kit, sd)
    for x in s: print(f"suggest {x['kind']}: {x['why']}")
    print(f"{len(s)} suggestion(s). Nothing changed. Only if the person says yes: forgex.py prune --confirm <card> --kit {kit}" if s else "prune: no duplicate or stale cards")

# ---------- review ----------
def lessons(log_rows, roadmap):
    out = []
    for s in (roadmap or {}).get("slices", []):
        n = s.get("failedChecks", 0)
        if n >= 2:
            area = Path((s.get("files") or ["?"])[0]).parent.as_posix()
            out.append({"spot": f"slice {s['id']} ({s.get('title', '')})", "fixes": n,
                        "rule": f"For `{area}/`: write the slice test first and run `{s.get('test') or 'the check'}` before `slice done`"})
    for r in log_rows:
        if r.get("kind") == "rating" and r.get("rating") in ("1-2", "many"):
            out.append({"spot": f"{r.get('scope')} {r.get('task')}", "fixes": 2 if r["rating"] == "1-2" else 3,
                        "rule": "Before closing: walk the user path end to end and add a golden example for the part that was redone"})
    return out

def numbers(log_rows, history):
    tk = [r for r in log_rows if r.get("kind") != "rating"]
    tot = sum((r.get("tokensIn") or 0) + (r.get("tokensOut") or 0) for r in tk)
    per = round(tot / len(tk)) if tk else 0
    fg, g = tokens.false_guarded(tk)
    cases = [r.get("task") for r in tk if r.get("classifierMode") == "GUARDED" and r.get("actualMode") in tokens.MODES and r["actualMode"] != "GUARDED"]
    hist = rows(history) if history else []
    avg = round(sum(h.get("tokensPerTask", 0) for h in hist) / len(hist)) if hist else None
    rt = [r for r in log_rows if r.get("kind") == "rating"]
    return {"tasks": len(tk), "tokens": tot, "tokensPerTask": per, "earlierAvgPerTask": avg,
            "deltaPct": round((per - avg) * 100 / avg) if avg else None, "falseGuarded": fg, "classifiedGuarded": g, "falseGuardedCases": cases,
            "ratings": {k: sum(1 for r in rt if (r.get("rating") or "skip") == k) for k in RATINGS}}

def build_review(kit=None, history=None, log="forgex/log.jsonl"):
    lr = rows(log); rp = Path("forgex/roadmap.json"); rm = json.loads(rp.read_text(encoding="utf-8")) if rp.exists() else None
    items = []
    def add(kind, text, action): items.append({"id": f"R{len(items) + 1}", "kind": kind, "text": text, "action": action, "status": "pending"})
    existing = kit_cards(kit) if kit else []
    for d in sorted(Path("forgex/harvest").glob("*.md")) if Path("forgex/harvest").is_dir() else []:
        ci = card_info(d); dup = next((c["card"] for c in existing if jacc(ci["words"], c["words"]) >= 0.5), None)
        if dup: add("card-merge", f"harvest draft `{d.name}` looks like existing card `{dup}`: merge by hand or skip", f"open {d} and {Path(kit) / 'blocks' / (dup + '.md')}")
        else: add("card-keep", f"keep harvest draft `{d.name}` ({ci['what'][:80]})", f"forgex.py harvest --confirm {d.as_posix()} --kit {kit or '<personal kit>'}")
    if kit:
        for s in prune_suggestions(kit): add("card-prune", s["why"], f"forgex.py prune --confirm {s['card']} --kit {kit}")
    ls = lessons(lr, rm)
    for l in ls: add("lesson", f"{l['spot']} needed {l['fixes']}+ fix rounds. Proposed rule: {l['rule']}", f"append rule to forgex/LESSONS.md: {l['rule']}")
    n = numbers(lr, history)
    ntext = f"tokens: {n['tokens']} over {n['tasks']} tasks ({n['tokensPerTask']}/task" + (f", {n['deltaPct']:+d}% vs earlier avg {n['earlierAvgPerTask']})" if n["earlierAvgPerTask"] else ", no earlier projects yet)")
    ntext += f"; false GUARDED {n['falseGuarded']}/{n['classifiedGuarded']}" + (f" ({', '.join(map(str, n['falseGuardedCases']))})" if n["falseGuardedCases"] else "")
    if history: add("numbers", ntext + " — record this project in history for next time", f"append to {history}")
    recs = []
    if n["classifiedGuarded"] and n["falseGuarded"] / n["classifiedGuarded"] > 0.2: recs.append(f"Tune risk signals: {n['falseGuarded']}/{n['classifiedGuarded']} GUARDED were not needed ({', '.join(map(str, n['falseGuardedCases']))}); add cases to core/risk/cases.json")
    if ls: recs.append(f"Adopt the lesson rule for {ls[0]['spot']}: {ls[0]['rule']}")
    if n["deltaPct"] is not None and n["deltaPct"] > 20: recs.append(f"Tokens/task up {n['deltaPct']}% vs earlier projects: lower ctxpack budgets or prune cards")
    if any(i["kind"] == "card-prune" for i in items): recs.append("Prune the suggested duplicate/stale cards so packs stay small")
    if any(i["kind"] == "card-keep" for i in items) and len(recs) < 3: recs.append("Confirm the useful harvest drafts into your kit")
    for r in recs[:3]: add("recommendation", r, "you decide; no command runs automatically")
    return {"version": "2.10.0", "created": datetime.datetime.now().astimezone().isoformat(timespec="seconds"), "kit": kit, "history": history, "numbers": n, "items": items}

def render(rv):
    n = rv["numbers"]; L = ["# REVIEW (suggestions only; accept or skip each: forgex.py review --accept Rn | --skip Rn)", f"Created: {rv['created']}", ""]
    sec = [("Cards", ("card-keep", "card-merge", "card-prune")), ("Lessons", ("lesson",)), ("Numbers", ("numbers",)), ("Top recommendations (max 3)", ("recommendation",))]
    for title, kinds in sec:
        L.append(f"## {title}")
        if title == "Numbers":
            L.append(f"- tokens {n['tokens']} · {n['tasks']} tasks · {n['tokensPerTask']}/task · earlier avg {n['earlierAvgPerTask'] if n['earlierAvgPerTask'] is not None else 'n/a'} · false GUARDED {n['falseGuarded']}/{n['classifiedGuarded']}"
                     + (f" ({', '.join(map(str, n['falseGuardedCases']))})" if n["falseGuardedCases"] else "") + f" · ratings {n['ratings']}")
        its = [i for i in rv["items"] if i["kind"] in kinds]
        L += [f"- [{ {'accepted': 'x', 'skipped': '-'}.get(i['status'], ' ') }] {i['id']} {i['text']}  \n  → {i['action']}" for i in its] or (["- (none)"] if title != "Numbers" else [])
        L.append("")
    return "\n".join(L)

def cmd_review(a):
    opt = lambda k: a[a.index(k) + 1] if k in a else None
    rj, rmd = Path("forgex/review.json"), Path("forgex/REVIEW.md")
    for flag, st in (("--accept", "accepted"), ("--skip", "skipped")):
        if flag in a:
            if not rj.exists(): sys.exit("review: run forgex.py review first")
            rv = json.loads(rj.read_text(encoding="utf-8")); it = next((i for i in rv["items"] if i["id"] == opt(flag)), None)
            if not it: sys.exit(f"review: item {opt(flag)} not found")
            it["status"] = st
            if st == "accepted" and it["kind"] == "lesson":
                p = Path("forgex/LESSONS.md"); old = p.read_text(encoding="utf-8") if p.exists() else "# LESSONS (accepted from REVIEW)\n"
                p.write_text(old + f"- {it['action'].split(': ', 1)[1]}\n", encoding="utf-8")
            if st == "accepted" and it["kind"] == "numbers" and rv.get("history"):
                append(rv["history"], {"ts": rv["created"], "project": Path.cwd().name, **{k: rv["numbers"][k] for k in ("tasks", "tokens", "tokensPerTask", "falseGuarded", "classifiedGuarded")}})
            rj.write_text(json.dumps(rv, ensure_ascii=False, indent=1), encoding="utf-8"); rmd.write_text(render(rv), encoding="utf-8")
            print(f"{it['id']} {st}." + (f" To apply, run: {it['action']}" if st == "accepted" and it["action"].startswith("forgex.py") else ""))
            return
    if not feedback_cfg()["review"] and "--force" not in a: print("review: disabled in config (feedback.review=false)"); return
    rv = build_review(opt("--kit"), opt("--history") or (str(Path(opt("--kit")) / "metrics/projects.jsonl") if opt("--kit") else None), opt("--log") or "forgex/log.jsonl")
    Path("forgex").mkdir(exist_ok=True); rj.write_text(json.dumps(rv, ensure_ascii=False, indent=1), encoding="utf-8"); rmd.write_text(render(rv), encoding="utf-8")
    print(render(rv)); print(f"wrote {rmd} + {rj}. Suggestions only; nothing in the kit changed.")
