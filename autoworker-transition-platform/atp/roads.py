"""Drive times from each plant over the StatCan 2021 Road Network File (shortest-time paths)."""
import numpy as np
import pandas as pd
from pyproj import Transformer
from scipy.sparse import coo_matrix
from scipy.sparse.csgraph import dijkstra
from scipy.spatial import cKDTree

from . import config as C
from .geo import haversine_km

TO_LAMBERT = Transformer.from_crs(4326, 3347, always_xy=True)


def _read_roads():
    import pyogrio
    import shapely
    xs, ys = TO_LAMBERT.transform([p["lon"] for p in C.PLANTS.values()], [p["lat"] for p in C.PLANTS.values()])
    b = C.ROAD_BUFFER_KM * 1000
    bbox = (min(xs) - b, min(ys) - b, max(xs) + b, max(ys) + b)
    df = pyogrio.read_dataframe(f"zip://{C.ROAD_NETWORK_ZIP}", bbox=bbox, columns=["CLASS"])
    g = df.geometry.values
    a, z = shapely.get_point(g, 0), shapely.get_point(g, -1)
    return pd.DataFrame({
        "x0": shapely.get_x(a), "y0": shapely.get_y(a), "x1": shapely.get_x(z), "y1": shapely.get_y(z),
        "m": shapely.length(g), "cls": df["CLASS"].astype(str).values})


def build():
    """Minutes (free flow) from each plant to every road node, cached as node tables."""
    path = C.CACHE / "drive_nodes.pkl"
    if path.exists():
        return pd.read_pickle(path)
    r = _read_roads()
    ends = np.vstack([r[["x0", "y0"]].values, r[["x1", "y1"]].values]).round(0)
    nodes, inv = np.unique(ends, axis=0, return_inverse=True)
    inv = inv.ravel()
    u, v = inv[: len(r)], inv[len(r):]
    kmh = r["cls"].map(C.ROAD_SPEED_KMH).fillna(C.DEFAULT_SPEED_KMH).values
    w = r["m"].values / 1000 / kmh * 60 + 1e-6
    n = len(nodes)
    g = coo_matrix((np.r_[w, w], (np.r_[u, v], np.r_[v, u])), shape=(n, n)).tocsr()
    tree = cKDTree(nodes)
    out = pd.DataFrame({"x": nodes[:, 0], "y": nodes[:, 1]})
    for key, p in C.PLANTS.items():
        px, py = TO_LAMBERT.transform(p["lon"], p["lat"])
        _, src = tree.query([px, py])
        out[key] = dijkstra(g, indices=int(src)).astype("float32")
    C.CACHE.mkdir(parents=True, exist_ok=True)
    out.to_pickle(path)
    print(f"road graph: {len(r):,} segments, {n:,} nodes")
    return out


class DriveTimes:
    """Peak-hour drive minutes from a plant to arbitrary points."""

    def __init__(self):
        self.nodes = build()
        self.trees = {}
        for key in C.PLANTS:
            ok = np.isfinite(self.nodes[key].values)
            self.trees[key] = (cKDTree(self.nodes.loc[ok, ["x", "y"]].values), self.nodes.loc[ok, key].values)

    def minutes(self, key, lat, lon):
        lat, lon = np.asarray(lat, float), np.asarray(lon, float)
        ok = np.isfinite(lat) & np.isfinite(lon)
        x, y = TO_LAMBERT.transform(np.where(ok, lon, -80.0), np.where(ok, lat, 43.0))
        tree, mins = self.trees[key]
        dist, idx = tree.query(np.c_[x, y])
        t = mins[idx] + dist / 1000 / C.ACCESS_SPEED_KMH * 60
        # Points far off the graph (outside the buffer): straight line x 1.3 at 80 km/h.
        p = C.PLANTS[key]
        far = dist > 5000
        t = np.where(far, haversine_km(p["lat"], p["lon"], lat, lon) * 1.3 / 80 * 60, t)
        return np.where(ok, t * C.PEAK_FACTOR[key], np.nan)
