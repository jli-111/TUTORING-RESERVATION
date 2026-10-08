# Studyroom — React / Django / MySQL

A three-tier tutoring reservation application. React renders the user interface, Django REST Framework exposes JSON APIs, and MySQL stores relational data. This edition replaces the earlier server-rendered SQLite architecture; it is a separate project and does not automatically migrate old accounts.

```text
frontend/   React components and HTTP API client (port 5173)
backend/    Django REST API, serializers, services and models (port 8001)
database/   MySQL bootstrap and schema explanation (normally port 3306)
docs/       Setup, API contract and architecture learning material
```

## Features

- Student/tutor registration, login and logout with session-cookie authentication.
- Signed email verification and password recovery through React forms.
- Administrator approval before tutors can publish availability.
- Slot search, student booking/cancellation and tutor editing of unbooked slots.
- MySQL transactions, ordered row locking and a generated-column unique index to prevent double booking.
- Blue-and-white academic interface. Times are sent as ISO 8601 UTC and displayed in the browser's timezone.
- 29 backend tests on MySQL, including five concurrency scenarios; three frontend HTTP-client tests.

## Start here

Read [Setup](docs/SETUP.md), then [API contract](docs/API.md) and [Architecture](docs/ARCHITECTURE.md).

```bash
# Terminal 1: after configuring MySQL and installing backend dependencies
cd backend
source .venv/bin/activate
# Export the MYSQL_* values described in backend/.env.example.
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver 127.0.0.1:8001

# Terminal 2
cd frontend
npm ci
npm run dev
```

Visit **http://127.0.0.1:5173/** for React and **http://127.0.0.1:8001/admin/** for staff approval. The development proxy forwards `/api/` requests to Django. There is no Django HTML template for the student/tutor application; Django Admin retains its framework-owned templates.

## Verification

```bash
# backend, with a configured MySQL user permitted to create test_studyroom
python manage.py test --settings=config.test_settings --noinput
python manage.py check
python manage.py makemigrations --check --dry-run

# frontend
npm test
npm run build
```

The implementation was tested locally with MySQL 26.7.0/InnoDB, Python 3.12, Django 5.2.17 and Node 24. The included CI configuration targets MySQL 8.4; that remote workflow has not been run here. It must pass on your GitHub repository before claiming that environment was validated.

## Boundaries

Console email is the development default. Mailbox verification is not legal identity verification; tutor approval is manual. Booked lessons cannot be moved without student cancellation. Authentication rate limiting and real SMTP must be configured before public deployment. No load-test throughput claims are made.

This repository is ready to upload as source; uploading does not deploy a running Python application. GitHub Pages cannot run the Django backend. See setup documentation for deployment responsibilities. No credentials, user database or MySQL runtime directory are included in the source archive.
