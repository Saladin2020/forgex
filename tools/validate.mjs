#!/usr/bin/env node
// FORGEX validator. Deps: ajv + ajv-formats only. Usage:
//   node tools/validate.mjs                 validate repo (schemas, policy, examples, rules)
//   node tools/validate.mjs --dist          also validate built dist/ packages
//   node tools/validate.mjs path/to/x.json  validate one task contract (exit 1 on failure)
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";
import Ajv2020 from "ajv/dist/2020.js";
import Ajv7 from "ajv";
import addFormats from "ajv-formats";

const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const rd = (p) => JSON.parse(fs.readFileSync(path.resolve(ROOT, p), "utf8"));
const ajv = new Ajv2020({ allErrors: true, strict: false }); addFormats(ajv);
const task = ajv.compile(rd("schemas/task-contract.schema.json"));
const policy = ajv.compile(rd("schemas/policy.schema.json"));
const pattern = ajv.compile(rd("schemas/pattern-record.schema.json"));
const ctxPolicy = ajv.compile(rd("schemas/context-policy.schema.json"));
let failures = 0;
const ok = (m) => console.log(`  PASS  ${m}`);
const bad = (m, e) => { failures++; console.log(`  FAIL  ${m}`); if (e) console.log("        " + JSON.stringify(e).slice(0, 400)); };
const errs = (v) => (v.errors || []).map((e) => `${e.instancePath || "/"} ${e.message}`);

// ---- cross-field checks JSON Schema cannot express ----
const projPolicy = path.resolve(process.cwd(), "forgex/policy.json");
const POLICY = JSON.parse(fs.readFileSync(fs.existsSync(projPolicy) ? projPolicy : path.join(ROOT, "config/default-policy.json"), "utf8"));
// Shared risk classifier: same rules/logic as tools/ctxpack.py (core/risk in source, references/risk when shipped).
const RISK_DIR = [path.join(ROOT, "risk"), path.join(ROOT, "core/risk")].find((d) => fs.existsSync(path.join(d, "classifier.mjs")));
const { classify, globToRegExp, RULES: RISK_RULES } = await import(new URL("file://" + path.join(RISK_DIR, "classifier.mjs")).href);
export { globToRegExp };
const EXTRA_GLOBS = POLICY.guardedGlobs || [];
const GUARDED_RE = [...new Set([...RISK_RULES.guardedGlobs, ...EXTRA_GLOBS])].map((g) => [g, globToRegExp(g)]);
function crossCheck(c) {
  const out = [];
  if (typeof c.mode === "string") {
    const r = classify({ mode: c.mode, paths: c.touchedPaths || [], risk: c.riskLevel ?? null, extraGlobs: EXTRA_GLOBS });
    if (r.mode !== c.mode) {
      const g = r.reasons.find((x) => x.includes("guarded glob"));
      out.push(g ? `/touchedPaths ${g.replace(" matches guarded glob ", ` matches guardedGlob "`)}": risk under-rated, use ${r.mode}` : `/mode ${c.mode} under-rated (${r.reasons.join("; ")}): use ${r.mode}`);
    }
  }
  const ids = (c.checks || []).map((k) => k.id).filter(Boolean);
  const dup = ids.filter((x, i) => ids.indexOf(x) !== i);
  if (dup.length) out.push(`/checks duplicate ids ${[...new Set(dup)]}`);
  const refs = [...(c.acceptanceCriteria || []).flatMap((a) => (a.checks || []).map((r) => [a.id, r])), ...(c.blocks || []).flatMap((b) => (b.checks || []).map((r) => [b.name, r]))];
  for (const [owner, r] of refs) if (!ids.includes(r)) out.push(`/${owner} references missing check ${r}`);
  return out;
}
function validateContract(obj) {
  const okSchema = task(obj);
  const e = okSchema ? [] : errs(task);
  if (obj && typeof obj === "object") e.push(...crossCheck(obj));
  return e;
}
function expect(validator, file, shouldPass) {
  const e = validator === task ? validateContract(rd(file)) : (validator(rd(file)) ? [] : errs(validator));
  const valid = e.length === 0;
  if (valid === shouldPass) ok(`${file} ${shouldPass ? "valid" : "rejected as expected"}${shouldPass ? "" : ": " + e[0]}`);
  else bad(`${file} expected ${shouldPass ? "valid" : "invalid"}`, e);
}
function frontmatter(file) {
  const t = fs.readFileSync(file, "utf8");
  const m = t.match(/^---\n([\s\S]*?)\n---\n/);
  if (!m) return null;
  const o = {};
  for (const line of m[1].split("\n")) { const kv = line.match(/^([A-Za-z][\w-]*):\s*(.*)$/); if (kv) o[kv[1]] = kv[2].replace(/^["']|["']$/g, ""); }
  return o;
}
function checkRule(f) {
  const fm = frontmatter(f);
  if (fm && fm.alwaysApply === "true") { const body = fs.readFileSync(f, "utf8").split(/^---\n[\s\S]*?\n---\n/)[1].trim().split("\n").length; if (body > 15) return bad(`${f} always-on rule body ${body} lines > 15`); ok(`${path.relative(ROOT, f)} always-on body ${body} lines (<=15)`); }
  if (!fm || !fm.description || !["true", "false"].includes(fm.alwaysApply)) return bad(`${f} rule frontmatter (description + alwaysApply)`, fm);
  if (fm.alwaysApply === "false" && !fm.globs) return bad(`${f} non-always rule needs globs`);
  ok(`${path.relative(ROOT, f)} rule frontmatter`);
}
function checkSkill(f) {
  const fm = frontmatter(f);
  if (!fm || !fm.name || !fm.description) return bad(`${f} SKILL.md needs name + description`, fm);
  if (!/^[a-z0-9-]+$/.test(fm.name)) return bad(`${f} skill name must be kebab-case`);
  ok(`${path.relative(ROOT, f)} skill frontmatter`);
}
const ls = (d) => fs.existsSync(path.join(ROOT, d)) ? fs.readdirSync(path.join(ROOT, d)).filter((f) => f.endsWith(".json")).sort().map((f) => `${d}/${f}`) : [];

const single = process.argv.slice(2).filter((a) => !a.startsWith("--"));
if (single.length) {
  for (const f of single) { let e; try { e = validateContract(JSON.parse(fs.readFileSync(f, "utf8"))); } catch (x) { e = [String(x.message)]; } e.length ? bad(f, e) : ok(f); }
  process.exit(failures ? 1 : 0);
}
console.log("Schemas compiled (draft 2020-12).");
console.log("Policy:"); expect(policy, "config/default-policy.json", true);
// Cross-check: the policy mapping must agree with schema rules R1/R2.
const pol = rd("config/default-policy.json");
for (const [risk, mode] of Object.entries(pol.riskModeMapping)) {
  const probe = { contractVersion: "2.2", taskId: "probe", goal: "p", touchedPaths: ["src/x.ts"], checks: [], constraints: ["c"], nonGoals: [], git: {}, acceptanceCriteria: [{ id: "AC-1", criterion: "c", status: "NOT_RUN" }], riskLevel: risk, mode, status: "planned" };
  task(probe) ? ok(`policy mapping ${risk}->${mode} accepted by task schema`) : bad(`policy mapping ${risk}->${mode} conflicts with schema`, errs(task));
}
console.log("Context policy:"); { const cp = rd("config/context-policy.json"); ctxPolicy(cp) ? ok("config/context-policy.json valid") : bad("context-policy", errs(ctxPolicy)); const b = cp.budgets; b.QUICK < b.STANDARD && b.STANDARD < b.GUARDED ? ok(`budgets ${b.QUICK} < ${b.STANDARD} < ${b.GUARDED}`) : bad("budgets must grow QUICK < STANDARD < GUARDED"); }
console.log("Glob self-test:");
for (const [p, want] of [["db/migrations/1.sql", true], ["migrations/1.sql", true], ["app/auth/x.ts", true], [".env.local", true], ["apps/web/.env", true], ["app/orders/Row.tsx", false], ["src/authz.ts", false]]) { const hit = GUARDED_RE.some(([, re]) => re.test(p)); hit === want ? ok(`${p} guarded=${hit}`) : bad(`${p} guarded=${hit} expected ${want}`); }
console.log("Scaffold stubs:"); { const st = ls("examples/stubs"); st.length >= 3 ? ok(`${st.length} stubs present`) : bad("expected >=3 scaffold stubs in examples/stubs"); st.forEach((f) => expect(task, f, true)); }
console.log("Valid contracts:"); ls("examples/contracts/valid").forEach((f) => expect(task, f, true));
console.log("Invalid contracts:"); ls("examples/contracts/invalid").forEach((f) => expect(task, f, false));
console.log("Patterns:"); ls("examples/patterns").forEach((f) => expect(pattern, f, !path.basename(f).startsWith("invalid")));
console.log("Rules:"); fs.readdirSync(path.join(ROOT, "core/rules")).filter((f) => f.endsWith(".mdc")).forEach((f) => checkRule(path.join(ROOT, "core/rules", f)));

if (process.argv.includes("--dist")) {
  console.log("Dist:");
  const ver = JSON.parse(fs.readFileSync(path.join(ROOT, "package.json"), "utf8")).version;
  const a7 = new Ajv7({ allErrors: true, strict: false }); addFormats(a7); const manifestSchema = a7.compile(rd("tools/vendor/cursor-plugin.schema.json"));
  for (const pkg of fs.readdirSync(path.join(ROOT, "dist")).filter((d) => d !== "public-repo" && !d.startsWith("_"))) {
    const base = path.join(ROOT, "dist", pkg), cur = path.join(base, "forgex-cursor-plugin");
    const man = JSON.parse(fs.readFileSync(path.join(cur, ".cursor-plugin/plugin.json"), "utf8"));
    manifestSchema(man) ? ok(`${pkg}: plugin.json matches cursor/plugins schema`) : bad(`${pkg} plugin.json`, manifestSchema.errors);
    fs.readdirSync(path.join(cur, "rules")).forEach((f) => checkRule(path.join(cur, "rules", f)));
    for (const s of fs.readdirSync(path.join(cur, "skills"))) checkSkill(path.join(cur, "skills", s, "SKILL.md"));
    for (const c of fs.readdirSync(path.join(cur, "commands"))) { const fm = frontmatter(path.join(cur, "commands", c)); fm?.name && fm?.description ? ok(`${pkg}: command ${c}`) : bad(`command ${c}`, fm); }
    checkSkill(path.join(base, "forgex-grokbot-skill/forgex/SKILL.md"));
    const zips = ["forgex-cursor-plugin.zip", "forgex-grokbot-skill.zip", ...(pkg === "public" ? [`FORGEX_v${ver}-src.zip`] : [])];
    for (const z of zips) fs.existsSync(path.join(base, z)) ? ok(`${pkg}/${z} exists`) : bad(`${pkg}/${z} missing`);
    const hasKit = fs.existsSync(path.join(base, "forgex-grokbot-skill/forgex/references/kit"));
    (pkg === "public" ? !hasKit : hasKit) ? ok(`${pkg}: kit ${hasKit ? "included" : "absent"} as expected`) : bad(`${pkg}: kit presence wrong`);
  }
}
console.log(failures ? `\n${failures} check(s) failed` : "\nAll checks passed");
process.exit(failures ? 1 : 0);
