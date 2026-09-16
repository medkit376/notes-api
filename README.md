# Notes API

A REST API for managing personal notes, built with FastAPI, PostgreSQL, and
SQLAlchemy (async). Includes JWT authentication, tag-based filtering,
pagination, Alembic migrations, and a pytest suite.

## Stack

- **FastAPI** — async web framework, auto-generated Swagger/OpenAPI docs
- **PostgreSQL** — via `asyncpg` (runtime) and `psycopg2` (Alembic migrations)
- **SQLAlchemy 2.0** — async ORM
- **Alembic** — schema migrations
- **JWT** (`python-jose`) + **bcrypt** (`passlib`) — auth
- **Docker / docker-compose** — containerized app + database
- **pytest** + `httpx.AsyncClient` — async test suite running against an
  in-memory SQLite database (no Docker required to run tests)

## Project layout

```
app/
  api/          # routers: auth.py, notes.py, deps.py (shared dependencies)
  core/         # config, database session, security (JWT/hashing), custom types
  models/       # SQLAlchemy ORM models (User, Note)
  schemas/      # Pydantic request/response schemas
  crud/         # DB access functions, one module per resource
  main.py       # FastAPI app instance, router registration
alembic/
  versions/     # migration scripts
tests/
  conftest.py   # test fixtures (in-memory SQLite DB, async client, auth headers)
  test_auth.py
  test_notes.py
```

## Running with Docker (recommended)

```bash
cp .env.example .env     # edit SECRET_KEY before any real deployment
docker compose up --build
```

This starts Postgres, waits for it to be healthy, runs `alembic upgrade head`,
then starts the API with auto-reload.

- API: http://localhost:8000
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## Running locally without Docker

```bash
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt

# Point POSTGRES_SERVER at a local/remote Postgres instance in .env
alembic upgrade head
uvicorn app.main:app --reload
```

## Running tests

```bash
pip install -r requirements.txt
pytest -v
```

Tests use an in-memory SQLite database (via `aiosqlite`) with the `get_db`
dependency overridden, so **no running Postgres or Docker is required** to
run the suite. A custom `StringArray` column type (`app/core/types.py`)
transparently uses Postgres's native `ARRAY(String)` in production and
SQLAlchemy's `JSON` type under SQLite for tests, so the same model works
against both.

Test coverage includes:
- registration, duplicate-email rejection, login success/failure
- note CRUD (create/read/update/delete)
- pagination (`page`, `page_size`, correct `total`/`pages`)
- tag filtering
- per-user data isolation (user A cannot read/see user B's notes)
- auth required on note endpoints

## API overview

All endpoints are prefixed with `/api/v1`.

| Method | Path              | Auth | Description                          |
|--------|-------------------|------|---------------------------------------|
| POST   | `/auth/register`  | No   | Create a new user                    |
| POST   | `/auth/login`     | No   | OAuth2 password flow, returns JWT    |
| POST   | `/notes`          | Yes  | Create a note                        |
| GET    | `/notes`          | Yes  | List notes (`page`, `page_size`, `tag`) |
| GET    | `/notes/{id}`     | Yes  | Get a single note                    |
| PATCH  | `/notes/{id}`     | Yes  | Partially update a note              |
| DELETE | `/notes/{id}`     | Yes  | Delete a note                        |

Authenticate by sending `Authorization: Bearer <token>` after logging in.
`/auth/login` uses the standard OAuth2 password form (`username` field holds
the email, per the OAuth2 spec) so it works directly with Swagger UI's
"Authorize" button.

### Example: register, log in, create a note

```bash
curl -X POST localhost:8000/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{"email": "me@example.com", "password": "supersecret1"}'

curl -X POST localhost:8000/api/v1/auth/login \
  -d "username=me@example.com&password=supersecret1"
# => {"access_token": "...", "token_type": "bearer"}

curl -X POST localhost:8000/api/v1/notes \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{"title": "Groceries", "content": "Milk, eggs", "tags": ["home"]}'

curl "localhost:8000/api/v1/notes?tag=home&page=1&page_size=10" \
  -H "Authorization: Bearer <token>"
```

## Migrations

```bash
# create a new migration after changing models
alembic revision --autogenerate -m "description"

# apply migrations
alembic upgrade head
```

## Notes on design decisions

- **Notes are scoped to their owner** at the query level (`WHERE owner_id = ...`)
  in every CRUD function, not just checked after fetching — this is what the
  `test_notes_are_isolated_per_user` test verifies.
- **Passwords** are hashed with bcrypt via `passlib`; plaintext passwords are
  never stored or logged.
- **Tags** are stored as a Postgres array column for efficient filtering with
  `func.array_position(tags, tag) IS NOT NULL`, kept simple (single-tag
  filter) rather than building a separate many-to-many tags table — a
  reasonable tradeoff for this scope.
