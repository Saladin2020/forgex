# T5 · STANDARD · แก้บั๊กในโค้ดเดิม
**Prompt:**
> หน้า dashboard แสดงยอด 125.8 แต่ควรเป็น 125.75 แก้ให้ถูก

**ผ่านเมื่อ:** ไม่มี `/ 100).toFixed(1)` และไม่มี toFixed/parseFloat ใน `lib/money.ts` (ใช้ integer satang) · มี test ที่มี `125.75` · `npm test` ผ่าน (ถ้าลง node_modules แล้ว)
