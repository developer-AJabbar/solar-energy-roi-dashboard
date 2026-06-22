"""
03_clean_merge.py

Merges weather data (script 01) with electricity price data (script 02),
per location, and calculates solar production + revenue for a
hypothetical 100 kW solar installation at each site.

FOLDER STRUCTURE ASSUMED (flat layout):
    Energy Data/
    ├── data_raw/
    │   ├── nasa_power_phoenix_usa.csv
    │   ├── nasa_power_london_uk.csv
    │   ├── eia_price_usa.csv
    │   └── ofgem_price_uk.csv
    ├── data_clean/        <- created automatically if missing
    ├── 01_fetch_weather_data.py
    ├── 02_fetch_price_data.py
    └── 03_clean_merge.py  <- this file

Output (to data_clean/):
- production_clean.csv   <- main table for Power BI (one row per day per location)
"""

import pandas as pd
import os

# data_raw and data_clean sit in the SAME folder as this script (flat layout)
RAW_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data_raw")
CLEAN_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data_clean")
os.makedirs(CLEAN_DIR, exist_ok=True)

# ---- Assumptions for the hypothetical installation ----
SYSTEM_SIZE_KW = 100          # 100 kW system, same for both locations (apples-to-apples comparison)
PERFORMANCE_RATIO = 0.78      # accounts for inverter losses, wiring, dust, temperature derating etc.
                              # 0.75-0.80 is a standard real-world assumption for well-maintained systems


def load_weather(filename: str) -> pd.DataFrame:
    path = os.path.join(RAW_DIR, filename)
    df = pd.read_csv(path)
    # date_raw comes from NASA POWER as a string like "20220101"
    df["date"] = pd.to_datetime(df["date_raw"], format="%Y%m%d")
    df = df.drop(columns=["date_raw"])
    return df


def load_price(filename: str) -> pd.DataFrame:
    path = os.path.join(RAW_DIR, filename)
    df = pd.read_csv(path)
    df["date"] = pd.to_datetime(df["date"], format="%Y%m%d")
    return df


def merge_location(weather_file: str, price_file: str, price_col: str, location_name: str) -> pd.DataFrame:
    weather = load_weather(weather_file)
    price = load_price(price_file)

    weather_slim = weather[["date", "irradiance_kwh_m2_day", "temp_c", "location"]]
    price_slim = price[["date", price_col, "currency"]].rename(columns={price_col: "price_per_kwh"})

    merged = pd.merge(weather_slim, price_slim, on="date", how="inner")

    expected_rows = min(len(weather_slim), len(price_slim))
    if len(merged) < expected_rows * 0.95:
        print(f"  WARNING [{location_name}]: merged rows ({len(merged)}) is notably less than "
              f"expected ({expected_rows}) -- check date range overlap between weather and price files.")

    return merged


def calculate_production_and_revenue(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df["production_kwh"] = df["irradiance_kwh_m2_day"] * SYSTEM_SIZE_KW * PERFORMANCE_RATIO
    df["revenue"] = df["production_kwh"] * df["price_per_kwh"]

    theoretical_max_kwh = SYSTEM_SIZE_KW * 24
    df["capacity_factor_pct"] = (df["production_kwh"] / theoretical_max_kwh) * 100

    return df


def main():
    print(f"Looking for input files in: {RAW_DIR}")

    print("Merging Phoenix, USA data...")
    phoenix = merge_location(
        weather_file="nasa_power_phoenix_usa.csv",
        price_file="eia_price_usa.csv",
        price_col="price_usd_per_kwh",
        location_name="phoenix_usa",
    )
    phoenix = calculate_production_and_revenue(phoenix)
    print(f"  -> {len(phoenix)} merged rows")

    print("Merging London, UK data...")
    london = merge_location(
        weather_file="nasa_power_london_uk.csv",
        price_file="ofgem_price_uk.csv",
        price_col="price_gbp_per_kwh",
        location_name="london_uk",
    )
    london = calculate_production_and_revenue(london)
    print(f"  -> {len(london)} merged rows")

    combined = pd.concat([phoenix, london], ignore_index=True)
    combined = combined.sort_values(["location", "date"]).reset_index(drop=True)

    combined["year"] = combined["date"].dt.year
    combined["month"] = combined["date"].dt.month
    combined["month_name"] = combined["date"].dt.strftime("%b")
    combined["quarter"] = combined["date"].dt.quarter

    out_path = os.path.join(CLEAN_DIR, "production_clean.csv")
    combined.to_csv(out_path, index=False)

    print(f"\nFinal clean table saved: {out_path}")
    print(f"Total rows: {len(combined)}")
    print(f"Date range: {combined['date'].min().date()} to {combined['date'].max().date()}")
    print(f"Locations: {combined['location'].unique().tolist()}")
    print("\nSample stats by location:")
    print(combined.groupby("location")[["production_kwh", "revenue", "capacity_factor_pct"]].mean().round(2))


if __name__ == "__main__":
    main()