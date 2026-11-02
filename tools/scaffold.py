#!/usr/bin/env python3
"""FORGEX scaffold: JSON stubs per mode + render + pattern (stdlib only). Run from project root.

  scaffold.py quick    <taskId> "<goal>" [--path P ...] [--check CMD ...]
  scaffold.py standard <taskId> "<goal>" [--path P ...] [--check CMD ...] [--blocks a,b,c] [--ac "..." ...]
  scaffold.py guarded  <taskId> "<goal>" [--path P ...] [--check CMD ...] [--ac "..." ...] [--risk high|critical]
  scaffold.py render   forgex/tasks/<taskId>.json        -> prints closeout Markdown (PR body); never stored twice
  scaffold.py pattern  forgex/tasks/<taskId>.json        -> appends its `pattern` to forgex/patterns.md
Stubs go to forgex/tasks/<taskId>.json and are never overwritten. The agent fills values only.
"""
import argparse, json, re, subprocess, sys
from pathlib import Path

OUT = Path("forgex/tasks")
RISK = {"quick": "low", "standard": "medium"}

def tid(s):
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]{0,63}", s):
        sys.exit(f"invalid taskId {s!r}: letters, digits, . _ - only")
    return s

def checks(cmds, ids):
    cmds = cmds or ["TODO: exact command"]
    out = []
    for i, c in enumerate(cmds, 1):
        k = {"cmd": c, "status": "NOT_RUN", "reason": "not run yet"}
        if ids: k = {"id": f"C{i}", **k}
        out.append(k)
    return out

def head():
    try:
        h = subprocess.run(["git", "rev-parse", "--short", "HEAD"], capture_output=True, text=True, check=True).stdout.strip()
        return h if re.fullmatch(r"[0-9a-f]{7,40}", h) else None
    except Exception:
        return None

def stub(mode, a):
    c = {"contractVersion": "2.2", "taskId": tid(a.taskId), "mode": mode.upper(),
         "riskLevel": RISK.get(mode) or a.risk, "goal": a.goal,
         "touchedPaths": a.path or ["TODO/path"], "checks": checks(a.check, mode != "quick"), "status": "planned"}
    if mode == "quick":
        return c
    acs = a.ac or ["TODO: observable criterion"]
    c["acceptanceCriteria"] = [{"id": f"AC-{i}", "criterion": t, "status": "NOT_RUN", "checks": []} for i, t in enumerate(acs, 1)]
    if mode == "standard":
        bl = [b.strip() for b in (a.blocks or "").split(",") if b.strip()]
        if bl:
            c["blocks"] = [{"name": n + (" (seed)" if i == 0 else ""), "interface": "", "checks": []} for i, n in enumerate(bl)]
        c["git"] = {"branch": f"forgex/{a.taskId}"}
        return c
    c.update(nonGoals=[], constraints=["Preserve user changes"], git={"branch": f"forgex/{a.taskId}"},
             deployment={"rollbackRunbook": "guides/runbooks.md#TODO"}, budget={"source": "unavailable"})
    if head(): c["git"]["baseCommit"] = head()
    return c

def render(c):
    st = lambda k: f"`{k['cmd']}` {k['status']}" + (f" ({k['reason']})" if k.get("reason") and k["status"] != "PASS" else "")
    if c["mode"] == "QUICK":
        lines = [f"Goal: {c['goal']}", "Check: " + "; ".join(st(k) for k in c["checks"]), f"Result: {c.get('result', c['status'])}"]
        if c.get("pattern"): lines.append(f"Pattern: {c['pattern']}")
        return "\n".join(lines) + "\n"
    L = [f"## {c['taskId']} [{c['mode']}] {c['status']}", f"**Goal:** {c['goal']}", ""]
    if c.get("result"): L += [f"**Result:** {c['result']}", ""]
    L += ["| AC | Criterion | Status | Checks |", "|---|---|---|---|"]
    L += [f"| {a['id']} | {a['criterion']} | {a['status']} | {', '.join(a.get('checks', [])) or a.get('rationale', '')} |" for a in c.get("acceptanceCriteria", [])]
    L += ["", "| Check | Command / URL | Status |", "|---|---|---|"]
    L += [f"| {k.get('id', '-')} | `{k['cmd']}` | {k['status']} |" for k in c["checks"]]
    L += ["", "**Files:** " + ", ".join(c["touchedPaths"])]
    if c.get("git", {}).get("branch"): L.append(f"**Branch:** {c['git']['branch']}")
    if c.get("deployment", {}).get("rollbackRunbook"): L.append(f"**Rollback:** {c['deployment']['rollbackRunbook']}")
    if c.get("budget"): b = c["budget"]; L.append(f"**Budget:** {b['source']}" + (f" · {b.get('tokensIn')} in / {b.get('tokensOut')} out · {b.get('attempts')} attempt(s)" if b["source"] != "unavailable" else ""))
    for d in c.get("discoveries", []): L.append(f"- {d['class']}: {d['note']}")
    if c.get("pattern"): L.append(f"**Pattern candidate:** {c['pattern']}")
    return "\n".join(L) + "\n"

def main():
    ap = argparse.ArgumentParser(); sub = ap.add_subparsers(dest="cmd", required=True)
    for m in ("quick", "standard", "guarded"):
        s = sub.add_parser(m); s.add_argument("taskId"); s.add_argument("goal")
        s.add_argument("--path", action="append"); s.add_argument("--check", action="append")
        if m != "quick": s.add_argument("--ac", action="append")
        if m == "standard": s.add_argument("--blocks")
        if m == "guarded": s.add_argument("--risk", default="high", choices=["high", "critical"])
    for m in ("render", "pattern"):
        sub.add_parser(m).add_argument("file")
    a = ap.parse_args()
    if a.cmd in ("quick", "standard", "guarded"):
        f = OUT / f"{tid(a.taskId)}.json"
        if f.exists(): sys.exit(f"exists, not overwriting: {f}")
        f.parent.mkdir(parents=True, exist_ok=True)
        f.write_text(json.dumps(stub(a.cmd, a), indent=2, ensure_ascii=False) + "\n"); print(f)
    elif a.cmd == "render":
        print(render(json.loads(Path(a.file).read_text())), end="")
    else:
        c = json.loads(Path(a.file).read_text())
        if not c.get("pattern"): sys.exit("no `pattern` in contract")
        pf = Path("forgex/patterns.md")
        if not pf.exists():
            pf.parent.mkdir(parents=True, exist_ok=True); pf.write_text("# Project patterns (FORGEX)\n<!-- one line each; rg to search; [candidate n/2] -> [rule] at 2+ -->\n")
        line = f"- [candidate 1/2] {c['pattern']} ({c['taskId']})\n"
        if line in pf.read_text(): sys.exit("already recorded")
        with pf.open("a") as fh: fh.write(line)
        print(line, end="")

if __name__ == "__main__":
    main()
