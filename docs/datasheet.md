# Datasheet for the Dataset: Tyrol Avalanche Danger Level and Snow/Weather Features
## Von Dominik Glätzle and Malte Braig

**Project:** Data Analysis Project, Foundations of Data Engineering and Analytics
**Version / date:** v0.3, 2026-10-23
**Research question:** How accurately can the avalanche warning level issued by LWD Tirol be predicted based on weather and snow data from previous days, and which factors (fresh snow, temperature, wind, snow depth) are key to this prediction?

---

## 1. Motivation

**For what purpose was the dataset created?**
To predict the daily avalanche danger level (1–5) per Tyrolean warning region from snow and weather conditions of the preceding days. The task is supervised classification/ordinal regression. We couldn't find a dataset that links the LWD Tirol bulletins to snow and station weather data in one table, so we build it.

---

## 2. Composition

**What do the instances represent?**
One instance = one **(date, warning region)** pair in the Tyrol bulletin area, during the winter season. Each row holds the danger level issued for that date and region, plus weather and snow features for that region. Regions use IDs `AT-07-01` … `AT-07-29`, plus finer sub-region IDs introduced later (e.g. `AT-07-02-01`) — see the region-stability finding below; region IDs are **not stable across the full date range**.

**How many instances are there?**
36178 rows (`combined.csv`, checked directly: `wc -l` minus the header), spanning dates 2019-11-16 to 2026-05-01. Rows use **47 distinct region codes**, not 29 — see the region-stability finding below; 29 is only the count of "base" regions used in the earliest seasons.

**Is it all possible instances or a sample?**
A sample: 7 winters (seasons `2019/20` through `2025/26`) from a larger bulletin archive. Season boundaries are **not fixed** — they vary per year and were taken as-is from the data:

| Season | First date | Last date | Rows | Unique days |
|---|---|---|---|---|
| 2019/20 | 2019-11-16 | 2020-05-03 | 4929 | 170 |
| 2020/21 | 2020-12-04 | 2021-05-09 | 4553 | 157 |
| 2021/22 | 2021-12-01 | 2022-05-01 | 4408 | 152 |
| 2022/23 | 2022-12-10 | 2023-05-01 | 5148 | 143 |
| 2023/24 | 2023-11-25 | 2024-05-01 | 5724 | 159 |
| 2024/25 | 2024-12-07 | 2025-05-01 | 5256 | 146 |
| 2025/26 | 2025-11-29 | 2026-05-01 | 6160 | 154 |

Roughly "late Nov to early May" each year, but start dates range from 2023-11-25 to 2022-12-10 — no single cutoff applies to all seasons. Representativeness was not tested; 7 winters will not cover all snowpack types (e.g. very low-snow or exceptional avalanche winters).

**What data does each instance consist of?** (35 columns)

*Keys and bulletin information*

| Column | Type | Description |
|---|---|---|
| `date` | date | Day the bulletin is valid for (e.g. 2019-11-16). |
| `season` | string | Winter season, e.g. `2019/20`. |
| `region` | string | Warning region ID, e.g. `AT-07-01`. |
| `region_name` | string | Region name, e.g. "Allgäuer Alpen". |
| `status` | string | Row status. Checked on the full 36178 rows: the only value present is `ok` (100%). No other status occurs in this extract, so other values (e.g. a missing-bulletin marker) are either not used by the pipeline or never triggered in these 7 seasons — not something we can confirm from the data alone. |
| `danger_max` | int | Highest danger level (1–5) for this region and date. **Confirmed:** `danger_max = max(danger_above, danger_below, danger_am, danger_pm)` exactly, with zero exceptions over all 36178 rows. Earlier text claimed `danger_max` always equals `danger_above` — that only held in the small sample; over the full data it's true for 32403/36178 rows (89.6%). **Candidate target.** |
| `danger_above` | int | Danger level above the elevation limit. |
| `danger_below` | float | Danger level below the elevation limit. Missing in 232/36178 rows (0.64%) — stored as float because of these. In the remaining rows, `danger_below` equals `danger_above` in 11955 rows, is lower in 20216, and higher in 3775; TODO: confirm with the team why `danger_below` is occasionally missing (e.g. regions with no band below treeline) rather than guessing. |
| `elev_limit` | string | Elevation limit between the two bands. **Resolved:** empty in 10623/36178 rows (29.4%), and empty *exactly* when `danger_above == danger_below` (i.e. no elevation split that day — single danger level for the whole region). When non-empty it is either the literal string `treeline` (8081 rows) or a number given as a **string**, e.g. `"2200"` (17474 rows across values 1000–3000, in 100 m steps) — plausibly metres above sea level, consistent with Alpine terrain, but the unit is not stated anywhere in the data itself. |
| `danger_am`, `danger_pm` | int | Danger level in the morning / afternoon. Not always equal: `danger_am == danger_pm` in 32812/36178 rows (90.7%); `danger_am == danger_above` in 32749 (90.5%); `danger_pm == danger_above` in 32395 (89.5%). Exact AM/PM cut-off time is not in the data — still a TODO. |
| `problems` | string | Avalanche problems, `;`-separated. **Full vocabulary found** (6 values, standard EAWS problem types): `wind_slab` (21204 rows), `persistent_weak_layers` (15589), `gliding_snow` (8911), `wet_snow` (8337), `new_snow` (2667), `favourable_situation` (72). Empty in 3230 rows (8.9%). |
| `danger_patterns` | string | Danger patterns (EAWS/LWD codes), `;`-separated. **Codes found:** DP6 (22665), DP1 (8958), DP2 (8906), DP10 (7834), DP7 (3923), DP4 (2840), DP5 (1770), DP3 (1147), DP8 (969), DP9 (345) — all ten EAWS "Dangerous Patterns" codes occur. Empty in 2020 rows (5.6%). [TODO: we have not independently verified the DP1–DP10 → textual-meaning mapping; cite the EAWS documentation rather than assume.] |
| `tendency` | string | Expected trend. **Full vocabulary:** `steady` (28884, 79.8%), `increasing` (4110, 11.4%), `decreasing` (3134, 8.7%), empty (50, 0.14%). |
| `published` | timestamp | Publication time of the bulletin (UTC). **Not a single fixed time.** 1089 distinct timestamps occur. Most rows cluster at `16:00:00Z` (24230, 67%) or `15:00:00Z` (6975, 19%, probably the CET/CEST offset flipping the UTC hour) — consistent with "evening before the valid date". But ~13% of rows (4750) are published at other hours (07:00, 06:00, 17:00, 18:00, 08:00, 05:00, 09:00, …), some with odd second-level precision (e.g. `18:06:01Z`). [TODO: confirm with the team whether these are genuine bulletin amendments or an artifact of how/when the archive was scraped — needed to be sure no bulletin used is published *after* the date it's assigned to.] |
| `n_bulletins` | int | Number of bulletins found for that date. **Resolved:** 36145 rows have 1, 33 rows have 2; no row has more than 2. [TODO: confirm how the 33 two-bulletin days were merged into a single row — which one "wins".] |

*Weather and snow features* (units checked against observed value ranges over all 36178 rows; still **not stated anywhere in the data itself**, so treat as plausible, not confirmed)

| Column | Type | Description |
|---|---|---|
| `air_temp_mean`, `air_temp_min`, `air_temp_max` | float | Air temperature (probably °C — Alpine daily values, plausible range). |
| `wind_speed_mean`, `wind_gust_max` | float | Mean wind speed and maximum gust. [TODO: unit, m/s or km/h — value range alone can't disambiguate this.] |
| `wind_dir_deg` | float | Wind direction in degrees, range is exactly 0–360 over all rows (consistent with a compass bearing). [TODO: still can't tell from the data whether it's a circular mean or the dominant sector.] |
| `rel_humidity_mean` | float | Mean relative humidity (probably %). |
| `pressure_mean` | float | Mean air pressure. Full-data range is **678–866** (not 775–790 as in the small sample). This range is far below sea-level pressure (~950–1050 hPa), confirming it is **station-level (not sea-level-reduced) pressure**, consistent with Alpine station altitudes. |
| `sunshine_sum` | float | Sunshine duration. Full-data range is 0–13.5, consistent with **hours** (max possible daylight hours), not minutes. |
| `snow_depth_cm` | float | Snow depth in cm. Range 0–318.7 cm, plausible for Alpine stations. |
| `dist_snow_station_km` | float | Distance (km) between the region and the station that supplies the snow value. Full-data range is **0–93.4 km** — much wider than the 2–32 km seen in the small sample. A 93 km mismatch between a region and its assigned station is a real data-quality concern, not just a sample artifact. |
| `precip_sum_mm` | float | Precipitation sum in mm. |
| `dist_precip_station_km` | float | Distance (km) to the station that supplies the precipitation value. Same 0–93.4 km range as `dist_snow_station_km`. |
| `snow_delta_24h_cm`, `snow_delta_72h_cm` | float | Change in snow depth over 24 h / 72 h (cm). Can be negative (settling, melt). Used as the fresh-snow proxy. **Verified exactly:** for a given region, `snow_delta_24h_cm` on date `d` equals `snow_depth_cm(d) - snow_depth_cm(d-1)` (checked to float precision on consecutive days) — see the leakage caveat below. |
| `precip_sum_3d_mm`, `precip_sum_7d_mm` | float | Precipitation sum over 3 / 7 days. |
| `air_temp_mean_3d` | float | Mean air temperature over 3 days. |
| `wind_gust_max_3d` | float | Maximum gust over 3 days. |

**[RESOLVED, and important] Which day each weather/snow value covers — likely leakage.**
`snow_delta_24h_cm` on date `d` was verified to equal `snow_depth_cm(d) − snow_depth_cm(d−1)`, which means `snow_depth_cm` for row `date = d` is the snow depth **measured on `d` itself**, not `d−1`. But `published` shows the bulletin for date `d` is issued the evening *before* `d` (mostly 15:00–16:00 UTC on `d−1`). So as currently joined, `snow_depth_cm`, and by extension `snow_delta_24h_cm`/`snow_delta_72h_cm`, describe conditions that are **not yet known at the time the forecaster actually wrote the bulletin** — the forecast target would be paired with same-day (not prior-day) snow data. This is a likely **leakage bug** for the stated research question ("predicted ... from ... previous days"), not just a documentation gap. **TODO before modelling: either confirm `snow_depth_cm` is actually a morning-of measurement available before the (evening-before) publish time in practice, or shift all weather/snow features back by one day relative to the bulletin date.**

[TODO: explain how a value is assigned to a region (nearest station? station inside region? average?). The distance columns suggest one nearest station per variable, and the 0–93.4 km range above shows the assignment isn't always a close match.]

[TODO: add the elevation of the stations used (not in the table, but relevant because bulletin regions span large altitude ranges).]

**Is there a label or target?**
Yes: the danger level on the EAWS five-level scale (1 low … 5 very high). The table offers several: `danger_max`, `danger_above`, `danger_below`, `danger_am`, `danger_pm`. [TODO: decide and state the target used for modelling, probably `danger_max`.] All come from the bulletin.

**Is any information missing from individual instances?**
Probably. `danger_below` is stored as float, and stations have missing days. [TODO: report the missing-value share per column and how it was handled.]

**Are relationships between instances explicit?**
Rows share the keys `date` and `region`. Rows are ordered in time, neighbouring regions have similar weather, and the rolling features (`_3d`, `_7d`, `snow_delta_*`) overlap between consecutive days. Rows are therefore not independent.

**Recommended data splits?**
Split by **time** (e.g. train on earlier winters, test on the last winter, or by season blocks) rather than randomly, to avoid leakage between adjacent days. [TODO: fix the final split.]

**Errors, sources of noise, redundancies?**
- **Station-to-region mismatch.** Weather and snow values come from stations that are **0–93.4 km** away from the region (`dist_*_station_km`, full data — wider than the 2–32 km seen in the small sample), while bulletin regions are large and span wide altitude ranges. A single, possibly distant station may not represent conditions where the danger arises.
- **Redundant columns.** `danger_max = max(danger_above, danger_below, danger_am, danger_pm)` exactly (verified on all rows) — fully derivable, not independent information. Despite this, `danger_max` only equals `danger_above` in 89.6% of rows (not "all rows", as previously written from the small sample). Rolling features overlap with the daily ones by construction.
- **Region definitions are NOT stable across seasons — resolved, and this is a real issue.** Several region codes were split into finer sub-regions partway through the archive:
  - `AT-07-02` → `AT-07-02-01` / `AT-07-02-02`, `AT-07-04` → `AT-07-04-01` / `AT-07-04-02`, `AT-07-14` → `AT-07-14-01…05`, `AT-07-17` → `AT-07-17-01` / `AT-07-17-02`: all split starting season **2022/23**.
  - `AT-07-23` → `AT-07-23-01` / `AT-07-23-02`, `AT-07-26` → `AT-07-26-01` / `AT-07-26-02`, `AT-07-29` → `AT-07-29-01` / `AT-07-29-02` / `AT-07-29-03`: all split starting season **2025/26**.
  - This is why the region count grows from 29 (2019/20–2021/22) to 47 overall. Any model or split that treats `region` as a stable categorical key across seasons must account for these splits (and the pre-split region's rows aren't simply replaceable by one of its successors).
  - Minor related issue: `region_name` for `AT-07-01` changes from `"Allgäuer Alpen"` to `"Allgäuer Alpen Ost"` partway through the archive, and `region_name` for `AT-07-02` contains non-breaking-space characters (U+00A0) instead of normal spaces — a string-matching trap if `region_name` is ever joined on or displayed naively.
- **Irregular bulletins.** 33/36178 days have 2 bulletins issued instead of 1 (`n_bulletins`); [TODO: confirm merge rule for these]. `status` is `ok` for 100% of rows in this extract — no missing-bulletin rows observed, so that case may simply not occur in the seasons pulled, or rows with other statuses were filtered out before being saved.
- **Rolling-window boundary behaviour is inconsistent across seasons.** At the very first bulletin day of season 2019/20 (the earliest season in the archive), every region's `wind_gust_max_3d` equals `wind_gust_max`, i.e. the "3-day" window only had 1 real day of data — expected, since there's no earlier data in the archive at all. The same degenerate pattern (window = single day) also appears for most region-seasons from 2020/21 through 2024/25. But in season **2025/26**, this never happens — every region, including brand-new split sub-regions that had never appeared before, already has a full, non-degenerate 3-day window on its first day. This suggests the rolling-window computation changed between seasons (e.g. pulling from continuous calendar-day station data only for the newest season), which would mean rolling features are **not computed the same way for all seasons**. [TODO: confirm with whoever wrote the feature pipeline whether this is a real version difference or an artifact of how/when each season's data was pulled.]
- Danger levels are expert judgement, which includes subjective variation.

**Is the dataset self-contained?**
No. It was built from external sources. Their availability over time is not guaranteed by us, so the raw downloads should be archived [TODO: confirm we store them].

| Source | Used for | Access | Restrictions |
|---|---|---|---|
| LWD Tirol avalanche bulletins, via lawinen.report | danger levels, problems, patterns, tendency | [TODO: exact URL/format used for the 2019+ bulletins] | [TODO: check terms; bulletins are issued by Land Tirol / LWD Tirol] |
| GeoSphere Austria station data (candidate: `klima-v2-1d`) | temperature, wind, humidity, pressure, sunshine, precipitation, snow depth | Data Hub API [TODO: confirm dataset and station list] | [TODO: check licence on the dataset page] |
| SNOWGRID-CL v2.1 (GeoSphere Austria), DOI 10.60669/fsxx-6977 | [TODO: **not visible in the sample.** No column mentions it; snow depth appears to come from stations. Remove this row if it is not used, or state which columns derive from it.] | Data Hub API | CC BY 4.0 |

**Confidential data?** No. All sources are public.

**Offensive or distressing content?** No. Bulletin texts concern avalanche hazard only.

**Does the dataset relate to people?** No. No personal data is included.

---

## 3. Collection Process

**How was the data acquired?**

- **Danger levels:** *produced by humans*. LWD Tirol forecasters issue the bulletin. According to `published`, the bulletin for a day is published in the evening of the previous day (about 17:00 local time in the sample). [TODO: format of the source files (CAAML version, XML/JSON) and the exact URL.]
- **Weather and snow features:** *directly observed* at stations of the GeoSphere Austria network [TODO: confirm dataset and station selection], then aggregated by us (3-day and 7-day sums/means/maxima, 24 h and 72 h snow depth changes).
- **SNOWGRID-CL:** [TODO: say whether it was used. If yes: modelled, not measured; daily snow depth and snow water equivalent on a 1 × 1 km grid; method in Olefs et al. 2020, *Atmosphere* 11(12), 1330.]

**Mechanisms/procedures used for collection?**
Software: Python script(s) [TODO: repo link] that
1. download and parse the bulletins;
2. request station data from the Data Hub API;
3. assign stations to regions [TODO: method];
4. compute the derived and rolling features;
5. join everything on (`date`, `region`).

**Sampling strategy?**
Deterministic: all bulletin days within the selected winters. [TODO: confirm winters and season start/end.]

**Who was involved?**
The student team (Dominik Glätzle, Malte Braig). No crowdworkers.

**Over what timeframe was the data collected?**
Downloaded in [TODO: date] (October 2026). The data covers [TODO: seasons, first seen: 2019/20]. The creation timeframe of the data differs from the download time.

**Ethical review?** Not applicable (no human subjects).

*Questions about data from individuals: not applicable.*

---

## 4. Preprocessing / Cleaning / Labeling

**Was any preprocessing done?** Yes. Known from the table:

- Bulletins reduced to one row per (`date`, `region`) with the ratings split into `_above`/`_below` and `_am`/`_pm`. Confirmed: `danger_max = max(danger_above, danger_below, danger_am, danger_pm)`; `elev_limit` is empty exactly when `danger_above == danger_below`. [TODO: describe rule for the 33 two-bulletin days.]
- Station values assigned to regions with recorded distance. [TODO: describe method and any distance limit.]
- Derived features: 24 h / 72 h snow depth changes, 3-day and 7-day precipitation sums, 3-day mean temperature and 3-day maximum gust.
- [TODO: unit conversions, e.g. wind speed.]
- [TODO: missing values: method (interpolation limits, drop, flag).]
- [TODO: handling at the start of a season, when 3-day/7-day windows are incomplete. In the first sample rows `wind_gust_max_3d` equals `wind_gust_max`.]
- [TODO: out-of-season days (no bulletin) removal.]
- **Leakage control:** [TODO: state exactly which days feed each feature and confirm that nothing from after the publication time of the bulletin is used.]

**Was the raw data saved?** [TODO: Yes, in `data/raw/`, confirm.]

**Is the preprocessing software available?** [TODO: repo link; Jupyter notebook submitted via OLAT.]

---

## 5. Uses

**Has the dataset been used already?** Only in this course project.

**Other possible tasks:** danger level forecasting for the next day; analysis of fresh-snow thresholds by region; predicting avalanche problems or danger patterns from the weather columns; study of bulletin consistency.

**Anything that might affect future use?**
- The target is a human forecast, not an observed avalanche event. A model learns to imitate forecasters, not to predict avalanches.
- A limited number of winters is a small and possibly unrepresentative sample; results may not transfer to other seasons or later region definitions.
- Point station data and large regions limit how precisely features describe conditions where danger arises. Wind-driven loading and weak layers in the snowpack are only partly captured.
- Class imbalance, confirmed on `danger_max`: level 1 = 17.5%, 2 = 50.7%, 3 = 28.1%, 4 = 3.65%, 5 = 0.02% (6 rows total).

**Tasks the dataset should not be used for:**
**Not for real avalanche safety decisions.** Official bulletins and local assessment must be used.

---

## 6. Distribution

**Distributed to third parties?** Only to course staff via OLAT (CSV plus notebooks) [TODO: confirm if also published].

**How / DOI?** File upload; no DOI.

**Licence / terms of use:**
[TODO: confirm licence of each source.] SNOWGRID-CL (if used) is CC BY 4.0, so attribution to GeoSphere Austria is required. Station data and bulletin terms: [TODO: check]. Until clarified, redistribute only the derived table with source attribution, not the raw files.

**Third-party restrictions / export controls:** None known.

---

## 7. Maintenance

**Who maintains it?** The project team until course end (final submission 19 Jan 2027). [TODO: contact e-mail]

**Erratum?** None.

**Will it be updated?** No planned updates after submission.

**Older versions?** Versions are tracked in the project repository [TODO: link]. v0.1 described the plan; v0.2 describes the sample table.

**Can others extend it?** Yes: the scripts can be rerun with other date ranges or regions, provided source terms are respected.

---

## Sources

- Avalanche bulletin archive, Tyrol: https://lawinen.report/bulletins/archive/tyrol/caaml/ [TODO: confirm this is where the 2019+ bulletins come from]
- Station data v2, 1 d (`klima-v2-1d`): https://data.hub.geosphere.at/en/dataset/klima-v2-1d [TODO: confirm]
- SNOWGRID Klima v2.1, GeoSphere Austria Data Hub (if used): https://data.hub.geosphere.at/dataset/snowgrid_cl-v2-1d-1km (DOI 10.60669/fsxx-6977)
- Olefs et al. (2020), *Atmosphere* 11(12), 1330 (if SNOWGRID is used): https://doi.org/10.3390/atmos11121330
- Gebru et al., Datasheets for Datasets: https://arxiv.org/abs/1803.09010