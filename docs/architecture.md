# SubmitEXP architecture (starter)

```
Chrome MV3 popup (React + TypeScript)
   |  screenshot (planned, local only)
   v
Tesseract.js (client-side OCR planned)
   |  user-approved extracted assignment fields only
   v
FastAPI REST endpoints (health checks implemented; auth/submissions planned)
   |
   v
MySQL (users, submissions, point_transactions, user_progress)
```

- Avoid direct Canvas account access or handling Canvas passwords.
- Never upload or store screenshots on the server.
- Validate parsed text before awarding points; screenshot evidence is untrusted.
- Passwords: store **hashes only**, never plaintext; JWT authentication is not implemented yet.
- Only `/health` and `/health/database` exist in this starter.
- Browser extension runs a bundled production build, not the Vite development server.
- Add minimal Chrome permissions only when corresponding features exist.
- The SQL files initialize tables; later schema changes should use migrations.
