# Solar Energy Production & Revenue Forecasting Dashboard
**Created by Abdul Jabbar Akhtar**

A comparative analysis of solar energy viability, revenue, and investment return across two markets — Phoenix, USA and London, UK — built with a Python data pipeline and an interactive Power BI dashboard.

![Dashboard Preview](dashboard_screenshots/page1_production.png)

## 🔑 Headline Finding

Phoenix produces nearly **double** the solar energy of London, yet **London achieves a faster investment payback and a higher 25-year ROI** — driven by substantially higher UK electricity prices. The analysis shows that revenue potential depends as much on local market pricing as it does on raw solar resource availability.

| Metric | Phoenix, USA | London, UK |
|---|---|---|
| Avg. Daily Production | 455 kWh | 240 kWh |
| Avg. Capacity Factor | 18.98% | 10.01% |
| Avg. Annual Revenue | $19,516 | £25,983 |
| Simple Payback Period | 5.64 years | 5.39 years |
| 25-Year Lifetime ROI | 343.5% | 364.0% |

## 📊 Project Overview

This project models a hypothetical 100kW solar installation in each city, using two full years of real historical weather and electricity pricing data to calculate production, revenue, a 90-day forward forecast, and a full ROI / break-even analysis — then presents it all through a 5-page interactive Power BI dashboard with a built-in scenario simulator.

**Why these two cities?** Phoenix represents a high-irradiance, low-price market; London represents a low-irradiance, high-price market. Comparing them in parallel isolates the real driver of solar investment returns — and the result is genuinely counterintuitive.

## 🛠️ Tech Stack

- **Python** — data acquisition, cleaning, merging, forecasting, financial modeling (`pandas`, `requests`, `numpy`)
- **Power BI** — interactive dashboard, DAX measures, What-If parameters, data modeling

## 🗂️ Data Sources

| Data | Source |
|---|---|
| Solar irradiance & temperature | [NASA POWER API](https://power.larc.nasa.gov/) |
| US electricity prices | [U.S. EIA API](https://www.eia.gov/opendata/) (Arizona, retail price, all sectors) |
| UK electricity prices | [Ofgem Energy Price Cap](https://www.ofgem.gov.uk/energy-price-cap) (published quarterly unit rates) |

## ⚙️ Pipeline

| Script | Purpose |
|---|---|
| `01_fetch_weather_data.py` | Pulls 2 years of daily solar irradiance + temperature data for both cities via NASA POWER API |
| `02_fetch_price_data.py` | Pulls US electricity prices via EIA API; builds UK price table from Ofgem's published quarterly rates |
| `03_clean_merge.py` | Merges weather + price data per location; calculates daily production, revenue, and capacity factor for a 100kW system |
| `04_forecast.py` | Generates a 90-day forward forecast using a seasonal-naive method with confidence bands, appropriate for weather-driven data |
| `05_roi_breakeven.py` | Calculates installation cost, payback period, break-even electricity price, and 25-year lifetime ROI for each location |

Run them in order:
```bash
pip install requests pandas numpy
python scripts/01_fetch_weather_data.py
python scripts/02_fetch_price_data.py   # requires a free EIA API key
python scripts/03_clean_merge.py
python scripts/04_forecast.py
python scripts/05_roi_breakeven.py
```

## 📈 Dashboard Pages

1. **Production Overview** — daily output, capacity factor, and seasonal patterns by location
2. **Revenue & Market Price** — revenue tracked against regional electricity prices (kept in native currency — USD/GBP — to avoid misleading blended totals)
3. **Forecast** — 90-day production/revenue forecast with confidence ranges
4. **Scenario Simulator** — interactive What-If sliders for irradiance and electricity price variance, with live revenue impact
5. **ROI & Break-Even Analysis** — payback period, break-even pricing, and lifetime ROI comparison

A full written summary with screenshots is available in [`Solar_Energy_Dashboard_Summary.pdf`](Solar_Energy_Dashboard_Summary.pdf).

## 📝 Methodology Notes

- **Performance ratio** of 0.78 applied to theoretical solar output, accounting for real-world inverter and system losses (standard industry assumption range: 0.75–0.80)
- **UK electricity pricing** modeled using Ofgem's published quarterly price cap rather than a live spot price, since UK residential/small-business electricity is genuinely governed by this regulated quarterly rate — not a simplification of convenience, but the correct real-world model
- **Installed cost assumptions** ($1.10/W USA, £1.40/W UK) reflect realistic commercial solar market ranges; sourceable in more detail via [NREL cost benchmarks](https://www.nrel.gov/solar/market-research-analysis) and Solar Energy UK
- **Forecast method** uses a seasonal-naive baseline (same calendar day, prior years) rather than linear regression, since solar output is dominated by seasonal patterns rather than short-term momentum

## 👤 About This Project

Built as a portfolio project demonstrating end-to-end data analysis capability — from raw API data through Python cleansing and financial modeling, to a polished, decision-ready BI dashboard. Companion piece to a [Bitcoin Mining Profitability Dashboard](#) applying the same methodology to crypto/energy economics.

---

*Questions or interested in similar analysis for your own market or asset? Feel free to reach out.*
