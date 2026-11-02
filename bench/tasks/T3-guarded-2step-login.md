# T3 · GUARDED · ล็อกอิน 2 ขั้น
**Prompt:**
> ทำล็อกอินด้วยรหัสผ่าน แล้วต่อด้วยรหัส 6 หลักจากแอป authenticator (TOTP) ใช้ Auth.js ที่มีอยู่

**ผ่านเมื่อ:** hash รหัสด้วย argon2/bcrypt · มี TOTP · ไม่มีการเทียบรหัสผ่านตรง ๆ (`password ===`) · มี test กรณีผิด (401/403/invalid)
