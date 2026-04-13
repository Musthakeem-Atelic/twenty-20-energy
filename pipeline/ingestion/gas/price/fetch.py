import requests
from datetime import datetime, timedelta

EIA_API_KEY = "SDToq3NmpHvTevHoS9axphhxfvLy0b9qa94dg77D"
EIA_URL     = "https://api.eia.gov/v2/natural-gas/pri/fut/data/"

def fetch_gas_prices(days: int = 10) -> dict:
    end_date   = datetime.today().date()
    start_date = end_date - timedelta(days=days)

    params = {
        "frequency":          "daily",
        "data[0]":            "value",
        "start":              start_date.isoformat(),
        "end":                end_date.isoformat(),
        "sort[0][column]":    "period",
        "sort[0][direction]": "desc",
        "offset":             0,
        "length":             5,
        "api_key":            EIA_API_KEY,
    }

    print(f"Fetching EIA gas prices from {start_date} to {end_date}...")
    response = requests.get(EIA_URL, params=params, timeout=30)
    response.raise_for_status()

    data = response.json()
    records = data.get("response", {}).get("data", [])
    api_version = data.get("response", {}).get("apiVersion", None)

    print(f"  → {len(records)} records fetched")
    return {"records": records, "api_version": api_version}