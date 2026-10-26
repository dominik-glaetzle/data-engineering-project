# Datasheet for the Dataset: Tyrol Avalanche Danger Level and Snow/Weather Features
## Von Dominik Glätzle and Malte Braig

**Project:** Data Analysis Project, Foundations of Data Engineering and Analytics
**Version / date:** v0.5, 2026-10-26
**Research question:** How accurately can the avalanche warning level issued by LWD Tirol be predicted based on weather and snow data from previous days, and which factors (temperature, wind, snow depth) are key to this prediction?

---

## 1. Motivation

**For what purpose was the dataset created?**
To predict the daily avalanche danger level (1–5) per Tyrolean warning region from snow and weather conditions of the preceding days. We found no dataset links LWD Tirol bulletins to station weather/snow data in one table, so we built it.

---

## 2. Composition

**What do the instances represent?**
One instance = one **(date, warning region)** pair. As of `preprocessing.ipynb` the dataset is filtered to **9 regions**, each chosen for having a weather station directly in/near it (above ~1400 m): `AT-07-07, -10, -13, -14, -15, -17, -20, -21, -23`.

**How many instances are there?**
**8371 rows** (`final_avalanche_data.csv`, 9 regions, 2019-11-16 to 2026-05-01). Supersedes `combined.csv` (36178 rows, ~47 regions, all of Tyrol), which is now just an intermediate file.

**Is it all possible instances or a sample?**
A sample on two axes: 7 winters (season boundaries vary, roughly late Nov–early May), and 9 of Tyrol's warning regions (chosen for station quality, not randomly). Row counts per season:

| Season | First date | Last date | Rows |
|---|---|---|---|
| 2019/20 | 2019-11-16 | 2020-05-03 | 1530 |
| 2020/21 | 2020-12-04 | 2021-05-09 | 1413 |
| 2021/22 | 2021-12-01 | 2022-05-01 | 1368 |
| 2022/23 | 2022-12-10 | 2023-05-01 | 1001 |
| 2023/24 | 2023-11-25 | 2024-05-01 | 1113 |
| 2024/25 | 2024-12-07 | 2025-05-01 | 1022 |
| 2025/26 | 2025-11-29 | 2026-05-01 | 924 |

**What data does each instance consist of?** (29 columns in `final_avalanche_data.csv`)

*Keys and bulletin information*

| Column | Type | Description |
|---|---|---|
| `date` | date | Day the bulletin is valid for. |
| `season` | string | Winter season, e.g. `2019/20`. |
| `region` | string | Warning region ID (one of the 9 kept regions). |
| `region_name` | string | Region name, backfilled to the latest name per region (3 of the 9 regions got renamed mid-archive — see Preprocessing). |
| `danger_max` | int | `= max(danger_above, danger_below, danger_am, danger_pm)`, 0 exceptions. |
| `danger_above` | int | Danger level above the elevation limit. |
| `danger_below` | float | Danger level below the limit. Missing in 0.86% of rows (left as `NaN`, not inferred). |
| `elev_limit` | string | `treeline`, a metres value as a string, or sentinel `no_elev_limit` (25% of rows, previously just empty). |
| `danger_am`, `danger_pm` | int | AM/PM danger level, not always equal to each other or to `danger_above`. |
| `problems` | string | `;`-separated EAWS problem types, or sentinel `no_avalanche_problem` (478 rows, previously empty). |
| `tendency` | string | `steady`, `increasing`, `decreasing`, or missing (0.12%). |
| `published` | timestamp | Bulletin publish time, now local time + UTC offset (was UTC `Z` in `combine.py`'s output). |
| `n_bulletins` | int | 1 (8362 rows) or 2 (9 rows). |
| `days_before` | int | Days between publish date and valid date: `1` for 90% of rows, `0` for 10% — worth confirming this doesn't conflict with the leakage cutoff (which uses publish *time*, not just date). |
| `station_name` | string | Single named station manually matched to each region (e.g. `AT-07-07` → `Valluga`). |

*Weather and snow features* — units from `parameter_metadata.csv` / `preprocessing.ipynb`'s `RENAME` dict:

| Column | Type | Description |
|---|---|---|
| `air_temp_mean/min/max` | float | °C (param `tl`). |
| `wind_speed_mean`, `wind_gust_max` | float | m/s (params `ff`/`ffx`). |
| `wind_dir_deg` | float | °, 0–360. A vector mean (sin/cos components averaged, then `atan2`), not a dominant sector. |
| `rel_humidity_mean` | float | % (param `rf`), clipped to `[0, 100]` in `preprocessing.ipynb` (no-op: no out-of-range values found). |
| `pressure_mean` | float | hPa, **station-level**, not sea-level-reduced (param `p`). |
| `sunshine_sum` | float | hours (param `so_h`). |
| `snow_depth_cm` | float | cm (param `sh`), clipped to `>= 0` (no-op). |
| `precip_sum_mm` | float | mm (param `rr`), clipped to `>= 0` (no-op). |
| `air_temp_mean_3d`, `wind_gust_max_3d` | float | 3-day rolling mean / max per region (from `combine.py`). |

**[TODO]** Station Höhe is in `stations_metadata.csv` but not in `final_avalanche_data.csv` — intentional?

**Is any information missing from individual instances?**
`danger_below` (0.86%) and `tendency` (0.12%) are real missing values, `elev_limit`/`problems` missing values were filled with sentinel strings instead. 

**Are relationships between instances explicit?**
Rows share keys `date`/`region`, are ordered in time, and the rolling features overlap between consecutive days -> rows are not independent.


**Errors, sources of noise, redundancies?** (TODO: maybe we need to do sth about that. do we just do the 07-14-* so all 07-14-01 and 07-14-02 get treated as 07-14?)
- **Region IDs are not stable.** `AT-07-02/04/14/17` split into sub-regions in 2022/23, `AT-07-23/26/29` in 2025/26 (29 → 47 regions in `combined.csv`). 3 of those split regions (`AT-07-14`, `AT-07-17`, `AT-07-23`) are in the 9 kept regions, causing the row-count bug above.
- 3 of the 9 kept regions (`AT-07-07`, `AT-07-10`, `AT-07-15`) also had their English name changed mid-archive, `preprocessing.ipynb` backfills to the latest name.
- Danger levels are expert judgement, which includes subjective variation and real experiments on the Mountain.

**Is the dataset self-contained?**
No, built from external sources e.g. raw downloads from archives.

| Source | Used for | Access |
|---|---|---|
| LWD Tirol / EUREGIO avalanche bulletins | danger levels, problems, patterns, tendency | CAAML v6 JSON, `lawinen.report/bulletins/{date}/{date}_EUREGIO_de_CAAMLv6.json` |
| GeoSphere Austria station data, `klima-v2-1h` | temperature, wind, humidity, pressure, sunshine, precipitation, snow depth | GeoSphere Data Hub API |

---

## 3. Collection Process

**How was the data acquired?**
- **Danger levels:** produced by LWD Tirol forecasters, as CAAML v6 JSON (`avalanche_euregio.py`).
- **Weather/snow:** observed hourly at GeoSphere stations (`klima-v2-1h`), aggregated to station-day then region-day then rolling windows (`combine.py`), then filtered to 9 regions and cleaned (`preprocessing.ipynb` to `final_avalanche_data.csv`).

**Mechanisms/procedures used for collection?**
Scripts live in `src/data_engineering_project/data-scripts/`: `avalanche_euregio.py` downloads/parses bulletins, `assign_regions.py` + `combine.py` build `combined.csv`. `preprocessing.ipynb` then reads `data/combined_cleaned.csv` and writes `final_avalanche_data.csv`.

**Sampling strategy?** Deterministic: all bulletin days within the 7 selected winters.

**Who was involved?** Dominik Glätzle, Malte Braig

**Over what timeframe was the data collected?** 22.10.2026 , data covers seasons 2019/20–2025/26.

**Ethical review?** Not applicable (no human subjects / personal data).

---

## 4. Preprocessing / Cleaning / Labeling

- Bulletins reduced to one row per (`date`, `region`), `danger_max = max(above, below, am, pm)`, `elev_limit` empty if `above == below`. (`combine.py` -> `combined.csv`)
- Station values assigned to regions via 3-nearest, inverse-distance weighting with a 30% coverage filter. (`combine.py`/`assign_regions.py`)
- Derived: 24h/72h snow-depth deltas, 3-/7-day precip sums, 3-day temp mean, 3-day gust max — computed in `combine.py`, but snow-delta/precip-rolling columns are dropped again in `preprocessing.ipynb`.
- No unit conversions, units kept same as GeoSphere.
- Leakage control: 24h feature window ends exactly at the bulletin's publish cutoff (17:00 local
- Rolling-window "degenerate" values on many seasons' first day (`wind_gust_max_3d == wind_gust_max`)
- `preprocessing.ipynb` additionally: filters to 9 regions, drops duplicate `(region, date)` rows (0 found), sanity-clips snow/precip/humidity to valid ranges (all no-ops), fills `elev_limit`/`problems` sentinels, backfills `region_name`.


**Is the preprocessing software available?** Yes: `preprocessing.ipynb`, `avalanche_euregio.py`, `assign_regions.py`, `combine.py`. (`combined_cleaned.csv` from preprocessing.ipynb is nt in the repo).

---

## 5. Uses

**Has the dataset been used already?** Only in this course project.

**Other possible tasks:** personal Projects

**Anything that might affect future use?**
- The target is a human forecast, not an observed avalanche, a model learns to imitate forecasters, not predict avalanches.
- 7 winters is a small, possibly unrepresentative sample, now narrowed to 9 of Tyrol's regions — may not generalize to the rest of Tyrol.
- Point station data + large regions limit how precisely features describe where danger arises.
- Class imbalance, `danger_max`: 1 = 13.0%, 2 = 50.3%, 3 = 32.2%, 4 = 4.6%, **5 = 0 rows** (vs. 0.02% in the full `combined.csv`) — this subset can't learn level 5 at all.

**It should not be used for:** real avalanche safety decisions, use official bulletins and local assessment.

---

## 6. Distribution

**Distributed to third parties?** Only to course staff via OLAT.

**Third-party restrictions / export controls:** None known.

---

## 7. Maintenance

**Who maintains it?** The project team until course end (final submission 2027-01-19).

---

## Sources

- EUREGIO avalanche bulletins (CAAML v6 JSON): `lawinen.report/bulletins/{date}/{date}_EUREGIO_de_CAAMLv6.json`
- GeoSphere Austria station data, `klima-v2-1h`: https://dataset.api.hub.geosphere.at/app/frontend/station/historical/klima-v2-1h
- Gebru et al., Datasheets for Datasets: https://arxiv.org/abs/1803.09010
