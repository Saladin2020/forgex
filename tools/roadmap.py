#!/usr/bin/env python3
"""FORGEX light planning (stdlib). forgex/roadmap.json is the source; forgex/ROADMAP.md is generated from it.

  forgex.py plan "<goal>"        scaffold roadmap.json (3 milestones, 4 slices to fill) + ROADMAP.md; never overwrites
  forgex.py plan --check         validate: 3-5 milestones with outcomes, slices 1-3 files, deps exist, no cycles,
                                 first slice walkable (has `walk` steps end to end), mode = risk classifier floor
  forgex.py next                 pick the next ready slice (deps done) -> STATE.md Plan; marks it "doing"
  forgex.py slice done <id> [--check-cmd "<cmd>"]   mark done (runs the check first if given; fails if it fails)
Only for new projects or features with >3 slices. QUICK and single tasks skip planning entirely.
"""
import json, re, subprocess, sys
from pathlib import Path

HERE = Path(__file__).resolve().parent; PKG = HERE.parent
sys.path.insert(0, str(PKG / "risk" if (PKG / "risk").is_dir() else PKG / "core/risk")); sys.path.insert(0, str(HERE))
from classifier import classify  # noqa: E402
import context as ctx  # noqa: E402

RJ, RM = Path("forgex/roadmap.json"), Path("forgex/ROADMAP.md")
ORDER = {"QUICK": 0, "STANDARD": 1, "GUARDED": 2}
PH = re.compile(r"<[^>]+>")

def load(): return json.loads(RJ.read_text(encoding="utf-8"))
def save(r): RJ.parent.mkdir(exist_ok=True); RJ.write_text(json.dumps(r, ensure_ascii=False, indent=1) + "\n", encoding="utf-8"); RM.write_text(render(r), encoding="utf-8")

def scaffold(goal):
    ms = [{"id": f"M{i}", "title": "<milestone>", "outcome": "<what the user can see/do>"} for i in (1, 2, 3)]
    sl = [{"id": f"S{i}", "milestone": f"M{1 if i < 3 else i - 1}", "title": "<slice>", "files": ["<path>"], "test": "<command or test file that proves it>",
           "dependsOn": [] if i == 1 else [f"S{i - 1}"], "mode": None, "status": "todo"} for i in (1, 2, 3, 4)]
    sl[0]["walk"] = ["<step 1 on the real user path>", "<step 2>", "<last step: user sees result>"]
    return {"version": "2.9.0", "goal": " ".join(goal.split()), "milestones": ms, "slices": sl}

def cycles(sl):
    deps = {s["id"]: s.get("dependsOn", []) for s in sl}; seen, stack, out = set(), [], []
    def dfs(n):
        if n in stack: out.append(" -> ".join(stack[stack.index(n):] + [n])); return
        if n in seen or n not in deps: return
        seen.add(n); stack.append(n)
        for d in deps[n]: dfs(d)
        stack.pop()
    for n in deps: dfs(n)
    return out

def problems(r, placeholders_ok=False):
    p, ms, sl = [], r.get("milestones", []), r.get("slices", [])
    if not 3 <= len(ms) <= 5: p.append(f"milestones: need 3-5, have {len(ms)}")
    if len(sl) <= 3: p.append(f"slices: planning is for >3 slices (have {len(sl)}); use a single task instead")
    mids, ids = {m.get("id") for m in ms}, [s.get("id") for s in sl]
    for m in ms:
        if not (m.get("outcome") or "").strip(): p.append(f"{m.get('id')}: missing user-visible outcome")
    if len(set(ids)) != len(ids): p.append("slices: duplicate ids")
    for s in sl:
        sid, fs = s.get("id"), s.get("files") or []
        if not 1 <= len(fs) <= 3: p.append(f"{sid}: {len(fs)} files (slice size must be 1-3)")
        if not (s.get("test") or "").strip(): p.append(f"{sid}: no test (each slice must be independently testable)")
        if s.get("milestone") not in mids: p.append(f"{sid}: milestone {s.get('milestone')} not found")
        for d in s.get("dependsOn", []):
            if d not in ids: p.append(f"{sid}: dependsOn {d} does not exist")
        if not placeholders_ok:
            if any(PH.search(str(x)) for x in [s.get("title"), s.get("test"), *fs]): p.append(f"{sid}: still has <placeholders>")
            want = classify(paths=[f for f in fs if not PH.search(f)], task=f"{s.get('title', '')} {s.get('test', '')}")["mode"]
            if s.get("mode") is not None and ORDER.get(s["mode"], -1) < ORDER[want]: p.append(f"{sid}: mode {s['mode']} under-rated, classifier says {want}")
    p += [f"dependsOn cycle: {c}" for c in cycles(sl)]
    if sl:
        first = sl[0]
        if first.get("dependsOn"): p.append(f"{first.get('id')}: first slice must not depend on others")
        w = [x for x in first.get("walk") or [] if (placeholders_ok or not PH.search(x))]
        if len(w) < 2: p.append(f"{first.get('id')}: first slice must be walkable end to end (`walk`: >=2 real user-path steps)")
    if not placeholders_ok and any(PH.search(str(m.get(k, ""))) for m in ms for k in ("title", "outcome")): p.append("milestones: still have <placeholders>")
    return p

def set_modes(r):
    for s in r["slices"]:
        fs = [f for f in s.get("files", []) if not PH.search(f)]
        want = classify(paths=fs, task=f"{s.get('title', '')} {s.get('test', '')}")["mode"] if fs else None
        if want and (s.get("mode") not in ORDER or ORDER[s["mode"]] < ORDER[want]): s["mode"] = want
    return r

def render(r):
    L = ["# ROADMAP (generated from forgex/roadmap.json by forgex.py; edit the JSON)", f"Goal: {r.get('goal', '')}", ""]
    box = {"done": "x", "doing": "~"}
    for m in r["milestones"]:
        L.append(f"## {m['id']} · {m.get('title', '')} — outcome: {m.get('outcome', '')}")
        for s in [s for s in r["slices"] if s.get("milestone") == m["id"]]:
            L.append(f"- [{box.get(s.get('status'), ' ')}] {s['id']} {s.get('title', '')} ({len(s.get('files', []))} files · {s.get('mode') or '?'} · deps {', '.join(s.get('dependsOn', [])) or '-'})")
        L.append("")
    return "\n".join(L)

def ready(r):
    done = {s["id"] for s in r["slices"] if s.get("status") == "done"}
    return [s for s in r["slices"] if s.get("status") != "done" and all(d in done for d in s.get("dependsOn", []))]

def current_and_next(r):
    """For ctxpack: the slice in progress (or first ready) and the one after it. Never the whole roadmap."""
    cur = next((s for s in r["slices"] if s.get("status") == "doing"), None) or next(iter(ready(r)), None)
    if not cur: return None, None
    done = {s["id"] for s in r["slices"] if s.get("status") == "done"} | {cur["id"]}
    nxt = next((s for s in r["slices"] if s.get("status") not in ("done", "doing") and s is not cur and all(d in done for d in s.get("dependsOn", []))), None)
    return cur, nxt

def slice_text(s, label):
    return (f"{label} {s['id']} · {s.get('title', '')} · {s.get('mode') or '?'}\n- files: {', '.join(s.get('files', []))}\n- test: {s.get('test', '')}\n- deps: {', '.join(s.get('dependsOn', [])) or '-'}"
            + (f"\n- walk: {' → '.join(s['walk'])}" if s.get("walk") else ""))

def cmd_plan(args):
    if "--check" in args:
        if not RJ.exists(): sys.exit("plan: forgex/roadmap.json missing (run forgex.py plan \"<goal>\")")
        r = set_modes(load()); p = problems(r)
        if not p: save(r)
        print("\n".join(f"FAIL  {x}" for x in p) or f"PASS  roadmap: {len(r['milestones'])} milestones, {len(r['slices'])} slices"); sys.exit(1 if p else 0)
    goal = " ".join(a for a in args if not a.startswith("--"))
    if not goal: sys.exit('usage: forgex.py plan "<goal>" | plan --check')
    if RJ.exists(): print(f"exists: {RJ} (edit it, then plan --check)"); return
    r = scaffold(goal); p = problems(r, placeholders_ok=True)
    assert not p, p  # scaffold must be structurally valid
    save(r); print(f"created: {RJ} + {RM}. Fill titles/outcomes/files/tests/walk (3-5 milestones, slices 1-3 files), then `forgex.py plan --check`.")

def cmd_next(args):
    r = load(); p = problems(set_modes(r))
    if p: print("\n".join(f"FAIL  {x}" for x in p)); sys.exit(1)
    cur, _ = current_and_next(r)
    if not cur: print("roadmap: all slices done"); return
    cur["status"] = "doing"; save(r)
    steps = [f"{cur['id']} {cur['title']}: edit {', '.join(cur['files'])}", f"test: {cur['test']}", f"then `forgex.py slice done {cur['id']}`"]
    sys.argv = ["context.py", "close", "--now", f"slice {cur['id']} ({cur['mode']}) of roadmap: {r['goal']}", "--mode", cur["mode"] or "STANDARD", "--by", "forgex next"] + [x for s in steps for x in ("--next", s)]
    try: ctx.main()
    except SystemExit as e:
        if e.code: raise
    print(f"next: {cur['id']} · {cur['mode']} · {cur['title']}")

def cmd_slice(args):
    if len(args) < 2 or args[0] != "done": sys.exit("usage: forgex.py slice done <id> [--check-cmd \"<cmd>\"]")
    r = load(); s = next((x for x in r["slices"] if x["id"] == args[1]), None)
    if not s: sys.exit(f"slice {args[1]} not found")
    if "--check-cmd" in args:
        c = args[args.index("--check-cmd") + 1]; rc = subprocess.run(c, shell=True).returncode
        if rc:
            s["failedChecks"] = s.get("failedChecks", 0) + 1; save(r)
            print(f"FAIL  {s['id']}: check failed (exit {rc}); not marked done"); sys.exit(1)
    s["status"] = "done"; save(r)
    left = [x["id"] for x in r["slices"] if x.get("status") != "done"]
    print(f"done: {s['id']} · left: {', '.join(left) or 'none'} · optional: `forgex.py harvest {s['id']}` (personal kit, you confirm)")
    import review
    if not left: t = review.prompt_text("project", r.get("goal", "project")[:40].strip() or "project")
    elif all(x.get("status") == "done" for x in r["slices"] if x.get("milestone") == s.get("milestone")): t = review.prompt_text("milestone", s.get("milestone"))
    else: t = ""
    if t: print(t)
