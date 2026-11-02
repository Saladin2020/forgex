// Money is stored as integer satang (1 baht = 100 satang).
export type Entry = { amountSatang: number };
export function totalSatang(rows: Entry[]): number {
  return rows.reduce((s, r) => s + r.amountSatang, 0);
}
// BUG (task T5): shows 125.75 as "125.8" and uses float division.
export function totalBalance(rows: Entry[]): string {
  return (totalSatang(rows) / 100).toFixed(1);
}
