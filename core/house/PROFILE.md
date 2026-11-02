# House profile → AGENTS.md (template)
Copy the fenced block into a new repo's `AGENTS.md`. Replace every `<…>`; delete lines that do not apply.

```md
# AGENTS.md
## Stack
- <framework + version>, <language>, <styling>.
- <database + ORM>; migrations in `<path>`.
- <auth>; <validation lib>; <file storage>; <hosting/region/cron>.
- <package manager>, <runtime version>. Tests: <runner> for <what>.
## Layout
- `<dir>` <purpose>   (repeat; 4–8 lines)
- File naming: <kebab-case | PascalCase>.
## Scripts
<dev, build, lint, typecheck, test, db:*> · CI: <order>.
## Rules
- <language/locale/timezone>; <money or units rule>; <error convention>.
- <audit / idempotency / security rules>; <env var conventions, never commit .env>.
## Don't
- <things the AI must never do>.
```
Example line: `- Next.js 16 App Router + React 19 + TypeScript 5; Tailwind v4.`
