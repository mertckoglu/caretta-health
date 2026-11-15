"""SQLite storage for readings (stdlib only, one file, works offline on board).

The database path comes from the ``CARETTA_DB`` environment variable and
defaults to ``data/caretta.db`` in the repository.
"""
from __future__ import annotations

import json
import os
import sqlite3
import uuid
from datetime import datetime
from pathlib import Path

import pandas as pd

from app.core.indicators import validate_value
from app.core.thresholds import DEFAULT_ENVIRONMENT, ENVIRONMENTS

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_DB_PATH = ROOT / "data" / "caretta.db"

SCHEMA = """
CREATE TABLE IF NOT EXISTS readings (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    astronaut_id  TEXT    NOT NULL,
    ts            TEXT    NOT NULL,
    indicator     TEXT    NOT NULL,
    value         REAL    NOT NULL,
    environment   TEXT    NOT NULL DEFAULT 'iss',
    note          TEXT
);
CREATE INDEX IF NOT EXISTS idx_readings_astro_ts ON readings (astronaut_id, ts);
CREATE TABLE IF NOT EXISTS photos (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    astronaut_id  TEXT    NOT NULL,
    ts            TEXT    NOT NULL,
    environment   TEXT    NOT NULL DEFAULT 'iss',
    category      TEXT    NOT NULL DEFAULT 'other',
    caption       TEXT,
    filename      TEXT    NOT NULL,
    mime          TEXT    NOT NULL DEFAULT 'image/jpeg'
);
CREATE INDEX IF NOT EXISTS idx_photos_astro_ts ON photos (astronaut_id, ts);
CREATE TABLE IF NOT EXISTS diagnoses (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    astronaut_id  TEXT    NOT NULL,
    ts            TEXT    NOT NULL,
    environment   TEXT    NOT NULL DEFAULT 'iss',
    outcome_id    TEXT    NOT NULL,
    title         TEXT    NOT NULL,
    urgency       TEXT    NOT NULL,
    details       TEXT    NOT NULL           -- full assessment as JSON
);
CREATE INDEX IF NOT EXISTS idx_diagnoses_astro_ts ON diagnoses (astronaut_id, ts);
"""

#: Photo categories offered in the check-in (key -> label)
PHOTO_CATEGORIES = {
    "skin": "Skin / rash",
    "eye": "Eye",
    "wound": "Wound / injury",
    "swelling": "Swelling / oedema",
    "mouth": "Mouth / teeth",
    "other": "Other",
}
_EXT = {"image/jpeg": ".jpg", "image/jpg": ".jpg", "image/png": ".png", "image/webp": ".webp"}
MAX_PHOTO_BYTES = 15 * 1024 * 1024

COLUMNS = ["id", "astronaut_id", "ts", "indicator", "value", "environment", "note"]


def db_path() -> Path:
    return Path(os.environ.get("CARETTA_DB", DEFAULT_DB_PATH))


def photo_dir(conn: sqlite3.Connection | None = None) -> Path:
    """Photos live next to the database file, in a ``photos`` folder."""
    if conn is not None:
        main = conn.execute("PRAGMA database_list").fetchone()
        if main and main[2]:
            return Path(main[2]).parent / "photos"
    return db_path().parent / "photos"


def connect(path: str | Path | None = None) -> sqlite3.Connection:
    path = Path(path) if path else db_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.executescript(SCHEMA)
    return conn


def _ts(ts: datetime | str | None) -> str:
    if ts is None:
        return datetime.now().isoformat(timespec="seconds")
    # one fixed format (seconds precision) so every stored timestamp parses the same way
    return pd.Timestamp(ts).floor("s").isoformat(timespec="seconds")


def insert_reading(
    conn: sqlite3.Connection,
    astronaut_id: str,
    indicator: str,
    value: float,
    ts: datetime | str | None = None,
    environment: str = DEFAULT_ENVIRONMENT,
    note: str | None = None,
) -> int:
    validate_value(indicator, float(value))
    if environment not in ENVIRONMENTS:
        raise ValueError(f"Unknown environment: {environment!r}")
    if not astronaut_id or not astronaut_id.strip():
        raise ValueError("astronaut_id must not be empty")
    cur = conn.execute(
        "INSERT INTO readings (astronaut_id, ts, indicator, value, environment, note) VALUES (?,?,?,?,?,?)",
        (astronaut_id.strip(), _ts(ts), indicator, float(value), environment, note),
    )
    conn.commit()
    return int(cur.lastrowid)


def insert_dataframe(conn: sqlite3.Connection, df: pd.DataFrame) -> int:
    """Bulk insert a long DataFrame (ts, astronaut_id, indicator, value[, environment, note])."""
    rows = []
    for r in df.to_dict("records"):
        validate_value(r["indicator"], float(r["value"]))
        rows.append(
            (
                str(r["astronaut_id"]),
                _ts(r["ts"]),
                r["indicator"],
                float(r["value"]),
                r.get("environment") or DEFAULT_ENVIRONMENT,
                r.get("note") if isinstance(r.get("note"), str) else None,
            )
        )
    conn.executemany(
        "INSERT INTO readings (astronaut_id, ts, indicator, value, environment, note) VALUES (?,?,?,?,?,?)",
        rows,
    )
    conn.commit()
    return len(rows)


def fetch_readings(
    conn: sqlite3.Connection,
    astronaut_id: str | None = None,
    since: datetime | str | None = None,
    indicator: str | None = None,
    environment: str | None = None,
) -> pd.DataFrame:
    sql = "SELECT * FROM readings WHERE 1=1"
    params: list = []
    if environment:
        sql += " AND environment = ?"
        params.append(environment)
    if astronaut_id:
        sql += " AND astronaut_id = ?"
        params.append(astronaut_id)
    if since is not None:
        sql += " AND ts >= ?"
        params.append(_ts(since))
    if indicator:
        sql += " AND indicator = ?"
        params.append(indicator)
    sql += " ORDER BY ts, id"
    rows = conn.execute(sql, params).fetchall()
    df = pd.DataFrame([dict(r) for r in rows], columns=COLUMNS)
    if not df.empty:
        df["ts"] = pd.to_datetime(df["ts"], format="ISO8601")  # tolerant of older rows with microseconds
    return df


def list_astronauts(conn: sqlite3.Connection, environment: str | None = None) -> list[str]:
    if environment:
        rows = conn.execute(
            "SELECT DISTINCT astronaut_id FROM readings WHERE environment = ? ORDER BY astronaut_id", (environment,)
        )
    else:
        rows = conn.execute("SELECT DISTINCT astronaut_id FROM readings ORDER BY astronaut_id")
    return [r[0] for r in rows]


def count_readings(conn: sqlite3.Connection, environment: str | None = None) -> int:
    if environment:
        return conn.execute("SELECT COUNT(*) FROM readings WHERE environment = ?", (environment,)).fetchone()[0]
    return conn.execute("SELECT COUNT(*) FROM readings").fetchone()[0]


def delete_environment(conn: sqlite3.Connection, environment: str) -> int:
    cur = conn.execute("DELETE FROM readings WHERE environment = ?", (environment,))
    conn.commit()
    return cur.rowcount


def delete_astronaut(conn: sqlite3.Connection, astronaut_id: str, environment: str | None = None) -> int:
    if environment:
        cur = conn.execute(
            "DELETE FROM readings WHERE astronaut_id = ? AND environment = ?", (astronaut_id, environment)
        )
        conn.commit()
        return cur.rowcount
    cur = conn.execute("DELETE FROM readings WHERE astronaut_id = ?", (astronaut_id,))
    conn.commit()
    return cur.rowcount


def delete_reading(conn: sqlite3.Connection, reading_id: int) -> bool:
    cur = conn.execute("DELETE FROM readings WHERE id = ?", (reading_id,))
    conn.commit()
    return cur.rowcount > 0


# ------------------------------------------------------------------ photos --
PHOTO_COLUMNS = ["id", "astronaut_id", "ts", "environment", "category", "caption", "filename", "mime"]


def insert_photo(
    conn: sqlite3.Connection,
    astronaut_id: str,
    data: bytes,
    mime: str = "image/jpeg",
    ts: datetime | str | None = None,
    environment: str = DEFAULT_ENVIRONMENT,
    category: str = "other",
    caption: str | None = None,
) -> int:
    """Store the image file in the photos folder and register it in the database."""
    if not data:
        raise ValueError("empty photo")
    if len(data) > MAX_PHOTO_BYTES:
        raise ValueError("photo larger than 15 MB")
    mime = (mime or "image/jpeg").lower()
    if mime not in _EXT:
        raise ValueError(f"unsupported image type {mime!r}")
    if category not in PHOTO_CATEGORIES:
        raise ValueError(f"unknown photo category {category!r}")
    if environment not in ENVIRONMENTS:
        raise ValueError(f"Unknown environment: {environment!r}")
    stamp = pd.Timestamp(_ts(ts))
    folder = photo_dir(conn)
    folder.mkdir(parents=True, exist_ok=True)
    safe_id = "".join(c for c in astronaut_id.strip() if c.isalnum() or c in "-_") or "crew"
    name = f"{safe_id}_{stamp:%Y%m%d_%H%M%S}_{uuid.uuid4().hex[:8]}{_EXT[mime]}"
    _write_image_and_thumb(folder / name, data)
    cur = conn.execute(
        "INSERT INTO photos (astronaut_id, ts, environment, category, caption, filename, mime) VALUES (?,?,?,?,?,?,?)",
        (astronaut_id.strip(), stamp.isoformat(), environment, category, (caption or "").strip() or None, name, mime),
    )
    conn.commit()
    return int(cur.lastrowid)


THUMB_PX = 480


def thumb_name(filename: str) -> str:
    return "thumb_" + Path(filename).stem + ".jpg"


def _write_image_and_thumb(path: Path, data: bytes) -> None:
    """Validate that ``data`` really is an image, save it, and save a small JPEG thumbnail for the gallery."""
    import io

    from PIL import Image, ImageOps, UnidentifiedImageError

    try:
        with Image.open(io.BytesIO(data)) as im:
            im.verify()
        with Image.open(io.BytesIO(data)) as im:
            im = ImageOps.exif_transpose(im)
            if im.mode not in ("RGB", "L"):
                im = im.convert("RGB")
            # uniform 4:3 crop so gallery cards line up; the full image is kept untouched
            im = ImageOps.fit(im, (THUMB_PX, THUMB_PX * 3 // 4), Image.Resampling.LANCZOS)
            path.write_bytes(data)
            im.save(path.parent / thumb_name(path.name), "JPEG", quality=82, optimize=True)
    except (UnidentifiedImageError, OSError, ValueError) as exc:
        raise ValueError("file is not a valid image") from exc


def thumb_path(conn: sqlite3.Connection, filename: str) -> Path:
    """Thumbnail if it exists, otherwise the original file."""
    t = photo_dir(conn) / thumb_name(Path(filename).name)
    return t if t.exists() else photo_path(conn, filename)


def fetch_photos(
    conn: sqlite3.Connection,
    astronaut_id: str | None = None,
    environment: str | None = None,
    category: str | None = None,
) -> pd.DataFrame:
    sql, params = "SELECT * FROM photos WHERE 1=1", []
    for col, val in (("astronaut_id", astronaut_id), ("environment", environment), ("category", category)):
        if val:
            sql += f" AND {col} = ?"
            params.append(val)
    rows = conn.execute(sql + " ORDER BY ts DESC, id DESC", params).fetchall()
    df = pd.DataFrame([dict(r) for r in rows], columns=PHOTO_COLUMNS)
    if not df.empty:
        df["ts"] = pd.to_datetime(df["ts"], format="ISO8601")  # tolerant of older rows with microseconds
    return df


def photo_path(conn: sqlite3.Connection, filename: str) -> Path:
    return photo_dir(conn) / Path(filename).name  # .name: never escape the photos folder


def update_photo(conn: sqlite3.Connection, photo_id: int, caption: str | None = None, category: str | None = None) -> bool:
    if category is not None and category not in PHOTO_CATEGORIES:
        raise ValueError(f"unknown photo category {category!r}")
    cur = conn.execute(
        "UPDATE photos SET caption = COALESCE(?, caption), category = COALESCE(?, category) WHERE id = ?",
        ((caption.strip() or None) if caption is not None else None, category, photo_id),
    )
    conn.commit()
    return cur.rowcount > 0


def delete_photo(conn: sqlite3.Connection, photo_id: int) -> bool:
    row = conn.execute("SELECT filename FROM photos WHERE id = ?", (photo_id,)).fetchone()
    if not row:
        return False
    conn.execute("DELETE FROM photos WHERE id = ?", (photo_id,))
    conn.commit()
    photo_path(conn, row["filename"]).unlink(missing_ok=True)
    (photo_dir(conn) / thumb_name(row["filename"])).unlink(missing_ok=True)
    return True


# --------------------------------------------------------------- diagnoses --
DIAGNOSIS_COLUMNS = ["id", "astronaut_id", "ts", "environment", "outcome_id", "title", "urgency", "details"]


def insert_diagnosis(
    conn: sqlite3.Connection,
    astronaut_id: str,
    assessment: dict,
    environment: str = DEFAULT_ENVIRONMENT,
    ts: datetime | str | None = None,
) -> int:
    """Store a finished triage (``Assessment.to_dict()``)."""
    if environment not in ENVIRONMENTS:
        raise ValueError(f"Unknown environment: {environment!r}")
    for key in ("outcome_id", "title", "urgency"):
        if not assessment.get(key):
            raise ValueError(f"assessment is missing {key!r}")
    cur = conn.execute(
        "INSERT INTO diagnoses (astronaut_id, ts, environment, outcome_id, title, urgency, details) "
        "VALUES (?,?,?,?,?,?,?)",
        (astronaut_id.strip(), _ts(ts), environment, assessment["outcome_id"], assessment["title"],
         assessment["urgency"], json.dumps(assessment, ensure_ascii=False)),
    )
    conn.commit()
    return int(cur.lastrowid)


def fetch_diagnoses(
    conn: sqlite3.Connection, astronaut_id: str | None = None, environment: str | None = None
) -> pd.DataFrame:
    sql, params = "SELECT * FROM diagnoses WHERE 1=1", []
    for col, val in (("astronaut_id", astronaut_id), ("environment", environment)):
        if val:
            sql += f" AND {col} = ?"
            params.append(val)
    rows = conn.execute(sql + " ORDER BY ts DESC, id DESC", params).fetchall()
    df = pd.DataFrame([dict(r) for r in rows], columns=DIAGNOSIS_COLUMNS)
    if not df.empty:
        df["ts"] = pd.to_datetime(df["ts"], format="ISO8601")  # tolerant of older rows with microseconds
        df["details"] = df["details"].map(json.loads)
    return df


def delete_diagnosis(conn: sqlite3.Connection, diagnosis_id: int) -> bool:
    cur = conn.execute("DELETE FROM diagnoses WHERE id = ?", (diagnosis_id,))
    conn.commit()
    return cur.rowcount > 0
