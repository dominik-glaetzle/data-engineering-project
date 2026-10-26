"""Lawinenberichte Tirol (CAAML v5, lawinen.report-Archiv) -> DataFrame.

    from avalanche import get_avalanche_data
    df = get_avalanche_data("01-11-2015", "31-12-2015")      # dd-mm-yyyy
"""
import datetime as dt
import re
import time
import xml.etree.ElementTree as ET
from pathlib import Path

import pandas as pd
import requests

URL = "https://lawinen.report/bulletins/archive/tyrol/caaml/"
NS = {"c": "http://caaml.org/Schemas/V5.0/Profiles/BulletinEAWS"}
XLINK = "{http://www.w3.org/1999/xlink}href"


def _download(url, path):
    if path.exists():
        return path.read_text(encoding="utf8")
    for i in range(4):
        try:
            r = requests.get(url, timeout=60)
            if r.status_code == 404:
                return None
            r.raise_for_status()
            r.encoding = "utf8"
            path.write_text(r.text, encoding="utf8")
            return r.text
        except requests.RequestException:
            time.sleep(2 ** i)
    return None


def _text(el, path):
    x = el.find(path, NS)
    return x.text.strip() if x is not None and x.text else None


def _parse(xml, day):
    """Eine Datei -> Zeilen (eine je Region)."""
    root = ET.fromstring(xml.encode("utf8"))
    ratings = list(root.iter("{%s}DangerRating" % NS["c"]))
    # Gueltigkeitstag: Dateidatum, bei Abendberichten der naechste Tag
    begins = sorted({(_text(r, "c:validTime/c:TimePeriod/c:beginPosition") or "")[:10]
                     for r in ratings if r.find("c:locRef", NS) is not None} - {""})
    iso = day.isoformat()
    if iso not in begins:
        iso = next((b for b in begins if b >= iso), iso)

    regions, tirol = {}, None
    for r in ratings:
        value = int(_text(r, "c:mainValue"))
        loc = r.find("c:locRef", NS)
        if loc is None:                                   # Tirol-weite Stufe
            if (_text(r, "c:validTime/c:TimeInstant/c:timePosition") or "").startswith(iso):
                tirol = value
            continue
        begin = _text(r, "c:validTime/c:TimePeriod/c:beginPosition") or ""
        if not begin.startswith(iso):
            continue
        band, limit = "all", None
        rng = r.find("c:validElevation/c:ElevationRange", NS)
        if rng is not None:
            lo, hi = _text(rng, "c:beginPosition"), _text(rng, "c:endPosition")
            if lo and not hi:
                band, limit = "above", int(lo)
            elif hi and not lo:
                band, limit = "below", int(hi)
        regions.setdefault(loc.get(XLINK), []).append(
            (("am" if int(begin[11:13]) < 12 else "pm"), band, limit, value))

    problems = sorted({_text(p, "c:type") for p in root.iter("{%s}AvProblem" % NS["c"])} - {None})
    rows = []
    for region, rs in regions.items():
        top = lambda f: max([v for h, b, l, v in rs if f(h, b)], default=None)
        limits = [l for *_, l, _ in rs if l]
        rows.append({
            "date": iso, "region": region,
            "danger_max": top(lambda h, b: True),
            "danger_above": top(lambda h, b: b in ("above", "all")),
            "danger_below": top(lambda h, b: b in ("below", "all")),
            "elev_threshold_m": min(limits) if limits else None,
            "danger_am": top(lambda h, b: h == "am"),
            "danger_pm": top(lambda h, b: h == "pm"),
            "danger_tirol": tirol,
            "problems": ";".join(problems),
            "file_date": day.isoformat(),
        })
    return rows


def get_avalanche_data(von, bis, cache="data/cache"):
    """Berichte von..bis (dd-mm-yyyy oder date, inklusive) -> DataFrame (Datum x Region).
    Tage ohne Bericht werden uebersprungen und am Ende aufgelistet."""
    to_date = lambda x: dt.datetime.strptime(x, "%d-%m-%Y").date() if isinstance(x, str) else x
    von, bis = to_date(von), to_date(bis)
    cache = Path(cache)
    cache.mkdir(parents=True, exist_ok=True)

    index = _download(URL, cache / "_index.html") or ""
    files = {}                                            # date -> [Dateinamen, spaeteste zuletzt]
    for name in sorted(set(re.findall(r"\d{4}-\d{2}-\d{2}_\d{4}_avalanche_bulletin_tyrol_(?:en|de)\.xml", index))):
        files.setdefault(dt.date.fromisoformat(name[:10]), []).append(name)

    rows, missing = [], []
    for n in range((bis - von).days + 1):
        day = von + dt.timedelta(days=n)
        # englisch zuerst, spaetester Bericht des Tages zuerst
        names = files.get(day, [])
        candidates = sorted([f for f in names if f.endswith("_en.xml")], reverse=True) + \
                     sorted([f for f in names if f.endswith("_de.xml")], reverse=True)
        new = []
        for name in candidates:
            xml = _download(URL + name, cache / name)
            if xml:
                new = _parse(xml, day)
            if new:
                break
        rows += new
        if not new:
            missing.append(day.isoformat())

    df = pd.DataFrame(rows)
    if len(df):
        df = df.sort_values(["date", "region", "file_date"]).drop_duplicates(["date", "region"], keep="last")
    print(f"{df.date.nunique() if len(df) else 0} Tage mit Bericht, {len(missing)} ohne: {missing[:8]}{' ...' if len(missing) > 8 else ''}")
    return df.reset_index(drop=True)


if __name__ == "__main__":
    import sys
    out = get_avalanche_data(sys.argv[1], sys.argv[2])
    out.to_csv("avalanche_bulletins.csv", index=False)
    print(out.head())
