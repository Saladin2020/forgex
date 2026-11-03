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
const esc = (s) => s.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
const has = (t, k) => /[\u0E01-\u0E59]/.test(k) ? t.includes(k) : new RegExp("(?<![a-z0-9])" + esc(k) + "(?![a-z0-9])").test(t);
export function writeSignals(task) {
  const t = String(task || "").toLowerCase();
  const ro = [...RULES.displaySignals, ...RULES.uiSignals].filter((x) => has(t, x));
  const found = {};
  for (const [kind, s] of Object.entries(RULES.touchSignals)) {
    let hits = s.strong.filter((x) => has(t, x));
    if (!hits.length && !ro.length) {
      const n = s.nouns.filter((x) => has(t, x)), v = s.verbs.filter((x) => has(t, x));
      if (n.length && v.length) hits = [...n.slice(0, 2), ...v.slice(0, 1)];
    }
    if (hits.length) found[kind] = hits;
  }
  return [found, ro];
}
export function classify({ mode = null, paths = [], areas = [], risk = null, extraGlobs = [], task = "" } = {}) {
  const R = RULES, reasons = [], warnings = [];
  const globs = [...new Set([...R.guardedGlobs, ...extraGlobs])];
  paths = (paths || []).map(norm); const A = new Set(areas || []);
  let d;
  if (!paths.length) { d = R.noPathsMode; warnings.push(`no paths given: at least ${d}`); }
  else if (paths.length <= R.quickMaxPaths && A.size && [...A].every((a) => R.quickAreas.includes(a))) d = "QUICK";
  else d = "STANDARD";
  let hard = "QUICK";
  if (risk !== null && risk !== undefined) {
    let rm = R.riskModeMapping[risk];
    if (!rm) { warnings.push(`unknown riskLevel '${risk}': ${R.unknownMode}`); rm = R.unknownMode; }
    if (ORDER[rm] > ORDER[d]) reasons.push(`riskLevel ${risk} -> ${rm}`);
    d = top(d, rm); hard = top(hard, rm);
  }
  for (const p of paths) { const g = guardedHit(p, globs); if (g) { reasons.push(`path ${p} matches guarded glob ${g}`); d = hard = "GUARDED"; } }
  const [writes, ro] = writeSignals(task);
  for (const k of Object.keys(writes).sort()) { reasons.push(`${k} (${writes[k].slice(0, 3).join(", ")})`); d = hard = "GUARDED"; }
  if (ro.length && !Object.keys(writes).length && hard !== "GUARDED" && ["auth", "money", "db"].some((x) => A.has(x))) reasons.push(`read-only (${ro.slice(0, 2).join(", ")}): no escalation`);
  let final = d;
  if (mode !== null && mode !== undefined) {
    if (!(mode in ORDER)) { warnings.push(`unknown mode '${mode}': ${R.unknownMode}`); mode = R.unknownMode; }
    final = top(mode, hard);
    reasons.push(final !== mode ? `explicit ${mode} escalated to ${final}` : `explicit ${mode} kept`);
  }
  return { mode: final, derived: d, reasons, warnings, writes: Object.keys(writes).sort() };
}
