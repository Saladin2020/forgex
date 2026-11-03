#!/usr/bin/env python3
"""FORGEX UI style capture (stdlib). Draft tokens + UI pattern cards from reference images or URLs.

  forgex.py style capture <image-or-url ...> [--out forgex/style] [--no-fetch]
Writes DRAFTS only (forgex/style/): style.draft.json (spacing, radius, shadow, color, type scale, motion), DESIGN.draft.md,
cards/ui-skeleton-list.md, ui-empty-state.md, ui-data-table.md (runnable example components + rules), CHECKLIST.md.
The tool cannot see images: for images it writes a structured template + agent instructions (the agent looks at the image
and fills values). For http(s)/file URLs it fetches the page and up to 5 same-origin stylesheets and pulls CSS custom
properties (--x: v) plus common values (border-radius, box-shadow, font-size, transition/animation durations).
Copy style PRINCIPLES only: never logos, images, fonts files, brand assets or code verbatim. Review, then move into
your DESIGN.md / kit cards by hand.
"""
import json, re, sys, urllib.parse, urllib.request
from pathlib import Path

IMG = re.compile(r"\.(png|jpe?g|webp|gif|avif|bmp)$", re.I)
VAR = re.compile(r"(--[\w-]+)\s*:\s*([^;{}]+);")
PROPS = {"radius": r"border-radius\s*:\s*([^;{}]+);", "shadow": r"box-shadow\s*:\s*([^;{}]+);", "fontSize": r"font-size\s*:\s*([^;{}]+);",
         "spacing": r"(?:gap|padding|margin)\s*:\s*([^;{}]+);", "duration": r"(?:transition|animation)(?:-duration)?\s*:\s*[^;{}]*?(\d+(?:\.\d+)?m?s)"}
GUIDE = "Copy style principles (rhythm, density, radius, contrast, motion timing). Never copy logos, images, icons, font files, brand names or code verbatim."

def fetch(url, limit=400000):
    with urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": "forgex-style/2.9"}), timeout=15) as r:
        return r.read(limit).decode("utf-8", "replace")

def from_url(url):
    html = fetch(url); css = "\n".join(re.findall(r"<style[^>]*>(.*?)</style>", html, re.S | re.I)) + "\n" + " ".join(re.findall(r'style="([^"]+)"', html))
    base = urllib.parse.urlparse(url); sheets = []
    for href in re.findall(r'<link[^>]+rel=["\']?stylesheet["\']?[^>]*href=["\']([^"\']+)', html, re.I) + re.findall(r'<link[^>]+href=["\']([^"\']+\.css[^"\']*)["\'][^>]*rel=["\']?stylesheet', html, re.I):
        u = urllib.parse.urljoin(url, href)
        if urllib.parse.urlparse(u).netloc == base.netloc and u not in sheets: sheets.append(u)
    for u in sheets[:5]:
        try: css += "\n" + fetch(u)
        except Exception: pass
    vars_ = {}
    for k, v in VAR.findall(css): vars_.setdefault(k, v.strip())
    found = {k: sorted(set(x.strip() for x in re.findall(rx, css, re.I)))[:12] for k, rx in PROPS.items()}
    return {"source": url, "kind": "url", "cssVariables": dict(list(vars_.items())[:120]), "observed": found, "stylesheets": sheets[:5]}

def guess(vars_, words):
    return {k: v for k, v in vars_.items() if any(w in k.lower() for w in words)}

def draft(sources):
    v = {k: x for s in sources for k, x in s.get("cssVariables", {}).items()}
    obs = lambda k: sorted({x for s in sources for x in s.get("observed", {}).get(k, [])})
    return {"version": "2.9.0", "status": "draft", "sources": [s["source"] for s in sources], "principlesOnly": GUIDE,
            "tokens": {"color": guess(v, ["color", "bg", "fg", "accent", "brand", "border", "muted"]) or {"--color-bg": "?", "--color-fg": "?", "--color-card": "?", "--color-border": "?", "--color-accent": "?", "--color-muted": "?"},
                       "spacing": guess(v, ["space", "gap", "pad"]) or {"scale": obs("spacing") or ["4px", "8px", "12px", "16px", "24px", "32px"], "note": "?"},
                       "radius": guess(v, ["radius", "rounded"]) or {"--radius-card": (obs("radius") or ["?"])[0], "--radius-control": "?", "all": obs("radius")},
                       "shadow": guess(v, ["shadow", "elev"]) or {"--shadow-card": (obs("shadow") or ["?"])[0], "all": obs("shadow")},
                       "type": guess(v, ["font", "text", "leading", "line"]) or {"scale": obs("fontSize") or ["12px", "14px", "16px", "20px", "24px", "32px"], "body": "?", "display": "?"},
                       "motion": {**guess(v, ["duration", "ease", "motion", "anim"]), "durationsSeen": obs("duration"), "skeletonShimmerMs": "? (typ. 1200-1600)", "staggerMs": "? (typ. 40-80 per row)", "easing": "?", "reducedMotion": "disable shimmer + stagger under prefers-reduced-motion"}},
            "agentFill": [s for s in sources if s["kind"] == "image"]}

def design_md(d):
    L = ["# DESIGN (DRAFT from forgex style capture; review, then merge into DESIGN.md)", f"> {GUIDE}", "", f"Sources: {', '.join(d['sources'])}", ""]
    for k, t in d["tokens"].items(): L += [f"## {k}"] + [f"- `{a}`: {b}" for a, b in t.items()] + [""]
    if d["agentFill"]:
        L += ["## Fill from images (agent)", "Open each image and replace every `?` above with what you SEE (estimate px from the layout grid; colors as hex from the dominant areas).",
              "Note: density (compact/comfortable), corner style, shadow depth, heading weight, how lists load (skeleton? stagger?), empty and error looks.",
              *[f"- {s['source']}" for s in d["agentFill"]]]
    return "\n".join(L) + "\n"

CARDS = {
 "ui-skeleton-list": ("ui, skeleton, loading", "Skeleton list that matches the real row shape", '''```tsx
export function SkeletonList({ rows = 5 }: { rows?: number }) {
  return (
    <ul aria-busy="true" aria-label="loading" className="divide-y divide-[var(--color-border)]">
      {Array.from({ length: rows }, (_, i) => (
        <li key={i} className="flex items-center gap-3 py-3" style={{ animationDelay: `calc(${i} * var(--stagger-ms, 60ms))` }}>
          <div className="skeleton size-10 rounded-full" />{/* same size as the real avatar */}
          <div className="flex-1 space-y-2"><div className="skeleton h-4 w-2/5 rounded" /><div className="skeleton h-3 w-3/5 rounded" /></div>
          <div className="skeleton h-6 w-16 rounded-[var(--radius-control)]" />{/* same as the real status pill */}
        </li>))}
    </ul>);
}
/* globals.css: .skeleton{background:linear-gradient(90deg,var(--color-muted) 25%,var(--color-card) 50%,var(--color-muted) 75%);background-size:200% 100%;animation:shimmer var(--shimmer-ms,1400ms) linear infinite}
   @keyframes shimmer{to{background-position:-200% 0}} @media (prefers-reduced-motion:reduce){.skeleton{animation:none}} */
```''', ["Skeleton = same layout shape as the real row (avatar size, line count, pill width); no layout shift when data arrives.", "Shimmer timing and stagger come from motion tokens; respect prefers-reduced-motion.", "Show only while loading; then render empty, error or data."]),
 "ui-empty-state": ("ui, empty-state", "Empty / error state with one clear next action", '''```tsx
export function EmptyState({ title, hint, action }: { title: string; hint?: string; action?: React.ReactNode }) {
  return (
    <div role="status" className="mx-auto flex max-w-sm flex-col items-center gap-2 py-12 text-center">
      <p className="text-base font-medium text-[var(--color-fg)]">{title}</p>
      {hint && <p className="text-sm text-[var(--color-muted)]">{hint}</p>}
      {action}
    </div>);
}
// error: <EmptyState title="โหลดไม่สำเร็จ" hint="ลองใหม่อีกครั้ง" action={<button onClick={retry}>ลองใหม่</button>} />
```''', ["Empty and error are different messages; error always offers retry.", "One action max; no stock illustration copied from the reference.", "Text uses tokens (fg/muted), not raw hex."]),
 "ui-data-table": ("ui, table, data-table", "Data table with loading/empty/error and a mobile card layout", '''```tsx
type Col<T> = { key: keyof T; label: string; align?: "right" };
export function DataTable<T extends { id: string }>({ cols, rows, state }: { cols: Col<T>[]; rows: T[]; state: "loading" | "error" | "ready" }) {
  if (state === "loading") return <SkeletonList rows={5} />;
  if (state === "error") return <EmptyState title="โหลดไม่สำเร็จ" hint="ลองใหม่" />;
  if (!rows.length) return <EmptyState title="ยังไม่มีข้อมูล" />;
  return (<>
    <table className="hidden w-full text-sm md:table"><thead><tr>{cols.map((c) => <th key={String(c.key)} className={c.align === "right" ? "text-right" : "text-left"}>{c.label}</th>)}</tr></thead>
      <tbody>{rows.map((r) => <tr key={r.id} className="border-t border-[var(--color-border)]">{cols.map((c) => <td key={String(c.key)} className={c.align === "right" ? "text-right tabular-nums" : ""}>{String(r[c.key])}</td>)}</tr>)}</tbody></table>
    <ul className="space-y-2 md:hidden">{rows.map((r) => <li key={r.id} className="rounded-[var(--radius-card)] bg-[var(--color-card)] p-3 shadow-[var(--shadow-card)]">{cols.map((c) => <div key={String(c.key)} className="flex justify-between"><span className="text-[var(--color-muted)]">{c.label}</span><span>{String(r[c.key])}</span></div>)}</li>)}</ul>
  </>);
}
```''', ["Four states: loading (skeleton in table shape), empty, error, ready.", "Mobile (<768px): rows become cards; numbers right-aligned with tabular-nums.", "Money columns format via the kit money block, never float math in the view."]),
}

CHECK = """# Visual check (run on the real page, light + dark, 375px and 1280px)
- [ ] Colors, radius, shadow, spacing come from tokens (no raw hex in components)
- [ ] Type scale: headings/body/small match the draft scale; Thai text not clipped (line-height ≥ 1.5)
- [ ] Skeleton has the same shape as the loaded content; no layout shift when data arrives
- [ ] Shimmer duration and stagger match motion tokens; off under prefers-reduced-motion
- [ ] Every list/table has loading, empty, error and mobile states
- [ ] Focus rings visible; contrast AA for text on bg and on accent
- [ ] Nothing copied verbatim: no logos, images, icons, font files, brand names or code from the reference
"""

def card_md(name, tags, what, code, rules):
    return f"# {name}  (DRAFT from style capture)\n- **Tags:** {tags}\n- **What:** {what}\n- **From:** style capture (principles only)\n- **Reuse:** copy the component, wire tokens from DESIGN.md\n- **Gotchas:** " + "; ".join(rules) + f"\n\n{code}\n\n## Rules\n" + "\n".join(f"- {r}" for r in rules) + "\n"

def capture(srcs, out="forgex/style", no_fetch=False):
    sources = []
    for s in srcs:
        if re.match(r"^(https?|file)://", s) and not IMG.search(urllib.parse.urlparse(s).path) and not no_fetch:
            try: sources.append(from_url(s))
            except Exception as e: sources.append({"source": s, "kind": "image", "note": f"fetch failed ({type(e).__name__}); fill by looking at a screenshot"})
        else: sources.append({"source": s, "kind": "image", "note": "agent: open the image and fill every '?'"})
    d = draft(sources); o = Path(out); (o / "cards").mkdir(parents=True, exist_ok=True)
    (o / "style.draft.json").write_text(json.dumps(d, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    (o / "DESIGN.draft.md").write_text(design_md(d), encoding="utf-8")
    for n, (tags, what, code, rules) in CARDS.items(): (o / "cards" / f"{n}.md").write_text(card_md(n, tags, what, code, rules), encoding="utf-8")
    (o / "CHECKLIST.md").write_text(CHECK, encoding="utf-8")
    return d, o

def main(args):
    if not args or args[0] != "capture" or len(args) < 2: sys.exit(__doc__)
    out = args[args.index("--out") + 1] if "--out" in args else "forgex/style"
    srcs = [a for i, a in enumerate(args[1:], 1) if not a.startswith("--") and args[i - 1] != "--out"]
    d, o = capture(srcs, out, "--no-fetch" in args)
    n = sum(len(t) for t in d["tokens"].values())
    print(f"draft: {o}/style.draft.json, DESIGN.draft.md, cards/(ui-skeleton-list, ui-empty-state, ui-data-table), CHECKLIST.md · {n} token fields")
    if d["agentFill"]: print(f"agent: {len(d['agentFill'])} image source(s): open them and fill every '?' in DESIGN.draft.md / style.draft.json")
    print(GUIDE)
