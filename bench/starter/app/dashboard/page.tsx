import { totalBalance } from "@/lib/money";
export default function Dashboard() {
  return <main className="p-6">ยอดรวม {totalBalance([{ amountSatang: 10050 }, { amountSatang: 2525 }])}</main>;
}
