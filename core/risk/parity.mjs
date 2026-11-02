// node core/risk/parity.mjs -> prints JSON results of classifier.mjs over cases.json (used by tools/test_risk.py)
import fs from "node:fs"; import path from "node:path"; import { fileURLToPath } from "node:url";
import { classify } from "./classifier.mjs";
const cases = JSON.parse(fs.readFileSync(path.join(path.dirname(fileURLToPath(import.meta.url)), "cases.json"), "utf8"));
console.log(JSON.stringify(cases.map((c) => classify(c.in).mode)));
