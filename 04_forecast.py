"""
04_forecast.py

Generates a 90-day forward forecast of solar production and revenue
for both locations, using a seasonal-naive method:

    forecast for a given future date
        = average of that same calendar day (+/- a few days window)
          across the historical years available
        adjusted by a simple recent trend factor

This approach is standard for energy/weather-driven forecasting because
solar output is dominated by seasonal patterns (day length, sun angle,
typical cloud cover for that time of year) rather than by short-term
momentum the way stock prices are. A "same time last year" baseline is
a strong, defensible predictor here -- much stronger than a generic
linear trend line would be for this kind of data.

We also add a simple confidence band (+/- 1 standard deviation of the
historical day-of-year variability) so the dashboard can show forecast
uncertainty, not just a single line.

Input:
- data_clean/production_clean.csv   (from 03_clean_merge.py)

Output:
- data_clean/forecast_output.csv    (90 days per location, with
  forecasted production, revenue, and upper/lower confidence bounds)
"""

import pandas as pd
import numpy as np
import os

CLEAN_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data_clean")
os.makedirs(CLEAN_DIR, exist_ok=True)
# NOTE: this assumes a FLAT layout where data_clean/ sits in the SAME folder
# as this script (matching the structure confirmed working for 03_clean_merge.py):
#   Energy Data/
#   ├── data_raw/
#   ├── data_clean/
#   ├── 03_clean_merge.py
#   └── 04_forecast.py   <- this file

FORECAST_DAYS = 90
DAY_WINDOW = 5          # +/- days around the matching calendar day, to build a stable seasonal average
TREND_LOOKBACK_DAYS = 60  # how many recent days to use when measuring the recent trend adjustment


def load_history() -> pd.DataFrame:
    path = os.path.join(CLEAN_DIR, "production_clean.csv")
    df = pd.read_csv(path)
    df["date"] = pd.to_datetime(df["date"])
    df["day_of_year"] = df["date"].dt.dayofyear
    return df


def seasonal_baseline(df_loc: pd.DataFrame, target_doy: int, metric: str) -> tuple[float, float]:
    """
    Returns (mean, std) for a given metric (e.g. 'production_kwh') across
    all historical rows whose day-of-year falls within DAY_WINDOW days of
    target_doy. Handles year-end wraparound (e.g. day 365 vs day 3).
    """
    doy_series = df_loc["day_of_year"]

    # Circular distance handles wraparound across Dec 31 -> Jan 1
    diff = (doy_series - target_doy).abs()
    diff = np.minimum(diff, 365 - diff)

    window_mask = diff <= DAY_WINDOW
    window_values = df_loc.loc[window_mask, metric]

    if len(window_values) == 0:
        # Fallback: just use overall mean/std if no matching window (shouldn't happen with 2 yrs of data)
        return df_loc[metric].mean(), df_loc[metric].std()

    return window_values.mean(), window_values.std()


def recent_trend_factor(df_loc: pd.DataFrame, metric: str) -> float:
    """
    Compares the most recent TREND_LOOKBACK_DAYS average against the
    seasonal baseline for that same calendar window last year, to get a
    simple multiplicative adjustment factor (e.g. 1.05 = running 5% above
    the typical seasonal level recently, perhaps due to a particularly
    sunny/cloudy stretch or a price shift).

    This factor is intentionally damped (sqrt) so a short noisy streak
    doesn't overwhelm the seasonal baseline -- the seasonal pattern is
    the primary signal, recent trend is a secondary nudge.
    """
    df_sorted = df_loc.sort_values("date")
    recent = df_sorted.tail(TREND_LOOKBACK_DAYS)
    recent_avg = recent[metric].mean()

    # Compare to the same calendar window one year before the most recent date
    last_date = df_sorted["date"].max()
    one_year_before_window_start = last_date - pd.Timedelta(days=365 + TREND_LOOKBACK_DAYS)
    one_year_before_window_end = last_date - pd.Timedelta(days=365)

    same_period_last_year = df_sorted[
        (df_sorted["date"] >= one_year_before_window_start) &
        (df_sorted["date"] <= one_year_before_window_end)
    ]

    if len(same_period_last_year) == 0 or same_period_last_year[metric].mean() == 0:
        return 1.0  # no adjustment possible, stay neutral

    baseline_avg = same_period_last_year[metric].mean()
    raw_factor = recent_avg / baseline_avg

    # Damp the factor toward 1.0 so it nudges rather than dominates
    damped_factor = 1 + (raw_factor - 1) * 0.5
    # Keep it within a sane range so one weird week can't blow up the forecast
    return float(np.clip(damped_factor, 0.85, 1.15))


def forecast_location(df_loc: pd.DataFrame, location_name: str) -> pd.DataFrame:
    last_date = df_loc["date"].max()
    future_dates = pd.date_range(last_date + pd.Timedelta(days=1), periods=FORECAST_DAYS, freq="D")

    production_trend = recent_trend_factor(df_loc, "production_kwh")
    revenue_trend = recent_trend_factor(df_loc, "revenue")

    rows = []
    for future_date in future_dates:
        target_doy = future_date.dayofyear

        prod_mean, prod_std = seasonal_baseline(df_loc, target_doy, "production_kwh")
        rev_mean, rev_std = seasonal_baseline(df_loc, target_doy, "revenue")

        forecast_production = prod_mean * production_trend
        forecast_revenue = rev_mean * revenue_trend

        rows.append({
            "date": future_date,
            "location": location_name,
            "forecast_production_kwh": round(forecast_production, 2),
            "forecast_production_lower": round(max(forecast_production - prod_std, 0), 2),
            "forecast_production_upper": round(forecast_production + prod_std, 2),
            "forecast_revenue": round(forecast_revenue, 2),
            "forecast_revenue_lower": round(max(forecast_revenue - rev_std, 0), 2),
            "forecast_revenue_upper": round(forecast_revenue + rev_std, 2),
        })

    forecast_df = pd.DataFrame(rows)
    print(f"  [{location_name}] trend factors -> production: {production_trend:.3f}, revenue: {revenue_trend:.3f}")
    return forecast_df


def main():
    history = load_history()

    all_forecasts = []
    for location_name in history["location"].unique():
        print(f"Forecasting {location_name}...")
        df_loc = history[history["location"] == location_name].copy()
        forecast_df = forecast_location(df_loc, location_name)
        all_forecasts.append(forecast_df)
        print(f"  -> {len(forecast_df)} days forecasted")

    combined = pd.concat(all_forecasts, ignore_index=True)
    combined = combined.sort_values(["location", "date"]).reset_index(drop=True)

    out_path = os.path.join(CLEAN_DIR, "forecast_output.csv")
    combined.to_csv(out_path, index=False)

    print(f"\nForecast saved: {out_path}")
    print(f"Forecast horizon: {combined['date'].min().date()} to {combined['date'].max().date()}")
    print("\nForecast totals by location (sum over 90 days):")
    print(combined.groupby("location")[["forecast_production_kwh", "forecast_revenue"]].sum().round(2))


if __name__ == "__main__":
    main()
