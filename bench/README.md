# FORGEX A/B bench: FORGEX ช่วยจริงไหม

วัดแบบยุติธรรม: โปรเจกต์ตั้งต้นเดียวกัน, โมเดลเดียวกัน, prompt สั้นเหมือนกันทุกตัวอักษร ต่างกันแค่ **A = ไม่มี FORGEX** กับ **B = ติดตั้ง FORGEX v2.6**

## 1. เตรียม (ครั้งเดียว ~10 นาที)
```bash
cp -r starter bench-A && cp -r starter bench-B        # หรือใช้ repo ของคุณเอง: git worktree add ../bench-A <commit> แล้วทำ B จาก commit เดียวกัน
cd bench-A && git init -q && git add -A && git commit -qm start && cd ..
cd bench-B && git init -q && git add -A && git commit -qm start && cd ..
```
- **B เท่านั้น:** ติดตั้ง FORGEX (ดู QUICKSTART.md: คัดลอก `rules/*.mdc` → `.cursor/rules/`, `skills/forgex/` → `.cursor/skills/forgex/`) แล้วรัน `python3 .cursor/skills/forgex/references/tools/context.py init` และ `codemap.py`
- **A:** ห้ามมีไฟล์ rules/skill/AGENTS.md ใด ๆ (ลบ `.cursor/` ถ้ามี)
- (ไม่บังคับ) `npm install` ทั้งสองฝั่ง เพื่อให้ score.py รัน `npm test` ได้

## 2. กติกาให้ยุติธรรม
- เปิด A และ B เป็นคนละหน้าต่าง Cursor, เลือก **โมเดลเดียวกัน**, โหมด Agent เหมือนกัน
- คัดลอก prompt จาก `tasks/T*.md` ไปวาง **ตรงตัว** ทำ T1 → T6 ตามลำดับ (งานต่อยอดกันในโฟลเดอร์เดียว)
- ถ้า AI ถาม ให้ตอบสั้นที่สุดและเหมือนกันทั้งสองฝั่ง ทุกข้อความที่คุณพิมพ์เพิ่ม = +1 round
- หยุดเมื่อ AI บอกว่าเสร็จ หรือครบ 20 นาทีต่องาน แล้ว commit (`git commit -am T1`)
- สลับลำดับรอบหน้า (ทำ B ก่อน A) เพื่อตัดผลจากความเหนื่อย/ความคุ้น

## 3. ทดสอบความจำ (T6)
แชทเดิมสั่งวางแผนขั้น reject → **ปิดแชท เปิดแชทใหม่** → พิมพ์แค่ `ทำต่อ`  
ถ้า AI ไม่รู้ว่าต้องทำอะไรต่อจนต้องอธิบายใหม่ ใส่ `reexplained=1` ฝั่ง B ควรอ่าน `forgex/STATE.md` แล้วทำต่อได้เอง

## 4. บันทึกผล
คัดลอก `results-template.csv` เป็น `results.csv` แล้วกรอกต่องาน:
- `tokens`: จาก Cursor (Settings → Usage หรือเมนูดูการใช้งานของแชท) รวม input+output
- `rounds`: จำนวนข้อความที่คุณพิมพ์ (prompt แรก = 1)
- `minutes`: เวลาจาก prompt แรกถึงเสร็จ
- `reexplained`: 1 ถ้าต้องอธิบายงานซ้ำ (สำคัญใน T6)

## 5. ให้คะแนน
```bash
python3 score.py --a bench-A --b bench-B --results results.csv --out report.md
```
score.py ตรวจแบบอัตโนมัติจากโฟลเดอร์สุดท้ายของแต่ละฝั่งตาม `tasks/checks.json` (grep หาสิ่งที่ต้องมี/ต้องไม่มี เช่นการคิดเงินด้วย float, `auth()` ใน API, maker≠checker, ไฟล์ migration, design token ตาม `style.json`, และ `npm test` ถ้ามี node_modules) แล้วรวมกับ results.csv เป็นตาราง markdown พร้อมผู้ชนะแต่ละตัวชี้วัด  
**B ชนะจริง** เมื่อผ่าน check ได้ไม่น้อยกว่า A และชนะตัวชี้วัดส่วนใหญ่ ทำซ้ำ 2-3 รอบก่อนสรุป

## ไฟล์
- `tasks/T1…T6.md` prompt + เกณฑ์ผ่าน (QUICK ×1, STANDARD ×2, GUARDED ×3) · `tasks/checks.json` เกณฑ์ที่เครื่องตรวจ
- `starter/` โปรเจกต์ตั้งต้น Next.js 16 + Tailwind v4 + Drizzle/Neon + Auth.js v5 (มีบั๊กเงินไว้ให้ T5)
- `style.json` รายชื่อ design token ที่ต้องใช้ (แก้ให้ตรงกับดีไซน์ของคุณได้)
- `score.py`, `results-template.csv`
