# Concept: Predicting Avalanche Danger Levels in Tyrol from Weather and Snow Data

**Project:** Data Analysis Project, Foundations of Data Engineering and Analytics  
**Authors:** Dominik Glätzle, Malte Braig  
(und ne priese Claude)

## Research question

How accurately can the avalanche warning level issued by LWD Tirol be predicted from weather and snow data of the preceding days, and which factors are the key drivers of that prediction?

The danger level is the EAWS 1–5 scale (low … very high), issued per day and per one of Tyrol's warning regions. We treat this as a supervised classification/ordinal-regression problem: predict the level for region *R* on day *d* using only weather/snow information available up to the bulletin's publish time on day *d-1*.

## Why this is interesting and challenging

Avalanche danger ratings are safety-critical expert judgments, not direct physical measurements, they summarize complex, spatially varying snowpack conditions (weak layers, loading history, wind transport) that aren't observed directly. This makes the prediction task hard in several specific ways:

- **Indirect signal.** We only have point weather-station measurements, while danger depends on layered, elevation- and aspect-dependent snowpack structure that no single station captures.
- **Sparse station network in complex terrain.** Tyrol's warning regions are large and span huge altitude ranges, but usable weather stations are unevenly distributed — some regions only have a usable station tens of kilometres away.
- **Imbalanced, target.** Levels 2–3 dominate, level 5 is nearly absent (6 of 36k rows in the full dataset, 0 of 8371 in the 9-region subset we actually model with). Both the rarity and the ordinal structure (a level-3 prediction for a true level-4 day is a smaller error than predicting level-1) need to be reflected in evaluation, not just plain accuracy.
- **No existing ready-made dataset.** Nothing public links LWD Tirol's bulletin archive to historical station weather/snow data at the region-day level, we have to build the dataset ourselves before any modelling can start.

## Related work

Avalanche forecasting across the Alps follows the EAWS (European Avalanche Warning Services) framework, under which forecasters assign danger levels using standardized "avalanche problems" and "danger patterns" — both of which are present as metadata in our bulletin data and could later be used as auxiliary targets or features. Operational avalanche centers have long used statistical nearest-neighbour methods (matching today's conditions against historically similar days) as decision support, this is the most similar to what we're attempting with a learned model instead of hand-picked analogues. We are not aware of a public, ready-to-use dataset combining the LWD Tirol/EUREGIO bulletin archive with GeoSphere Austria station data at daily region-level granularity, this project's main data-engineering contribution is constructing that table correctly, in particular without leaking future information into the features.

## Data required and how we retrieve it

Two raw sources, joined on `(date, region)`:

1. **Avalanche bulletins** (danger levels, problems, danger patterns, tendency), downloaded as CAAML v6 JSON, one file per day, from the EUREGIO/lawinen.report archive (`avalanche_euregio.py`). Covers winter seasons 2019/20 through 2025/26.
2. **Hourly weather/snow station data** (temperature, wind speed/gust/direction, humidity, pressure, sunshine, precipitation, snow depth) from the GeoSphere Austria Data Hub (`klima-v2-1h`), for stations above roughly 1400–1500 m.

These are combined with `assign_regions.py` (assigning each region's day-level value as an inverse-distance-weighted average of the 3 nearest stations that have sufficient data coverage for that variable) and `combine.py` (daily aggregation, 3-/7-day rolling windows, and the bulletin join), producing `combined.csv` across all of Tyrol's warning regions (~36k region-days, 47 region codes after later subdivisions of a few regions). The pipeline is deliberately built so that the feature window for day *d* ends exactly at the bulletin's publish cutoff (17:00 local on *d-1*), confirmed, not just assumed, by re-running the pipeline and inspecting the underlying time series.

For the actual modelling dataset, `preprocessing.ipynb` then narrows this down to **9 regions** that each have a weather station located directly in/near them, to avoid relying on stations tens of kilometres away, cleans and deduplicates, and writes `final_avalanche_data.csv` (8371 rows). This is a real scope reduction, not just a renaming: it shrinks the dataset to under a quarter of its original size and to 9 of Tyrol's ~29+ warning regions. Full details, including known data-quality caveats (a mismatch between the elevation-resolved target and non-elevation-resolved weather features, region IDs that are split into sub-regions partway through the archive, and an open question about whether the 9-region dataset's weather values are truly single-station or still a multi-station blend), are documented in the accompanying datasheet.

## Methods and resources for analysis, prediction, and evaluation 
Claude war hier schon sehr creative.

- **Baselines:** majority-class prediction and a "persistence" baseline (predict yesterday's danger level) to contextualize any model's actual skill.
- **Models:** tree-based ensembles (random forest / gradient boosting) as the primary approach, since the features are tabular, non-linear interactions between fresh snow/wind/temperature are expected, and feature importances directly answer the "which factors matter" half of the research question. Ordinal or multinomial logistic regression as a simpler, more interpretable comparison point.
- **Splitting:** time-based (train on earlier seasons, evaluate on the most recent one(s)) rather than random, since rows for nearby days/regions are not independent (rolling features overlap, weather is spatially correlated).
- **Evaluation:** macro-F1 and a confusion matrix to account for class imbalance, plus an ordinal-aware metric (e.g. share of predictions within one level of the true rating) given that a one-level miss is a materially smaller error than a two-level miss. Feature importance / permutation importance to address which factors (fresh snow, temperature, wind, snow depth) drive predictions.
- **Tools:** Python, pandas, scikit-learn, all existing preprocessing code and data already live in this repository.

## Risks and limitations

- **Small, unverified sample.** Only 7 winters are available, representativeness of these specific seasons (versus unusually low-snow or exceptional avalanche winters) has not been tested.
- **Label is a forecast, not ground truth.** The target reflects expert judgment, not an observed avalanche event, a model learns to imitate forecasters, not to predict avalanches directly, and must never be used for real safety decisions.
- **Feature quality ceiling.** The lack of elevation-band-resolved weather features caps how accurately the model can realistically perform, independent of model choice.
- **Region non-stationarity, with a concrete consequence.** Several region codes were split into finer sub-regions mid-archive (2022/23 and 2025/26). 3 of the 9 regions we actually model with are affected, and right now `preprocessing.ipynb` just silently drops their post-split seasons instead of handling the rename, so those regions currently have 4 (`AT-07-14`, `AT-07-17`) and 1 (`AT-07-23`) seasons missing. Needs fixing before modelling, not just noting.
- **Scope got a lot smaller.** `final_avalanche_data.csv`, the dataset we'll actually train on, is 9 regions and 8371 rows, down from 47 regions and 36k rows. Good for data quality (each region now has a directly co-located station) but bad for how far results generalize.
- **Fresh-snow features got dropped along the way.** `snow_delta_24h_cm`/`snow_delta_72h_cm`, the direct proxies for "fresh snow" (one of our four named factors), exist in `combined.csv` but are gone from `final_avalanche_data.csv`. Either re-add them or drop "fresh snow" from the factors we claim to test.
- **Severe class imbalance** at the highest danger levels, level 5 doesn't occur at all in the 9-region data, so the model can't be evaluated on it, this needs to be reported honestly rather than optimized away.
