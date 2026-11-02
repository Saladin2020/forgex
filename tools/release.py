#!/usr/bin/env python3
"""FORGEX dual-update release (stdlib + git + node). Never pushes or publishes.

  release.py [--sync-to DIR] [--no-sync]
0. test_ctxpack.py scenarios
1. build.py: dist/public (privacy-scanned) + dist/personal-<kit>
2. validate.mjs --dist
3. sync personal Grok Bot skill to --sync-to (default from config/kit.json "syncTo"), backing up the old copy
4. stage dist/public-repo/: public source tree (no kits/, no config/kit.json), re-scanned, committed locally
Publishing (git push, GitHub release with dist/public/*.zip) stays manual and needs the owner's OK each time.
When OK'd, an agent may use env GITHUB_TOKEN_FORGEX (fine-grained: Contents RW, Workflows RW, Administration RW
for repo creation) via per-command GIT_CONFIG_* http.extraheader; never store it in git config or remotes.
"""
import argparse, datetime, json, shutil, subprocess, sys, zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DIST = ROOT / "dist"
sys.path.insert(0, str(ROOT / "tools"))
import build  # noqa: E402

def run(*cmd, cwd=ROOT):
    print("$", " ".join(cmd)); subprocess.run(cmd, cwd=cwd, check=True)

def main():
    cfg = json.loads((ROOT / "config/kit.json").read_text()) if (ROOT / "config/kit.json").exists() else {}
    ap = argparse.ArgumentParser(); ap.add_argument("--sync-to", default=cfg.get("syncTo")); ap.add_argument("--no-sync", action="store_true")
    a = ap.parse_args()
    run(sys.executable, "tools/test_ctxpack.py")
    run(sys.executable, "tools/build.py")
    run("node", "tools/validate.mjs", "--dist")
    kit = cfg.get("kit")
    if kit and a.sync_to and not a.no_sync:
        dst = Path(a.sync_to); src = DIST / f"personal-{kit}/forgex-grokbot-skill/forgex"
        if dst.exists():
            bak = dst.parent.parent / "skill-backups" / f"{dst.name}.bak-{datetime.datetime.now():%Y%m%d-%H%M%S}"
            bak.parent.mkdir(exist_ok=True); shutil.copytree(dst, bak); shutil.rmtree(dst); print("backup:", bak)
        shutil.copytree(src, dst); print("synced:", dst)
    repo = DIST / "public-repo"; old_git = None
    if repo.exists() and (repo / ".git").exists():
        old_git = DIST / "_git"; shutil.move(str(repo / ".git"), old_git)
    shutil.rmtree(repo, ignore_errors=True)
    with zipfile.ZipFile(next((DIST / "public").glob("FORGEX_v*-src.zip"))) as z:
        z.extractall(DIST / "_src")
    inner = next((DIST / "_src").iterdir()); shutil.move(str(inner), repo); shutil.rmtree(DIST / "_src")
    terms = sorted({t.strip() for f in (ROOT / "kits").glob("*/private-terms.txt") for t in f.read_text().splitlines() if t.strip() and not t.startswith("#")})
    hits = build.scan(repo, terms)
    if hits: print("PRIVACY SCAN FAILED on public-repo:", *hits, sep="\n  "); sys.exit(1)
    print(f"privacy scan: dist/public-repo clean ({len(terms)} terms)")
    if old_git: shutil.move(str(old_git), repo / ".git")
    else: run("git", "init", "-q", "-b", "main", cwd=repo)
    ver = build.VERSION
    run("git", "add", "-A", cwd=repo)
    if subprocess.run(["git", "diff", "--cached", "--quiet"], cwd=repo).returncode:
        run("git", "-c", "user.name=FORGEX contributors", "-c", "user.email=forgex@users.noreply.github.com", "commit", "-q", "-m", f"FORGEX v{ver}", cwd=repo)
    if subprocess.run(["git", "rev-parse", "-q", "--verify", f"refs/tags/v{ver}"], cwd=repo, capture_output=True).returncode:
        run("git", "tag", f"v{ver}", cwd=repo)
    print(f"\nReady. Publish manually: push dist/public-repo, tag v{ver}, attach dist/public/*.zip to the release.")

if __name__ == "__main__":
    main()
