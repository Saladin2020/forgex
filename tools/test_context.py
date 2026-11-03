#!/usr/bin/env python3
"""v2.8 tests (stdlib): cross-chat plan (context.py close/resume/check), mandatory tags, sharded CODEMAP + import
graph + symbol index feeding ctxpack, tokenizer adapter + measurement log. Calls the real tools. Exit 1 on failure."""
import json, os, subprocess, sys, tempfile, textwrap
from pathlib import Path

HERE = Path(__file__).resolve().parent
FAIL = 0
def check(name, cond, info=""):
    global FAIL
    print(("ok  " if cond else "FAIL") + f" {name} {info if not cond else ''}"); FAIL += not cond
def w(p, s): p.parent.mkdir(parents=True, exist_ok=True); p.write_text(textwrap.dedent(s).lstrip(), encoding="utf-8")
def run(root, tool, *a, ok=True):
    p = subprocess.run([sys.executable, str(HERE / tool), *a], cwd=root, capture_output=True, text=True, encoding="utf-8")
    if ok and p.returncode: print(p.stdout, p.stderr)
    return p

def main():
    with tempfile.TemporaryDirectory() as t:
        root = Path(t)
        w(root / "lib/money.ts", "export function totalBalance(xs: number[]) { return 0 }\nexport const SATANG = 100\n")
        w(root / "lib/format.ts", 'import { SATANG } from "./money";\nexport function formatBaht(n: number) { return String(n / SATANG) }\n')
        w(root / "app/dashboard/page.tsx", 'import { formatBaht } from "@/lib/format";\nexport default function Dashboard() { return null }\n')
        w(root / "app/other/page.tsx", "export default function Other() { return null }\n")
        w(root / "server/ledger.py", "from .money_py import to_satang\n\ndef post_entry(x):\n    return to_satang(x)\n\nclass Ledger: pass\n")
        w(root / "server/money_py.py", "def to_satang(x):\n    return int(x * 100)\n")
        w(root / "server/__init__.py", "")
        w(root / "server/api.py", "from server.ledger import post_entry\n")
        # --- codemap ---
        p = run(root, "codemap.py"); check("codemap: runs", p.returncode == 0, p.stderr)
        idx = json.loads((root / "forgex/codemap/index.json").read_text(encoding="utf-8"))
        g = json.loads((root / "forgex/codemap/graph.json").read_text(encoding="utf-8"))
        sy = json.loads((root / "forgex/codemap/symbols.json").read_text(encoding="utf-8"))
        check("codemap: sharded per dir", {"lib", "app/dashboard", "server"} <= set(idx["dirs"]) and all((root / "forgex/codemap" / v["shard"]).exists() for v in idx["dirs"].values()))
        check("codemap: TS @/ alias import resolved", "lib/format.ts" in g["app/dashboard/page.tsx"]["imports"], str(g.get("app/dashboard/page.tsx")))
        check("codemap: TS relative import + importedBy", "app/dashboard/page.tsx" in g["lib/format.ts"]["importedBy"] and "lib/money.ts" in g["lib/format.ts"]["imports"])
        check("codemap: Python relative + absolute imports", "server/money_py.py" in g["server/ledger.py"]["imports"] and "server/ledger.py" in g["server/api.py"]["imports"], str(g.get("server/api.py")))
        check("codemap: symbol index", sy.get("formatBaht") == ["lib/format.ts"] and sy.get("post_entry") == ["server/ledger.py"] and "Ledger" in sy)
        r = json.loads(run(root, "codemap.py", "related", "app/dashboard/page.tsx").stdout)
        check("codemap related: 2 hops (page -> format -> money)", r == {"lib/format.ts": 1, "lib/money.ts": 2}, str(r))
        r = json.loads(run(root, "codemap.py", "related", "app/dashboard/page.tsx", "--hops", "1").stdout)
        check("codemap related: --hops 1", r == {"lib/format.ts": 1}, str(r))
        big = "\n".join(f"export function f{i}() {{}}" for i in range(400))
        for i in range(30): w(root / f"many/m{i}.ts", big)
        run(root, "codemap.py")
        sh = json.loads((root / "forgex/codemap/shards/many.json").read_text(encoding="utf-8"))
        check("codemap: no 200-line truncation (30 files x 400 symbols kept)", len(sh["files"]) == 30 and len(json.loads((root / "forgex/codemap/symbols.json").read_text(encoding="utf-8"))["f399"]) == 30 and all(len(v["symbols"]) == 400 for v in sh["files"].values()))
        # --- context files ---
        run(root, "context.py", "init")
        p = run(root, "context.py", "check", ok=False)
        check("check: fresh template STATE fails (no concrete plan)", p.returncode == 1 and "Plan" in p.stdout, p.stdout)
        p = run(root, "context.py", "decide", "Money is integer satang", "--why", "no float", ok=False)
        check("decide: --tag required", p.returncode != 0)
        p = run(root, "context.py", "decide", "Money is integer satang", "--why", "no float", "--tag", "money")
        p = run(root, "context.py", "decide", "Dashboard reads from formatBaht", "--why", "one formatter", "--tag", "ui,money")
        check("decide: tagged entries", "- Tags: ui, money" in (root / "forgex/DECISIONS.md").read_text(encoding="utf-8"))
        p = run(root, "context.py", "close", "--now", "approve route half done", "--next", "add app/api/approve/route.ts calling post_entry", "--next", "test: checker approves -> ledger row", "--task", "s-003", "--mode", "STANDARD", "--by", "chat-1")
        st = (root / "forgex/STATE.md").read_text(encoding="utf-8")
        check("close: plan written to STATE", p.returncode == 0 and "1. add app/api/approve/route.ts" in st and "2. test: checker" in st and "Updated: " in st and "<YYYY" not in st, p.stdout + st)
        check("check: passes after close", run(root, "context.py", "check").returncode == 0)
        p = run(root, "validate.py", "--context"); check("validate.py --context passes after close", p.returncode == 0, p.stdout)
        p = run(root, "context.py", "resume")
        check("resume: new chat sees Plan step 1 first", p.stdout.index("## Plan") < p.stdout.index("## Now") and "approve/route.ts" in p.stdout and "Continue with Plan step 1" in p.stdout, p.stdout)
        p = run(root, "context.py", "close", "--now", "x", "--next", "step two only")
        st = (root / "forgex/STATE.md").read_text(encoding="utf-8")
        check("close: rewrites (does not append) the plan", st.count("## Plan") == 1 and "approve/route.ts" not in st and "1. step two only" in st)
        with (root / "forgex/DECISIONS.md").open("a", encoding="utf-8") as fh: fh.write("\n## D-9 · 2026-11-01 · legacy untagged\n- Why: old\n")
        p = run(root, "validate.py", "--context", ok=False); check("validate.py --context: untagged decision fails", p.returncode == 1 and "D-9" in p.stdout, p.stdout)
        w(root / "kit/blocks/nope.md", "# nope\n- **What:** x\n")
        p = run(root, "context.py", "check", "--blocks", "kit/blocks", ok=False); check("check: untagged card fails", p.returncode == 1 and "nope.md" in p.stdout, p.stdout)
        # --- ctxpack uses graph + symbols + tags ---
        kit = root / "_kit"; w(kit / "blocks/money-math.md", "# money-math\n- **Tags:** money\n- **What:** satang\n"); w(kit / "blocks/async-button.md", "# b\n- **Tags:** ui, button\n- **What:** b\n")
        cmd = lambda task, *a: json.loads(subprocess.run([sys.executable, str(HERE / "ctxpack.py"), task, "--kit", str(kit), "--json", *a], cwd=root, capture_output=True, text=True, encoding="utf-8", check=True).stdout)
        r = cmd("fix wrong total on dashboard", "--path", "app/dashboard/page.tsx")
        L = {x["item"]: x["why"] for x in r["loaded"]}
        pk = (root / "forgex/context-pack.md").read_text(encoding="utf-8")
        check("ctxpack: related files via import graph (not word guessing)", "CODEMAP related (import graph)" in L and "lib/money.ts" in pk and "app/other/page.tsx" not in pk, str(L))
        check("ctxpack: dashboard display stays STANDARD", r["mode"] == "STANDARD" and r["classifierMode"] == "STANDARD", str(r["modeReasons"]))
        r = cmd("bug in post_entry rounding", "--path", "server/api.py")
        pk = (root / "forgex/context-pack.md").read_text(encoding="utf-8")
        check("ctxpack: symbol index pulls defining file", "CODEMAP symbols" in [x["item"] for x in r["loaded"]] and "`post_entry` → server/ledger.py" in pk)
        r = cmd("show balance on dashboard", "--path", "app/dashboard/page.tsx")
        L = [x["item"] for x in r["loaded"]]
        check("ctxpack: decisions selected by tag (money D-1, ui+money D-2)", {"DECISIONS D-1", "DECISIONS D-2"} <= set(L), str(L))
        check("ctxpack: untagged legacy decision flagged when skipped", any("untagged" in s["why"] for s in r["skipped"] if "D-9" in s["item"]))
        check("ctxpack: report has tokensIn + method + estimate flag", isinstance(r["tokensIn"], int) and r["tokenMethod"] and isinstance(r["tokenEstimate"], bool))
        r = cmd("restyle css", "--mode", "GUARDED", "--path", "app/dashboard/page.tsx")
        check("ctxpack: classifierMode vs explicit mode both reported", r["mode"] == "GUARDED" and r["classifierMode"] in ("QUICK", "STANDARD") and r["explicitMode"] == "GUARDED", str(r["classifierMode"]))
        # --- tokens adapter + log ---
        p = run(root, "tokens.py", "count", "forgex/context-pack.md"); c = json.loads(p.stdout)
        check("tokens count: method labelled; chars/4 flagged as estimate", c["tokens"] > 0 and (c["estimate"] is True) == c["method"].startswith("chars/4"), str(c))
        run(root, "tokens.py", "log", "--task", "T2", "--classifier-mode", "GUARDED", "--actual-mode", "STANDARD", "--tokens-in", "41000", "--tokens-out", "3200", "--source", "cursor-usage")
        run(root, "tokens.py", "log", "--task", "T3", "--classifier-mode", "GUARDED", "--actual-mode", "GUARDED", "--pack", "forgex/context-pack.md")
        rep = json.loads(run(root, "tokens.py", "report").stdout)
        check("tokens report: false-GUARDED rate", rep["falseGuarded"] == 1 and rep["classifiedGuarded"] == 2 and rep["falseGuardedRate"] == 0.5, str(rep))
        check("tokens report: real (Cursor Usage) tokens separated from estimates", rep["realTokens"] >= 44200, str(rep))
        # --- non-UTF-8 locale ---
        env = {k: v for k, v in os.environ.items() if not k.startswith(("LC_", "LANG", "PYTHONUTF8", "PYTHONIOENCODING"))}; env.update(LC_ALL="C", PYTHONUTF8="0")
        p = subprocess.run([sys.executable, str(HERE / "context.py"), "close", "--now", "ทำครึ่งหนึ่ง", "--next", "เพิ่มหน้าอนุมัติ"], cwd=root, capture_output=True, env=env)
        p2 = subprocess.run([sys.executable, str(HERE / "codemap.py")], cwd=root, capture_output=True, env=env)
        check("utf-8: close (Thai) + codemap under LC_ALL=C", p.returncode == 0 and p2.returncode == 0 and "เพิ่มหน้าอนุมัติ" in (root / "forgex/STATE.md").read_text(encoding="utf-8"), (p.stderr + p2.stderr).decode("utf-8", "replace")[-300:])
    print("\nAll v2.8 context tests passed" if not FAIL else f"\n{FAIL} failed"); sys.exit(1 if FAIL else 0)

if __name__ == "__main__":
    main()
