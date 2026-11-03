#!/usr/bin/env python3
"""Build FORGEX packages from core/ (stdlib only).

dist/public/                 generic: blank house template only, no kit, privacy-scanned
dist/personal-<kit>/         same + kits/<kit>/ shipped as references/kit/ (kit from config/kit.json or --kit)
Each holds forgex-cursor-plugin/, forgex-grokbot-skill/forgex/ and their zips; public also FORGEX_v<ver>-src.zip.
  build.py [--kit NAME] [--public-only]
"""
import argparse, json, re, shutil, sys, zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DIST = ROOT / "dist"
VERSION = json.loads((ROOT / "package.json").read_text(encoding="utf-8"))["version"]
TEXT = {".md", ".mdc", ".json", ".py", ".mjs", ".js", ".yml", ".txt", ""}
SECRETISH = re.compile(r"(postgres(ql)?://\S+:\S+@|sk_(live|test)_\w+|ghp_\w{20,}|AKIA[0-9A-Z]{16}|-----BEGIN [A-Z ]*PRIVATE KEY|[\w.+-]+@(gmail|hotmail|outlook|yahoo)\.com)", re.I)

def references(dst: Path, kit: Path | None):
    dst.mkdir(parents=True, exist_ok=True)
    shutil.copy(ROOT / "core/FORGEX.md", dst / "FORGEX.md")
    for d in ("guides", "templates", "house", "risk"):
        shutil.copytree(ROOT / "core" / d, dst / d, ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
    if kit:
        shutil.copytree(kit, dst / "kit", ignore=shutil.ignore_patterns("private-terms.txt"))
    shutil.copytree(ROOT / "schemas", dst / "schemas")
    (dst / "config").mkdir(); shutil.copy(ROOT / "config/default-policy.json", dst / "config"); shutil.copy(ROOT / "config/context-policy.json", dst / "config")
    (dst / "tools").mkdir()
    for f in ("validate.mjs", "scaffold.py", "context.py", "codemap.py", "ctxpack.py", "tokens.py", "forgex.py", "roadmap.py", "harvest.py", "style.py", "review.py", "test_risk.py", "validate.py"): shutil.copy(ROOT / "tools" / f, dst / "tools")
    shutil.copytree(ROOT / "extras", dst / "extras")
    shutil.copytree(ROOT / "tools/hooks", dst / "tools/hooks")
    shutil.copytree(ROOT / "tools/vendor", dst / "tools/vendor")
    shutil.copy(ROOT / "package.json", dst / "package.json")

def zipdir(src: Path, out: Path, prefix: str = "", skip=("node_modules", "dist", ".git", "__pycache__")):
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as z:
        for p in sorted(src.rglob("*")):
            rel = p.relative_to(src)
            if any(part in skip for part in rel.parts) or not p.is_file():
                continue
            z.write(p, str(Path(prefix) / rel))

def package(out: Path, kit: Path | None, author: str | None):
    out.mkdir(parents=True)
    cp = out / "forgex-cursor-plugin"
    (cp / ".cursor-plugin").mkdir(parents=True)
    m = json.loads((ROOT / "targets/cursor/plugin.json").read_text(encoding="utf-8")); m["version"] = VERSION
    if author: m["author"] = {"name": author}
    (cp / ".cursor-plugin/plugin.json").write_text(json.dumps(m, indent=2) + "\n", encoding="utf-8")
    shutil.copytree(ROOT / "core/rules", cp / "rules")
    shutil.copytree(ROOT / "targets/cursor/commands", cp / "commands")
    for target in (cp / "skills/forgex", out / "forgex-grokbot-skill/forgex"):
        target.mkdir(parents=True); shutil.copy(ROOT / "core/skill/SKILL.md", target / "SKILL.md")
        references(target / "references", kit)
    for f in ("README.md", "QUICKSTART.md", "LICENSE"): shutil.copy(ROOT / f, cp / f)
    zipdir(cp, out / "forgex-cursor-plugin.zip", "forgex")
    zipdir(out / "forgex-grokbot-skill", out / "forgex-grokbot-skill.zip")

def scan(base: Path, terms: list[str]) -> list[str]:
    hits = []
    for p in base.rglob("*"):
        if not p.is_file() or p.suffix.lower() not in TEXT: continue
        t = p.read_text(errors="ignore"); low = t.lower()
        for term in terms:
            if term.lower() in low: hits.append(f"{p.relative_to(DIST)}: term {term!r}")
        for m in SECRETISH.finditer(t): hits.append(f"{p.relative_to(DIST)}: pattern {m.group(0)[:30]!r}")
    return hits

def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--kit"); ap.add_argument("--public-only", action="store_true")
    a = ap.parse_args()
    name = a.kit or json.loads((ROOT / "config/kit.json").read_text(encoding="utf-8")).get("kit")
    DIST.mkdir(exist_ok=True)  # keep dist/public-repo (its .git holds publish history)
    for d in DIST.iterdir():
        if d.name != "public-repo": shutil.rmtree(d) if d.is_dir() else d.unlink()
    pub = DIST / "public"
    package(pub, None, None)
    zipdir(ROOT, pub / f"FORGEX_v{VERSION}-src.zip", f"FORGEX_v{VERSION}", skip=("node_modules", "dist", ".git", "kits", "kit.json", "__pycache__"))
    # Privacy scan: every kit's private-terms.txt must be absent from the public output.
    terms = sorted({t.strip() for f in (ROOT / "kits").glob("*/private-terms.txt") for t in f.read_text(encoding="utf-8").splitlines() if t.strip() and not t.startswith("#")})
    zipcheck = DIST / "_scan"; 
    with zipfile.ZipFile(pub / f"FORGEX_v{VERSION}-src.zip") as z: z.extractall(zipcheck)
    hits = scan(pub, terms) + scan(zipcheck, terms); shutil.rmtree(zipcheck)
    if hits:
        print("PRIVACY SCAN FAILED:", *hits, sep="\n  "); sys.exit(1)
    print(f"privacy scan: public package clean ({len(terms)} private terms + secret/email patterns)")
    if name and not a.public_only:
        kit = ROOT / "kits" / name
        if not kit.is_dir(): sys.exit(f"kit not found: {kit}")
        meta = kit / "kit.json"
        author = json.loads(meta.read_text(encoding="utf-8")).get("author") if meta.exists() else None
        package(DIST / f"personal-{name}", kit, author)
    for d in sorted(x for x in DIST.iterdir() if x.name != "public-repo"): print("built:", d.name, *sorted(p.name for p in d.iterdir()))

if __name__ == "__main__":
    main()
