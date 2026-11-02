#!/usr/bin/env python3
"""Token counts (tiktoken cl100k_base; fallback ceil(chars/4), labelled) for v2 vs v2.1 vs v2.2.
Usage: measure_tokens.py <v2_root> <v2.1_root> <v2.2_root> <v2_task_artifacts_dir>"""
import sys, math, json, subprocess
from pathlib import Path
try:
    import tiktoken; enc = tiktoken.get_encoding("cl100k_base"); METHOD = "tiktoken cl100k_base"; count = lambda s: len(enc.encode(s))
except ImportError:
    METHOD = "chars/4 estimate"; count = lambda s: math.ceil(len(s) / 4)
v2, v21, v22, v2t = map(Path, sys.argv[1:5])
tok = lambda *fs: sum(count(Path(f).read_text()) for f in fs)
body = lambda f: count(Path(f).read_text())
def render(f):
    return count(subprocess.run([sys.executable, str(v22 / "tools/scaffold.py"), "render", str(f)], capture_output=True, text=True, check=True).stdout)
V = v22 / "examples/contracts/valid"
rows = [("Always-on rule forgex.mdc", body(v2/"core/rules/forgex.mdc"), body(v21/"core/rules/forgex.mdc"), body(v22/"core/rules/forgex.mdc"), None)]
rows.append(("Always-on skill catalog entry", *(count((p/"core/skill/SKILL.md").read_text().split("---")[1]) for p in (v2, v21, v22)), None))
rows.append(("On demand: SKILL.md", *(body(p/"core/skill/SKILL.md") for p in (v2, v21, v22)), None))
for m, f21 in (("QUICK", ["quick.md"]), ("STANDARD", ["standard.md"]), ("GUARDED", ["guarded.json", "guarded.closeout.md"])):
    k = m.lower()
    a = tok(v2t/f"{k}.json", v2t/f"{k}.blueprint.md", v2t/f"{k}.closeout.md")
    b = tok(*[v2t/"v2.1"/x for x in f21])
    j = V / f"{k}-completed.json"
    rows.append((f"Task {m}: written artifacts", a, b, body(j), render(j)))
print(f"Method: {METHOD}\n")
print("| Item | v2 | v2.1 | v2.2 | v2.2 rendered closeout (generated, not typed) |\n|---|---:|---:|---:|---:|")
for n, a, b, c, r in rows: print(f"| {n} | {a} | {b} | {c} | {'' if r is None else r} |")
