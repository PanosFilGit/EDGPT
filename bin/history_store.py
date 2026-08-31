import glob
import json
import os
import sqlite3
import threading
from pathlib import Path
from typing import Optional

DEFAULT_ELITE_DIR = Path.home() / "Saved Games" / "Frontier Developments" / "Elite Dangerous"
ELITE_DIR = Path(os.environ.get("ELITE_JOURNAL_DIR", str(DEFAULT_ELITE_DIR))).expanduser()
DATA_DIR = Path(os.environ.get("EDGPT_DATA_DIR", "data")).expanduser()
DATA_DIR.mkdir(parents=True, exist_ok=True)
DB_PATH = DATA_DIR / "edgpt_history.db"

_LOCK = threading.RLock()


def _connect():
    conn = sqlite3.connect(DB_PATH, timeout=30)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA synchronous=NORMAL")
    return conn


def init_db():
    with _LOCK, _connect() as conn:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT,
                event TEXT,
                journal_file TEXT NOT NULL,
                line_no INTEGER NOT NULL,
                system TEXT,
                system_address INTEGER,
                body TEXT,
                station TEXT,
                ship TEXT,
                raw_json TEXT NOT NULL,
                UNIQUE(journal_file, line_no)
            );

            CREATE INDEX IF NOT EXISTS idx_events_timestamp ON events(timestamp);
            CREATE INDEX IF NOT EXISTS idx_events_event ON events(event);
            CREATE INDEX IF NOT EXISTS idx_events_system ON events(system);
            CREATE INDEX IF NOT EXISTS idx_events_ship ON events(ship);

            CREATE TABLE IF NOT EXISTS journal_state (
                journal_file TEXT PRIMARY KEY,
                offset INTEGER NOT NULL DEFAULT 0,
                line_no INTEGER NOT NULL DEFAULT 0,
                size INTEGER NOT NULL DEFAULT 0,
                mtime REAL NOT NULL DEFAULT 0
            );
            """
        )


def _extract_fields(e: dict):
    system = e.get("StarSystem") or e.get("SystemName")
    system_address = e.get("SystemAddress")
    body = e.get("Body") or e.get("BodyName")
    station = e.get("StationName")
    ship = e.get("Ship") or e.get("ShipType")
    return system, system_address, body, station, ship


def sync_journals():
    """Index every Journal.*.log file and append only newly written lines."""
    init_db()
    files = sorted(glob.glob(str(ELITE_DIR / "Journal.*.log")))
    inserted = 0

    with _LOCK, _connect() as conn:
        for filename in files:
            path = Path(filename)
            try:
                stat = path.stat()
            except OSError:
                continue

            row = conn.execute(
                "SELECT offset, line_no, size FROM journal_state WHERE journal_file=?",
                (path.name,),
            ).fetchone()

            offset = int(row["offset"]) if row else 0
            line_no = int(row["line_no"]) if row else 0
            old_size = int(row["size"]) if row else 0

            if stat.st_size < old_size or offset > stat.st_size:
                offset = 0
                line_no = 0

            if stat.st_size == old_size and row:
                continue

            try:
                with path.open("rb") as f:
                    f.seek(offset)
                    while True:
                        raw_line = f.readline()
                        if not raw_line:
                            break
                        line_no += 1
                        try:
                            text = raw_line.decode("utf-8", errors="replace").strip()
                            if not text:
                                continue
                            e = json.loads(text)
                        except Exception:
                            continue

                        system, system_address, body, station, ship = _extract_fields(e)
                        cur = conn.execute(
                            """
                            INSERT OR IGNORE INTO events
                            (timestamp,event,journal_file,line_no,system,system_address,body,station,ship,raw_json)
                            VALUES (?,?,?,?,?,?,?,?,?,?)
                            """,
                            (
                                e.get("timestamp"),
                                e.get("event"),
                                path.name,
                                line_no,
                                system,
                                system_address,
                                body,
                                station,
                                ship,
                                json.dumps(e, ensure_ascii=False, separators=(",", ":")),
                            ),
                        )
                        if cur.rowcount:
                            inserted += 1

                    new_offset = f.tell()
            except OSError:
                continue

            conn.execute(
                """
                INSERT INTO journal_state(journal_file,offset,line_no,size,mtime)
                VALUES(?,?,?,?,?)
                ON CONFLICT(journal_file) DO UPDATE SET
                    offset=excluded.offset,
                    line_no=excluded.line_no,
                    size=excluded.size,
                    mtime=excluded.mtime
                """,
                (path.name, new_offset, line_no, stat.st_size, stat.st_mtime),
            )
        conn.commit()
    return inserted


def _row_to_event(row):
    try:
        return json.loads(row["raw_json"])
    except Exception:
        return {"event": row["event"], "timestamp": row["timestamp"]}


def recent_events(limit=200):
    sync_journals()
    limit = max(1, min(int(limit), 5000))
    with _connect() as conn:
        rows = conn.execute(
            "SELECT raw_json,event,timestamp FROM events ORDER BY id DESC LIMIT ?", (limit,)
        ).fetchall()
    return [_row_to_event(r) for r in reversed(rows)]


def latest_event(event_name: str):
    sync_journals()
    with _connect() as conn:
        row = conn.execute(
            "SELECT raw_json,event,timestamp FROM events WHERE event=? ORDER BY id DESC LIMIT 1",
            (event_name,),
        ).fetchone()
    return _row_to_event(row) if row else None


def search_events(
    query: str = "",
    event: str = "",
    start_time: str = "",
    end_time: str = "",
    limit: int = 200,
    newest_first: bool = True,
):
    """Search raw historical events. `query` searches the serialized event JSON."""
    sync_journals()
    limit = max(1, min(int(limit), 5000))
    clauses = []
    params = []

    if event:
        clauses.append("event = ?")
        params.append(event)
    if start_time:
        clauses.append("timestamp >= ?")
        params.append(start_time)
    if end_time:
        clauses.append("timestamp <= ?")
        params.append(end_time)
    if query:
        clauses.append("raw_json LIKE ?")
        params.append(f"%{query}%")

    where = " WHERE " + " AND ".join(clauses) if clauses else ""
    order = "DESC" if newest_first else "ASC"
    sql = f"SELECT raw_json,event,timestamp FROM events{where} ORDER BY id {order} LIMIT ?"
    params.append(limit)

    with _connect() as conn:
        rows = conn.execute(sql, params).fetchall()
    return [_row_to_event(r) for r in rows]


def history_summary():
    sync_journals()
    with _connect() as conn:
        total = conn.execute("SELECT COUNT(*) FROM events").fetchone()[0]
        journals = conn.execute("SELECT COUNT(*) FROM journal_state").fetchone()[0]
        first = conn.execute(
            "SELECT timestamp FROM events WHERE timestamp IS NOT NULL ORDER BY id ASC LIMIT 1"
        ).fetchone()
        last = conn.execute(
            "SELECT timestamp FROM events WHERE timestamp IS NOT NULL ORDER BY id DESC LIMIT 1"
        ).fetchone()
        event_rows = conn.execute(
            "SELECT event, COUNT(*) AS c FROM events GROUP BY event ORDER BY c DESC LIMIT 100"
        ).fetchall()
        systems = conn.execute(
            "SELECT COUNT(DISTINCT system) FROM events WHERE system IS NOT NULL AND system != ''"
        ).fetchone()[0]
        ships = conn.execute(
            "SELECT COUNT(DISTINCT ship) FROM events WHERE ship IS NOT NULL AND ship != ''"
        ).fetchone()[0]

    return {
        "database": str(DB_PATH),
        "journal_files_indexed": journals,
        "events_indexed": total,
        "first_event_time": first[0] if first else None,
        "last_event_time": last[0] if last else None,
        "distinct_systems_seen_in_events": systems,
        "distinct_ship_types_seen_in_events": ships,
        "event_counts": {r["event"]: r["c"] for r in event_rows if r["event"]},
    }


def get_event_page(before_id: Optional[int] = None, limit: int = 500):
    """Page through every raw journal event without losing data."""
    sync_journals()
    limit = max(1, min(int(limit), 5000))
    with _connect() as conn:
        if before_id is None:
            rows = conn.execute(
                "SELECT id, raw_json FROM events ORDER BY id DESC LIMIT ?", (limit,)
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT id, raw_json FROM events WHERE id < ? ORDER BY id DESC LIMIT ?",
                (int(before_id), limit),
            ).fetchall()

    items = []
    for r in rows:
        try:
            event = json.loads(r["raw_json"])
        except Exception:
            event = {}
        items.append({"id": r["id"], "data": event})

    return {
        "items": items,
        "next_before_id": items[-1]["id"] if items else None,
        "count": len(items),
    }
