"""FORGEX shared risk classifier (stdlib). Same rules + logic as classifier.mjs; parity-tested on cases.json.
classify(mode=None, paths=(), areas=(), risk=None, extra_globs=(), task="") -> {"mode", "derived", "reasons", "warnings", "writes"}
GUARDED only for hard signals: a guarded glob (schema/migrations, auth config, secrets, env, deploy config), a write
signal in the task text (money-write, schema-change, authz-change), riskLevel high/critical, or an explicit GUARDED.
v2.8: a kind fires on a strong phrase or noun+verb (nouns alone never). Display/UI words cancel noun+verb only.
Area keywords alone (auth, money, db) never escalate. Explicit mode is a floor; unknown data -> more conservative."""
import json, re
from pathlib import Path

RULES = json.loads((Path(__file__).resolve().parent / "rules.json").read_text(encoding="utf-8"))
ORDER = {m: i for i, m in enumerate(RULES["modes"])}

def glob_re(g):
    out, i = "", 0
    while i < len(g):
        if g.startswith("**/", i): out += "(?:.*/)?"; i += 3
        elif g.startswith("**", i): out += ".*"; i += 2
        elif g[i] == "*": out += "[^/]*"; i += 1
        elif g[i] == "?": out += "[^/]"; i += 1
        else: out += re.escape(g[i]); i += 1
    return re.compile("^" + out + "$")

def norm(p): return re.sub(r"^(\./)+", "", str(p).replace("\\", "/"))
def guarded_hit(path, globs): return next((g for g in globs if glob_re(g).match(norm(path))), None)
def top(*ms): return max(ms, key=lambda m: ORDER[m])

def _has(text, k):
    if re.search(r"[ก-๙]", k): return k in text
    return re.search(r"(?<![a-z0-9])" + re.escape(k) + r"(?![a-z0-9])", text) is not None

def write_signals(task):
    """Real-touch signals per kind: a strong phrase, or noun AND verb. Display/UI wording cancels noun+verb only."""
    t = (task or "").lower()
    ro = [k for k in RULES["displaySignals"] + RULES["uiSignals"] if _has(t, k)]
    found = {}
    for kind, s in RULES["touchSignals"].items():
        hits = [k for k in s["strong"] if _has(t, k)]
        if not hits and not ro:
            n = [k for k in s["nouns"] if _has(t, k)]; v = [k for k in s["verbs"] if _has(t, k)]
            if n and v: hits = n[:2] + v[:1]
        if hits: found[kind] = hits
    return found, ro

def classify(mode=None, paths=(), areas=(), risk=None, extra_globs=(), task=""):
    R, reasons, warnings = RULES, [], []
    globs = list(dict.fromkeys([*R["guardedGlobs"], *extra_globs]))
    paths, areas = [norm(p) for p in paths or []], set(areas or [])
    if not paths: d = R["noPathsMode"]; warnings.append(f"no paths given: at least {d}")
    elif len(paths) <= R["quickMaxPaths"] and areas and areas <= set(R["quickAreas"]): d = "QUICK"
    else: d = "STANDARD"
    hard = "QUICK"
    if risk is not None:
        rm = R["riskModeMapping"].get(risk)
        if rm is None: warnings.append(f"unknown riskLevel {risk!r}: {R['unknownMode']}"); rm = R["unknownMode"]
        if ORDER[rm] > ORDER[d]: reasons.append(f"riskLevel {risk} -> {rm}")
        d, hard = top(d, rm), top(hard, rm)
    for p in paths:
        g = guarded_hit(p, globs)
        if g: reasons.append(f"path {p} matches guarded glob {g}"); d = hard = "GUARDED"
    writes, ro = write_signals(task)
    for k in sorted(writes): reasons.append(f"{k} ({', '.join(writes[k][:3])})"); d = hard = "GUARDED"
    if ro and not writes and hard != "GUARDED" and areas & {"auth", "money", "db"}: reasons.append(f"read-only ({', '.join(ro[:2])}): no escalation")
    final = d
    if mode is not None:
        if mode not in ORDER: warnings.append(f"unknown mode {mode!r}: {R['unknownMode']}"); mode = R["unknownMode"]
        final = top(mode, hard)
        reasons.append(f"explicit {mode} escalated to {final}" if final != mode else f"explicit {mode} kept")
    return {"mode": final, "derived": d, "reasons": reasons, "warnings": warnings, "writes": sorted(writes)}
