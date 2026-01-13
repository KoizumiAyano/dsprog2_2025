from typing import Any, Dict, List, Tuple, Optional

def _to_float(x: Any) -> Optional[float]:
    try:
        if x is None or x == "":
            return None
        return float(x)
    except Exception:
        return None

def parse_jma_forecast(area_code: str, area_name: str, data: list) -> Tuple[List[Dict], Dict]:
    """
    returns:
      rows: forecastsテーブルに入れるdictのリスト
      meta: 表示用のサブタイトル情報
    """
    if not data or not isinstance(data, list):
        return [], {}

    first = data[0]
    publishing_office = first.get("publishingOffice", "")
    published_at = first.get("reportDatetime", "")

    time_series_list = first.get("timeSeries", [])
    if not time_series_list:
        return [], {}

    weather_ts = time_series_list[0]
    time_defines = weather_ts.get("timeDefines", [])
    areas = weather_ts.get("areas", [])
    if not areas:
        return [], {}

    target_area = areas[0]
    detail_area_name = target_area.get("area", {}).get("name", "")

    weathers = target_area.get("weathers", [])
    winds = target_area.get("winds", [])
    waves = target_area.get("waves", [])

    temps_min = []
    temps_max = []
    for ts in time_series_list:
        a0 = ts.get("areas", [{}])[0]
        if "tempsMin" in a0 and not temps_min:
            temps_min = a0.get("tempsMin", [])
        if "tempsMax" in a0 and not temps_max:
            temps_max = a0.get("tempsMax", [])

    days = min(len(time_defines), len(weathers)) if weathers else len(time_defines)

    rows: List[Dict] = []
    for i in range(days):
        target_date = time_defines[i][:10]  # YYYY-MM-DD
        row = {
            "area_code": area_code,
            "area_name": area_name,
            "detail_area_name": detail_area_name,
            "publishing_office": publishing_office,
            "published_at": published_at,
            "target_date": target_date,
            "weather": weathers[i] if i < len(weathers) else None,
            "wind": winds[i] if i < len(winds) else None,
            "wave": waves[i] if i < len(waves) else None,
            "temp_min": _to_float(temps_min[i]) if i < len(temps_min) else None,
            "temp_max": _to_float(temps_max[i]) if i < len(temps_max) else None,
            "source": "jma",
        }
        rows.append(row)

    meta = {
        "publishing_office": publishing_office,
        "published_at": published_at,
        "detail_area_name": detail_area_name,
    }
    return rows, meta
