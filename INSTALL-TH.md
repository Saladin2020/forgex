# ติดตั้ง FORGEX v2.4 (เร็ว ถูก ประหยัด token และให้เครื่องตรวจทุกงาน)

## หลักการใช้งานแบบสั้น
- **ทุกโหมดมี JSON contract ขนาดเล็ก** สร้างด้วย `python3 tools/scaffold.py quick|standard|guarded <id> "<goal>" --path ... --check ...` แล้วเติมแค่ค่า
- **QUICK:** มีแค่ goal, check, touchedPaths และ status
- **STANDARD:** เพิ่มรายการ AC พร้อมระบุว่า AC แต่ละข้อพิสูจน์ด้วย check ไหน (`C1`, `C2`)
- **GUARDED:** ใช้กฎเต็มชุด ต้องมี runbook, budget, CI และ human review
- **ตรวจ:** `python3 tools/validate.py forgex/tasks/<id>.json` (Python ล้วน ไม่ต้องติดตั้งอะไร) หรือ `node tools/validate.mjs …` ถ้างาน STANDARD แตะไฟล์ใน migrations, auth หรือ .env* ตัวตรวจจะไม่ผ่าน เพราะประเมินความเสี่ยงต่ำเกินไป ต้องเปลี่ยนเป็น GUARDED
- **ปิดงาน:** `scaffold.py render <file>` สร้างสรุปงานจาก JSON ให้อัตโนมัติ ไม่ต้องเขียนซ้ำ
- **แพตเทิร์น:** `scaffold.py pattern <file>` บันทึกลงใน `forgex/patterns.md` ให้
- **pre-commit hook (ไม่บังคับ):** เปิดด้วย `git config core.hooksPath <forgex>/tools/hooks` ถ้าจะข้ามเป็นครั้งคราวใช้ `git commit --no-verify`
- **ทีมหลายบอท:** เป็นโมดูลเสริมใน `extras/` ค่าเริ่มต้นไม่โหลด

## Cursor แบบ Plugin (วิธีหลัก)
ใช้รูปแบบ Cursor Plugin ตามเอกสาร https://cursor.com/docs/reference/plugins

1. แตก `dist/forgex-cursor-plugin.zip` จะได้โฟลเดอร์ `forgex/`
2. คัดลอกโฟลเดอร์นั้นไปไว้ที่ `~/.cursor/plugins/local/forgex/`
   - Windows ใช้ `%USERPROFILE%\.cursor\plugins\local\forgex\`
   - ต้องมีไฟล์ `~/.cursor/plugins/local/forgex/.cursor-plugin/plugin.json` อยู่
3. ปิดแล้วเปิด Cursor ใหม่ หรือใช้คำสั่ง Reload Window
4. เปิด Settings แล้วไปที่ Rules หรือ Plugins จะเห็น rule `forgex` (ทำงานทุกแชท) กับ `forgex-guarded` (ทำงานเฉพาะไฟล์ migrations, auth, .env*) รวมถึง skill `forgex` และคำสั่ง `/forgex-start`, `/forgex-close`, `/forgex-validate`

ถ้าต้องการแจกให้ทั้งทีม ให้อัปโหลดขึ้น Git repo แล้วเพิ่มเป็น team marketplace ตามเอกสารของ Cursor

## Cursor แบบสำรอง (ไม่ใช้ plugin)
คัดลอก rule ไปไว้ในโปรเจกต์โดยตรง
```bash
mkdir -p .cursor/rules
cp forgex/rules/forgex.mdc forgex/rules/forgex-guarded.mdc .cursor/rules/
# ถ้าต้องการ skill ให้คัดลอกเพิ่ม
mkdir -p .cursor/skills && cp -r forgex/skills/forgex .cursor/skills/
```

## Grok Bot
1. แตก `dist/forgex-grokbot-skill.zip` จะได้โฟลเดอร์ `forgex/` ที่มี `SKILL.md` กับ `references/`
2. ติดตั้งได้ 2 แบบ
   - **ผ่าน Cursor plugin:** ถ้าติดตั้ง Cursor plugin ข้างบนแล้ว skill `forgex` จะใช้ใน Grok Bot ได้ด้วย ในรูป skill จาก plugin ที่แก้ไขไม่ได้
   - **ส่งไฟล์ให้ Grok Bot:** ส่ง zip ให้ Grok Bot แล้วพิมพ์ "บันทึก skill forgex จากไฟล์นี้" ระบบจะสร้าง skill ชื่อ `forgex` ส่วนไฟล์อ้างอิงให้เก็บไว้บนเครื่องของบอท เช่น `<โฟลเดอร์ของบอท>/forgex/references/`
3. เรียกใช้ด้วยการพิมพ์ `/forgex` หรือ `@forgex` ในแชท หรือสั่งตรงๆ ว่า "ทำงานนี้แบบ FORGEX"
4. ถ้าใช้กับทีมหลายบอท (ไม่บังคับ) ให้สั่งบอทเองว่า "ใช้ FORGEX แบบทีม" บอทจะไปอ่าน `references/extras/multi-agent.md` เฉพาะตอนนั้น

## ใช้ในโปรเจกต์ (Next.js + Vercel + Neon)
1. คัดลอก `tools/` (scaffold, validate และ hooks), `schemas/`, `config/` และ `.github/workflows/forgex.yml` เข้าไปในโปรเจกต์
2. (ไม่บังคับ) รัน `npm i -D ajv ajv-formats` ถ้าจะใช้ validate.mjs
3. ทุกงานเก็บเป็น `forgex/tasks/<id>.json` ระบบ CI ตรวจทุกไฟล์ทุกโหมด และรัน gitleaks ทุกครั้งที่เปิด PR ถ้าต้องการตั้ง guardedGlobs ของโปรเจกต์เอง ให้สร้าง `forgex/policy.json`
4. แก้ path ในไฟล์ workflow ให้ตรงกับตำแหน่งที่คัดลอกไฟล์ไปวาง
5. (v2.9) งานใหม่ที่มีมากกว่า 3 slice: รัน `python3 tools/forgex.py plan "<เป้าหมาย>"` เติม `forgex/roadmap.json` แล้ว `plan --check` และ `next` เพื่อเขียน slice ถัดไปลง STATE ทำเสร็จใช้ `slice done <id> --check-cmd "<test>"` ส่วน `forgex.py harvest <id>` แค่ร่างการ์ด ต้องยืนยันเองและเข้า kit ส่วนตัวเท่านั้น และ `forgex.py style capture <รูปหรือ URL>` ร่าง style/DESIGN/การ์ด UI (ลอกแค่หลักการ ห้ามลอกโลโก้ รูป หรือโค้ด)

## ตรวจแพ็กเกจเอง
```bash
npm install && npm run validate && npm run build
```
