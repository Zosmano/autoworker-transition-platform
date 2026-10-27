"""Locations: FSA centroids from the StatCan boundary file, place names and addresses from NRCan services."""
import json
import time
import urllib.parse
import urllib.request
from concurrent.futures import ThreadPoolExecutor

import numpy as np
import pandas as pd

from . import config as C

GEONAMES = "https://geogratis.gc.ca/services/geoname/en/geonames.json?"
GEOLOCATE = "https://geogratis.gc.ca/services/geolocation/en/locate?"
# Populated-place feature codes, best first.
PLACE_RANK = {"CITY": 0, "TOWN": 1, "MUN1": 2, "MUN2": 3, "VILG": 4, "UNP": 5, "HAM": 6, "IR": 7}


def _get(url, tries=3):
    for i in range(tries):
        try:
            with urllib.request.urlopen(url, timeout=30) as r:
                return json.loads(r.read().decode("utf-8-sig"))
        except Exception:
            if i == tries - 1:
                raise
            time.sleep(2 * (i + 1))


def fsa_centroids():
    """Ontario FSA representative points (lat, lon), cached."""
    path = C.CACHE / "fsa_centroids_on.csv"
    if path.exists():
        return pd.read_csv(path, dtype={"fsa": str})
    import zipfile
    import geopandas as gpd
    shp = next(n for n in zipfile.ZipFile(C.FSA_BOUNDARY_ZIP).namelist() if n.endswith(".shp"))
    g = gpd.read_file(f"zip://{C.FSA_BOUNDARY_ZIP}!{shp}")
    g = g[g["PRUID"].astype(str) == "35"]
    pts = g.geometry.representative_point().to_crs(4326)
    d = pd.DataFrame({"fsa": g["CFSAUID"].values, "lat": pts.y.values, "lon": pts.x.values})
    C.CACHE.mkdir(parents=True, exist_ok=True)
    d.to_csv(path, index=False)
    return d


def _lookup_place(name):
    d = _get(GEONAMES + urllib.parse.urlencode({"q": name, "province": "35"}))
    best = None
    for it in d.get("items", []):
        rank = PLACE_RANK.get(it.get("concise", {}).get("code"))
        if rank is None or it.get("name", "").lower() != name.lower():
            continue
        if best is None or rank < best[0]:
            best = (rank, it["latitude"], it["longitude"], it.get("concise", {}).get("code"))
    return best


def places(names):
    """Geocode Ontario place names (cached). Returns {name: (lat, lon, feature) or None}."""
    path = C.CACHE / "geonames_on.json"
    cache = json.loads(path.read_text()) if path.exists() else {}
    todo = sorted({n for n in names if isinstance(n, str) and n not in cache})
    if todo:
        with ThreadPoolExecutor(6) as ex:
            for n, r in zip(todo, ex.map(lambda n: _safe(_lookup_place, n), todo)):
                cache[n] = None if r is None else list(r[1:])
        C.CACHE.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(cache, indent=0))
    return {n: cache.get(n) for n in names}


def _safe(f, *a):
    try:
        return f(*a)
    except Exception:
        return None


def addresses(addrs):
    """Geocode street addresses with NRCan's geolocation service (cached). {address: (lat, lon) or None}."""
    path = C.CACHE / "addresses.json"
    cache = json.loads(path.read_text()) if path.exists() else {}
    for a in addrs:
        if a in cache:
            continue
        r = _safe(_get, GEOLOCATE + urllib.parse.urlencode({"q": a}))
        hit = next((x for x in (r or []) if x.get("qualifier") in ("INTERPOLATED_POSITION", "LOCATION")), None)
        cache[a] = None if hit is None else [hit["geometry"]["coordinates"][1], hit["geometry"]["coordinates"][0]]
    C.CACHE.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(cache, indent=0))
    return {a: cache.get(a) for a in addrs}


def haversine_km(lat1, lon1, lat2, lon2):
    lat1, lon1, lat2, lon2 = map(np.radians, (lat1, lon1, lat2, lon2))
    a = np.sin((lat2 - lat1) / 2) ** 2 + np.cos(lat1) * np.cos(lat2) * np.sin((lon2 - lon1) / 2) ** 2
    return 6371.0 * 2 * np.arcsin(np.sqrt(a))
