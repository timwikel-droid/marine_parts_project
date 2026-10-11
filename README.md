# Marine Parts Tracker API

A small REST API for tracking critical spare parts on marine and offshore assets.
Its main job is to answer one question: **which parts are running low, and which of
those will take longest to replace?** A pump impeller with a 60-day lead time that
hits zero stock means a vessel sits idle, so the low-stock report is sorted by lead time.

Built with **Python, FastAPI, SQLite (plain SQL), and pytest**.

## Features

- Create, read, update, and delete spare parts (full REST CRUD)
- Filter parts by category, with pagination (`limit` / `offset`)
- Record stock arriving or being used, with a rule that stock can never go negative
- Low-stock report, sorted so the longest-lead-time parts come first
- Input validation with clear error codes (400, 404, 409, 422)
- Automatic interactive API docs at `/docs`
- 11 automated tests, run on every push with GitHub Actions
- Dockerfile for running it anywhere

## Run it locally

```bash
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
python seed.py                   # loads 6 sample marine parts
uvicorn app.main:app --reload
```

Open http://127.0.0.1:8000/docs to try every endpoint in your browser.

## Run with Docker

```bash
docker build -t marine-parts-api .
docker run -p 8000:8000 marine-parts-api
```

## Run the tests

```bash
pytest -v
```

Each test gets its own temporary database, so tests never interfere with each other
or with your real data.

## Endpoints

| Method | Path                     | What it does                                  |
|--------|--------------------------|-----------------------------------------------|
| GET    | `/health`                | Check the service is running                  |
| POST   | `/parts`                 | Add a new part                                |
| GET    | `/parts`                 | List parts (`?category=Pumps&limit=20`)       |
| GET    | `/parts/low-stock`       | Parts at or below reorder level               |
| GET    | `/parts/{id}`            | Get one part                                  |
| PATCH  | `/parts/{id}`            | Update some fields of a part                  |
| POST   | `/parts/{id}/stock`      | Adjust stock: `{"change": -2}`                |
| DELETE | `/parts/{id}`            | Remove a part                                 |

## Design decisions

- **Plain SQL instead of an ORM**, to keep the database layer easy to read and to show
  the SQL directly. All values use `?` placeholders to prevent SQL injection.
- **Database constraints as a second line of defence**: `UNIQUE` on part numbers and
  `CHECK (quantity_on_hand >= 0)` mean bad data is rejected even if the API code has a bug.
- **Stock changes go through their own endpoint** rather than a plain PATCH, so the
  "never below zero" business rule lives in one place.

## What I'd build next

- A `work_orders` table linked to parts with a foreign key, so using a part is tied to a job
- A stock movement history table (who changed what, when, and why)
- Authentication
- Moving from SQLite to PostgreSQL
