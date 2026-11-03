#!/usr/bin/env python3
"""FORGEX tokenizer adapter + measurement log (stdlib; tiktoken optional).

  tokens.py count <file|-> [...]                  -> {"tokens", "method", "estimate"} per file
  tokens.py log --task T1 --classifier-mode M --actual-mode M [--pack forgex/context-pack.md] [--out-file F]
                [--tokens-in N --tokens-out N --source cursor-usage] [--arm A|B] [--note "..."] [--log forgex/log.jsonl]
  tokens.py report [--log forgex/log.jsonl]       -> totals, real vs estimated tokens, false-GUARDED rate
Counting: tiktoken (o200k_base, else cl100k_base) when installed = "real" tokenizer count; otherwise ceil(chars/4),
always flagged estimate=true. Manual numbers from Cursor Usage (Dashboard → Usage, per request: input/output tokens)
go in with --source cursor-usage and are the ground truth for A/B; they override counted values.
false GUARDED = classifierMode GUARDED but actualMode (what the task really needed, set at close) is lower.
"""
import argparse, datetime, json, math, sys
from pathlib import Path
for _s in (sys.stdout, sys.stderr):
    try: _s.reconfigure(encoding="utf-8", errors="replace")
    except Exception: pass

_ENC, METHOD = None, "chars/4 estimate"
try:
    import tiktoken
    for _n in ("o200k_base", "cl100k_base"):
        try: _ENC = tiktoken.get_encoding(_n); METHOD = f"tiktoken {_n}"; break
        except Exception: pass
except Exception: pass

def count(text):
    text = text or ""
    if _ENC is not None: return {"tokens": len(_ENC.encode(text)), "method": METHOD, "estimate": False}
    return {"tokens": math.ceil(len(text) / 4), "method": "chars/4 estimate", "estimate": True}

def read(p): return sys.stdin.read() if p == "-" else Path(p).read_text(encoding="utf-8", errors="replace")

MODES = ["QUICK", "STANDARD", "GUARDED"]
def false_guarded(rows):
    g = [r for r in rows if r.get("classifierMode") == "GUARDED" and r.get("actualMode") in MODES]
    f = [r for r in g if r["actualMode"] != "GUARDED"]
    return len(f), len(g)

def entry(a):
    e = {"ts": datetime.datetime.now().astimezone().isoformat(timespec="seconds"), "task": a.task, "arm": a.arm,
         "classifierMode": a.classifier_mode, "actualMode": a.actual_mode}
    if a.tokens_in is not None or a.tokens_out is not None:
        e.update(tokensIn=a.tokens_in, tokensOut=a.tokens_out, tokenSource=a.source or "manual", tokenEstimate=False)
    else:
        ti = count(read(a.pack)) if a.pack and Path(a.pack).exists() else None
        to = count(read(a.out_file)) if a.out_file and Path(a.out_file).exists() else None
        src = (ti or to or count(""))
        e.update(tokensIn=ti and ti["tokens"], tokensOut=to and to["tokens"], tokenSource=src["method"], tokenEstimate=src["estimate"])
    if a.note: e["note"] = a.note
    return e

def main():
    ap = argparse.ArgumentParser(); sub = ap.add_subparsers(dest="cmd", required=True)
    c = sub.add_parser("count"); c.add_argument("files", nargs="+")
    l = sub.add_parser("log")
    for k in ("--task", "--classifier-mode", "--actual-mode"): l.add_argument(k, required=k == "--task", choices=MODES if "mode" in k else None)
    l.add_argument("--pack"); l.add_argument("--out-file"); l.add_argument("--tokens-in", type=int); l.add_argument("--tokens-out", type=int)
    l.add_argument("--source", choices=["cursor-usage", "manual", "api"]); l.add_argument("--arm"); l.add_argument("--note"); l.add_argument("--log", default="forgex/log.jsonl")
    r = sub.add_parser("report"); r.add_argument("--log", default="forgex/log.jsonl")
    a = ap.parse_args()
    if a.cmd == "count":
        for f in a.files: print(json.dumps({"file": f, **count(read(f))}, ensure_ascii=False))
    elif a.cmd == "log":
        e = entry(a); p = Path(a.log); p.parent.mkdir(parents=True, exist_ok=True)
        with p.open("a", encoding="utf-8") as fh: fh.write(json.dumps(e, ensure_ascii=False) + "\n")
        print(json.dumps(e, ensure_ascii=False))
    else:
        rows = [json.loads(x) for x in Path(a.log).read_text(encoding="utf-8").splitlines() if x.strip()] if Path(a.log).exists() else []
        real = [x for x in rows if not x.get("tokenEstimate") and x.get("kind") != "rating"]; fg, g = false_guarded(rows)
        tot = lambda rs: sum((x.get("tokensIn") or 0) + (x.get("tokensOut") or 0) for x in rs)
        print(json.dumps({"entries": len([x for x in rows if x.get("kind") != "rating"]), "realTokenEntries": len(real), "realTokens": tot(real), "estimatedTokens": tot([x for x in rows if x.get("tokenEstimate")]),
                          "falseGuarded": fg, "classifiedGuarded": g, "falseGuardedRate": round(fg / g, 3) if g else None,
                          "ratings": {k: sum(1 for x in rows if x.get("kind") == "rating" and (x.get("rating") or "skip") == k) for k in ("first-try", "1-2", "many", "skip")}}, indent=1))

if __name__ == "__main__":
    main()
