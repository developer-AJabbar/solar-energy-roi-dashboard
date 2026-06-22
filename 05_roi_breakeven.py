"""
05_roi_breakeven.py

Calculates ROI / payback period / break-even analysis for a hypothetical
100 kW solar installation at each location, using the actual historical
production and revenue data already calculated in script 03.

This is the "is this investment worth it" layer -- it turns raw kWh and
revenue numbers into financial decision-support metrics:

- Total install cost (based on a realistic $/W installed cost assumption,
  which differs between the US and UK markets)
- Annual revenue (from actual historical data, averaged per year)
- Simple payback period (years to recover the install cost)
- Break-even electricity price (the minimum $/kWh or GBP/kWh needed for
  the system to pay for itself within a chosen target payback window)
- 25-year lifetime revenue projection (standard solar panel warranty
  period), assuming flat future production (no degradation modeled,
  call this out plainly as a simplification)

Input:
- data_clean/production_clean.csv   (from 03_clean_merge.py)

Output:
- data_clean/roi_breakeven.csv      (one row per location, ROI summary)
- data_clean/roi_breakeven_yearly.csv (year-by-year cumulative cash flow,
  for a "payback over time" chart in Power BI)
"""

import pandas as pd
import os

CLEAN_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data_clean")
os.makedirs(CLEAN_DIR, exist_ok=True)

SYSTEM_SIZE_KW = 100
PANEL_LIFETIME_YEARS = 25          # standard solar panel warranty/lifetime assumption
TARGET_PAYBACK_YEARS = 7           # used only for the break-even price calculation below

# Installed cost assumptions (cost per watt, including panels + inverter +
# labor + permitting). These vary meaningfully by market -- US commercial-
# scale solar typically runs lower per-watt than UK due to market maturity,
# labor cost structure, and import/permitting differences.
# Figures are mid-range industry estimates for a system this size as of
# 2022-2023; treat as a clearly stated assumption, not a quoted vendor price.
INSTALL_COST_PER_WATT = {
    "phoenix_usa": 1.10,   # USD/W -- typical US commercial solar installed cost range is ~$1.00-1.30/W
    "london_uk":   1.40,   # GBP/W -- UK commercial solar typically runs higher per-watt than US
}

CURRENCY_SYMBOL = {
    "phoenix_usa": "$",
    "london_uk":   "£",
}


def load_history() -> pd.DataFrame:
    path = os.path.join(CLEAN_DIR, "production_clean.csv")
    df = pd.read_csv(path)
    df["date"] = pd.to_datetime(df["date"])
    df["year"] = df["date"].dt.year
    return df


def calculate_roi_summary(df_loc: pd.DataFrame, location_name: str) -> dict:
    install_cost_total = SYSTEM_SIZE_KW * 1000 * INSTALL_COST_PER_WATT[location_name]

    # Average annual revenue based on actual historical data (averaged across
    # however many full years of history we have -- currently 2022 + 2023)
    annual_revenue_by_year = df_loc.groupby("year")["revenue"].sum()
    avg_annual_revenue = annual_revenue_by_year.mean()
    avg_annual_production = df_loc.groupby("year")["production_kwh"].sum().mean()

    simple_payback_years = install_cost_total / avg_annual_revenue if avg_annual_revenue > 0 else None

    # Break-even price per kWh needed to hit the TARGET_PAYBACK_YEARS payback window,
    # holding production constant at the historical average
    required_annual_revenue_for_target = install_cost_total / TARGET_PAYBACK_YEARS
    breakeven_price_per_kwh = (
        required_annual_revenue_for_target / avg_annual_production
        if avg_annual_production > 0 else None
    )

    # Current actual average price per kWh (for comparison against break-even price)
    avg_actual_price_per_kwh = df_loc["revenue"].sum() / df_loc["production_kwh"].sum()

    lifetime_revenue_25yr = avg_annual_revenue * PANEL_LIFETIME_YEARS
    lifetime_net_profit_25yr = lifetime_revenue_25yr - install_cost_total
    lifetime_roi_pct = (lifetime_net_profit_25yr / install_cost_total) * 100

    return {
        "location": location_name,
        "system_size_kw": SYSTEM_SIZE_KW,
        "install_cost_per_watt": INSTALL_COST_PER_WATT[location_name],
        "total_install_cost": round(install_cost_total, 2),
        "avg_annual_production_kwh": round(avg_annual_production, 2),
        "avg_annual_revenue": round(avg_annual_revenue, 2),
        "simple_payback_years": round(simple_payback_years, 2) if simple_payback_years else None,
        "avg_actual_price_per_kwh": round(avg_actual_price_per_kwh, 4),
        "breakeven_price_per_kwh_for_7yr_payback": round(breakeven_price_per_kwh, 4) if breakeven_price_per_kwh else None,
        "lifetime_revenue_25yr": round(lifetime_revenue_25yr, 2),
        "lifetime_net_profit_25yr": round(lifetime_net_profit_25yr, 2),
        "lifetime_roi_pct": round(lifetime_roi_pct, 1),
    }


def calculate_yearly_cashflow(roi_row: dict, max_years: int = 15) -> pd.DataFrame:
    """
    Builds a year-by-year cumulative cash flow table for a payback chart:
    year 0 = -install cost, then each subsequent year adds avg_annual_revenue,
    until cumulative cash flow crosses zero (the payback point).
    """
    rows = []
    cumulative = -roi_row["total_install_cost"]
    rows.append({"location": roi_row["location"], "year_number": 0, "cumulative_cashflow": round(cumulative, 2)})

    for year_num in range(1, max_years + 1):
        cumulative += roi_row["avg_annual_revenue"]
        rows.append({
            "location": roi_row["location"],
            "year_number": year_num,
            "cumulative_cashflow": round(cumulative, 2),
        })

    return pd.DataFrame(rows)


def main():
    history = load_history()

    roi_rows = []
    yearly_frames = []

    for location_name in history["location"].unique():
        print(f"Calculating ROI for {location_name}...")
        df_loc = history[history["location"] == location_name].copy()

        roi_row = calculate_roi_summary(df_loc, location_name)
        roi_rows.append(roi_row)

        yearly_df = calculate_yearly_cashflow(roi_row)
        yearly_frames.append(yearly_df)

        sym = CURRENCY_SYMBOL[location_name]
        print(f"  Install cost: {sym}{roi_row['total_install_cost']:,.0f}")
        print(f"  Avg annual revenue: {sym}{roi_row['avg_annual_revenue']:,.2f}")
        print(f"  Simple payback: {roi_row['simple_payback_years']} years")
        print(f"  25-yr lifetime ROI: {roi_row['lifetime_roi_pct']}%")

    roi_summary_df = pd.DataFrame(roi_rows)
    roi_path = os.path.join(CLEAN_DIR, "roi_breakeven.csv")
    roi_summary_df.to_csv(roi_path, index=False)
    print(f"\nROI summary saved: {roi_path}")

    yearly_combined = pd.concat(yearly_frames, ignore_index=True)
    yearly_path = os.path.join(CLEAN_DIR, "roi_breakeven_yearly.csv")
    yearly_combined.to_csv(yearly_path, index=False)
    print(f"Yearly cash flow table saved: {yearly_path}")

    print("\nFull ROI summary:")
    print(roi_summary_df.to_string(index=False))


if __name__ == "__main__":
    main()
