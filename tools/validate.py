#!/usr/bin/env python3
"""FORGEX contract validator, pure Python (stdlib only, no ajv/Node needed). Same verdicts as validate.mjs.
  validate.py forgex/tasks/<id>.json [...]   validate contracts (exit 1 on failure)
  validate.py --self-test                    run every examples/contracts + stubs file against its expected verdict
Schema: schemas/task-contract.schema.json via a small JSON Schema 2020-12 subset (type, enum, const, required,
properties, additionalProperties, items, contains, minItems, minimum, minLength, maxLength, pattern, allOf, anyOf,
oneOf, not, if/then/else, local $ref, boolean schemas). Cross-checks use the shared risk classifier (core/risk)."""
import json, re, sys
from pathlib import Path
for _s in (sys.stdout, sys.stderr):  # Windows consoles: never crash on Thai output
    try: _s.reconfigure(encoding="utf-8", errors="replace")
    except Exception: pass
sys.argv = [x.encode("utf-8", "surrogateescape").decode("utf-8", "replace") for x in sys.argv]  # non-UTF-8 POSIX locales

HERE = Path(__file__).resolve().parent
PKG = HERE.parent
sys.path.insert(0, str(PKG / "risk" if (PKG / "risk").is_dir() else PKG / "core/risk"))
from classifier import classify  # noqa: E402

TYPES = {"object": dict, "array": list, "string": str, "boolean": bool, "null": type(None)}

def is_type(v, t):
    if t == "integer": return isinstance(v, int) and not isinstance(v, bool)
    if t == "number": return isinstance(v, (int, float)) and not isinstance(v, bool)
    return isinstance(v, TYPES[t])

class V:
    def __init__(self, root): self.root = root
    def ref(self, r):
        node = self.root
        for part in r.lstrip("#/").split("/"): node = node[part.replace("~1", "/").replace("~0", "~")]
        return node
    def ok(self, v, s): return not self.errs(v, s, "")
    def errs(self, v, s, at):
        if s is True: return []
        if s is False: return [f"{at or '/'} not allowed"]
        e = []
        if "$ref" in s: e += self.errs(v, self.ref(s["$ref"]), at)
        if "type" in s:
            ts = s["type"] if isinstance(s["type"], list) else [s["type"]]
            if not any(is_type(v, t) for t in ts): return e + [f"{at or '/'} must be {'/'.join(ts)}"]
        if "const" in s and v != s["const"]: e.append(f"{at or '/'} must be {json.dumps(s['const'])}")
        if "enum" in s and v not in s["enum"]: e.append(f"{at or '/'} must be one of {s['enum']}")
        if isinstance(v, str):
            if len(v) < s.get("minLength", 0): e.append(f"{at or '/'} too short")
            if "maxLength" in s and len(v) > s["maxLength"]: e.append(f"{at or '/'} too long")
            if "pattern" in s and not re.search(s["pattern"], v): e.append(f"{at or '/'} must match {s['pattern']}")
        if is_type(v, "number") and "minimum" in s and v < s["minimum"]: e.append(f"{at or '/'} must be >= {s['minimum']}")
        if isinstance(v, list):
            if len(v) < s.get("minItems", 0): e.append(f"{at or '/'} needs >= {s['minItems']} items")
            if "items" in s:
                for i, x in enumerate(v): e += self.errs(x, s["items"], f"{at}/{i}")
            if "contains" in s and not any(self.ok(x, s["contains"]) for x in v): e.append(f"{at or '/'} must contain a matching item")
        if isinstance(v, dict):
            for k in s.get("required", []):
                if k not in v: e.append(f"{at or '/'} must have required property '{k}'")
            props = s.get("properties", {})
            for k, x in v.items():
                if k in props: e += self.errs(x, props[k], f"{at}/{k}")
                elif "additionalProperties" in s: e += self.errs(x, s["additionalProperties"], f"{at}/{k}")
        for sub in s.get("allOf", []): e += self.errs(v, sub, at)
        if "anyOf" in s and not any(self.ok(v, x) for x in s["anyOf"]): e.append(f"{at or '/'} must match anyOf")
        if "oneOf" in s and sum(self.ok(v, x) for x in s["oneOf"]) != 1: e.append(f"{at or '/'} must match exactly one of oneOf")
        if "not" in s and self.ok(v, s["not"]): e.append(f"{at or '/'} must NOT match")
        if "if" in s:
            br = s.get("then") if self.ok(v, s["if"]) else s.get("else")
            if br is not None: e += self.errs(v, br, at)
        return e

def load(p): return json.loads(Path(p).read_text(encoding="utf-8"))
SCHEMA = load(PKG / "schemas/task-contract.schema.json")
_pp = Path("forgex/policy.json")
POLICY = load(_pp if _pp.exists() else PKG / "config/default-policy.json")

def cross(c):
    out = []
    if isinstance(c.get("mode"), str):
        r = classify(mode=c["mode"], paths=c.get("touchedPaths") or [], risk=c.get("riskLevel"), extra_globs=POLICY.get("guardedGlobs", []), task=c.get("goal", ""))
        if r["mode"] != c["mode"]:
            g = next((x for x in r["reasons"] if "guarded glob" in x), None)
            out.append(f"/touchedPaths {g.replace(' matches guarded glob ', ' matches guardedGlob ')}: risk under-rated, use {r['mode']}" if g else f"/mode {c['mode']} under-rated ({'; '.join(r['reasons'])}): use {r['mode']}")
    ids = [k.get("id") for k in c.get("checks") or [] if isinstance(k, dict) and k.get("id")]
    dup = sorted({x for x in ids if ids.count(x) > 1})
    if dup: out.append(f"/checks duplicate ids {dup}")
    refs = [(a.get("id"), r) for a in c.get("acceptanceCriteria") or [] if isinstance(a, dict) for r in a.get("checks") or []]
    refs += [(b.get("name"), r) for b in c.get("blocks") or [] if isinstance(b, dict) for r in b.get("checks") or []]
    out += [f"/{o} references missing check {r}" for o, r in refs if r not in ids]
    return out

def validate(obj):
    e = V(SCHEMA).errs(obj, SCHEMA, "")
    if isinstance(obj, dict): e += cross(obj)
    return e

def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    fails = 0
    if "--self-test" in sys.argv:
        ex = PKG / "examples"
        if not ex.is_dir(): print("self-test: no examples/ here (shipped toolkit); skipped"); return
        cases = [(f, True) for d in ("contracts/valid", "stubs") for f in sorted((ex / d).glob("*.json"))] + [(f, False) for f in sorted((ex / "contracts/invalid").glob("*.json"))]
        for f, want in cases:
            e = validate(load(f)); good = (not e) == want; fails += not good
            print(("PASS " if good else "FAIL ") + f"{f.relative_to(ex)} {'valid' if want else 'rejected: ' + (e[0] if e else 'NOT REJECTED')}" + ("" if good or want else "") + ("" if good or not want else f" -> {e[:2]}"))
        print(f"\n{len(cases) - fails}/{len(cases)} contract examples as expected"); sys.exit(1 if fails else 0)
    if not args: sys.exit(__doc__)
    for f in args:
        try: e = validate(load(f))
        except (OSError, ValueError) as x: e = [str(x)]
        fails += bool(e); print(f"{'PASS' if not e else 'FAIL'}  {f}" + ("" if not e else f": {e[0]}" + (f" (+{len(e) - 1} more)" if len(e) > 1 else "")))
    sys.exit(1 if fails else 0)

if __name__ == "__main__":
    main()
