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