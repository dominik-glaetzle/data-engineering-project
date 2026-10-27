# Datasheet for the Dataset: Tyrol Avalanche Danger Level and Snow/Weather Features
## By Dominik Glätzle and Malte Braig

**Project:** Data Analysis Project, Foundations of Data Engineering and Analytics
**Version / date:** v0.6, 2026-10-27
**Research question:** How accurately can the avalanche warning level issued by LWD Tirol be predicted from weather and snow data of previous days, and which factors (temperature, wind, precipitation, snow depth) are key to this prediction?

---

## 1. Motivation

**For what purpose was the dataset created?**
To predict the daily avalanche danger level (1–5) for each Tyrolean warning region based on snow and weather conditions from the preceding days. Since we found no dataset that links LWD Tirol bulletins to station weather/snow data in a single table, we built one ourselves.

---

## 2. Composition

**What do the instances represent?**
Each instance corresponds to one **(date, warning region)** pair. The dataset covers **9 regions**, each with a weather station (above ~1400 m) located in or near it: `AT-07-07, -10, -13, -14, -15, -17, -20, -21, -23`.

**How many instances are there?**
**9729 rows** (`data/final.csv`, 9 regions × 1081 days, 2019-11-16 to 2026-05-01).

**Is it all possible instances or a sample?**
It is a sample on two axes: 7 winters (season boundaries vary, roughly late Nov–early May), and 9 of Tyrol's warning regions (selected for station quality rather than randomly). Row counts per season:

| Season | First date | Last date | Rows |
|---|---|---|---|
| 2019/20 | 2019-11-16 | 2020-05-03 | 1530 |
| 2020/21 | 2020-12-04 | 2021-05-09 | 1413 |
| 2021/22 | 2021-12-01 | 2022-05-01 | 1368 |
| 2022/23 | 2022-12-10 | 2023-05-01 | 1287 |
| 2023/24 | 2023-11-25 | 2024-05-01 | 1431 |
| 2024/25 | 2024-12-07 | 2025-05-01 | 1314 |
| 2025/26 | 2025-11-29 | 2026-05-01 | 1386 |

**What data does each instance consist of?** (27 columns in `final.csv`)

*Keys and bulletin information*

| Column | Type | Description |
|---|---|---|
| `date` | date | Day the bulletin is valid for. |
| `season` | string | Winter season, e.g. `2019/20`. |
| `region` | string | Warning region ID (one of the 9 regions). |
| `region_name` | string | Region name (German), one name per region: the most recent name used in the bulletins. |
| `danger_max` | int | `= max(danger_above, danger_below, danger_am, danger_pm)`, 0 exceptions. |
| `danger_above` | int | Danger level above the elevation limit. |
| `danger_below` | float | Danger level below the limit. Missing in 0.74% of rows (72, left as `NaN`, not inferred). |
| `elev_limit` | string | `treeline`, a metres value as a string, or the sentinel `no_elev_limit` (26.2% of rows, where the bulletin gives no elevation limit). |
| `danger_am`, `danger_pm` | int | AM/PM danger level, not always equal to each other or to `danger_above`. |
| `problems` | string | `;`-separated EAWS problem types, or the sentinel `no_avalanche_problem` (642 rows). |
| `tendency` | string | `steady`, `increasing`, `decreasing`, or missing (0.13%, 13 rows). |
| `published` | timestamp | Bulletin publish time, local time with UTC offset. |
| `n_bulletins` | int | Number of bulletins covering the region that day: 1 (9719 rows) or 2 (10 rows). |
| `days_before` | int | Days between publish date and valid date: `1` for 89.4% of rows (published at 17:00 or later the evening before), `0` for 10.6% (published on the morning of the valid day). |
| `station_name` | string | Reference weather station in or near the region (e.g. `AT-07-07` → `Valluga`). |

*Weather and snow features* (units from `parameter_metadata.csv`), each covering the 24 h before the bulletin's publish cutoff:

| Column | Type | Description |
|---|---|---|
| `air_temp_mean/min/max` | float | °C (param `tl`). |
| `wind_speed_mean`, `wind_gust_max` | float | m/s (params `ff`/`ffx`). |
| `wind_dir_deg` | float | °, 0–360. A vector mean (sin/cos components averaged, then `atan2`), not a dominant sector. |
| `rel_humidity_mean` | float | % (param `rf`), clipped to `[0, 100]` in `preprocessing.ipynb` (a no-op: no out-of-range values were found). |
| `pressure_mean` | float | hPa, **station-level**, not reduced to sea level (param `p`). |
| `sunshine_sum` | float | hours (param `so_h`). |
| `snow_depth_cm` | float | cm (param `sh`), clipped to `>= 0` (no-op). |
| `precip_sum_mm` | float | mm (param `rr`), clipped to `>= 0` (no-op). |

**[TODO]** Station elevation is present in `stations_metadata.csv` but not in `final.csv` — is this intentional?

**Is any information missing from individual instances?**
`danger_below` (0.74%) and `tendency` (0.13%) are genuine missing values, while missing `elev_limit`/`problems` values were replaced with sentinel strings. 0.87% of rows contain at least one missing value.

**Are relationships between instances explicit?**
Rows share the keys `date`/`region` and are ordered in time; weather on consecutive days and in neighbouring regions is correlated, so rows are not independent.

**Errors, sources of noise, redundancies?**
- For `AT-07-14`, `AT-07-17` and `AT-07-23`, the bulletins use finer sub-region IDs (e.g. `AT-07-14-01`) in some seasons. These are mapped to the parent ID, and where several sub-regions exist for one day only one row is kept, so the danger level comes from a single sub-region. `region_name` for these three regions is a sub-region name (`Serleskamm`, `Kitzbüheler Alpen Brixental`, `Zillertaler Alpen Nordwest`).
- Danger levels are expert judgement, which includes subjective variation as well as real experiments on the mountain.

**Is the dataset self-contained?**
No, it was built from external sources, e.g. raw downloads from archives.

| Source | Used for | Access |
|---|---|---|
| LWD Tirol / EUREGIO avalanche bulletins | danger levels, problems, tendency | CAAML v6 JSON, `lawinen.report/bulletins/{date}/{date}_EUREGIO_de_CAAMLv6.json` |
| GeoSphere Austria station data, `klima-v2-1h` | temperature, wind, humidity, pressure, sunshine, precipitation, snow depth | GeoSphere Data Hub API |

---

## 3. Collection Process

**How was the data acquired?**
- **Danger levels:** produced by LWD Tirol forecasters as CAAML v6 JSON (`mine_avalanche_bulletins.py`).
- **Weather/snow:** observed hourly at GeoSphere stations (`klima-v2-1h`), aggregated to station-day and then region-day (`combine_stations_and_avalanche.py`), then filtered to 9 regions and cleaned (`preprocessing.ipynb` to `final.csv`).

**Mechanisms/procedures used for collection?**
The scripts are located in `../src/data_engineering_project/data_scripts`: `mine_avalanche_bulletins.py` downloads and parses bulletins, while `assign_stations_to_regions.py` + `combine_stations_and_avalanche.py` combine them with the station data. `combine.ipynb` runs these on `data/geosphere/station_data_cleaned.csv` + `data/avalanche/avalanche_bulletins.csv` and writes `data/combined.csv`; `preprocessing.ipynb` reads `data/combined.csv` and writes `data/final.csv`.

**Sampling strategy?** Deterministic: all bulletin days within the 7 selected winters.

**Who was involved?** Dominik Glätzle, Malte Braig

**Over what timeframe was the data collected?** 22.10.2026; the data covers seasons 2019/20–2025/26.

**Ethical review?** Not applicable (no human subjects / personal data).

---

## 4. Preprocessing / Cleaning / Labeling

- Bulletins were reduced to one row per (`date`, `region`), `danger_max = max(above, below, am, pm)`, and `elev_limit` is left empty if the bulletin gives no elevation limit. (`mine_avalanche_bulletins.py`, `combine_stations_and_avalanche.py`)
- Station values are assigned to regions by inverse-distance weighting of the nearest stations with data. (`combine_stations_and_avalanche.py`/`assign_stations_to_regions.py`)
- No unit conversions were performed; units are kept the same as GeoSphere's.
- Leakage control: the 24h feature window for day *d* ends at 17:00 local time on *d-1*, the bulletin's publish cutoff. Every bulletin in the dataset is published at or after that time.
- `preprocessing.ipynb`: maps sub-region IDs to their parent region, filters to 9 regions, drops duplicate `(region, date)` rows, sanity-clips snow/precip/humidity to valid ranges (all no-ops), drops `status` and `danger_patterns`, sets one `region_name` per region, adds `days_before`/`station_name`, and fills `elev_limit`/`problems` sentinels.


**Is the preprocessing software available?** Yes: `mine_avalanche_bulletins.py`, `assign_stations_to_regions.py`, `combine_stations_and_avalanche.py`, `combine.ipynb`, `preprocessing.ipynb`.

---

## 5. Uses

**Has the dataset been used already?** Only in this course project.

**Other possible tasks:** personal projects

**Anything that might affect future use?**
- The target is a human forecast, not an observed avalanche, so a model learns to imitate forecasters rather than predict avalanches.
- 7 winters is a small, possibly unrepresentative sample, and only 9 of Tyrol's regions are included — it may not generalize to the rest of Tyrol.
- Point station data + large regions limit how precisely the features describe where danger arises.
- Class imbalance, `danger_max`: 1 = 14.2%, 2 = 50.7%, 3 = 30.8%, 4 = 4.3%, **5 = 0 rows** — the dataset cannot be used to learn level 5.

**It should not be used for:** real avalanche safety decisions; use official bulletins and local assessment instead.

---

## 6. Distribution

**Distributed to third parties?** Only to course staff via OLAT.

**Third-party restrictions / export controls:** None known.

---

## 7. Maintenance

**Who maintains it?** The project team until the course ends (final submission 2027-01-19).

---

## Sources

- EUREGIO avalanche bulletins (CAAML v6 JSON): `lawinen.report/bulletins/{date}/{date}_EUREGIO_de_CAAMLv6.json`
- GeoSphere Austria station data, `klima-v2-1h`: https://dataset.api.hub.geosphere.at/app/frontend/station/historical/klima-v2-1h
- Gebru et al., Datasheets for Datasets: https://arxiv.org/abs/1803.09010