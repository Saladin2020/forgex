#!/usr/bin/env python3
"""v2.9 tests (stdlib): forgex.py plan/next/slice done, roadmap validator, ctxpack current+next slice, harvest
(draft only, personal kit only), style capture (image template + URL CSS variables). Calls the real tools. Exit 1 on failure."""
import json, subprocess, sys, tempfile
from pathlib import Path
HERE = Path(__file__).resolve().parent; FAIL = 0
def check(n, c, info=""):
    global FAIL
    print(("ok  " if c else "FAIL") + f" {n} {'' if c else info}"); FAIL += not c
def fx(root, *a): return subprocess.run([sys.executable, str(HERE / "forgex.py"), *a], cwd=root, capture_output=True, text=True, encoding="utf-8")
def w(p, s): p.parent.mkdir(parents=True, exist_ok=True); p.write_text(s, encoding="utf-8")

def filled(goal="loan approvals"):
    ms = [{"id": f"M{i}", "title": t, "outcome": o} for i, (t, o) in enumerate([("request", "member submits a loan request"), ("approve", "checker approves and ledger posts"), ("report", "staff sees monthly report")], 1)]
    sl = [{"id": "S1", "milestone": "M1", "title": "loan request form saves pending row", "files": ["app/loans/new/page.tsx", "server/loans.ts"], "test": "node --test tests/loans.test.mjs",
           "dependsOn": [], "mode": None, "status": "todo", "walk": ["member opens /loans/new", "submits amount", "sees pending loan in list"]},
          {"id": "S2", "milestone": "M2", "title": "approve route", "files": ["app/api/approve/route.ts"], "test": "node --test tests/approve.test.mjs", "dependsOn": ["S1"], "mode": None, "status": "todo"},
          {"id": "S3", "milestone": "M2", "title": "post to ledger on approval", "files": ["server/ledger.ts"], "test": "node --test tests/ledger.test.mjs", "dependsOn": ["S2"], "mode": None, "status": "todo"},
          {"id": "S4", "milestone": "M3", "title": "monthly report page", "files": ["app/reports/page.tsx"], "test": "node --test tests/report.test.mjs", "dependsOn": ["S1"], "mode": None, "status": "todo"}]
    return {"version": "2.9.0", "goal": goal, "milestones": ms, "slices": sl}

def main():
    with tempfile.TemporaryDirectory() as t:
        root = Path(t); (root / "forgex").mkdir()
        subprocess.run([sys.executable, str(HERE / "context.py"), "init"], cwd=root, capture_output=True)
        p = fx(root, "plan", "loan approvals"); check("plan: scaffolds roadmap.json + ROADMAP.md", p.returncode == 0 and (root / "forgex/roadmap.json").exists() and (root / "forgex/ROADMAP.md").exists(), p.stderr)
        r = json.loads((root / "forgex/roadmap.json").read_text(encoding="utf-8"))
        check("plan: 3 milestones with outcomes, >3 slices", len(r["milestones"]) == 3 and len(r["slices"]) == 4 and all("outcome" in m for m in r["milestones"]))
        p = fx(root, "plan", "--check"); check("plan --check: unfilled placeholders fail", p.returncode == 1 and "placeholders" in p.stdout, p.stdout)
        rj = root / "forgex/roadmap.json"
        def bad(mut, word, name):
            r = filled(); mut(r); rj.write_text(json.dumps(r), encoding="utf-8"); p = fx(root, "plan", "--check")
            check(f"validator: {name}", p.returncode == 1 and word in p.stdout, p.stdout)
        bad(lambda r: r["slices"][1].update(dependsOn=["S3"]) or r["slices"][2].update(dependsOn=["S2"]), "cycle", "dependsOn cycle rejected")
        bad(lambda r: r["slices"][1].update(files=["a.ts", "b.ts", "c.ts", "d.ts"]), "slice size", "slice >3 files rejected")
        bad(lambda r: r["slices"][1].update(dependsOn=["S9"]), "does not exist", "missing dep rejected")
        bad(lambda r: r["slices"][0].pop("walk"), "walkable", "first slice must be walkable")
        bad(lambda r: r["slices"].pop(), "planning is for >3 slices", "<=3 slices: use a single task")
        bad(lambda r: r["milestones"].pop(), "3-5", "milestone count 3-5")
        r = filled(); r["slices"][2]["mode"] = "QUICK"; rj.write_text(json.dumps(r), encoding="utf-8"); fx(root, "plan", "--check")
        check("per-slice mode never below the classifier (QUICK ledger slice raised)", json.loads(rj.read_text(encoding="utf-8"))["slices"][2]["mode"] == "GUARDED")
        rj.write_text(json.dumps(filled()), encoding="utf-8")
        p = fx(root, "plan", "--check"); r = json.loads(rj.read_text(encoding="utf-8"))
        modes = {s["id"]: s["mode"] for s in r["slices"]}
        check("plan --check: valid roadmap passes", p.returncode == 0, p.stdout)
        check("per-slice mode from risk classifier (ledger post -> GUARDED, page -> STANDARD)", modes["S3"] == "GUARDED" and modes["S1"] == "STANDARD", str(modes))
        p = fx(root, "next"); st = (root / "forgex/STATE.md").read_text(encoding="utf-8")
        check("next: picks S1 and writes it into STATE Plan", p.returncode == 0 and "1. S1 loan request form" in st and "slice done S1" in st, p.stdout + p.stderr + st)
        kit = root / "_kit"; w(kit / "blocks/async-button.md", "# b\n- **Tags:** ui, button\n- **What:** b\n")
        pk = json.loads(subprocess.run([sys.executable, str(HERE / "ctxpack.py"), "loan request form", "--kit", str(kit), "--json", "--path", "app/loans/new/page.tsx"], cwd=root, capture_output=True, text=True, encoding="utf-8").stdout)
        L = [x["item"] for x in pk["loaded"]]
        check("ctxpack: loads current + next slice only", "roadmap S1 (current)" in L and any(x.startswith("roadmap S") and "(next)" in x for x in L) and sum(x.startswith("roadmap") for x in L) == 2 and any("only current + next" in s["why"] for s in pk["skipped"]), str(L))
        pk = json.loads(subprocess.run([sys.executable, str(HERE / "ctxpack.py"), "button padding css", "--kit", str(kit), "--json", "--path", "app/globals.css"], cwd=root, capture_output=True, text=True, encoding="utf-8").stdout)
        check("QUICK skips roadmap entirely", pk["mode"] == "QUICK" and not any(x["item"].startswith("roadmap") for x in pk["loaded"]), str(pk["mode"]))
        p = fx(root, "slice", "done", "S1", "--check-cmd", f'"{sys.executable}" -c "raise SystemExit(1)"')
        check("slice done: failing test blocks done", p.returncode == 1 and json.loads(rj.read_text(encoding="utf-8"))["slices"][0]["status"] == "doing", p.stdout)
        w(root / "server/loans.ts", "export function createLoan(a: number) { return a }\nexport const MAX = 5\n"); w(root / "app/loans/new/page.tsx", "export default function NewLoan() { return null }\n")
        p = fx(root, "harvest", "S1"); check("harvest: refused before slice is done", p.returncode != 0)
        p = fx(root, "slice", "done", "S1", "--check-cmd", f'"{sys.executable}" -c "pass"'); r = json.loads(rj.read_text(encoding="utf-8"))
        check("slice done: passes -> done, ROADMAP.md updated", p.returncode == 0 and r["slices"][0]["status"] == "done" and "[x] S1" in (root / "forgex/ROADMAP.md").read_text(encoding="utf-8"), p.stdout)
        p = fx(root, "next"); check("next: after S1, S2 (deps met) is next", "next: S2" in p.stdout, p.stdout)
        p = fx(root, "harvest", "S1"); ds = sorted((root / "forgex/harvest").glob("*.md"))
        check("harvest: drafts only (kit untouched)", p.returncode == 0 and any("createLoan" in d.read_text(encoding="utf-8") for d in ds) and not (kit / "blocks/loans.md").exists(), p.stdout + p.stderr)
        d = next(d for d in ds if "loans" in d.name)
        p = fx(root, "harvest", "--confirm", str(d), "--kit", str(kit)); check("harvest --confirm: refuses a non-personal kit", p.returncode != 0 and "refused" in p.stderr, p.stderr)
        house = root / "core/house"; w(house / "kit.json", "{}")
        p = fx(root, "harvest", "--confirm", str(d), "--kit", str(house)); check("harvest --confirm: never core/house (public)", p.returncode != 0 and "refused" in p.stderr)
        w(kit / "kit.json", "{}"); p = fx(root, "harvest", "--confirm", str(d), "--kit", str(kit))
        c = (kit / "blocks/loans.md")
        check("harvest --confirm: personal kit gets tagged card + INDEX line", p.returncode == 0 and c.exists() and "**Tags:**" in c.read_text(encoding="utf-8") and "DRAFT" not in c.read_text(encoding="utf-8") and "loans" in (kit / "blocks/INDEX.md").read_text(encoding="utf-8"), p.stdout + p.stderr)
        # style capture
        w(root / "ref/site.css", ":root{--color-bg:#faf6f1;--radius-card:12px;--shadow-card:0 1px 2px rgba(0,0,0,.1);--space-2:8px}.sk{animation:shimmer 1400ms linear infinite}h1{font-size:28px}")
        w(root / "ref/index.html", '<html><head><link rel="stylesheet" href="site.css"><style>:root{--color-accent:#b4532f;--font-body:Sarabun}</style></head><body></body></html>')
        p = fx(root, "style", "capture", (root / "ref/index.html").as_uri(), "shot.png", "--out", "forgex/style")
        sd = json.loads((root / "forgex/style/style.draft.json").read_text(encoding="utf-8"))
        tk = sd["tokens"]
        check("style capture URL: CSS variables pulled (inline + linked sheet)", p.returncode == 0 and tk["color"].get("--color-accent") == "#b4532f" and tk["color"].get("--color-bg") == "#faf6f1" and tk["radius"].get("--radius-card") == "12px", p.stdout + p.stderr + json.dumps(tk)[:300])
        check("style capture: motion tokens (shimmer timing, stagger, reduced motion)", "1400ms" in tk["motion"]["durationsSeen"] and "staggerMs" in tk["motion"] and "reducedMotion" in tk["motion"])
        check("style capture image: template + agent instructions", any(s["source"] == "shot.png" for s in sd["agentFill"]) and "Fill from images" in (root / "forgex/style/DESIGN.draft.md").read_text(encoding="utf-8"))
        cards = {n: (root / f"forgex/style/cards/{n}.md").read_text(encoding="utf-8") for n in ("ui-skeleton-list", "ui-empty-state", "ui-data-table")}
        check("style cards: 3 tagged drafts with runnable tsx + rules", all("**Tags:** ui" in c and "```tsx" in c and "export function" in c and "## Rules" in c for c in cards.values()))
        check("style cards: skeleton shape + 4 states + mobile", "same layout shape" in cards["ui-skeleton-list"] and all(k in cards["ui-data-table"] for k in ("loading", "empty", "error", "Mobile")))
        ck = (root / "forgex/style/CHECKLIST.md").read_text(encoding="utf-8")
        check("style: visual checklist + never copy logos/assets/code", "Skeleton has the same shape" in ck and "no logos" in ck and "Never copy logos" in sd["principlesOnly"])
        p = fx(root, "style", "capture", "http://127.0.0.1:9/nope", "--out", "forgex/style2")
        check("style capture: unreachable URL falls back to template (no crash)", p.returncode == 0 and json.loads((root / "forgex/style2/style.draft.json").read_text(encoding="utf-8"))["agentFill"])
    print("\nAll v2.9 plan/harvest/style tests passed" if not FAIL else f"\n{FAIL} failed"); sys.exit(1 if FAIL else 0)

if __name__ == "__main__":
    main()
