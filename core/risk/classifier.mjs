// FORGEX shared risk classifier (ESM). Mirror of classifier.py; both read rules.json and are parity-tested on cases.json.
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";
export const RULES = JSON.parse(fs.readFileSync(path.join(path.dirname(fileURLToPath(import.meta.url)), "rules.json"), "utf8"));
const ORDER = Object.fromEntries(RULES.modes.map((m, i) => [m, i]));
export function globToRegExp(g) {
  let r = "";
  for (let i = 0; i < g.length; i++) {
    const c = g[i];
    if (c === "*" && g[i + 1] === "*") { i++; if (g[i + 1] === "/") { i++; r += "(?:.*/)?"; } else r += ".*"; }
    else if (c === "*") r += "[^/]*";
    else if (c === "?") r += "[^/]";
    else r += c.replace(/[.+^${}()|[\]\\]/g, "\\$&");
  }
  return new RegExp("^" + r + "$");
}
export const norm = (p) => String(p).replace(/\\/g, "/").replace(/^(\.\/)+/, "");
export const guardedHit = (p, globs) => globs.find((g) => globToRegExp(g).test(norm(p))) ?? null;
const top = (...ms) => ms.reduce((a, b) => (ORDER[b] > ORDER[a] ? b : a));
export function classify({ mode = null, paths = [], areas = [], risk = null, extraGlobs = [] } = {}) {
  const R = RULES, reasons = [], warnings = [];
  const globs = [...new Set([...R.guardedGlobs, ...extraGlobs])];
  paths = (paths || []).map(norm); const A = new Set(areas || []);
  let d;
  if (!paths.length) { d = R.noPathsMode; warnings.push(`no paths given: at least ${d}`); }
  else if (paths.length <= R.quickMaxPaths && A.size && [...A].every((a) => R.quickAreas.includes(a))) d = "QUICK";
  else d = "STANDARD";
  let hard = "QUICK"; // floor from hard signals only; the heuristic above never overrides an explicit mode
  if (risk !== null && risk !== undefined) {
    let rm = R.riskModeMapping[risk];
    if (!rm) { warnings.push(`unknown riskLevel '${risk}': ${R.unknownMode}`); rm = R.unknownMode; }
    if (ORDER[rm] > ORDER[d]) reasons.push(`riskLevel ${risk} -> ${rm}`);
    d = top(d, rm); hard = top(hard, rm);
  }
  for (const p of paths) { const g = guardedHit(p, globs); if (g) { reasons.push(`path ${p} matches guarded glob ${g}`); d = hard = "GUARDED"; } }
  for (const a of [...A].filter((x) => R.guardedAreas.includes(x)).sort()) { reasons.push(`guarded area ${a}`); d = hard = "GUARDED"; }
  let final = d;
  if (mode !== null && mode !== undefined) {
    if (!(mode in ORDER)) { warnings.push(`unknown mode '${mode}': ${R.unknownMode}`); mode = R.unknownMode; }
    final = top(mode, hard);
    reasons.push(final !== mode ? `explicit ${mode} escalated to ${final}` : `explicit ${mode} kept`);
  }
  return { mode: final, derived: d, reasons, warnings };
}
