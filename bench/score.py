#!/usr/bin/env python3
"""FORGEX A/B bench scorer (stdlib only).
  score.py --a <arm A folder> --b <arm B folder> [--results results.csv] [--out report.md] [--no-cmd]
Runs tasks/checks.json against each arm's final folder (grep / exists / style / cmd checks), reads results.csv
(arm,task,tokens,rounds,minutes,reexplained,notes) and prints a markdown table with a winner per metric.
cmd checks run only if the arm has node_modules (else SKIP, not counted)."""
import argparse, csv, json, re, subprocess, sys
from pathlib import Path
for _s in (sys.stdout, sys.stderr):  # Windows consoles (cp874/cp1252): never crash on Thai output
    try: _s.reconfigure(encoding="utf-8", errors="replace")
    except Exception: pass
sys.argv = [x.encode("utf-8", "surrogateescape").decode("utf-8", "replace") for x in sys.argv]  # non-UTF-8 POSIX locales

HERE = Path(__file__).resolve().parent
SKIP_DIRS = {"node_modules", ".next", ".git", "dist", "forgex"}

def braces(g):
    m = re.search(r"\{([^}]*)\}", g)
    return [x for o in m.group(1).split(",") for x in braces(g[:m.start()] + o + g[m.end():])] if m else [g]

def files(root, pattern):
    out = set()
    for g in braces(pattern):
        for p in root.glob(g):
            if p.is_file() and not SKIP_DIRS & set(p.relative_to(root).parts): out.add(p)
    return sorted(out)

def run_check(root, c, style, allow_cmd):
    t = c["type"]
    if t == "exists": return bool(files(root, c["files"])), ""
    if t == "grep":
        fs = files(root, c["files"]); rx = re.compile(c["pattern"])
        hits = [f.relative_to(root).as_posix() for f in fs if rx.search(f.read_text(errors="ignore"))]
        if c["expect"] == "present": return bool(hits), "" if hits else ("no files" if not fs else "not found")
        if not fs: return False, "no files"
        return not hits, ", ".join(hits[:3])
    if t == "style":
        fs = files(root, c["files"])
        if not fs: return False, "no files"
        txt = "\n".join(f.read_text(errors="ignore") for f in fs)
        tok = any(k in txt or k.replace("--color-", "-") in txt for k in style["tokens"])
        hexes = re.findall(style["forbiddenHex"], txt)
        return tok and not hexes, ("" if tok else "no tokens ") + (f"raw hex {hexes[:2]}" if hexes else "")
    if t == "cmd":
        if not allow_cmd or not (root / "node_modules").is_dir(): return None, "skipped (no node_modules)"
        r = subprocess.run(c["cmd"], shell=True, cwd=root, capture_output=True, text=True, encoding="utf-8", timeout=600)
        return r.returncode == 0, "" if r.returncode == 0 else (r.stdout + r.stderr).strip()[-120:]
    return False, f"unknown check type {t}"

def num(x):
    try: return float(x)
    except (TypeError, ValueError): return None

def win(a, b, lower=True):
    if a is None or b is None or a == b: return "tie" if a == b and a is not None else "-"
    return ("A" if a < b else "B") if lower else ("A" if a > b else "B")

def fmt(x): return "-" if x is None else (str(int(x)) if float(x).is_integer() else f"{x:.1f}")

def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--a", required=True); ap.add_argument("--b", required=True)
    ap.add_argument("--results", default="results.csv"); ap.add_argument("--out"); ap.add_argument("--no-cmd", action="store_true")
    ap.add_argument("--checks", default=str(HERE / "tasks/checks.json")); ap.add_argument("--style", default=str(HERE / "style.json"))
    a = ap.parse_args()
    checks, style = json.loads(Path(a.checks).read_text(encoding="utf-8")), json.loads(Path(a.style).read_text(encoding="utf-8"))
    arms = {"A": Path(a.a).resolve(), "B": Path(a.b).resolve()}
    for k, v in arms.items():
        if not (v / "package.json").is_file(): ap.error(f"arm {k}: {v} has no package.json (not a project folder)")
    L = [f"# FORGEX A/B bench report", "", f"A = `{arms['A']}` (no FORGEX) · B = `{arms['B']}` (FORGEX) · style: {style['name']}", "",
         "## Objective checks (final folder of each arm)", "", "| Task | Mode | A pass | B pass | Winner |", "|---|---|---:|---:|---|"]
    detail, tot = [], {"A": [0, 0], "B": [0, 0]}
    for tid, t in checks.items():
        sc = {}
        for arm, root in arms.items():
            p = n = 0
            for c in t["checks"]:
                ok, why = run_check(root, c, style, not a.no_cmd)
                if ok is None: detail.append(f"| {tid} | {arm} | {c['id']} | SKIP | {why} |"); continue
                n += 1; p += ok
                detail.append(f"| {tid} | {arm} | {c['id']} | {'PASS' if ok else 'FAIL'} | {why} |")
            sc[arm] = (p, n); tot[arm][0] += p; tot[arm][1] += n
        ra, rb = (sc[x][0] / sc[x][1] if sc[x][1] else None for x in "AB")
        L.append(f"| {tid} {t['title']} | {t['mode']} | {sc['A'][0]}/{sc['A'][1]} | {sc['B'][0]}/{sc['B'][1]} | {win(ra, rb, lower=False)} |")
    ra, rb = (tot[x][0] / tot[x][1] if tot[x][1] else None for x in "AB")
    L.append(f"| **All** | | **{tot['A'][0]}/{tot['A'][1]}** | **{tot['B'][0]}/{tot['B'][1]}** | **{win(ra, rb, lower=False)}** |")
    rows, rp = [], Path(a.results)
    if rp.exists():
        rows = [r for r in csv.DictReader(rp.open(encoding="utf-8", newline="")) if (r.get("arm") or "").strip().upper() in arms]
    L += ["", "## Logged metrics (results.csv, lower is better)", ""]
    if not rows: L.append(f"_No rows in {rp} yet._")
    else:
        mets = [("tokens", "Tokens"), ("rounds", "Prompt rounds"), ("minutes", "Minutes"), ("reexplained", "Re-explained (T6 memory)")]
        L += ["| Metric | A | B | B vs A | Winner |", "|---|---:|---:|---:|---|"]
        for k, label in mets:
            s = {arm: [num(r.get(k)) for r in rows if r["arm"].strip().upper() == arm] for arm in arms}
            va, vb = (sum(v for v in s[x] if v is not None) if any(v is not None for v in s[x]) else None for x in "AB")
            d = f"{(vb - va) / va * 100:+.0f}%" if va and vb is not None else "-"
            L.append(f"| {label} | {fmt(va)} | {fmt(vb)} | {d} | {win(va, vb)} |")
        L += ["", "| Task | A tokens | B tokens | A rounds | B rounds | A min | B min |", "|---|---:|---:|---:|---:|---:|---:|"]
        for tid in checks:
            g = lambda arm, k: next((num(r.get(k)) for r in rows if r["arm"].strip().upper() == arm and r["task"].strip().upper() == tid), None)
            L.append(f"| {tid} | " + " | ".join(fmt(g(arm, k)) for k in ("tokens", "rounds", "minutes") for arm in "AB") + " |")
    L += ["", "<details><summary>Check details</summary>", "", "| Task | Arm | Check | Result | Note |", "|---|---|---|---|---|", *detail, "", "</details>", "",
          "Verdict rule: B wins only if it passes at least as many checks AND wins on most logged metrics. One run per arm is a signal, not proof; repeat 2-3 times."]
    rep = "\n".join(L) + "\n"
    if a.out: Path(a.out).write_text(rep, encoding="utf-8")
    print(rep)

if __name__ == "__main__":
    main()
