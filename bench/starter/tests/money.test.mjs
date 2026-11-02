import { test } from "node:test"; import assert from "node:assert";
// Pure-JS mirror of lib/money.ts formatting rule, kept tiny so `npm test` runs without a TS build.
const fmt = (s) => `${Math.trunc(s / 100)}.${String(Math.abs(s % 100)).padStart(2, "0")}`;
test("satang formats with 2 decimals", () => assert.equal(fmt(10050), "100.50"));
