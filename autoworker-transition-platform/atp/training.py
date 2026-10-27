"""Training catalogue: curated Ontario programs, located and timed from each plant."""
import numpy as np
import pandas as pd

from . import config as C
from . import geo


def load(drive):
    t = pd.read_csv(C.TRAINING_FILE, dtype=str).fillna("")
    t["months"] = pd.to_numeric(t["months"])
    t["target_nocs"] = t["target_nocs"].str.split(";")
    loc = geo.addresses([a for a in t["address"].unique() if a])
    t["lat"] = t["address"].map(lambda a: (loc.get(a) or [np.nan])[0])
    t["lon"] = t["address"].map(lambda a: (loc.get(a) or [np.nan, np.nan])[1])
    for key in C.PLANTS:
        t[f"min_{key}"] = np.round(drive.minutes(key, t["lat"].values, t["lon"].values), 0)
    return t


def months_for(target, origin, compulsory, match, programs, key):
    """Training time to move from origin to target (months) and how it is estimated.

    Uses the shortest listed program within TRAINING_MAX_MIN of the plant (or offered in many places)."""
    listed = [p for p in programs if target in p["target_nocs"]
              and (not np.isfinite(p[f"min_{key}"]) or p[f"min_{key}"] <= C.TRAINING_MAX_MIN)]
    ot, tt = int(origin[1]), int(target[1])
    # Ready now: a job at or below the worker's skill level (TEER) that is either low-formal-training
    # (TEER 4-5) or in the same broad occupational category, with a strong match and no licence.
    same_field = origin[0] == target[0]
    if tt >= ot and (tt >= 4 or same_field) and match >= 85 and not compulsory:
        return 1.0, "Ready now: short on-the-job or safety training"
    if listed:
        m = min(p["months"] for p in listed)
        return float(m), "Shortest listed program"
    return float(C.TEER_TRAINING_MONTHS.get(tt, 12)), "Typical for this skill level (TEER)"
