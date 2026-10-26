"""Assign weather stations to avalanche warning regions (numpy/pandas only, no shapely needed).

    from assign_regions import load_regions, station_regions, nearest_stations
    regions  = load_regions("AT-07_micro-regions.geojson.json")
    stations = hourly.drop_duplicates("station")[["station", "name", "lat", "lon", "elevation_m"]]
    station_regions(stations, regions)         # 1) which region is each station in?
    nearest_stations(stations, regions, k=3)   # 2) nearest stations per region (so every region gets weather data)
"""
import json

import numpy as np
import pandas as pd

ID_KEYS = ("id", "ID", "region", "regionID", "REGION_ID", "name")
LAT0 = 47.0


def _km(lon, lat):
    """Local flat approximation for Tyrol: lon/lat -> km (accurate enough for distances up to ~100 km)."""
    return np.column_stack([np.asarray(lon, float) * 111.32 * np.cos(np.deg2rad(LAT0)),
                            np.asarray(lat, float) * 110.57])


def _polygons(geom):
    """GeoJSON geometry -> list of polygons; polygon = list of rings (outer, holes), ring = (n,2) array in km."""
    polys = [geom["coordinates"]] if geom["type"] == "Polygon" else geom["coordinates"]
    return [[_km(*np.asarray(ring)[:, :2].T) for ring in poly] for poly in polys]


def _in_ring(p, ring):
    """Even-odd Ray-Casting."""
    x, y = p
    x1, y1, x2, y2 = ring[:-1, 0], ring[:-1, 1], ring[1:, 0], ring[1:, 1]
    crosses = ((y1 > y) != (y2 > y)) & (x < (x2 - x1) * (y - y1) / np.where(y2 == y1, 1e-12, y2 - y1) + x1)
    return bool(np.count_nonzero(crosses) % 2)


def _dist_ring(p, ring):
    """Shortest distance point <-> ring outline (km)."""
    a, b = ring[:-1], ring[1:]
    ab = b - a
    t = np.clip(((p - a) * ab).sum(1) / np.where((ab ** 2).sum(1) == 0, 1e-12, (ab ** 2).sum(1)), 0, 1)
    return float(np.min(np.linalg.norm(a + t[:, None] * ab - p, axis=1)))


def point_region_distance(lon, lat, polys):
    """0 if the point lies inside the region, otherwise distance to its boundary in km."""
    p = _km([lon], [lat])[0]
    best = np.inf
    for rings in polys:
        if _in_ring(p, rings[0]) and not any(_in_ring(p, h) for h in rings[1:]):
            return 0.0
        best = min(best, min(_dist_ring(p, r) for r in rings))
    return best


def load_regions(path, prefix="AT-07"):
    """GeoJSON -> DataFrame(region, polys), only regions with the given prefix (Tyrol = AT-07)."""
    gj = json.load(open(path, encoding="utf8"))
    rows = []
    for f in gj["features"]:
        props = f.get("properties") or {}
        rid = next((props[k] for k in ID_KEYS if props.get(k)), f.get("id"))
        if rid and str(rid).startswith(prefix):
            rows.append({"region": str(rid), "polys": _polygons(f["geometry"])})
    if not rows:
        raise ValueError(f"No regions with prefix {prefix}. Example properties: {gj['features'][0].get('properties')}")
    return pd.DataFrame(rows).sort_values("region").reset_index(drop=True)


def _distance_matrix(stations, regions):
    return pd.DataFrame({r.region: [point_region_distance(s.lon, s.lat, r.polys) for s in stations.itertuples()]
                         for r in regions.itertuples()}, index=stations.station.values)


def station_regions(stations, regions):
    """Per station: region it lies in (None = in no polygon) + nearest region and distance."""
    d = _distance_matrix(stations, regions)
    out = stations[["station", "name", "elevation_m"]].copy().reset_index(drop=True)
    out["region"] = [d.columns[d.loc[s].values == 0][0] if (d.loc[s] == 0).any() else None for s in out.station]
    out["nearest_region"] = d.idxmin(axis=1).values
    out["dist_to_nearest_km"] = d.min(axis=1).round(1).values
    return out


def nearest_stations(stations, regions, k=3):
    """Per region the k nearest stations (distance polygon <-> station, km); 0 = station lies inside the region."""
    d = _distance_matrix(stations, regions)
    rows = [{"region": reg, "rank": i, "station": st, "dist_km": round(km, 1)}
            for reg in d.columns for i, (st, km) in enumerate(d[reg].nsmallest(k).items(), 1)]
    return pd.DataFrame(rows)