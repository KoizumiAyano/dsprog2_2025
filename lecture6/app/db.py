import sqlite3
from typing import Dict, List, Optional
from .config import DB_PATH

def init_db(db_path: str = DB_PATH) -> sqlite3.Connection:
    conn = sqlite3.connect(db_path, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS forecasts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            area_code TEXT NOT NULL,
            area_name TEXT NOT NULL,
            detail_area_name TEXT,
            publishing_office TEXT,
            published_at TEXT NOT NULL,
            target_date TEXT NOT NULL,
            weather TEXT,
            wind TEXT,
            wave TEXT,
            temp_min REAL,
            temp_max REAL,
            source TEXT DEFAULT 'jma',
            UNIQUE(area_code, published_at, target_date)
        );
        """
    )

    cur.execute("CREATE INDEX IF NOT EXISTS idx_forecasts_area_date ON forecasts(area_code, target_date);")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_forecasts_area_pub ON forecasts(area_code, published_at);")

    conn.commit()
    return conn

def upsert_forecast(conn: sqlite3.Connection, row: Dict) -> None:
    sql = """
    INSERT INTO forecasts (
        area_code, area_name, detail_area_name, publishing_office,
        published_at, target_date, weather, wind, wave, temp_min, temp_max, source
    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ON CONFLICT(area_code, published_at, target_date) DO UPDATE SET
        area_name=excluded.area_name,
        detail_area_name=excluded.detail_area_name,
        publishing_office=excluded.publishing_office,
        weather=excluded.weather,
        wind=excluded.wind,
        wave=excluded.wave,
        temp_min=excluded.temp_min,
        temp_max=excluded.temp_max,
        source=excluded.source;
    """
    conn.execute(
        sql,
        (
            row["area_code"],
            row["area_name"],
            row.get("detail_area_name"),
            row.get("publishing_office"),
            row["published_at"],
            row["target_date"],
            row.get("weather"),
            row.get("wind"),
            row.get("wave"),
            row.get("temp_min"),
            row.get("temp_max"),
            row.get("source", "jma"),
        ),
    )
    conn.commit()

def get_latest_published_at(conn: sqlite3.Connection, area_code: str) -> Optional[str]:
    cur = conn.execute("SELECT MAX(published_at) AS latest FROM forecasts WHERE area_code=?;", (area_code,))
    r = cur.fetchone()
    return r["latest"] if r and r["latest"] else None

def load_latest_forecasts(conn: sqlite3.Connection, area_code: str) -> List[sqlite3.Row]:
    latest = get_latest_published_at(conn, area_code)
    if not latest:
        return []
    cur = conn.execute(
        """
        SELECT * FROM forecasts
        WHERE area_code=? AND published_at=?
        ORDER BY target_date ASC;
        """,
        (area_code, latest),
    )
    return list(cur.fetchall())

def list_available_target_dates(conn: sqlite3.Connection, area_code: str) -> List[str]:
    cur = conn.execute(
        """
        SELECT DISTINCT target_date
        FROM forecasts
        WHERE area_code=?
        ORDER BY target_date ASC;
        """,
        (area_code,),
    )
    return [r["target_date"] for r in cur.fetchall()]

def load_forecast_for_date_latest(conn: sqlite3.Connection, area_code: str, target_date: str):
    cur = conn.execute(
        """
        SELECT * FROM forecasts
        WHERE area_code=? AND target_date=?
        ORDER BY published_at DESC
        LIMIT 1;
        """,
        (area_code, target_date),
    )
    return cur.fetchone()
