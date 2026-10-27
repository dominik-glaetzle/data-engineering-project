# Concept: Predicting Avalanche Danger Levels in Tyrol from Weather and Snow Data

**Project:** Data Analysis Project, Foundations of Data Engineering and Analytics  
**Authors:** Dominik Glätzle, Malte Braig  

## Research question

How accurately can the avalanche warning level issued by LWD Tirol be predicted from weather and snow data of the preceding days, and which factors are the key drivers of that prediction?

The danger level is the EAWS 1–5 scale (low … very high), issued per day and per one of Tyrol's warning regions. We treat this as a supervised classification/ordinal-regression problem: predict the level for region *R* on day *d* using only weather/snow information available up to the bulletin's publish time on day *d-1*.

## Why this is interesting and challenging

Avalanche danger ratings are safety-critical expert judgments, not direct physical measurements, they summarize complex, spatially varying snowpack conditions (weak layers, loading history, wind transport) that aren't observed directly. This makes the prediction task hard in several specific ways:

- **Indirect signal.** We only have point weather-station measurements, while danger depends on layered, elevation- and aspect-dependent snowpack structure that no single station captures.
- **Sparse station network in complex terrain.** Tyrol's warning regions are large and span huge altitude ranges, but usable weather stations are unevenly distributed — some regions only have a usable station tens of kilometres away.
- **Imbalanced, target.** Levels 2–3 dominate, level 5 does not occur at all in the 9729 rows we model with. Both the rarity and the ordinal structure (a level-3 prediction for a true level-4 day is a smaller error than predicting level-1) need to be reflected in evaluation, not just plain accuracy.
- **No existing ready-made dataset.** Nothing public links LWD Tirol's bulletin archive to historical station weather/snow data at the region-day level, we have to build the dataset ourselves before any modelling can start.

## Related work

Avalanche forecasting across the Alps follows the EAWS (European Avalanche Warning Services) framework, under which forecasters assign danger levels using standardized "avalanche problems" and "danger patterns". The avalanche problems are part of our dataset and could be used as auxiliary targets or features. Operational avalanche centers have long used statistical nearest-neighbour methods (matching today's conditions against historically similar days) as decision support, this is the most similar to what we're attempting with a learned model instead of hand-picked analogues. We are not aware of a public, ready-to-use dataset combining the LWD Tirol/EUREGIO bulletin archive with GeoSphere Austria station data at daily region-level granularity, this project's main data-engineering contribution is constructing that table correctly, in particular without leaking future information into the features.

## Data required and how we retrieve it

Two raw sources, joined on `(date, region)`:

1. **Avalanche bulletins** (danger levels, problems, tendency), downloaded as CAAML v6 JSON, one file per day, from the EUREGIO/lawinen.report archive (`mine_avalanche_bulletins.py`). Covers winter seasons 2019/20 through 2025/26.
2. **Hourly weather/snow station data** (temperature, wind speed/gust/direction, humidity, pressure, sunshine, precipitation, snow depth) from the GeoSphere Austria Data Hub (`klima-v2-1h`), for 12 stations above roughly 1450 m.

These are combined in `combine.ipynb` with `assign_stations_to_regions.py` and `combine_stations_and_avalanche.py`: hourly station data is aggregated to one value per day and region, then joined onto the bulletins, producing `combined.csv` across all of Tyrol's warning regions (36,178 region-days). The pipeline is deliberately built so that the feature window for day *d* ends exactly at the bulletin's publish cutoff (17:00 local on *d-1*), confirmed, not just assumed, by re-running the pipeline and inspecting the underlying time series; every bulletin in the dataset is published at or after that cutoff.

For the actual modelling dataset, `preprocessing.ipynb` then narrows this down to **9 regions** that each have a weather station located in or near them, cleans and deduplicates, and writes `data/final.csv` (9729 rows, 27 columns). This is a real scope reduction: it shrinks the dataset to about 27% of its original size and to 9 of Tyrol's warning regions. Full details, including known data-quality caveats (e.g. a mismatch between the elevation-resolved target and non-elevation-resolved weather features), are documented in the accompanying datasheet.

## Methods and resources for analysis, prediction, and evaluation 

- **Baselines:** majority-class prediction and a "persistence" baseline (predict yesterday's danger level) to contextualize any model's actual skill.
- **Models:** tree-based ensembles (random forest / gradient boosting) as the primary approach, since the features are tabular, non-linear interactions between precipitation/snow depth/wind/temperature are expected, and feature importances directly answer the "which factors matter" half of the research question. Ordinal or multinomial logistic regression as a simpler, more interpretable comparison point.
- **Splitting:** time-based (train on earlier seasons, evaluate on the most recent one(s)) rather than random, since rows for nearby days/regions are not independent (weather is autocorrelated in time and spatially correlated).
- **Evaluation:** macro-F1 and a confusion matrix to account for class imbalance, plus an ordinal-aware metric (e.g. share of predictions within one level of the true rating) given that a one-level miss is a materially smaller error than a two-level miss. Feature importance / permutation importance to address which factors (temperature, wind, precipitation, snow depth) drive predictions.
- **Tools:** Python, pandas, all existing preprocessing code and data already live in this repository.

## Risks and limitations

- **Small, unverified sample.** Only 7 winters are available, representativeness of these specific seasons (versus unusually low-snow or exceptional avalanche winters) has not been tested.
- **Label is a forecast, not ground truth.** The target reflects expert judgment, not an observed avalanche event, a model learns to imitate forecasters, not to predict avalanches directly, and must never be used for real safety decisions.
- **Feature quality ceiling.** The lack of elevation-band-resolved weather features caps how accurately the model can realistically perform, independent of model choice.
- **Small scope.** `final.csv`, the dataset we'll actually train on, covers 9 regions and 9729 rows. Each region has a weather station in or near it, which is good for data quality but limits how far results generalize to the rest of Tyrol.
- **No direct fresh-snow measurement.** Fresh snow can only be approximated through `precip_sum_mm` and day-to-day changes in `snow_depth_cm`.
- **Severe class imbalance** at the highest danger levels, level 5 doesn't occur at all in the 9-region data, so the model can't be evaluated on it, this needs to be reported honestly rather than optimized away.
