#!/usr/bin/env python3
"""Scenario tests for ctxpack.py on a throwaway repo (stdlib only). Exit 1 on failure.
  test_ctxpack.py [--kit DIR]   (default: built-in fixture kit)
"""
import json, subprocess, sys, tempfile, textwrap
from pathlib import Path

HERE = Path(__file__).resolve().parent
FAIL = 0

def w(p, s): p.parent.mkdir(parents=True, exist_ok=True); p.write_text(textwrap.dedent(s).lstrip())

def fixture(root):
    files = ["src/auth.ts", "src/server/password.ts", "src/app/login/page.tsx", "src/app/globals.css",
             "src/components/Button.tsx", "src/app/api/members/route.ts", "src/server/loans.ts", "drizzle/0001_init.sql",
             "src/lib/pdf/receipt.tsx", "src/app/reports/page.tsx", "src/server/push.ts", "tests/login.test.ts"]
    for f in files: w(root / f, "export function x() {}\n")
    pol = json.loads((HERE.parent / "config/context-policy.json").read_text())
    w(root / "_p1.json", json.dumps({**pol, "maxCards": {"QUICK": 1, "STANDARD": 3, "GUARDED": 1}}))
    w(root / "_tiny.json", json.dumps({**pol, "budgets": {"QUICK": 100, "STANDARD": 100, "GUARDED": 100}}))
    w(root / "_bad.json", "{ not json")
    w(root / "_bad2.json", json.dumps({k: v for k, v in pol.items() if k != "budgets"}))
    w(root / "forgex/STATE.md", "# STATE\n- Goal: member app\n- Now: polishing\n- Next: login bug\n")
    big = "\n".join(f"## D-{i} · 2026-10-0{i%9+1} · " + t for i, t in enumerate([
        "Use argon2id for passwords\n- Why: memory-hard\n- Tags: auth",
        "Sessions are JWT, re-read sessionVersion\n- Why: revoke fast\n- Tags: auth",
        "Money stored as integer satang\n- Why: no float\n- Tags: money",
        "Migrations are append-only SQL\n- Why: Neon safe\n- Tags: db",
        "Brand colour terracotta\n- Why: owner pick\n- Tags: ui",
        "PDF via react-pdf with Thai font\n- Why: works on Vercel"], 1))
    w(root / "forgex/DECISIONS.md", "# DECISIONS\n\n" + big + "\n")
    cm = ["# CODEMAP"] + [f"## {d}/ (3 files)\n- `a.ts`: thing\n- `b.ts`: other\n- `c.ts`: more" for d in
          ["src", "src/app/login", "src/app/api/members", "src/server", "src/components", "src/lib/pdf", "src/app/reports", "drizzle", "tests"]] + ["## Notes\n# note: auth lives in src/auth.ts"]
    w(root / "forgex/CODEMAP.md", "\n".join(cm) + "\n")
    kit = root / "_kit"
    for n, tg in [("password-auth", "auth, login, password"), ("staff-totp", "auth, 2fa"), ("money-math", "money"),
                  ("thai-pdf", "pdf"), ("async-button", "ui, button"), ("web-push", "notify"), ("drizzle-neon-migrate", "db, migration")]:
        w(kit / f"blocks/{n}.md", f"# {n}\n- **Tags:** {tg}\n- **What:** {n} block\n- **Reuse:** " + "details " * 60 + "\n")
    for g in ["form-page", "api-route", "server-action", "test"]:
        w(kit / f"golden/{g}.md", f"# {g}\n```ts\n" + "// shape line\n" * 40 + "```\n")
    return kit

def pack(root, kit, task, *a):
    cmd = [sys.executable, str(HERE / "ctxpack.py"), task, "--kit", str(kit), "--json", *a]
    return json.loads(subprocess.run(cmd, cwd=root, capture_output=True, text=True, check=True).stdout)

def full(root, kit):
    fs = [root / "forgex/STATE.md", root / "forgex/DECISIONS.md", root / "forgex/CODEMAP.md", *(kit / "blocks").glob("*.md"), *(kit / "golden").glob("*.md")]
    return sum((len(f.read_text()) + 3) // 4 for f in fs)

def raw(root, kit, task, *a):
    cmd = [sys.executable, str(HERE / "ctxpack.py"), task, "--kit", str(kit), "--json", *a]
    return subprocess.run(cmd, cwd=root, capture_output=True, text=True)

def edge(root, kit):
    print("-- edge cases --")
    r = pack(root, kit, "tweak spacing", "--path", "drizzle/migrations/0002.sql")
    check("edge guarded glob: migrations -> GUARDED", r["mode"] == "GUARDED" and any("guarded glob" in x for x in r["modeReasons"]))
    r = pack(root, kit, "rename css class", "--mode", "STANDARD", "--path", "src/app/globals.css")
    check("edge explicit STANDARD never downgraded", r["mode"] == "STANDARD")
    r = pack(root, kit, "rename css class", "--mode", "GUARDED", "--path", "src/app/globals.css")
    check("edge explicit GUARDED kept + GUARDED cap", r["mode"] == "GUARDED" and r["capTokensEst"] == 7000)
    r = pack(root, kit, "login page pdf receipt with push reminder", "--path", "src/app/login/page.tsx", "--path", "src/lib/pdf/receipt.tsx", "--path", "src/server/push.ts")
    L = [x["item"] for x in r["loaded"]]
    check("edge multi-area: auth+pdf+notify all matched", {"auth", "pdf", "notify"} <= set(r["areas"]), str(list(r["areas"])))
    check("edge multi-area: one core card per area", {"card password-auth", "card thai-pdf", "card web-push"} <= set(L), str(L))
    r = pack(root, kit, "css loan payment login style", "--mode", "QUICK", "--path", "src/app/globals.css", "--policy", str(root / "_p1.json"))
    cards = [x for x in r["loaded"] if x["item"].startswith("card ")]
    check("edge more core cards than maxCards: limit held", len(cards) == 1, str([c["item"] for c in cards]))
    check("edge core cards over limit explained", any(s["why"].startswith("core card over maxCards") for s in r["skipped"]))
    check("edge core allocation: guarded area first", cards and cards[0]["item"] in ("card password-auth", "card money-math"))
    r = pack(root, kit, "refactor helper", "--path", "src/components/Button.tsx", "--policy", str(root / "_tiny.json"))
    check("edge over budget: cap held", r["usedTokensEst"] <= r["capTokensEst"] == 100)
    check("edge over budget: items listed with reason", sum("over budget" in s["why"] for s in r["skipped"]) >= 1)
    r = pack(root, kit, "zzz qqq", "--path", "src/server/loans.ts")
    check("edge no tags: no cards, STANDARD, warning", not any(x["item"].startswith("card") for x in r["loaded"]) and r["mode"] in ("STANDARD", "GUARDED") and any("no area" in w for w in r["warnings"]), r["mode"])
    r = pack(root, kit, "zzz qqq")
    check("edge no paths: conservative STANDARD + warning", r["mode"] == "STANDARD" and any("no paths" in w for w in r["warnings"]))
    r = pack(root, kit, "fix button", "--path", "src/components/Ghost.tsx")
    check("edge missing source file: warned, still packed", any("not found" in w for w in r["warnings"]) and r["loaded"])
    p = raw(root, kit, "x", "--policy", str(root / "_bad.json"))
    check("edge invalid policy (bad JSON): exit 2 + message", p.returncode == 2 and "invalid policy" in p.stderr, p.stderr.strip())
    p = raw(root, kit, "x", "--policy", str(root / "_bad2.json"))
    check("edge invalid policy (no budgets): exit 2", p.returncode == 2 and "budgets" in p.stderr, p.stderr.strip())
    for bad in ("../outside.ts", "/etc/passwd"):
        p = raw(root, kit, "x", "--path", bad)
        check(f"edge path outside root {bad}: exit 2", p.returncode == 2 and "outside project root" in p.stderr)
    r = pack(root, kit, "fix the page", "--path", "src/server/push.ts")
    check("edge golden min score: one kind word alone not enough", not any(x["item"].startswith("golden") for x in r["loaded"]) and any("golden score 1" in s["why"] for s in r["skipped"]))
    r = pack(root, kit, "add members api", "--path", "src/app/api/members/route.ts")
    head = (root / "forgex/context-pack.md").read_text().split("\n---\n# FORGEX", 1)[0]
    ok = all(k in head for k in ("forgexContextPack:", f"id: {r['packId']}", "forgexVersion:", "policyVersion:", "estimator: \"chars/4\"", "selected:", "skipped:", "warnings:"))
    check("edge metadata header: id, versions, budget, selected/skipped, warnings", ok and r["packId"].startswith("cp-"))
    check("edge metadata: deterministic id", pack(root, kit, "add members api", "--path", "src/app/api/members/route.ts")["packId"] == r["packId"])

def check(name, cond, info=""):
    global FAIL
    print(("ok  " if cond else "FAIL") + f" {name} {info}"); FAIL += not cond

def main():
    kit_arg = sys.argv[sys.argv.index("--kit") + 1] if "--kit" in sys.argv else None
    with tempfile.TemporaryDirectory() as t:
        root = Path(t); kit = Path(kit_arg).resolve() if kit_arg else fixture(root)
        if kit_arg: fixture(root)
        base = full(root, kit); print(f"load-everything baseline: {base} est. tokens (chars/4)")
        r = pack(root, kit, "fix login", "--path", "src/app/login/page.tsx")
        L = [x["item"] for x in r["loaded"]]
        print(f"[fix login] {r['mode']} {r['usedTokensEst']}/{r['capTokensEst']} est. · loaded {L}")
        check("login: GUARDED", r["mode"] == "GUARDED")
        check("login: STATE", any("STATE" in x for x in L))
        check("login: auth decisions D-1,D-2", {"DECISIONS D-1", "DECISIONS D-2"} <= set(L))
        check("login: no money/ui/db decisions", not {"DECISIONS D-3", "DECISIONS D-4", "DECISIONS D-5"} & set(L))
        check("login: password-auth card", "card password-auth" in L)
        check("login: no unrelated cards", not {"card money-math", "card thai-pdf", "card web-push"} & set(L))
        check("login: within cap", r["usedTokensEst"] <= r["capTokensEst"])
        r = pack(root, kit, "make the save button padding smaller", "--path", "src/app/globals.css")
        L = [x["item"] for x in r["loaded"]]
        print(f"[tiny CSS] {r['mode']} {r['usedTokensEst']}/{r['capTokensEst']} est. · loaded {L}")
        check("css: QUICK", r["mode"] == "QUICK")
        check("css: under QUICK cap", r["usedTokensEst"] <= r["capTokensEst"])
        check("css: no auth/money", not any(x in " ".join(L) for x in ["password", "D-1", "D-3", "money"]))
        check("css: golden skipped in QUICK", not any("golden" in x for x in L))
        r = pack(root, kit, "add loan repayment API endpoint", "--path", "src/app/api/members/route.ts", "--path", "src/server/loans.ts")
        L = [x["item"] for x in r["loaded"]]
        print(f"[money API] {r['mode']} {r['usedTokensEst']}/{r['capTokensEst']} est. · loaded {L}")
        check("api: money decision D-3", "DECISIONS D-3" in L)
        check("api: golden api-route", "golden api-route" in L)
        check("api: money core card money-math", "card money-math" in L)
        check("api: within cap", r["usedTokensEst"] <= r["capTokensEst"])
        r = pack(root, kit, "fix login", "--mode", "QUICK", "--path", "src/app/login/page.tsx")
        print(f"[explicit QUICK on auth] {r['mode']} {r['usedTokensEst']}/{r['capTokensEst']} est., reasons {r['modeReasons']}")
        check("edge auth path: explicit QUICK escalated to GUARDED", r["mode"] == "GUARDED" and any("escalated" in x for x in r["modeReasons"]))
        check("cap never exceeded + skips explained", r["usedTokensEst"] <= r["capTokensEst"] and all(s["why"] for s in r["skipped"]))
        edge(root, kit)
        pol = json.loads((HERE.parent / "config/context-policy.json").read_text()); pol["budgets"] = {"QUICK": 150, "STANDARD": 150, "GUARDED": 150}
        (root / "forgex/context-policy.json").write_text(json.dumps(pol))
        r = pack(root, kit, "fix login", "--path", "src/app/login/page.tsx")
        print(f"[override cap 150] {r['usedTokensEst']}/{r['capTokensEst']} est. · loaded {[x['item'] for x in r['loaded']]}")
        check("trim: <=150 and over-budget items listed", r["usedTokensEst"] <= 150 and any("over budget" in s["why"] for s in r["skipped"]))
        check("trim: STATE kept first", r["loaded"][0]["item"].startswith("forgex/STATE.md"))
    print("\nAll ctxpack scenarios passed" if not FAIL else f"\n{FAIL} failed"); sys.exit(1 if FAIL else 0)

if __name__ == "__main__":
    main()
