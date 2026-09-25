# EVE Healthcare — Backend Engineering Assignment

A backend service built with **FastAPI** and **PostgreSQL** for diagnostic test bookings, centre test catalogues with custom pricing, simulated payment processing, and idempotent payment webhooks.

---

## 1. How to Run the Project Locally

You can run the project either using **Docker** or directly with **Python**.

### Option A: Using Docker (Recommended)

Spins up the FastAPI application, PostgreSQL, and Redis containers together:

```bash
docker-compose up --build
```

The API will be available at: `http://localhost:8000`  
Interactive Swagger documentation: `http://localhost:8000/api/v1/docs`

---

### Option B: Running Locally with Python

1. **Create and activate a virtual environment**:
   ```bash
   python -m venv venv
   # On Windows:
   venv\Scripts\activate
   # On macOS/Linux:
   source venv/bin/activate
   ```

2. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

3. **Configure environment**:
   Copy `.env.example` to `.env`:
   ```bash
   copy .env.example .env
   ```
   *(By default, it uses SQLite so you can test it immediately without needing a local PostgreSQL server running).*

4. **Seed sample data** (centres, tests, and demo users):
   ```bash
   python scripts/seed_data.py
   ```

5. **Start the server**:
   ```bash
   uvicorn app.main:app --reload --port 8000
   ```

---

## 2. Database & Schema Design

The relational schema is designed with normalized tables to decouple central medical catalogues from centre-specific pricing:

### Core Tables

1. **`users`**
   - Stores user authentication and role details.
   - Fields: `id`, `email` (unique index), `hashed_password` (bcrypt), `full_name`, `phone_number`, `role` (`PATIENT` or `ADMIN`), `is_active`, `created_at`.

2. **`diagnostic_centres`**
   - Diagnostic centres and branch locations.
   - Fields: `id`, `name`, `location`, `address`, `contact_phone`, `contact_email`, `is_active`, `created_at`.

3. **`diagnostic_tests`**
   - Central diagnostic catalogue (e.g. CBC, Lipid Profile, Thyroid Panel).
   - Fields: `id`, `name`, `code` (unique), `description`, `category`, `preparation_instructions`, `is_active`.

4. **`centre_tests` (Association / Junction Table)**
   - Resolves the many-to-many relationship between centres and tests.
   - Enables each centre to set its own test price, duration, and availability.
   - Fields: `id`, `centre_id` (FK), `test_id` (FK), `price` (Numeric 10,2), `duration_minutes`, `is_available`.
   - Constraint: `UniqueConstraint("centre_id", "test_id")`.

5. **`bookings`**
   - Patient bookings managed via a state machine.
   - Fields: `id`, `booking_reference` (unique, e.g. `EVE-BK-XXXX`), `patient_id` (FK), `centre_id` (FK), `test_id` (FK), `appointment_datetime`, `amount`, `status` (`PENDING`, `CONFIRMED`, `FAILED`, `CANCELLED`), `notes`, `cancellation_reason`.

6. **`payments`**
   - Transaction records for simulated payments and webhooks.
   - Fields: `id`, `transaction_reference` (unique), `booking_id` (FK), `amount`, `currency`, `status` (`SUCCESS`, `FAILED`, `PENDING`), `payment_method`, `failure_reason`.

7. **`webhook_events` (Idempotency Ledger)**
   - Guarantees webhook idempotency.
   - Fields: `id`, `event_id` (unique index), `event_type`, `booking_id`, `status` (`PROCESSED`, `DUPLICATE_IGNORED`), `raw_payload`, `response_summary`.

---

## 3. API Endpoints & Example Requests

Interactive Swagger UI is available at **`http://localhost:8000/api/v1/docs`**.

### Default Demo Credentials
- **Patient**: `patient@evehealth.com` | `PatientPass123!`
- **Admin**: `admin@evehealth.com` | `AdminPass123!`

---

### Authentication

#### Signup (`POST /api/v1/auth/signup`)
```bash
curl -X POST "http://localhost:8000/api/v1/auth/signup" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "john.doe@example.com",
    "password": "Password123!",
    "full_name": "John Doe",
    "phone_number": "+919876543210"
  }'
```

#### Login (`POST /api/v1/auth/login`)
```bash
curl -X POST "http://localhost:8000/api/v1/auth/login" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "patient@evehealth.com",
    "password": "PatientPass123!"
  }'
```
*Returns JWT `access_token`.*

---

### Diagnostic Centres & Tests

#### List Centres with Search & Pagination (`GET /api/v1/centres/`)
```bash
curl -X GET "http://localhost:8000/api/v1/centres/?search=Koramangala&page=1&size=10"
```

#### Get Centre Details & Available Tests with Prices (`GET /api/v1/centres/1`)
```bash
curl -X GET "http://localhost:8000/api/v1/centres/1"
```

---

### Bookings

#### Create a Booking (`POST /api/v1/bookings/`)
```bash
curl -X POST "http://localhost:8000/api/v1/bookings/" \
  -H "Authorization: Bearer <TOKEN>" \
  -H "Content-Type: application/json" \
  -d '{
    "centre_id": 1,
    "test_id": 1,
    "appointment_datetime": "2026-10-15T10:00:00Z",
    "notes": "Annual medical checkup"
  }'
```

#### List User Bookings (`GET /api/v1/bookings/`)
```bash
curl -X GET "http://localhost:8000/api/v1/bookings/" \
  -H "Authorization: Bearer <TOKEN>"
```

#### Cancel a Booking (`POST /api/v1/bookings/1/cancel`)
```bash
curl -X POST "http://localhost:8000/api/v1/bookings/1/cancel" \
  -H "Authorization: Bearer <TOKEN>" \
  -H "Content-Type: application/json" \
  -d '{"reason": "Change of schedule"}'
```

---

### Simulated Payment & Idempotent Webhook

#### Mock Payment Endpoint (`POST /payments/`)
```bash
curl -X POST "http://localhost:8000/payments/" \
  -H "Content-Type: application/json" \
  -d '{
    "booking_id": 1,
    "payment_method": "UPI",
    "simulate_status": "SUCCESS"
  }'
```
*(Pass `"simulate_status": "FAILED"` to simulate a failed transaction).*

#### Idempotent Webhook Endpoint (`POST /payments/webhook/`)
```bash
curl -X POST "http://localhost:8000/payments/webhook/" \
  -H "Content-Type: application/json" \
  -d '{
    "event_id": "evt_live_test_001",
    "event_type": "payment.succeeded",
    "booking_id": 1,
    "amount": 350.00,
    "status": "SUCCESS"
  }'
```
*If this exact request is sent multiple times, the service returns `200 OK` with `"is_duplicate": true` and ignores re-processing, preventing duplicate charges or state corruption.*

---

## 4. Automated Testing

All 24 unit and integration tests can be run using:

```bash
python -m pytest -v
```

### Coverage Overview
- **Authentication**: User registration, duplicate email rejection, password validation, JWT login, and authorization guards.
- **Centres & Catalogue**: Creation, pagination, search, centre-test custom pricing associations.
- **Booking Flow**: Price verification from DB, past appointment rejection, unoffered test checks, user booking access boundaries.
- **Payments & Webhook Idempotency**: SUCCESS/FAILED status transitions, duplicate webhook replay protection, database payment count integrity.

---

## 5. Important Assumptions

1. **Server-Side Price Authority**: Clients do not pass booking amounts directly. The backend queries `centre_tests.price` in the database to prevent client-side price tampering.
2. **Centre-Specific Pricing**: Different diagnostic centres can offer the same test at different price points based on location, equipment, and operating costs.
3. **Idempotency Key**: External payment providers supply a unique `event_id` in webhook payloads, which acts as the idempotency key.
4. **State Machine Integrity**: Only `PENDING` bookings can be paid or transitioned to `CONFIRMED`/`FAILED`. `FAILED` or already `CANCELLED` bookings cannot be paid or re-cancelled.
5. **Local Fallback**: SQLite is used for zero-setup local runs, while PostgreSQL is configured in Docker for production parity.

---

## 6. What I Would Improve With More Time

1. **HMAC Webhook Signatures**: Verify incoming webhook payloads using an HMAC-SHA256 signature header (`X-Signature`) and a shared secret to ensure webhooks originate strictly from the authorized payment provider.
2. **Granular Slot & Capacity Management**: Add appointment time slot scheduling (e.g. 15 or 30-minute intervals) with per-centre daily booking limits.
3. **Asynchronous Notifications**: Use background tasks (Celery or Arq with Redis) to send email/SMS booking confirmations and invoices.
4. **Automated Refund Handling**: Implement refund initiation when a confirmed booking is cancelled by a user.
5. **Database Migrations with Alembic**: Include formal Alembic migration version files for tracking production schema changes over time.

---

### Author
**Sarthak Tomar**  
GitHub: [@sarthaktomar579](https://github.com/sarthaktomar579)  
*EVE Healthcare — SDE Intern Backend Engineering Assignment*
