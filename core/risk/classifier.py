"""FORGEX shared risk classifier (stdlib). Same rules + logic as classifier.mjs; parity-tested on cases.json.
classify(mode=None, paths=(), areas=(), risk=None, extra_globs=()) -> {"mode", "derived", "reasons", "warnings"}
Rules: explicit mode is a floor (never downgraded) and only hard signals raise it (guarded globs/areas -> GUARDED,
riskLevel mapping); without an explicit mode the path/area heuristic decides;
missing or unknown data picks the more conservative mode."""
import json, re
from pathlib import Path

RULES = json.loads((Path(__file__).resolve().parent / "rules.json").read_text())
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

def guarded_hit(path, globs):
    return next((g for g in globs if glob_re(g).match(norm(path))), None)

def top(*ms): return max(ms, key=lambda m: ORDER[m])

def classify(mode=None, paths=(), areas=(), risk=None, extra_globs=()):
    R, reasons, warnings = RULES, [], []
    globs = list(dict.fromkeys([*R["guardedGlobs"], *extra_globs]))
    paths, areas = [norm(p) for p in paths or []], set(areas or [])
    if not paths: d = R["noPathsMode"]; warnings.append(f"no paths given: at least {d}")
    elif len(paths) <= R["quickMaxPaths"] and areas and areas <= set(R["quickAreas"]): d = "QUICK"
    else: d = "STANDARD"
    hard = "QUICK"  # floor from hard signals only; the path/area heuristic above never overrides an explicit mode
    if risk is not None:
        rm = R["riskModeMapping"].get(risk)
        if rm is None: warnings.append(f"unknown riskLevel {risk!r}: {R['unknownMode']}"); rm = R["unknownMode"]
        if ORDER[rm] > ORDER[d]: reasons.append(f"riskLevel {risk} -> {rm}")
        d, hard = top(d, rm), top(hard, rm)
    for p in paths:
        g = guarded_hit(p, globs)
        if g: reasons.append(f"path {p} matches guarded glob {g}"); d = hard = "GUARDED"
    for a in sorted(areas & set(R["guardedAreas"])): reasons.append(f"guarded area {a}"); d = hard = "GUARDED"
    final = d
    if mode is not None:
        if mode not in ORDER: warnings.append(f"unknown mode {mode!r}: {R['unknownMode']}"); mode = R["unknownMode"]
        final = top(mode, hard)
        if final != mode: reasons.append(f"explicit {mode} escalated to {final}")
        else: reasons.append(f"explicit {mode} kept")
    return {"mode": final, "derived": d, "reasons": reasons, "warnings": warnings}
