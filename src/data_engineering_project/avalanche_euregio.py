"""Avalanche bulletins Tyrol (CAAML v6 JSON, EUREGIO, lawinen.report) -> pandas DataFrame.

    from avalanche_euregio import get_avalanche_data
    df = get_avalanche_data("01-12-2019", "30-04-2020")      # dd-mm-yyyy, inclusive

One file per day contains ALL regions, so we loop over days, not over regions:
    https://lawinen.report/bulletins/YYYY-MM-DD/YYYY-MM-DD_EUREGIO_de_CAAMLv6.json
Output: one row per date x region (AT-07-01 ... AT-07-29).
"""
import datetime as dt
import json
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pandas as pd
import requests

URL = "https://lawinen.report/bulletins/{d}/{d}_EUREGIO_de_CAAMLv6.json"
LEVELS = {"low": 1, "moderate": 2, "considerable": 3, "high": 4, "very_high": 5}
# non-numeric values seen in the data: "no_snow" (no snow cover), "no_rating"
PERIOD = {"all_day": "all", "earlier": "am", "later": "pm"}


def _download(day, cache: Path):
    """Return the raw JSON text of one day (from cache or web); None if there is no bulletin (404)."""
    path = cache / f"{day}.json"
    if path.exists():
        return path.read_text(encoding="utf8")
    for i in range(4):                                    # retry with backoff
        try:
            r = requests.get(URL.format(d=day), timeout=60)
            if r.status_code == 404:
                return None
            r.raise_for_status()
            path.write_text(r.text, encoding="utf8")
            return r.text
        except requests.RequestException:
            time.sleep(2 ** i)
    return "ERROR"                                        # network problem, not "no bulletin"


def _as_list(x):
    """The format varies between years: a field can be missing, a single object or a list."""
    return [] if not x else x if isinstance(x, list) else [x]


def _parse(text, day, prefix="AT-07"):
    """One day of CAAML v6 JSON -> list of rows (one per region)."""
    rows = []
    for b in json.loads(text).get("bulletins", []):
        regions = [r for r in _as_list(b.get("regions")) if r["regionID"].startswith(prefix)]
        if not regions:
            continue
        # ratings: (value 1-5, band above/below/all, treeline or elevation in m, period all/am/pm)
        ratings, status = [], "ok"
        for r in _as_list(b.get("dangerRatings")):
            if r["mainValue"] not in LEVELS:              # e.g. 'no_snow' / 'no_rating' -> no danger level
                status = r["mainValue"]
                continue
            el = r.get("elevation") or {}
            band, limit = ("above", el["lowerBound"]) if "lowerBound" in el else \
                          ("below", el["upperBound"]) if "upperBound" in el else ("all", None)
            ratings.append((LEVELS[r["mainValue"]], band, limit, PERIOD.get(r.get("validTimePeriod"), "all")))
        top = lambda f: max([v for v, band, lim, per in ratings if f(band, per)], default=None)
        limits = [lim for _, _, lim, _ in ratings if lim]
        problems = sorted({p["problemType"] for p in _as_list(b.get("avalancheProblems")) if p.get("problemType")})
        patterns = ((b.get("customData") or {}).get("LWD_Tyrol") or {}).get("dangerPatterns") or []
        tendency = ";".join(t["tendencyType"] for t in _as_list(b.get("tendency")) if t.get("tendencyType"))
        for reg in regions:
            rows.append({
                "date": day, "region": reg["regionID"], "region_name": reg.get("name"),
                "status": "ok" if ratings else status,        # 'ok', 'no_snow', 'no_rating'
                "danger_max": top(lambda band, per: True),
                "danger_above": top(lambda band, per: band in ("above", "all")),
                "danger_below": top(lambda band, per: band in ("below", "all")),
                "elev_limit": limits[0] if limits else None,          # 'treeline' or metres (as text)
                "danger_am": top(lambda band, per: per in ("am", "all")),
                "danger_pm": top(lambda band, per: per in ("pm", "all")),
                "problems": ";".join(problems),
                "danger_patterns": ";".join(patterns),
                "tendency": tendency or None,
                "published": b.get("publicationTime"),
            })
    return rows


def get_avalanche_data(von, bis, cache="data/cache_bulletins", workers=4):
    """Bulletins von..bis (dd-mm-yyyy or date, inclusive) -> DataFrame (date x region).
    Days without a bulletin (summer) are skipped and listed at the end."""
    to_date = lambda x: dt.datetime.strptime(x, "%d-%m-%Y").date() if isinstance(x, str) else x
    von, bis = to_date(von), to_date(bis)
    cache = Path(cache)
    cache.mkdir(parents=True, exist_ok=True)
    days = [(von + dt.timedelta(days=n)).isoformat() for n in range((bis - von).days + 1)]

    with ThreadPoolExecutor(workers) as ex:               # a few parallel downloads
        texts = list(ex.map(lambda d: _download(d, cache), days))

    rows, missing, errors = [], [], []
    for day, text in zip(days, texts):
        if text is None:
            missing.append(day)
        elif text == "ERROR":
            errors.append(day)
        else:
            rows += _parse(text, day)
    df = pd.DataFrame(rows)
    print(f"{df.date.nunique() if len(df) else 0} days with bulletin, {len(missing)} without (404), "
          f"{len(errors)} download errors {errors[:5]}")
    return df


if __name__ == "__main__":
    import sys
    out = get_avalanche_data(sys.argv[1], sys.argv[2])
    out.to_csv("avalanche_bulletins.csv", index=False)
    print(out.head())