"""Combine avalanche bulletins + station weather into ONE table (one row per date x region).

    from combine import build_combined
    combined = build_combined(df, ad_df, avalanche_regions)      # df = cleaned station data (renamed columns)
    combined.to_csv("data/combined.csv", index=False)

Steps
 1. station data (hourly) -> one row per station and day, using ONLY data before the bulletin was published
 2. station -> region: for every region the k nearest stations (inverse-distance weighted mean),
    separately per variable, so e.g. snow depth only uses stations that actually measure it
 3. rolling multi-day features per region (3 / 7 day sums and means)
 4. join onto the bulletins (target = danger_max etc.)
"""
import numpy as np
import pandas as pd

from assign_regions import nearest_stations

TZ = "Europe/Vienna"

# variable -> how it is aggregated over the 24 h window of one station
STATION_AGG = {
    "air_temp_mean": ("air_temp_c", "mean"), "air_temp_min": ("air_temp_c", "min"), "air_temp_max": ("air_temp_c", "max"),
    "wind_speed_mean": ("wind_speed_ms", "mean"), "wind_gust_max": ("wind_gust_ms", "max"),
    "rel_humidity_mean": ("rel_humidity_pct", "mean"), "pressure_mean": ("pressure_hpa", "mean"),
    "sunshine_sum": ("sunshine_h", "sum"),
}


def daily_station_features(df, cutoff_hour=17):
    """Hourly station data -> one row per (date, station) as a WIDE dict: feature -> DataFrame(date x station).

    `date` is the DATE OF THE BULLETIN. Its features cover the 24 h up to (bulletin date - 1 day) at
    `cutoff_hour` local time, because the EUREGIO bulletin for day D is published at ~17:00 on D-1.
    So nothing the forecaster could not have seen leaks into the features."""
    h = df.copy()
    t = pd.to_datetime(h["timestamp"], utc=True).dt.tz_convert(TZ).dt.tz_localize(None)
    h["date"] = (t - pd.Timedelta(hours=cutoff_hour)).dt.floor("D") + pd.Timedelta(days=2)
    rad = np.deg2rad(h["wind_dir_deg"])
    h["wind_u"], h["wind_v"] = h["wind_speed_ms"] * np.sin(rad), h["wind_speed_ms"] * np.cos(rad)

    g = h.groupby(["date", "station"])
    d = g.agg(**{name: (col, fn) for name, (col, fn) in STATION_AGG.items()},
              wind_u=("wind_u", "mean"), wind_v=("wind_v", "mean"),
              snow_depth_cm=("snow_depth_cm", "last"),
              precip_sum_mm=("precip_mm", lambda x: x.sum(min_count=1)),     # NaN (not 0) if never measured
              n_hours=("timestamp", "size"))
    d = d.reset_index()
    d.loc[d.n_hours < 12, d.columns.difference(["date", "station", "n_hours"])] = np.nan   # half-empty days (data edges)

    wide = {c: d.pivot(index="date", columns="station", values=c) for c in d.columns if c not in ("date", "station", "n_hours")}
    full = pd.date_range(d.date.min(), d.date.max(), freq="D")
    wide = {c: w.reindex(full) for c, w in wide.items()}
    wide["snow_delta_24h_cm"] = wide["snow_depth_cm"].diff(1)             # snow depth change vs previous day
    wide["snow_delta_72h_cm"] = wide["snow_depth_cm"].diff(3)
    return wide


def region_weather(wide, stations, regions, k=3, min_coverage=0.3):
    """Wide station features -> DataFrame (date, region, features) using the k nearest stations per region.

    min_coverage: a station only counts for a variable if it has data on >= 30 % of the days."""
    dist = nearest_stations(stations, regions, k=len(stations))               # region, rank, station, dist_km
    frames = []
    for region, dd in dist.groupby("region"):
        dkm = dd.set_index("station").dist_km
        out = {}
        for feat, X in wide.items():
            cand = [s for s in X.columns if X[s].notna().mean() >= min_coverage]
            if not cand:
                continue
            sel = dkm.loc[cand].nsmallest(k)                                  # k nearest stations WITH data for this variable
            w = 1.0 / (sel + 1.0)                                             # inverse-distance weights (+1 km avoids /0)
            Xs = X[sel.index]
            out[feat] = (Xs.fillna(0) * w).sum(axis=1) / (Xs.notna() * w).sum(axis=1).replace(0, np.nan)
            if feat in ("snow_depth_cm", "precip_sum_mm"):
                out[f"dist_{feat.split('_')[0]}_station_km"] = round(float(sel.min()), 1)   # how far away is the data from?
        r = pd.DataFrame(out)
        r["wind_dir_deg"] = (np.rad2deg(np.arctan2(r.pop("wind_u"), r.pop("wind_v"))) % 360).round(0)
        r.insert(0, "region", region)
        frames.append(r.rename_axis("date").reset_index())
    rw = pd.concat(frames, ignore_index=True).sort_values(["region", "date"])

    # multi-day features (the windows end with the bulletin day's own features -> still no leakage)
    g = rw.groupby("region")
    rw["precip_sum_3d_mm"] = g.precip_sum_mm.transform(lambda s: s.rolling(3, min_periods=3).sum())
    rw["precip_sum_7d_mm"] = g.precip_sum_mm.transform(lambda s: s.rolling(7, min_periods=7).sum())
    rw["air_temp_mean_3d"] = g.air_temp_mean.transform(lambda s: s.rolling(3, min_periods=3).mean())
    rw["wind_gust_max_3d"] = g.wind_gust_max.transform(lambda s: s.rolling(3, min_periods=3).max())
    return rw


def season_label(d):
    """2019-12-01 -> '2019/20' ; 2020-03-01 -> '2019/20' (use it to split train/test by whole winters)."""
    y = d.dt.year.where(d.dt.month >= 8, d.dt.year - 1)
    return y.astype(str) + "/" + ((y + 1) % 100).astype(str).str.zfill(2)


def dedupe_bulletins(ad_df):
    """Make (date, region) unique. A region can appear in several bulletins of one day.
    1) if they were published at different times, the LATEST one wins (it replaces the older one);
    2) rows that are still duplicated (same publication time) are merged: highest danger level, union of problems.
    The column n_bulletins tells you where this happened."""
    d = ad_df.copy()
    d["published"] = d["published"].fillna("") if "published" in d else ""
    d = d.sort_values(["date", "region", "published"])
    d["n_bulletins"] = d.groupby(["date", "region"]).date.transform("size")
    latest = d.groupby(["date", "region"]).published.transform("max")
    d = d[d.published == latest]                                    # step 1 (rows with published = NaN are kept below)
    num = [c for c in ("danger_max", "danger_above", "danger_below", "danger_am", "danger_pm") if c in d.columns]
    join = lambda x: ";".join(sorted({v for s in x.dropna() for v in str(s).split(";") if v}))
    agg = {c: "first" for c in d.columns if c not in ("date", "region")}
    agg.update({c: "max" for c in num})
    agg.update({c: join for c in ("problems", "danger_patterns", "tendency") if c in d.columns})
    return d.groupby(["date", "region"], as_index=False).agg(agg)


def build_combined(df, ad_df, regions, k=3, cutoff_hour=17):
    """df: cleaned hourly station data, ad_df: bulletins from get_avalanche_data, regions: load_regions(...)."""
    stations = df.drop_duplicates("station")[["station", "name", "lon", "lat", "elevation_m"]]
    rw = region_weather(daily_station_features(df, cutoff_hour), stations, regions, k)
    bull = dedupe_bulletins(ad_df)
    bull["date"] = pd.to_datetime(bull["date"])
    out = bull.merge(rw, on=["date", "region"], how="left", validate="one_to_one")
    out.insert(1, "season", season_label(out["date"]))
    out["date"] = out["date"].dt.strftime("%Y-%m-%d")
    return out