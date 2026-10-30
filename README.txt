ALTAIR BUSINESS SUITE — AUTHENTICATION / SESSION FIX

FILES
- app.py: patched backend.
- templates/index.html: your existing unified application interface (unchanged).
- templates/login.html: your supplied original login design.
- templates/register.html: your supplied original create-account design.

INSTALL
1. Back up your current project.
2. Replace the project's app.py with this app.py.
3. Copy templates/index.html into your project's templates/ folder.
4. Copy login.html and register.html into the same templates/ folder.
5. In Render > your service > Environment, confirm FLASK_SECRET_KEY exists and has one long, random, stable value.
   IMPORTANT: Do not regenerate this value on each deploy or app restart. Keep the same value across all workers.
6. Deploy the app.

SESSION / DATA BEHAVIOUR
- Login sessions are non-permanent browser-session cookies.
- Logout clears the authenticated session.
- Closing/restarting the app will no longer invalidate sessions because the secret key is stable.
- User accounts and business records remain stored in MySQL; this patch does not delete business data.
- If FLASK_SECRET_KEY is missing, the app stops with a clear error instead of silently generating a different key each restart.

NOTE
Do not set a new FLASK_SECRET_KEY if you already have one configured in Render. Keep the existing value.
