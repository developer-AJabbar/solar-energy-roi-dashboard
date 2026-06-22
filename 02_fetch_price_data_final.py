"""
02_fetch_price_data.py

Builds electricity price tables for USA and UK so they can be merged
with the NASA POWER solar irradiance data from 01_fetch_weather_data.py.
"""

import requests
import pandas as pd
import os

# ---- CONFIG ----
EIA_API_KEY = "DR1n4DZK74GN5E4Okad3hX2ac9zUZahL35IhRn7y"

STATE_CODE = "AZ"
START_DATE = "2022-01"
END_DATE   = "2023-12"

OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "..", "data_raw")
os.makedirs(OUTPUT_DIR, exist_ok=True)


def fetch_usa_prices() -> pd.DataFrame:
    url = "https://api.eia.gov/v2/electricity/retail-sales/data/"
    params = {
        "api_key": EIA_API_KEY,
        "frequency": "monthly",
        "data[0]": "price",
        "facets[stateid][0]": STATE_CODE,
        "facets[sectorid][0]": "ALL",
        "start": START_DATE,
        "end": END_DATE,
        "sort[0][column]": "period",
        "sort[0][direction]": "asc",
        "length": 5000,
    }

    print(f"Fetching EIA electricity prices for state={STATE_CODE}...")
    response = requests.get(url, params=params, timeout=60)
    response.raise_for_status()
    payload = response.json()

    records = payload["response"]["data"]
    if not records:
        raise ValueError("EIA API returned no records — check state code / date range / key.")

    df = pd.DataFrame(records)
    df = df[["period", "price"]].rename(columns={"price": "price_cents_per_kwh"})
    df["price_cents_per_kwh"] = pd.to_numeric(df["price_cents_per_kwh"], errors="coerce")
    df["price_usd_per_kwh"] = df["price_cents_per_kwh"] / 100.0

    df["period"] = pd.to_datetime(df["period"], format="%Y-%m")
    daily_rows = []
    for _, row in df.iterrows():
        month_start = row["period"]
        month_end = month_start + pd.offsets.MonthEnd(0)
        dates = pd.date_range(month_start, month_end, freq="D")
        for d in dates:
            daily_rows.append({
                "date": d.strftime("%Y%m%d"),
                "price_usd_per_kwh": row["price_usd_per_kwh"],
            })

    daily_df = pd.DataFrame(daily_rows)
    daily_df["location"] = "phoenix_usa"
    daily_df["currency"] = "USD"

    return daily_df


def build_uk_prices() -> pd.DataFrame:
    ofgem_quarterly_rates = [
        ("2022-01-01", 20.0),
        ("2022-04-01", 28.3),
        ("2022-10-01", 34.0),
        ("2023-01-01", 34.0),
        ("2023-04-01", 33.2),
        ("2023-07-01", 30.1),
        ("2023-10-01", 27.4),
    ]

    rows = []
    for i, (start_str, pence_per_kwh) in enumerate(ofgem_quarterly_rates):
        start_date = pd.to_datetime(start_str)
        if i + 1 < len(ofgem_quarterly_rates):
            end_date = pd.to_datetime(ofgem_quarterly_rates[i + 1][0]) - pd.Timedelta(days=1)
        else:
            end_date = pd.to_datetime("2023-12-31")

        dates = pd.date_range(start_date, end_date, freq="D")
        for d in dates:
            rows.append({
                "date": d.strftime("%Y%m%d"),
                "price_gbp_per_kwh": pence_per_kwh / 100.0,
            })

    df = pd.DataFrame(rows)
    df["location"] = "london_uk"
    df["currency"] = "GBP"

    return df


def main():
    usa_df = fetch_usa_prices()
    usa_path = os.path.join(OUTPUT_DIR, "eia_price_usa.csv")
    usa_df.to_csv(usa_path, index=False)
    print(f"USA prices saved: {usa_path} ({len(usa_df)} rows)")

    uk_df = build_uk_prices()
    uk_path = os.path.join(OUTPUT_DIR, "ofgem_price_uk.csv")
    uk_df.to_csv(uk_path, index=False)
    print(f"UK prices saved: {uk_path} ({len(uk_df)} rows)")

    usa_out = usa_df.rename(columns={"price_usd_per_kwh": "price_per_kwh_local"})
    uk_out = uk_df.rename(columns={"price_gbp_per_kwh": "price_per_kwh_local"})

    combined = pd.concat([usa_out, uk_out], ignore_index=True)
    combined_path = os.path.join(OUTPUT_DIR, "electricity_prices_combined.csv")
    combined.to_csv(combined_path, index=False)
    print(f"Combined file saved: {combined_path} ({len(combined)} rows total)")


if __name__ == "__main__":
    main()
