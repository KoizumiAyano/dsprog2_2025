import requests
from .config import AREA_URL, FORECAST_BASE_URL, HTTP_TIMEOUT

def fetch_areas_json() -> dict:
    res = requests.get(AREA_URL, timeout=HTTP_TIMEOUT)
    res.raise_for_status()
    return res.json()

def fetch_forecast_json(area_code: str) -> list:
    url = f"{FORECAST_BASE_URL}/{area_code}.json"
    res = requests.get(url, timeout=HTTP_TIMEOUT)
    res.raise_for_status()
    return res.json()
