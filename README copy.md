# Marine Parts Tracker API

A simple API for keeping track of spare parts on ships and offshore rigs.

When a part runs out, a ship can be stuck waiting for a replacement. This API shows
which parts are running low, starting with the ones that take longest to arrive.

Built with Python, FastAPI, SQLite, and pytest.

## What it can do

- Add, view, edit, and delete parts
- Record parts being used or delivered
- Show a list of parts that are running low

## How to run it

```bash
pip install -r requirements.txt
python seed.py
uvicorn app.main:app --reload
```

Then open http://127.0.0.1:8000/docs in your browser to try it out.

## How to run the tests

```bash
pytest
```

## Endpoints

| Method | Path               | What it does              |
|--------|--------------------|---------------------------|
| GET    | `/parts`           | List all parts            |
| POST   | `/parts`           | Add a part                |
| GET    | `/parts/{id}`      | Get one part              |
| PATCH  | `/parts/{id}`      | Edit a part               |
| DELETE | `/parts/{id}`      | Delete a part             |
| POST   | `/parts/{id}/stock`| Add or remove stock       |
| GET    | `/parts/low-stock` | List parts running low    |

## Ideas for later

- Link parts to work orders (jobs that use them)
- Keep a history of stock changes
