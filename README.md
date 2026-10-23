# Research Question:
**How accurately can the avalanche warning level issued by LWD Tirol be predicted based on weather and snow data from previous days, and which factors (fresh snow, temperature, wind, snow depth) are key to this prediction?**

- https://data.hub.geosphere.at/dataset/snowgrid_cl-v2-1d-1km -> snow data modeled (approx)
- https://dataset.api.hub.geosphere.at/app/frontend/station/historical/klima-v2-1h -> actual weather data from stations
- https://lawinen.report/bulletins/archive/tyrol/caaml/ -> LWD avalanche alerts
- 

## TODO -> 27.10
- data sheet
- concept 2 pages
- preprocessing
  - mining script

- https://dataset.api.hub.geosphere.at/app/frontend/station/historical/klima-v2-1h -> choose weather statios over 1500m
- match avalanche regions across those stations from 2019 - 2025
- snowgrid? 

## preprocessing
- step 1 (done)
  - download weather station data from 01.01.2019 - 01.05.2025 for all stations above 1400m
  - drop substations (not relevant) and tb100 (just zero values)
  - merge with metadata table for each station (elevation, region, coordinates) on station
  - rename columns to be able to understand them (e.g. air_temp, sunshine_h etc)
- step 2 
  - link stations to avalanche regions (e.g. Innsbruck, St. Anton, etc.) based on coordinates  
  - done but information not merged yet -> see table below
- step 3 (done)
  - download avalanche bulletins from 01.10.2019 - 01.05.2026
- step 4 (TODO)
  - merge avalanche bulletins with weather station data based on region and date
  - cleanup
  - drop stations with the same avalanche region (e.g. multiple stations in Innsbruck) -> keep only one station per region


|  station_name |  avalanche_region_id |
|---|---|
| Galtür  | AT-07-10  |
| Hahnenkamm-Ehrenbachhöhe | AT-07-17  |
| Patscherkofel | AT-07-15  |
| Valluga |  AT-07-07 |
| Schmirn |  AT-07-23 |
| Brunnenkogel |  AT-07-20 |
| Obergurgl |  AT-07-21 |
| Pitztaler Gletscher | AT-07-20  |
| Galzig |  AT-07-07 |
| St. Leonhard im Pitztal  | AT-07-14  |
| Hintertux | AT-07-15  |
| Ischgl-Idalpe  | AT-07-13  |
