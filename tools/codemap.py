#!/usr/bin/env python3
"""FORGEX CODEMAP v2.8 (stdlib only): sharded JSON index + shallow import graph + symbol index.

  codemap.py [root] [--out forgex/codemap] [--md forgex/CODEMAP.md]
  codemap.py related <file> [--hops 2] [--root .]     -> files 1-2 import hops away (imports + importers)
  codemap.py symbol <name> [--root .]                 -> files that define <name>
Writes forgex/codemap/index.json (version, files -> shard), shards/<dir>.json (per dir: files, symbols, imports),
symbols.json (name -> [files]), graph.json (file -> imports, importedBy; resolved project files only).
TS/JS: import/export-from/require/dynamic import, relative and "@/" or "~/" aliases (root or src/). Python: import/from
(absolute + relative). forgex/CODEMAP.md stays as a short human summary (dirs + counts); nothing is truncated in JSON.
Uses `git ls-files` when available (respects .gitignore), else walks the tree. Re-run after adding/moving files.
"""
import argparse, json, re, subprocess, sys
from collections import defaultdict
from pathlib import Path
for _s in (sys.stdout, sys.stderr):  # Windows consoles (cp874/cp1252): never crash on Thai output
    try: _s.reconfigure(encoding="utf-8", errors="replace")
    except Exception: pass
sys.argv = [x.encode("utf-8", "surrogateescape").decode("utf-8", "replace") for x in sys.argv]  # non-UTF-8 POSIX locales

SKIP = re.compile(r"(^|/)(node_modules|\.next|dist|build|coverage|\.git|public|assets|vendor|forgex|__pycache__)(/|$)|\.(lock|png|jpe?g|gif|svg|ico|webp|ttf|woff2?|map|sql|pyc)$|lock\.(json|yaml)$")
JS = (".ts", ".tsx", ".js", ".jsx", ".mjs", ".cjs")
CODE = set(JS) | {".py", ".go", ".rs"}
EXP = re.compile(r"^export\s+(?:default\s+)?(?:async\s+)?(?:function\*?|const|let|var|class|type|interface|enum)\s+([A-Za-z_$][\w$]*)", re.M)
JSDEF = re.compile(r"^(?:async\s+)?(?:function\*?|class)\s+([A-Za-z_$][\w$]*)", re.M)
PYDEF = re.compile(r"^(?:async\s+)?(?:def|class)\s+([A-Za-z_]\w*)", re.M)
JSIMP = re.compile(r"""(?:import\s+(?:[\w*{}\s,$]+\s+from\s+)?|export\s+[\w*{}\s,$]+\s+from\s+|require\(\s*|import\(\s*)["']([^"']+)["']""")
PYIMP = re.compile(r"^\s*(?:from\s+(\.*[\w.]*)\s+import\s+([\w, *]+)|import\s+([\w., ]+))", re.M)
VERSION = "2.8.0"

def files(root):
    try: out = subprocess.run(["git", "ls-files"], cwd=root, capture_output=True, text=True, encoding="utf-8", check=True).stdout.splitlines()
    except Exception: out = []
    if not out: out = [p.relative_to(root).as_posix() for p in root.rglob("*") if p.is_file()]
    return sorted(f for f in out if not SKIP.search(f))

def read(p):
    try: return p.read_text(encoding="utf-8", errors="ignore")[:200000]
    except Exception: return ""

def symbols(f, text):
    suf = Path(f).suffix
    if suf == ".py": names = PYDEF.findall(text)
    elif suf in JS: names = EXP.findall(text) + JSDEF.findall(text)
    else: names = []
    return [n for n in dict.fromkeys(names) if not n.startswith("_")]

def resolve_js(spec, f, fileset):
    if spec.startswith("."): base = (Path(f).parent / spec).as_posix()
    elif spec[:2] in ("@/", "~/"): base = spec[2:]
    else: return None
    base = re.sub(r"(^|/)\./", r"\1", str(Path(base).as_posix()))
    parts = []
    for x in base.split("/"):
        if x == "..": parts and parts.pop()
        elif x and x != ".": parts.append(x)
    base = "/".join(parts)
    roots = [base] + ([f"src/{base}"] if spec[:2] in ("@/", "~/") else [])
    for b in roots:
        for c in [b] + [b + e for e in JS] + [f"{b}/index{e}" for e in JS] + ([re.sub(r"\.js$", e, b) for e in (".ts", ".tsx")] if b.endswith(".js") else []):
            if c in fileset: return c
    return None

def resolve_py(mod, f, fileset, names=()):
    if mod.startswith("."):
        dots = len(mod) - len(mod.lstrip(".")); base = Path(f).parent
        for _ in range(dots - 1): base = base.parent
        rest = mod.lstrip(".").replace(".", "/"); bases = [(base / rest).as_posix() if rest else base.as_posix()]
    else:
        rest = mod.replace(".", "/"); bases = [rest, f"src/{rest}", (Path(f).parent / rest).as_posix()]
    out = []
    for b in bases:
        b = b.lstrip("./") if b not in (".",) else ""
        cands = [f"{b}.py", f"{b}/__init__.py"] + [f"{b}/{n.strip()}.py" for n in names if n.strip() and n.strip() != "*"]
        out += [c.lstrip("/") for c in cands if c.lstrip("/") in fileset]
        if out: break
    return out

def imports(f, text, fileset):
    suf, out = Path(f).suffix, []
    if suf in JS: out = [r for s in JSIMP.findall(text) if (r := resolve_js(s, f, fileset))]
    elif suf == ".py":
        for frm, names, plain in PYIMP.findall(text):
            if frm: out += resolve_py(frm, f, fileset, names.split(","))
            else: out += [r for m in plain.split(",") for r in resolve_py(m.strip().split(" ")[0], f, fileset)]
    return sorted(set(x for x in out if x != f))

def shard_name(d): return (d.replace("/", "__") if d not in ("", ".") else "_root") + ".json"

def build(root):
    fl = files(root); fs = set(fl); data = {}
    for f in fl:
        p = root / f; is_code = p.suffix in CODE; t = read(p) if is_code else ""
        data[f] = {"symbols": symbols(f, t) if is_code else [], "imports": imports(f, t, fs) if is_code else []}
    importers = defaultdict(set)
    for f, d in data.items():
        for i in d["imports"]: importers[i].add(f)
    graph = {f: {"imports": d["imports"], "importedBy": sorted(importers[f])} for f, d in data.items() if d["imports"] or importers[f]}
    syms = defaultdict(list)
    for f, d in data.items():
        for s in d["symbols"]: syms[s].append(f)
    by_dir = defaultdict(dict)
    for f, d in data.items(): by_dir[Path(f).parent.as_posix()][f] = d
    return data, graph, dict(sorted(syms.items())), by_dir

def write(root, out, md):
    data, graph, syms, by_dir = build(root)
    out = root / out; sh = out / "shards"
    if sh.is_dir():
        for old in sh.glob("*.json"): old.unlink()
    sh.mkdir(parents=True, exist_ok=True)
    for d, fs in by_dir.items(): (sh / shard_name(d)).write_text(json.dumps({"dir": d, "files": fs}, ensure_ascii=False, indent=1), encoding="utf-8")
    idx = {"version": VERSION, "files": len(data), "dirs": {d: {"shard": f"shards/{shard_name(d)}", "files": len(fs)} for d, fs in sorted(by_dir.items())}}
    (out / "index.json").write_text(json.dumps(idx, ensure_ascii=False, indent=1), encoding="utf-8")
    (out / "symbols.json").write_text(json.dumps(syms, ensure_ascii=False, indent=1), encoding="utf-8")
    (out / "graph.json").write_text(json.dumps(graph, ensure_ascii=False, indent=1), encoding="utf-8")
    mdp = root / md; notes = []
    if mdp.exists():
        t = mdp.read_text(encoding="utf-8"); notes = t.split("## Notes", 1)[1].strip().splitlines() if "## Notes" in t else []
    L = ["# CODEMAP (summary; full data in forgex/codemap/*.json, generated by codemap.py)", "",
         f"{len(data)} files · {len(syms)} symbols · {sum(len(g['imports']) for g in graph.values())} import edges", "", "## Dirs"]
    L += [f"- `{d}/` ({len(fs)} files)" for d, fs in sorted(by_dir.items())]
    L += ["", "## Notes", *(notes or ["# note: add one-line hints here; they survive refresh"])]
    mdp.parent.mkdir(parents=True, exist_ok=True); mdp.write_text("\n".join(L) + "\n", encoding="utf-8")
    print(f"wrote {out}/ (index, {len(by_dir)} shards, {len(syms)} symbols, {len(graph)} graph nodes) + {md}")

def load(root, out="forgex/codemap"):
    d = Path(root) / out
    if not (d / "index.json").exists(): return None
    j = lambda n: json.loads((d / n).read_text(encoding="utf-8"))
    return {"index": j("index.json"), "symbols": j("symbols.json"), "graph": j("graph.json"), "dir": d}

def shard_entry(cm, f):
    meta = cm["index"]["dirs"].get(Path(f).parent.as_posix())
    if not meta: return None
    return json.loads((cm["dir"] / meta["shard"]).read_text(encoding="utf-8"))["files"].get(f)

def related(cm, paths, hops=2):
    """BFS over imports + importers, up to `hops`. Returns {file: hop}."""
    g, seen, front = cm["graph"], {p: 0 for p in paths}, list(paths)
    for h in range(1, hops + 1):
        nxt = []
        for f in front:
            n = g.get(f, {})
            for x in n.get("imports", []) + n.get("importedBy", []):
                if x not in seen: seen[x] = h; nxt.append(x)
        front = nxt
    return {f: h for f, h in seen.items() if h}

IDENT = re.compile(r"[A-Za-z_$][\w$]{2,}")
def symbol_hits(cm, task):
    """Identifiers in the task text that are defined symbols (exact or case-insensitive). {name: [files]}"""
    syms = cm["symbols"]; low = {k.lower(): k for k in syms}; out = {}
    for w in IDENT.findall(task or ""):
        k = w if w in syms else low.get(w.lower()) if (any(c.isupper() for c in w[1:]) or "_" in w or len(w) >= 6) else None
        if k: out[k] = syms[k]
    return out

def main():
    if len(sys.argv) > 1 and sys.argv[1] in ("related", "symbol"):
        ap = argparse.ArgumentParser(); ap.add_argument("cmd"); ap.add_argument("arg"); ap.add_argument("--hops", type=int, default=2); ap.add_argument("--root", default=".")
        a = ap.parse_args(); cm = load(a.root)
        if not cm: sys.exit("codemap: forgex/codemap/index.json missing; run codemap.py first")
        res = related(cm, [a.arg.replace("\\", "/").lstrip("./")], a.hops) if a.cmd == "related" else cm["symbols"].get(a.arg, [])
        print(json.dumps(res, ensure_ascii=False, indent=1)); return
    ap = argparse.ArgumentParser(); ap.add_argument("root", nargs="?", default=".")
    ap.add_argument("--out", default="forgex/codemap"); ap.add_argument("--md", default="forgex/CODEMAP.md")
    ap.add_argument("--max-lines", type=int, help=argparse.SUPPRESS)  # v2.7 flag, ignored (no truncation since v2.8)
    a = ap.parse_args(); write(Path(a.root).resolve(), a.out, a.md)

if __name__ == "__main__":
    main()
