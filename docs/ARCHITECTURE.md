# Architecture

## Layers
- `app/api/`: HTTP routing only (request parsing, response mapping, status codes)
- `app/services/`: business rules and transaction orchestration
- `app/models/`: SQLAlchemy ORM entities
- `app/schemas/`: Pydantic request/response contracts
- `app/db/`: SQLAlchemy base/session setup
- `app/core/`: app configuration and shared core settings

## Request Flow
1. Request hits route in `app/api/routes/*`
2. Route calls service in `app/services/*`
3. Service reads/writes ORM models through SQLAlchemy session
4. Route returns response schema

## Conventions
- Routes should not contain business logic.
- Services should not return raw dictionaries; return ORM/domain objects.
- Money uses `Decimal` + Postgres `NUMERIC(18,2)`.
- Ledger writes happen in the same transaction as balance updates.
