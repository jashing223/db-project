# Application Server — Pet Hospital API

FastAPI backend for the pet hospital front-end (`front-end/common.js`). All paths and JSON field names use **PascalCase** to match the database schema and mock API contract.

## Structure

```
application-server/
├── main.py              # FastAPI app entry point + CORS
├── db.py                # PyMySQL connection (reads .env)
├── dependencies.py      # get_db() for route Depends()
├── errors.py            # MySQL exceptions → HTTP status codes
├── serialize.py         # Decimal / datetime → JSON-friendly values
├── helpers.py           # Appointment enrichment queries + slot constants
├── check_connection.py  # CLI: verify DB connection and print DDL
├── requirements.txt
├── .env.example
├── schemas/             # Pydantic request/response models
│   ├── owners.py
│   ├── pets.py
│   ├── appointments.py
│   ├── catalog.py
│   ├── records.py
│   └── invoices.py
└── routers/             # 23 API endpoints
    ├── owners.py
    ├── pets.py
    ├── doctors.py
    ├── schedule.py
    ├── appointments.py
    ├── catalog.py
    ├── records.py
    ├── invoices.py
    └── __init__.py      # api_router (aggregates all routers)
```

## Setup

1. Copy environment variables:

   ```bash
   cp .env.example .env
   ```

2. Fill in `DB_HOST`, `DB_PORT`, `DB_USER`, `DB_PASSWORD`, `DB_NAME` in `.env`.

3. Install dependencies:

   ```bash
   pip install -r requirements.txt
   ```

4. Verify database connectivity (optional):

   ```bash
   python check_connection.py
   ```

5. Ensure the database schema is loaded from `database/` (`tables.DDL`, `views.DDL`, `triggers.DDL`).

## Run

```bash
uvicorn main:app --host 127.0.0.1 --port 8000 --reload
```

- API base URL: `http://localhost:8000`
- Interactive docs: `http://localhost:8000/docs`
- OpenAPI schema: `http://localhost:8000/openapi.json`

## Connect the front-end

In `front-end/common.js`:

```js
const API_BASE = 'http://localhost:8000';
const USE_MOCK   = false;
```

Serve the HTML pages from any static file server or open them locally; CORS is enabled for all origins.

## API endpoints (23)

| Method | Path | Description |
|--------|------|-------------|
| GET | `/owners/search?q=` | Search owners by name/phone; empty `q` returns all non-anonymized |
| POST | `/owners` | Create owner |
| PATCH | `/owners/{id}` | Update owner contact info |
| PATCH | `/owners/{id}/anonymize` | Anonymize owner PII |
| GET | `/pets?owner_id=` | List pets for an owner (uses `Pets` view, includes `Age`) |
| POST | `/pets` | Create pet |
| GET | `/doctors` | List active veterinarians (`Role_Level = 3`) |
| GET | `/schedule?doctor_id=&date=` | Available time slots for a doctor on a date |
| POST | `/appointments` | Book appointment |
| GET | `/appointments/today` | Today's pending appointments (enriched) |
| GET | `/appointments?doctor_id=&date=` | Appointments for doctor/date (enriched) |
| PATCH | `/appointments/{id}/cancel` | Cancel appointment (`Appt_Status = 2`) |
| GET | `/catalog` | Active catalog items |
| GET | `/catalog/all` | All catalog items including discontinued |
| PATCH | `/catalog/{id}` | Update price or discontinue item |
| POST | `/records` | Create medical record + empty invoice |
| POST | `/records/{id}/details` | Add treatment detail |
| DELETE | `/records/{id}/details/{detail_id}` | Remove treatment detail |
| PATCH | `/records/{id}/draft` | Save clinical notes / diagnosis draft |
| PATCH | `/records/{id}/lock` | Lock record, deduct stock, mark appointment done |
| GET | `/invoices/pending` | Unpaid invoices for locked records |
| PATCH | `/invoices/{id}/pay` | Mark invoice paid |

## Request / response conventions

- **Content-Type:** `application/json` on requests with a body.
- **Field names:** PascalCase matching DB columns (`Owner_ID`, `Scheduled_Time`, etc.).
- **Dates:** `Consultation_Date`, `Birth_Date` as `"YYYY-MM-DD"`.
- **Datetimes:** `Scheduled_Time` as `"YYYY-MM-DDTHH:MM:SS"`.
- **Decimals:** `Current_Price`, `Total_Billed`, `Historical_Price` returned as JSON numbers.
- **Auth:** None — the front-end uses localStorage session only.

### Enriched appointment response

`GET /appointments/today` and `GET /appointments` return objects with nested `pet`, `owner`, and `doctor`:

```json
{
  "Appointment_ID": 1,
  "Pet_ID": 1,
  "Doc_Staff_ID": 1,
  "Scheduled_Time": "2026-06-13T09:00:00",
  "Appt_Status": 0,
  "pet": { "Pet_ID": 1, "Pet_Name": "小白", "Species_Type": "貓" },
  "owner": { "Owner_ID": 1, "Full_Name": "陳小明" },
  "doctor": { "Staff_ID": 1, "Staff_Name": "王大明", "Specialty": "一般內科" }
}
```

### Pending invoice response

`GET /invoices/pending` embeds related entities:

```json
{
  "Invoice_ID": 1,
  "Record_ID": 1,
  "Total_Billed": 1340.0,
  "Payment_Status": 0,
  "record": { "Record_ID": 1, "Record_Locked": true, "details": [...] },
  "appt": { ... },
  "pet": { ... },
  "owner": { ... }
}
```

## Business rules

Rules enforced by the **database triggers** (not duplicated in Python):

| Rule | Trigger |
|------|---------|
| `Historical_Price` overwritten from catalog on insert | `trg_td_before_insert` |
| Block detail changes on locked records | `trg_td_before_*` |
| `Total_Billed` updated on detail insert/update/delete | `trg_td_after_*` |
| Drug stock deducted when record locked | `trg_mr_after_update` |

Rules handled in **application code**:

| Rule | Where |
|------|-------|
| Create invoice when record is created | `POST /records` |
| Set `Appt_Status = 2` when record locked | `PATCH /records/{id}/lock` |
| Slot conflict check before booking | `POST /appointments` |
| Fixed busy slots per doctor | `GET /schedule` (`BUSY_SLOTS` in `helpers.py`) |

## Error responses

| Condition | HTTP |
|-----------|------|
| Resource not found | 404 |
| Trigger rejection (locked record, etc.) | 400 |
| Duplicate phone / slot conflict | 409 |
| Other database errors | 500 |

Error body is plain text via FastAPI `detail`.

## Enum reference

| Field | Values |
|-------|--------|
| `Appt_Status` | `0` pending, `1` in progress, `2` done/cancelled |
| `Payment_Status` | `0` unpaid, `1` paid |
| `Item_Category` | `1` drug, `2` lab, `3` treatment |
| `Payment_Method` | `cash`, `card`, `insurance` |

## Typical workflow

```
掛號預約 → 病歷/處方 → 帳單結算

POST /appointments
  → GET /appointments/today
  → POST /records
  → POST /records/{id}/details  (repeat)
  → PATCH /records/{id}/lock
  → GET /invoices/pending
  → PATCH /invoices/{id}/pay
```
