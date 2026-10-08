# JSON API contract

Base path: `/api/`. Requests with bodies use `Content-Type: application/json`. Responses use JSON, including handled errors. Protected routes use a Django session cookie. All unsafe requests require `X-CSRFToken`, including anonymous register/login/reset requests.

Call GET /auth/session/ first. It sets the CSRF cookie and returns a token. POST /auth/login/ rotates it and returns a replacement. The shared React HTTP client adopts the new token automatically. Cookies are sent using same-origin credentials through the development proxy.

| Method | Path after /api | Input | Successful result |
|---|---|---|---|
| GET | auth/session/ | — | 200 `{user: object or null, csrf_token}` |
| POST | auth/register/ | username, email, role, password | 201 message |
| POST | auth/login/ | username, password | 200 user and new csrf_token |
| POST | auth/logout/ | — | 200 message and token |
| POST | auth/verify/ | token | 200 message |
| POST | auth/resend/ | — | 200 message; 503 on email failure |
| POST | auth/password-reset/ | email | 200 generic message |
| POST | auth/password-reset/confirm/ | uid, token, password | 200 message |
| GET | slots/?q=Mathematics | query parameter | 200 array of available slots |
| GET | tutor/slots/ | — | 200 tutor's upcoming slots |
| POST | tutor/slots/ | subject, starts_at, ends_at, location | 201 slot |
| PUT | tutor/slots/{id}/ | full slot input fields | 200 updated slot |
| GET | bookings/ | — | 200 own reservations, including history |
| POST | bookings/ | slot_id | 201 reservation |
| POST | bookings/{id}/cancel/ | — | 200 cancelled reservation |

Dates are ISO 8601 with timezone, e.g. `2030-04-08T14:00:00Z`. Read-only IDs, tutor, approval flags and user roles are not accepted as edits through scheduling serializers. Student ownership comes from the session.

Example booking request:

```http
POST /api/bookings/ HTTP/1.1
Content-Type: application/json
X-CSRFToken: <token from session endpoint>
Cookie: sessionid=<browser-managed session>; csrftoken=<browser-managed cookie>

{"slot_id":12}
```

Example successful body (illustrative):

```json
{"id":9,"student_name":"student","slot":{"id":12,"tutor":1,"tutor_name":"tutor","subject":"Mathematics","starts_at":"2030-04-08T14:00:00Z","ends_at":"2030-04-08T15:00:00Z","location":"Online","available":false},"created_at":"2030-04-01T10:00:00Z","cancelled_at":null}
```

Handled errors use `{ "error": { "message": "...", "details": ... } }`. The CSRF rejection contains a message without details. Statuses: 400 invalid JSON/fields or token, 403 authentication/permission/CSRF failure under SessionAuthentication, 404 unavailable owned record, 405 unsupported method, 409 scheduling conflict. Unexpected server faults remain 500; the client handles non-JSON failures with a connection message.

GET does not create a reservation. Cancellation uses an explicit POST action because it records a cancellation timestamp rather than deleting history. Registration does not log in automatically. Password reset invalidates existing sessions through Django's password-based session authentication hash.
