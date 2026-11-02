# T4 · GUARDED · API เงิน + maker-checker
**Prompt:**
> เพิ่ม API โอนเงินระหว่างสมาชิก คนสร้างรายการ (maker) กับคนอนุมัติ (checker) ต้องเป็นคนละคน รายการเริ่มเป็น pending

**ผ่านเมื่อ:** ไม่มี float กับเงิน (parseFloat, toFixed(1), real/doublePrecision) · ทุก route ใน `app/api` เรียก `auth()` · มีโค้ดเทียบ maker กับ checker · มีสถานะ pending · มีไฟล์ migration .sql
