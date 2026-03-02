# Wallet API (Phase 1)

Backend wallet service using Python, FastAPI, and PostgreSQL.

## Features
- Create one wallet per user.
- Credit money to wallet.
- Debit money from wallet (never allows negative balance).
- Get wallet balance.
- Get transaction history (ledger with pagination).
- Every credit/debit creates a ledger entry.
- Data persisted in PostgreSQL.

## Tech Stack
- FastAPI
- SQLAlchemy 2.x
- PostgreSQL
- Alembic
- Pytest

## Project Structure
```text
app/
  api/
    router.py
    routes/
      users.py
      wallets.py
  core/config.py
  db/{base.py,session.py}
  models/{user.py,wallet.py,ledger_entry.py}
  schemas/{user.py,wallet.py,ledger.py}
  services/{user_service.py,wallet_service.py}
  main.py
alembic/
  env.py
  versions/0001_create_wallet_and_ledger.py
tests/
```

## Quick Start (Local)
1. Create PostgreSQL DB and user:
- DB: `wallet_db`
- User: `wallet`
- Password: `wallet`

2. Install deps:
```bash
pip install -r requirements.txt
```

3. Configure env:
```bash
copy .env.example .env
```

4. Run migrations:
```bash
alembic upgrade head
```

5. Start server:
```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

6. API docs:
```text
http://localhost:8000/docs
```

## API Endpoints
- `POST /users`
  - Body: `{"email":"alice@example.com"}`
- `POST /wallets/{user_id}`
- `POST /wallets/{user_id}/credit`
  - Body: `{"amount":"100.00","reference":"salary"}`
- `POST /wallets/{user_id}/debit`
  - Body: `{"amount":"10.00","reference":"payment"}`
- `GET /wallets/{user_id}/balance`
- `GET /wallets/{user_id}/ledger?limit=50&offset=0`
- `GET /healthz`

## Example cURL
```bash
curl -X POST http://localhost:8000/users -H "Content-Type: application/json" -d "{\"email\":\"alice@example.com\"}"
# Use the returned id as USER_ID in all wallet calls below.
curl -X POST http://localhost:8000/wallets/{USER_ID}
curl -X POST http://localhost:8000/wallets/{USER_ID}/credit -H "Content-Type: application/json" -d "{\"amount\":\"100.00\"}"
curl -X POST http://localhost:8000/wallets/{USER_ID}/debit -H "Content-Type: application/json" -d "{\"amount\":\"40.00\"}"
curl http://localhost:8000/wallets/{USER_ID}/balance
curl http://localhost:8000/wallets/{USER_ID}/ledger
```

## Run Tests
Tests expect a reachable PostgreSQL database via `TEST_DATABASE_URL` (or `DATABASE_URL`).
```bash
pytest -q
```

## Notes
- Credit/debit are wrapped in DB transactions.
- Wallet row is locked during update (`SELECT ... FOR UPDATE`) to prepare for concurrent safety in next phase.
