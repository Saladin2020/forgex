#!/usr/bin/env python3
"""v2.10 tests (stdlib): forgex.py rate / review / prune and the milestone-close prompt. Calls the real tools on a temp
repo + temp personal kit. Exit 1 on failure."""
import json, os, subprocess, sys, tempfile, time
from pathlib import Path
HERE = Path(__file__).resolve().parent; FAIL = 0; N = 0
def check(n, c, info=""):
    global FAIL, N
    N += 1; print(("ok  " if c else "FAIL") + f" {n} {'' if c else info}"); FAIL += not c
def fx(root, *a): return subprocess.run([sys.executable, str(HERE / "forgex.py"), *a], cwd=root, capture_output=True, text=True, encoding="utf-8")
def w(p, s): p.parent.mkdir(parents=True, exist_ok=True); p.write_text(s, encoding="utf-8")
def log(root): p = root / "forgex/log.jsonl"; return [json.loads(x) for x in p.read_text(encoding="utf-8").splitlines() if x.strip()] if p.exists() else []
CARD = "# {n}\n- **Tags:** {t}\n- **What:** {w}\n- **From:** x\n- **Reuse:** {r}\n- **Gotchas:** {g}\n"

def main():
    with tempfile.TemporaryDirectory() as t:
        root = Path(t) / "app"; (root / "forgex").mkdir(parents=True); kit = Path(t) / "kit"
        w(kit / "kit.json", "{}"); w(kit / "blocks/INDEX.md", "# idx\n- `idempotency`: replay safe\n- `idem-key`: replay safe 2\n- `old-thing`: old\n- `audit-log`: audit\n")
        w(kit / "blocks/idempotency.md", CARD.format(n="idempotency", t="money", w="Replay-safe server actions with idempotency key", r="withIdempotency userId route key payload", g="hash conflict"))
        w(kit / "blocks/idem-key.md", CARD.format(n="idem-key", t="money", w="Replay-safe server actions idempotency key", r="withIdempotency userId route key payload", g="none"))
        w(kit / "blocks/old-thing.md", CARD.format(n="old-thing", t="misc", w="Legacy fax sender", r="sendFax number", g="? not yet reused"))
        w(kit / "blocks/audit-log.md", CARD.format(n="audit-log", t="security", w="Append-only audit rows in same transaction", r="writeAudit tx", g="ok") + "- **Used:** " + time.strftime("%Y-%m-%d") + "\n")
        old = time.time() - 400 * 86400; os.utime(kit / "blocks/old-thing.md", (old, old))

        # 1) rating
        p = fx(root, "rate", "--scope", "quick", "--id", "T1", "many"); check("rate: QUICK never asked, nothing logged", p.returncode == 0 and "QUICK" in p.stdout and not log(root), p.stdout + p.stderr)
        p = fx(root, "rate", "--scope", "milestone", "--id", "M1", "1-2"); e = log(root)
        check("rate: milestone 1-2 logged into log.jsonl", p.returncode == 0 and e[-1]["kind"] == "rating" and e[-1]["rating"] == "1-2" and e[-1]["task"] == "M1", p.stderr)
        p = fx(root, "rate", "--scope", "project", "--id", "app", "skip"); e = log(root)
        check("rate: skip logs rating=null, exit 0", p.returncode == 0 and e[-1]["rating"] is None and e[-1]["skipped"] is True)
        p = fx(root, "rate", "--scope", "milestone", "--id", "M2"); e = log(root)
        check("rate: no answer = skip, never blocks", p.returncode == 0 and e[-1]["skipped"] is True)
        w(root / "forgex/context-policy.json", json.dumps({**json.loads((HERE.parent / "config/context-policy.json").read_text(encoding="utf-8")), "feedback": {"rating": False}}))
        n0 = len(log(root)); p = fx(root, "rate", "--scope", "milestone", "--id", "M3", "many")
        check("rate: disabled in config logs nothing", p.returncode == 0 and "disabled" in p.stdout and len(log(root)) == n0, p.stdout)
        (root / "forgex/context-policy.json").unlink()

        # milestone-close prompt from slice done (real roadmap)
        rm = {"version": "2.10.0", "goal": "loans", "milestones": [{"id": f"M{i}", "title": "m", "outcome": "o"} for i in (1, 2, 3)],
              "slices": [{"id": "S1", "milestone": "M1", "title": "form", "files": ["app/loans/page.tsx"], "test": "true", "dependsOn": [], "status": "todo", "walk": ["a", "b"]},
                         {"id": "S2", "milestone": "M2", "title": "approve", "files": ["server/approve.ts"], "test": "false", "dependsOn": ["S1"], "status": "todo"},
                         {"id": "S3", "milestone": "M2", "title": "post", "files": ["server/post.ts"], "test": "true", "dependsOn": ["S2"], "status": "todo"},
                         {"id": "S4", "milestone": "M3", "title": "report", "files": ["app/report.tsx"], "test": "true", "dependsOn": ["S1"], "status": "todo"}]}
        w(root / "forgex/roadmap.json", json.dumps(rm))
        p = fx(root, "slice", "done", "S1"); check("slice done closing M1 prints rating + review prompt", "milestone M1 closed" in p.stdout and "forgex.py rate" in p.stdout and "forgex.py review" in p.stdout, p.stdout + p.stderr)
        p = fx(root, "slice", "done", "S3"); check("slice done mid-milestone: no prompt", "closed" not in p.stdout, p.stdout)
        for _ in range(2): fx(root, "slice", "done", "S2", "--check-cmd", "exit 3")
        r = json.loads((root / "forgex/roadmap.json").read_text(encoding="utf-8"))
        check("failed checks counted per slice", next(s for s in r["slices"] if s["id"] == "S2").get("failedChecks") == 2)
        fx(root, "slice", "done", "S2"); p = fx(root, "slice", "done", "S4")
        check("last slice prints project prompt", "project " in p.stdout and "closed" in p.stdout, p.stdout)

        # 3) prune
        before = sorted(x.name for x in (kit / "blocks").iterdir())
        p = fx(root, "prune", "--kit", str(kit))
        check("prune: finds duplicate idem-key ~ idempotency", "duplicate" in p.stdout and "idem-key" in p.stdout, p.stdout)
        check("prune: finds stale unverified old-thing", "stale" in p.stdout and "old-thing" in p.stdout, p.stdout)
        check("prune: recently used audit-log not flagged", "audit-log" not in p.stdout)
        check("prune: suggest-only, kit unchanged", sorted(x.name for x in (kit / "blocks").iterdir()) == before)
        p = fx(root, "prune", "--confirm", "x", "--kit", str(HERE.parent / "core/house"))
        check("prune --confirm refuses core/house", p.returncode != 0 and "refused" in (p.stdout + p.stderr))
        nk = Path(t) / "notkit"; w(nk / "blocks/a.md", "x"); p = fx(root, "prune", "--confirm", "a", "--kit", str(nk))
        check("prune --confirm refuses non-personal kit", p.returncode != 0 and (nk / "blocks/a.md").exists())

        # 2) review
        fx(root, "rate", "--scope", "milestone", "--id", "M2", "many")
        with (root / "forgex/log.jsonl").open("a", encoding="utf-8") as fh:
            for i, (cm, am, ti) in enumerate([("GUARDED", "STANDARD", 3000), ("GUARDED", "GUARDED", 4000), ("STANDARD", "STANDARD", 2000)]):
                fh.write(json.dumps({"task": f"T{i}", "classifierMode": cm, "actualMode": am, "tokensIn": ti, "tokensOut": 1000, "tokenEstimate": False}) + "\n")
        w(kit / "metrics/projects.jsonl", json.dumps({"project": "old", "tokensPerTask": 2500}) + "\n")
        w(root / "forgex/harvest/S1-loan-form.md", CARD.format(n="loan-form", t="ui", w="Loan request form with zod", r="LoanForm", g="?"))
        w(root / "forgex/harvest/S3-post.md", CARD.format(n="post", t="money", w="Replay-safe server actions idempotency key", r="withIdempotency userId route key payload", g="?"))
        kb = sorted(str(x.relative_to(kit)) for x in kit.rglob("*"))
        p = fx(root, "review", "--kit", str(kit)); rv = json.loads((root / "forgex/review.json").read_text(encoding="utf-8")) if (root / "forgex/review.json").exists() else {"items": [], "numbers": {}}
        kinds = [i["kind"] for i in rv["items"]]; md = (root / "forgex/REVIEW.md").read_text(encoding="utf-8") if (root / "forgex/REVIEW.md").exists() else ""
        check("review: writes REVIEW.md with 4 sections", p.returncode == 0 and all(s in md for s in ("## Cards", "## Lessons", "## Numbers", "## Top recommendations")), p.stderr)
        check("review: keep new harvest draft", any(i["kind"] == "card-keep" and "S1-loan-form" in i["text"] for i in rv["items"]))
        check("review: draft duplicating a kit card -> merge", any(i["kind"] == "card-merge" and "S3-post" in i["text"] for i in rv["items"]))
        check("review: prune items for duplicate + stale", sum(k == "card-prune" for k in kinds) >= 2)
        check("review: lesson from repeated failed checks (S2)", any(i["kind"] == "lesson" and "S2" in i["text"] for i in rv["items"]))
        check("review: lesson from 'many' rating", any(i["kind"] == "lesson" and "M2" in i["text"] for i in rv["items"]))
        n = rv["numbers"]
        check("review: tokens vs earlier projects", n.get("tokensPerTask") == 4000 and n.get("earlierAvgPerTask") == 2500 and n.get("deltaPct") == 60, n)
        check("review: false GUARDED cases listed", n.get("falseGuarded") == 1 and n.get("classifiedGuarded") == 2 and n.get("falseGuardedCases") == ["T0"], n)
        check("review: at most 3 recommendations", 1 <= kinds.count("recommendation") <= 3)
        check("review: all items pending, kit unchanged", all(i["status"] == "pending" for i in rv["items"]) and sorted(str(x.relative_to(kit)) for x in kit.rglob("*")) == kb)
        les = next(i for i in rv["items"] if i["kind"] == "lesson"); keep = next(i for i in rv["items"] if i["kind"] == "card-keep")
        p = fx(root, "review", "--accept", les["id"]); check("review --accept lesson writes forgex/LESSONS.md", (root / "forgex/LESSONS.md").exists() and "slice test first" in (root / "forgex/LESSONS.md").read_text(encoding="utf-8"), p.stdout + p.stderr)
        p = fx(root, "review", "--accept", keep["id"]); check("review --accept card prints confirm command, kit still unchanged", "harvest --confirm" in p.stdout and sorted(str(x.relative_to(kit)) for x in kit.rglob("*")) == kb, p.stdout)
        p = fx(root, "review", "--skip", next(i for i in rv["items"] if i["kind"] == "card-prune")["id"]); md = (root / "forgex/REVIEW.md").read_text(encoding="utf-8")
        check("review --skip marks item, REVIEW.md shows [x]/[-]", "[-]" in md and "[x]" in md, md)
        num = next(i for i in rv["items"] if i["kind"] == "numbers"); fx(root, "review", "--accept", num["id"])
        h = (kit / "metrics/projects.jsonl").read_text(encoding="utf-8").splitlines()
        check("review --accept numbers appends to history", len(h) == 2 and json.loads(h[-1])["tokensPerTask"] == 4000)

        # prune confirm moves, never deletes
        p = fx(root, "prune", "--confirm", "old-thing", "--kit", str(kit))
        check("prune --confirm moves card to pruned/ and drops INDEX line", p.returncode == 0 and (kit / "pruned/old-thing.md").exists() and not (kit / "blocks/old-thing.md").exists() and "old-thing" not in (kit / "blocks/INDEX.md").read_text(encoding="utf-8"), p.stdout + p.stderr)
        rep = subprocess.run([sys.executable, str(HERE / "tokens.py"), "report", "--log", str(root / "forgex/log.jsonl")], capture_output=True, text=True)
        rj = json.loads(rep.stdout); check("tokens report counts ratings, excludes them from entries", rj["ratings"]["many"] == 1 and rj["ratings"]["1-2"] == 1 and rj["entries"] == 3, rep.stdout)
    print(f"\n{N - FAIL}/{N} passed"); sys.exit(1 if FAIL else 0)

if __name__ == "__main__":
    main()
