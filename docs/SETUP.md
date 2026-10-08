# Setup and operation

## Prerequisites

Use Python 3.12, Node 22.12+ (Node 24 was tested), and MySQL 8.4+ with InnoDB. The actual local verification used MySQL 26.7.0. There is no SQLite fallback: tests must exercise the same locking and generated-column behavior as the application.

## 1. Database tier

Review `database/bootstrap.sql`, replace CHANGE_ME with a local password, and execute it using your MySQL administrator account. It creates only the project database/user and grants schema-scoped privileges. The test grant permits Django to create/drop `test_studyroom`; use it only on a development/test instance.

```bash
mysql -u root -p < database/bootstrap.sql
```

If the project user already exists, CREATE USER IF NOT EXISTS does not change its password. Use its existing password, or explicitly change that project user's password as an administrator. Do not reset unrelated accounts.

Django migrations create tables, foreign keys and generated-column indexes. The SQL file bootstraps access only; do not also hand-create the business tables.

## 2. Backend tier

From backend/:

```bash
python3.12 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
export MYSQL_DATABASE=studyroom
export MYSQL_USER=studyroom
export MYSQL_PASSWORD='your-local-password'
export MYSQL_HOST=127.0.0.1
export MYSQL_PORT=3306
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver 127.0.0.1:8001
```

`.env.example` is documentation, not automatically loaded configuration. Set values in your shell or process environment. Never commit real credentials. Windows activation uses `.venv\Scripts\Activate.ps1`; set environment variables with PowerShell syntax.

`mysqlclient` needs MySQL development headers/libraries and a compiler if a suitable wheel is unavailable. On this Mac's official MySQL installation, the verified build command was:

```bash
MYSQLCLIENT_CFLAGS='-I/usr/local/mysql/include' \
MYSQLCLIENT_LDFLAGS='-L/usr/local/mysql/lib -lmysqlclient -Wl,-rpath,/usr/local/mysql/lib' \
.venv/bin/pip install -r requirements.txt
```

Adapt paths to your own installation. Linux typically requires the distribution's MySQL development package, Python headers and pkg-config. Runtime library paths must also remain available after installation.

## 3. Frontend tier

From frontend/:

```bash
npm ci
npm run dev
```

Open http://127.0.0.1:5173. Use the same hostname consistently; `localhost` and `127.0.0.1` do not share cookies. Vite sends `/api/` to http://127.0.0.1:8001. If you change these ports, update vite.config.js, FRONTEND_URL and CSRF_TRUSTED_ORIGINS together.

React sends ISO UTC timestamps. The datetime-local editor interprets entries in the browser's local timezone; session displays name that timezone.

## 4. Exercise the account flows

1. Register a tutor at the React page. The email prints in the backend terminal.
2. Open the link, which leads to a React verification page, and confirm it.
3. Sign in to Django Admin using your superuser. Approve the tutor's `Tutor approved` field after your own identity/qualification review.
4. Sign in as the tutor and create future availability.
5. Register and verify a student in another browser session. Reserve and cancel a lesson.
6. Test password recovery. Its link also goes to React, which submits the token and new password to Django.

No admin passwords or demo accounts ship with the project. Demo fixtures exist only in the isolated automated tests.

## 5. Public deployment is a separate step

Build React with npm run build. Serve its dist/ using a static web server. Run Django behind a production WSGI server. Route `/api/` to Django under the same public origin; configure staff `/admin/` and its static assets deliberately. The Vite dev proxy is not a production server.

Configure private production secrets, DEBUG=0, allowed hosts, HTTPS, FRONTEND_URL, CSRF_TRUSTED_ORIGINS, MySQL credentials/backup, SMTP, static-file serving, monitoring and shared authentication rate limiting. Restrict MySQL to the backend network. Do not expose the database directly to browsers. If front/backend use different public origins instead, implement a deliberate CORS and cookie policy; this project does not enable wildcard CORS.

Use the CI workflow as a starting validation gate. Publish source only after reviewing staged files; `.runtime/`, `.venv/`, node_modules/, .env and build outputs are excluded. No hosting provider or remote repository has been configured automatically.
