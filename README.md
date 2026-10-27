# Research Question:
**How accurately can the avalanche warning level issued by LWD Tirol be predicted based on weather and snow data from previous days, and which factors (temperature, wind, precipitation, snow depth) are key to this prediction?**

- https://dataset.api.hub.geosphere.at/app/frontend/station/historical/klima-v2-1h -> actual weather data from stations
- https://lawinen.report/bulletins/archive/tyrol/caaml/ -> LWD avalanche alerts

Docs: `docs/concept.md` (concept), `docs/datasheet.md` (datasheet for `final.csv`)

## preprocessing
All paths are relative to `src/data_engineering_project/`.

- step 1: weather station data
  - hourly data from GeoSphere `klima-v2-1h`, 2019-10-01 to 2026-05-01, 12 stations above ~1450 m
  - drop substations (not relevant) and tb100 (just zero values)
  - merge with metadata table for each station (elevation, coordinates) on station
  - rename columns to be able to understand them (e.g. air_temp_c, sunshine_h etc)
  - -> `data/geosphere/station_data_cleaned.csv`
- step 2: avalanche bulletins
  - `data_scripts/mine_avalanche_bulletins.py` downloads the daily EUREGIO CAAML v6 bulletins (2019-11-16 to 2026-05-01)
  - -> `data/avalanche/avalanche_bulletins.csv`
- step 3: combine (`combine.ipynb`)
  - station data -> one row per day, only using data from before the bulletin was published (24 h window ending 17:00 local on the day before)
  - assign weather values to the avalanche regions (`data_scripts/assign_stations_to_regions.py`, `data_scripts/combine_stations_and_avalanche.py`)
  - join with the bulletins on date and region
  - -> `data/combined.csv` (all Tyrolean regions)
- step 4: cleanup (`preprocessing.ipynb`)
  - keep only the 9 regions below
  - drop duplicate (region, date) rows, sanity checks / clipping for snow depth, humidity, precipitation
  - drop `status` and `danger_patterns`, add `days_before` and `station_name`
  - one region name per region (latest name)
  - fill missing `elev_limit` with `no_elev_limit` and missing `problems` with `no_avalanche_problem`
  - -> `data/final.csv` (9 regions, 9729 rows, 27 columns)

|  station_name |  avalanche_region_id |
|---|---|
| Galtür  | AT-07-10  |
| Hahnenkamm-Ehrenbachhöhe | AT-07-17  |
| Patscherkofel | AT-07-15  |
| Valluga |  AT-07-07 |
| Schmirn |  AT-07-23 |
| Obergurgl |  AT-07-21 |
| Pitztaler Gletscher | AT-07-20  |
| St. Leonhard im Pitztal  | AT-07-14  |
| Ischgl-Idalpe  | AT-07-13  |
