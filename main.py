"""Marine Parts Tracker API: a small REST API for tracking critical spare parts."""
import sqlite3
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, HTTPException, Query, Response, status

from app.database import get_connection, init_db
from app.schemas import Part, PartCreate, PartUpdate, StockAdjustment


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()  # create the table on startup if it doesn't exist
    yield


app = FastAPI(
    title="Marine Parts Tracker API",
    description="Track critical spare parts for marine and offshore assets "
                "and flag low stock before it causes downtime.",
    version="0.1.0",
    lifespan=lifespan,
)


def get_db():
    """Dependency: opens a DB connection per request and always closes it."""
    conn = get_connection()
    try:
        yield conn
    finally:
        conn.close()


def fetch_part_or_404(db: sqlite3.Connection, part_id: int) -> sqlite3.Row:
    row = db.execute("SELECT * FROM parts WHERE id = ?", (part_id,)).fetchone()
    if row is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail=f"Part {part_id} not found")
    return row


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/parts", response_model=Part, status_code=status.HTTP_201_CREATED)
def create_part(part: PartCreate, db: sqlite3.Connection = Depends(get_db)):
    try:
        cur = db.execute(
            """INSERT INTO parts (part_number, name, category, quantity_on_hand,
                                  reorder_level, lead_time_days, supplier)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (part.part_number, part.name, part.category, part.quantity_on_hand,
             part.reorder_level, part.lead_time_days, part.supplier),
        )
        db.commit()
    except sqlite3.IntegrityError:
        raise HTTPException(status.HTTP_409_CONFLICT,
                            detail=f"Part number {part.part_number} already exists")
    return dict(fetch_part_or_404(db, cur.lastrowid))


@app.get("/parts", response_model=list[Part])
def list_parts(
    category: str | None = None,
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    db: sqlite3.Connection = Depends(get_db),
):
    sql = "SELECT * FROM parts"
    params: list = []
    if category:
        sql += " WHERE category = ?"
        params.append(category)
    sql += " ORDER BY id LIMIT ? OFFSET ?"
    params += [limit, offset]
    return [dict(r) for r in db.execute(sql, params).fetchall()]


# Must come BEFORE /parts/{part_id}, otherwise FastAPI tries to read
# "low-stock" as a part id and returns a 422 error.
@app.get("/parts/low-stock", response_model=list[Part])
def low_stock(db: sqlite3.Connection = Depends(get_db)):
    """Parts at or below their reorder level, longest lead time first
    (those are the ones most likely to cause downtime)."""
    rows = db.execute(
        """SELECT * FROM parts
           WHERE quantity_on_hand <= reorder_level
           ORDER BY lead_time_days DESC, quantity_on_hand ASC"""
    ).fetchall()
    return [dict(r) for r in rows]


@app.get("/parts/{part_id}", response_model=Part)
def get_part(part_id: int, db: sqlite3.Connection = Depends(get_db)):
    return dict(fetch_part_or_404(db, part_id))


@app.patch("/parts/{part_id}", response_model=Part)
def update_part(part_id: int, changes: PartUpdate, db: sqlite3.Connection = Depends(get_db)):
    fetch_part_or_404(db, part_id)
    updates = changes.model_dump(exclude_unset=True)
    if not updates:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail="No fields to update")
    # Column names come from our own Pydantic model, never from raw user input,
    # so building the SET clause this way is safe. Values still use ? placeholders.
    set_clause = ", ".join(f"{col} = ?" for col in updates)
    try:
        db.execute(f"UPDATE parts SET {set_clause} WHERE id = ?", [*updates.values(), part_id])
        db.commit()
    except sqlite3.IntegrityError:
        raise HTTPException(status.HTTP_409_CONFLICT, detail="Update violates a constraint")
    return dict(fetch_part_or_404(db, part_id))


@app.post("/parts/{part_id}/stock", response_model=Part)
def adjust_stock(part_id: int, adj: StockAdjustment, db: sqlite3.Connection = Depends(get_db)):
    """Record parts arriving (+) or being used (-). Stock can never go below zero."""
    part = fetch_part_or_404(db, part_id)
    new_qty = part["quantity_on_hand"] + adj.change
    if new_qty < 0:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            detail=f"Only {part['quantity_on_hand']} in stock; cannot remove {-adj.change}",
        )
    db.execute("UPDATE parts SET quantity_on_hand = ? WHERE id = ?", (new_qty, part_id))
    db.commit()
    return dict(fetch_part_or_404(db, part_id))


@app.delete("/parts/{part_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_part(part_id: int, db: sqlite3.Connection = Depends(get_db)):
    fetch_part_or_404(db, part_id)
    db.execute("DELETE FROM parts WHERE id = ?", (part_id,))
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
