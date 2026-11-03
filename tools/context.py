#!/usr/bin/env python3
"""FORGEX context files (stdlib only). Run from project root.

  context.py init                      -> creates forgex/STATE.md, forgex/DECISIONS.md (never overwrites)
  context.py decide "<decision>" --why "<why>" --tag auth [--tag db] [--alt "<option>" ...] [--supersedes D-3]
  context.py close --now "<status>" --next "<step>" [--next "<step>" ...] [--task <id>] [--mode M] [--by <chat>]
                                       -> rewrites Updated + Now/Plan in forgex/STATE.md (cross-chat plan persistence)
  context.py resume                    -> prints Plan + Now from STATE (+ open contract) for a new chat; read it FIRST
  context.py check [--max-age-hours N] -> STATE has a filled Plan/Next + Updated line; DECISIONS/cards all tagged (exit 1)
"""
import argparse, datetime, json, re, sys
from pathlib import Path
for _s in (sys.stdout, sys.stderr):  # Windows consoles (cp874/cp1252): never crash on Thai output
    try: _s.reconfigure(encoding="utf-8", errors="replace")
    except Exception: pass

HERE = Path(__file__).resolve().parent
TPL = next((p for p in (HERE.parent / "templates", HERE.parent / "core/templates") if p.is_dir()), None)
OUT = Path("forgex")
PLAN_RE = re.compile(r"(?m)^##\s*(Plan|Next steps?|Next)\b.*$")
PLACEHOLDER = re.compile(r"<[^>]+>")
TAGS_RE = re.compile(r"^\s*-\s*\**Tags:?\**:?\s*(.+)$", re.M | re.I)

def section(text, rx):
    m = rx.search(text)
    if not m: return None
    rest = text[m.end():]; n = re.search(r"(?m)^## ", rest)
    return rest[: n.start()] if n else rest

def items(body): return [l.strip() for l in (body or "").splitlines() if re.match(r"\s*(\d+[.)]|[-*])\s+\S", l)]

def state_problems(text, max_age_hours=None, now=None):
    """Problems that would stop a new chat from continuing. Empty list = resumable."""
    p = []
    m = re.search(r"(?m)^Updated:\s*(.+)$", text)
    if not m or PLACEHOLDER.search(m.group(1)): p.append("STATE: 'Updated:' line missing or still a placeholder")
    elif max_age_hours is not None:
        d = re.match(r"(\d{4}-\d{2}-\d{2})(?:[ T](\d{2}:\d{2}))?", m.group(1).strip())
        if d:
            ts = datetime.datetime.fromisoformat(d.group(1) + "T" + (d.group(2) or "00:00"))
            if ((now or datetime.datetime.now()) - ts).total_seconds() > max_age_hours * 3600:
                p.append(f"STATE: Updated {m.group(1).strip()} is older than {max_age_hours}h (rewrite Plan before ending the chat)")
    body = section(text, PLAN_RE)
    if body is None: p.append("STATE: no '## Plan' (or '## Next steps') section")
    else:
        real = [i for i in items(body) if not PLACEHOLDER.search(i)]
        if not real: p.append("STATE: Plan/Next section has no concrete step (placeholders only)")
    return p

def decisions_untagged(text):
    out = []
    for e in re.split(r"(?m)^(?=## D-\d+)", text)[1:]:
        m = TAGS_RE.search(e)
        if not m or not [t for t in m.group(1).split(",") if t.strip()]: out.append(e.splitlines()[0].split("·")[0].strip("# ").strip())
    return out

def card_untagged(path):
    m = TAGS_RE.search(Path(path).read_text(encoding="utf-8"))
    return not m or PLACEHOLDER.search(m.group(1)) or not [t for t in m.group(1).split(",") if t.strip()]

def cards_untagged(blocks_dir):
    return [c.name for c in sorted(Path(blocks_dir).glob("*.md")) if not c.name.startswith("_") and c.name != "INDEX.md" and card_untagged(c)]

def init():
    OUT.mkdir(exist_ok=True)
    for name in ("STATE.md", "DECISIONS.md"):
        dst = OUT / name
        if dst.exists(): print(f"exists: {dst}")
        else: dst.write_text((TPL / name).read_text(encoding="utf-8"), encoding="utf-8"); print(f"created: {dst}")

def decide(a):
    p = OUT / "DECISIONS.md"
    if not p.exists(): sys.exit("run `context.py init` first")
    tags = [t.strip().lower() for x in a.tag for t in x.split(",") if t.strip()]
    if not tags: sys.exit("decide: at least one --tag is required (v2.8)")
    text = p.read_text(encoding="utf-8")
    n = 1 + max([int(x) for x in re.findall(r"^## D-(\d+)", text, re.M)] or [0])
    one = lambda s: " ".join(s.split())
    lines = [f"\n## D-{n} · {datetime.date.today().isoformat()} · {one(a.decision)}", f"- Why: {one(a.why)}"]
    if a.alt: lines.append("- Rejected: " + "; ".join(one(x) for x in a.alt))
    lines.append("- Tags: " + ", ".join(dict.fromkeys(tags)))
    if a.supersedes: lines.append(f"- Supersedes: {a.supersedes}")
    p.write_text(text.rstrip("\n") + "\n" + "\n".join(lines) + "\n", encoding="utf-8"); print(f"added D-{n}")

def close(a):
    p = OUT / "STATE.md"
    text = p.read_text(encoding="utf-8") if p.exists() else (TPL / "STATE.md").read_text(encoding="utf-8")
    stamp = datetime.datetime.now().astimezone().strftime("%Y-%m-%d %H:%M %Z").strip()
    upd = f"Updated: {stamp} by {a.by or 'agent'}"
    text = re.sub(r"(?m)^Updated:.*$", lambda _: upd, text, count=1) if re.search(r"(?m)^Updated:", text) else text.replace("\n", f"\n{upd}\n", 1)
    now = f"- Working on: {a.task or '-'}   Mode: {a.mode or '-'}\n- Status: {' '.join(a.now.split())}\n" + (f"- Contract: forgex/tasks/{a.task}.json\n" if a.task and Path(f'forgex/tasks/{a.task}.json').exists() else "")
    plan = "".join(f"{i}. {' '.join(s.split())}\n" for i, s in enumerate(a.next, 1))
    def put(text, rx, head, body):
        m = rx.search(text)
        if not m: return text.rstrip("\n") + f"\n{head}\n{body}"
        rest = text[m.end():]; n = re.search(r"(?m)^## ", rest); end = m.end() + (n.start() if n else len(rest))
        return text[: m.start()] + head + "\n" + body + text[end:]
    text = put(text, re.compile(r"(?m)^##\s*Now\b.*$"), "## Now", now)
    text = put(text, PLAN_RE, "## Plan (next chat starts here; numbered, concrete, file paths)", plan)
    OUT.mkdir(exist_ok=True); p.write_text(text, encoding="utf-8")
    probs = state_problems(text); print("closed: forgex/STATE.md plan saved" if not probs else "\n".join(probs)); sys.exit(1 if probs else 0)

def resume():
    p = OUT / "STATE.md"
    if not p.exists(): sys.exit("resume: forgex/STATE.md missing; nothing to continue (ask what to do)")
    t = p.read_text(encoding="utf-8")
    probs = state_problems(t)
    m = re.search(r"(?m)^Updated:.*$", t)
    print(m.group(0) if m else "Updated: ?")
    print("## Plan\n" + "\n".join(items(section(t, PLAN_RE))) if section(t, PLAN_RE) else "## Plan\n(none)")
    print("## Now\n" + (section(t, re.compile(r"(?m)^##\s*Now\b.*$")) or "(none)").strip())
    c = re.search(r"forgex/tasks/[\w.-]+\.json", t)
    if c and Path(c.group(0)).exists():
        j = json.loads(Path(c.group(0)).read_text(encoding="utf-8"))
        print(f"## Open contract {c.group(0)}: status {j.get('status')} · mode {j.get('mode')} · goal {j.get('goal', '')[:120]}")
    for x in probs: print("warning:", x)
    print("Continue with Plan step 1. Do not start other work until the plan is done or the user changes it.")

def check(a):
    probs = []
    sp = OUT / "STATE.md"
    probs += state_problems(sp.read_text(encoding="utf-8"), a.max_age_hours) if sp.exists() else ["forgex/STATE.md missing"]
    dp = OUT / "DECISIONS.md"
    if dp.exists(): probs += [f"DECISIONS {d}: missing '- Tags:' line" for d in decisions_untagged(dp.read_text(encoding="utf-8"))]
    for b in a.blocks or []: probs += [f"card {b}/{c}: missing '- **Tags:**' line" for c in cards_untagged(b)]
    print("\n".join(probs) if probs else "context: ok (plan saved, all entries tagged)"); sys.exit(1 if probs else 0)

def main():
    ap = argparse.ArgumentParser(); sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("init")
    d = sub.add_parser("decide"); d.add_argument("decision"); d.add_argument("--why", required=True)
    d.add_argument("--alt", action="append"); d.add_argument("--supersedes"); d.add_argument("--tag", action="append", required=True)
    c = sub.add_parser("close"); c.add_argument("--now", required=True); c.add_argument("--next", action="append", required=True)
    c.add_argument("--task"); c.add_argument("--mode"); c.add_argument("--by")
    sub.add_parser("resume")
    k = sub.add_parser("check"); k.add_argument("--max-age-hours", type=float); k.add_argument("--blocks", action="append")
    a = ap.parse_args()
    {"init": lambda: init(), "decide": lambda: decide(a), "close": lambda: close(a), "resume": lambda: resume(), "check": lambda: check(a)}[a.cmd]()

if __name__ == "__main__":
    sys.argv = [x.encode("utf-8", "surrogateescape").decode("utf-8", "replace") for x in sys.argv]  # non-UTF-8 POSIX locales
    main()
