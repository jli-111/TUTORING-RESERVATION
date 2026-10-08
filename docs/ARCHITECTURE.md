# Application architecture

Studyroom separates the React interface, Django JSON API, and MySQL database. Each layer has a defined responsibility and communicates through explicit interfaces.

| Layer | Files | Responsibility |
|---|---|---|
| User interface | frontend/src/pages and components | Render state and collect input |
| HTTP client | frontend/src/api/reservations.js and client.js | Send JSON requests and handle errors |
| HTTP controllers | backend/reservations/views.py | Route operations and return JSON status responses |
| Data validation | backend/reservations/serializers.py | Validate input and expose safe response fields |
| Business services | backend/reservations/services.py | Enforce permissions, scheduling rules, and transactions |
| Persistence | backend/reservations/models.py | Define relational entities and query them through the ORM |
| Configuration | backend/config/settings.py | Read server and database configuration from the environment |

```mermaid
sequenceDiagram
    participant UI as React Dashboard
    participant Client as reservations.js / client.js
    participant API as Django View + Serializer
    participant Service as services.book
    participant DB as MySQL InnoDB
    UI->>Client: bookSlot(slot.id)
    Client->>API: POST /api/bookings/ JSON + CSRF + cookie
    API->>Service: book(request.user, validated slot_id)
    Service->>DB: BEGIN; lock affected users in ID order
    Service->>DB: SELECT slot FOR UPDATE; check conflicts
    Service->>DB: INSERT booking; COMMIT
    API-->>Client: 201 JSON
    Client-->>UI: parsed booking
    UI->>Client: GET updated slots and reservations
    UI->>UI: setState and render
```

The browser has no MySQL credentials and never imports Python. Django does not generate the application UI. Django Admin is the only framework-rendered staff interface.

## Relational design

User stores identity and role; Slot references a tutor; Booking references a student and slot. A slot can have many historical bookings, but only one active booking. Django migrations own the schema. See database/README.md.

## MySQL-specific concurrency

SQLite's earlier partial unique index cannot be transferred to MySQL. Booking.active_slot_key is a stored generated column: `CASE WHEN cancelled_at IS NULL THEN slot_id ELSE NULL END`. A UNIQUE index prevents duplicate active slot IDs while allowing multiple NULLs for cancelled records. Callers cannot independently set this derived value.

Every scheduling operation locks affected User rows in ascending primary-key order, then the Slot, then an existing Booking when cancelling. Locking the student prevents simultaneous overlapping reservations across different slots; locking the tutor serializes overlapping availability edits/creation. The transaction uses READ COMMITTED. The unique index is a final safeguard even against direct duplicate inserts.

Tests exercise two students/one slot, one student/two overlapping slots, two overlapping tutor creates, cancellation/rebooking, and booking/edit. A booking may succeed after an edit if the edit commits first; if booking wins, editing is rejected. This serial behavior is correct but does not implement a version-based stale-schedule confirmation protocol. A future version could require an expected slot version before booking.

## Verification and identity

Passwords use Django's hashing and authentication APIs. Email ownership uses signed user/email/timestamp tokens with 24-hour expiry and explicit POST confirmation. The token is signed, not encrypted, and can be reconfirmed until expiry. Password recovery uses Django's token generator and validates/updates under a user row lock; expiry is one hour. Tutor approval is a manual staff action, not government-ID verification.

## Limits

The current list APIs are not paginated. Email delivery is synchronous and defaults to console. The resend cooldown is session-based; global authentication rate limiting remains deployment work. Role and time-overlap checks live in services, so arbitrary writes outside these services can bypass them. The generated unique column still prevents two active bookings for the same slot. No real-user data migration, public hosting, scale benchmark or booked-session rescheduling workflow has been performed.
