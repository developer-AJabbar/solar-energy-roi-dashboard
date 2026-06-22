"""
01_fetch_weather_data.py

Pulls daily solar irradiance + temperature data from the NASA POWER API
for two locations: Phoenix, USA and London, UK.

NASA POWER API docs: https://power.larc.nasa.gov/docs/services/api/
No API key required.

Parameters pulled:
- ALLSKY_SFC_SW_DWN : All-sky surface shortwave downward irradiance (kWh/m^2/day)
                      -> this is our core solar input
- T2M               : Temperature at 2 meters (deg C)
                      -> used later for panel efficiency derating

Output:
- data_raw/nasa_power_phoenix.csv
- data_raw/nasa_power_london.csv
"""

import requests
import pandas as pd
import os
import time

# ---- CONFIG ----
LOCATIONS = {
    "phoenix_usa": {"lat": 33.4484, "lon": -112.0740},
    "london_uk":   {"lat": 51.5074, "lon": -0.1278},
}

START_DATE = "20220101"
END_DATE   = "20231231"

PARAMETERS = "ALLSKY_SFC_SW_DWN,T2M"

BASE_URL = "https://power.larc.nasa.gov/api/temporal/daily/point"

OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "..", "data_raw")
os.makedirs(OUTPUT_DIR, exist_ok=True)


def fetch_location_data(name: str, lat: float, lon: float) -> pd.DataFrame:
    """Fetch daily NASA POWER data for a single location and return as a DataFrame."""
    params = {
        "parameters": PARAMETERS,
        "community": "RE",  # Renewable Energy community
        "longitude": lon,
        "latitude": lat,
        "start": START_DATE,
        "end": END_DATE,
        "format": "JSON",
    }

    print(f"Fetching data for {name} (lat={lat}, lon={lon})...")
    response = requests.get(BASE_URL, params=params, timeout=60)
    response.raise_for_status()
    payload = response.json()

    # The JSON structure nests daily values under properties -> parameter -> {PARAM} -> {date: value}
    parameter_data = payload["properties"]["parameter"]

    irradiance = parameter_data["ALLSKY_SFC_SW_DWN"]
    temperature = parameter_data["T2M"]

    dates = list(irradiance.keys())

    df = pd.DataFrame({
        "date_raw": dates,
        "irradiance_kwh_m2_day": [irradiance[d] for d in dates],
        "temp_c": [temperature[d] for d in dates],
    })

    df["location"] = name
    df["latitude"] = lat
    df["longitude"] = lon

    return df


def main():
    all_frames = []

    for name, coords in LOCATIONS.items():
        df = fetch_location_data(name, coords["lat"], coords["lon"])

        # Save raw per-location file (handy for debugging / inspection)
        out_path = os.path.join(OUTPUT_DIR, f"nasa_power_{name}.csv")
        df.to_csv(out_path, index=False)
        print(f"  -> saved {len(df)} rows to {out_path}")

        all_frames.append(df)
        time.sleep(1)  # be polite to the API between requests

    # Also save a combined raw file with both locations stacked
    combined = pd.concat(all_frames, ignore_index=True)
    combined_path = os.path.join(OUTPUT_DIR, "nasa_power_combined.csv")
    combined.to_csv(combined_path, index=False)
    print(f"\nCombined file saved: {combined_path} ({len(combined)} rows total)")


if __name__ == "__main__":
    main()
