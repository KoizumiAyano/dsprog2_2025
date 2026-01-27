import os
import time
import json
import sqlite3
import argparse

import requests
from dotenv import load_dotenv
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

load_dotenv()

DB_PATH = "estat.db"
RAW_JSON_PATH = "estat_raw.json"

STATS_LIST_URL = "https://api.e-stat.go.jp/rest/3.0/app/json/getStatsList"
STATS_DATA_URL = "https://api.e-stat.go.jp/rest/3.0/app/json/getStatsData"


session = requests.Session()
retries = Retry(
    total=3,
    backoff_factor=0.8,
    status_forcelist=[429, 500, 502, 503, 504],
    allowed_methods=["GET"],
)
adapter = HTTPAdapter(max_retries=retries)
session.mount("https://", adapter)


def dig(d, keys):
    cur = d
    for k in keys:
        if not isinstance(cur, dict) or k not in cur:
            return None
        cur = cur[k]
    return cur


def short_json(d, n=900):
    return json.dumps(d, ensure_ascii=False)[:n]


def get_app_id():
    app_id = os.getenv("ESTAT_APP_ID")
    if not app_id:
        raise RuntimeError("ESTAT_APP_ID が未設定です（.env に appId を入れてね）")
    return app_id


def assert_api_ok(resp_json: dict):
    """
    e-Stat がエラーを返しているとき、理由が見える形で落とす
    """
    result = resp_json.get("RESULT")
    if isinstance(result, dict):
        status = str(result.get("STATUS"))
        if status != "0":
            msg = result.get("ERROR_MSG") or result.get("ERROR_MESSAGE") or "Unknown error"
            raise RuntimeError(f"e-Stat API error: STATUS={status}, MSG={msg}")

    if "GET_STATS_DATA" not in resp_json and "GET_STATS_LIST" not in resp_json:
        raise RuntimeError("APIの返却が想定外です: " + short_json(resp_json, 500))


def api_get(url: str, params: dict) -> dict:
    headers = {
        "User-Agent": "Mozilla/5.0 (educational; e-Stat API client)"
    }
    r = session.get(url, params=params, headers=headers, timeout=(10, 30))
    r.raise_for_status()

    data = r.json()
    assert_api_ok(data)

    time.sleep(1)
    return data

def init_db():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("""
    CREATE TABLE IF NOT EXISTS observations (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        stats_data_id TEXT,
        value REAL,
        time TEXT,
        area TEXT,
        dims_json TEXT,
        scraped_at TEXT DEFAULT (datetime('now'))
    );
    """)
    cur.execute("CREATE INDEX IF NOT EXISTS idx_obs_time ON observations(time);")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_obs_area ON observations(area);")
    conn.commit()
    conn.close()


def normalize_value(v):
    if v is None:
        return None
    if isinstance(v, (int, float)):
        return float(v)
    if isinstance(v, str):
        s = v.strip()
        if s == "":
            return None
        try:
            return float(s)
        except ValueError:
            return None
    return None


def insert_rows(stats_data_id: str, values: list[dict]):
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    rows = []
    for item in values:
        raw_value = item.get("$") or item.get("@value") or item.get("value")
        val = normalize_value(raw_value)

        dims = {k.lstrip("@"): str(v) for k, v in item.items() if k.startswith("@")}
        t = dims.get("time")
        a = dims.get("area")
        dims_json = json.dumps(dims, ensure_ascii=False)

        rows.append((stats_data_id, val, t, a, dims_json))

    cur.executemany("""
        INSERT INTO observations(stats_data_id, value, time, area, dims_json)
        VALUES (?, ?, ?, ?, ?)
    """, rows)

    conn.commit()
    conn.close()
    print(f"Inserted: {len(rows)} rows")



def search_stats_list(keyword: str, limit: int = 10) -> list[dict]:
    app_id = get_app_id()
    params = {
        "appId": app_id,
        "searchWord": keyword,
        "limit": limit,
    }
    data = api_get(STATS_LIST_URL, params)

    items = dig(data, ["GET_STATS_LIST", "DATALIST_INF", "TABLE_INF"])
    if items is None:
        raise RuntimeError("統計表一覧が見つかりません: " + short_json(data, 600))

    if isinstance(items, dict):
        items = [items]
    if not isinstance(items, list):
        raise RuntimeError("統計表一覧の形式が想定外です")

    return items


def fetch_stats_data(stats_data_id: str) -> dict:
    app_id = get_app_id()
    params = {
        "appId": app_id,
        "statsDataId": stats_data_id,
    }
    return api_get(STATS_DATA_URL, params)


def extract_values(stats_data_json: dict) -> list[dict]:
    values = dig(stats_data_json, ["GET_STATS_DATA", "STATISTICAL_DATA", "DATA_INF", "VALUE"])
    if values is None:
        raise RuntimeError("VALUEが見つかりません。返却内容（先頭）: " + short_json(stats_data_json, 700))

    if isinstance(values, dict):
        values = [values]
    if not isinstance(values, list):
        raise RuntimeError("VALUEの形式が想定外です")

    return values

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--keyword", default="宿泊", help="統計表検索キーワード（例：宿泊 / 観光 / 旅行 / 住宅 / 人口）")
    parser.add_argument("--pick", type=int, default=1, help="候補の何番目を使うか（1始まり）")
    parser.add_argument("--statsDataId", default=None, help="分かっている場合は統計表IDを直接指定（優先）")
    args = parser.parse_args()

    init_db()
    stats_data_id = args.statsDataId

    if not stats_data_id:
        items = search_stats_list(args.keyword, limit=10)

        print("=== statsDataId 候補（上から10件）===")
        for i, it in enumerate(items, start=1):
            sid = it.get("@id") or it.get("STATSDATA_ID") or it.get("statsDataId") or ""
            title = it.get("TITLE") or it.get("STAT_NAME") or ""
            if isinstance(title, dict):
                title = title.get("$") or str(title)
            print(f"{i}. {sid}  {title}")

        if args.pick < 1 or args.pick > len(items):
            raise RuntimeError(f"--pick は 1〜{len(items)} の範囲で指定してね")

        chosen = items[args.pick - 1]
        stats_data_id = chosen.get("@id") or chosen.get("STATSDATA_ID") or chosen.get("statsDataId")

        if not stats_data_id:
            raise RuntimeError("選んだ候補からstatsDataIdを取得できませんでした")

        print(f"\n[選択] statsDataId = {stats_data_id}\n")


    data = fetch_stats_data(stats_data_id)

    with open(RAW_JSON_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print(f"Saved raw JSON: {RAW_JSON_PATH}")


    values = extract_values(data)
    insert_rows(stats_data_id, values)

    print(f"Done. DB: {DB_PATH}")


if __name__ == "__main__":
    main()
