"""Occupation skill profiles (ESDC OaSIS 2022) and worker-to-occupation transferability."""
import re

import numpy as np
import pandas as pd

from . import config as C


def _read(name):
    d = pd.read_csv(C.RAW / name, encoding="utf-8-sig", dtype=str)
    d.columns = [re.sub(r"\s+", " ", re.sub(r"\(Proficiency Level 0-5\)", "", c)).strip() for c in d.columns]
    return d.rename(columns={d.columns[0]: "code", d.columns[1]: "label"})


def profiles():
    """One row per 5-digit NOC: descriptor ratings 0-5 (profiles within a unit group averaged).

    Returns (matrix DataFrame indexed by NOC, descriptor table with group names)."""
    parts, desc = [], []
    for group, f in C.DESCRIPTOR_FILES.items():
        d = _read(f)
        d["noc"] = d["code"].str.replace(".", "", regex=False).str[:5]
        cols = [c for c in d.columns if c not in ("code", "label", "noc")]
        v = d[cols].apply(pd.to_numeric, errors="coerce")
        v["noc"] = d["noc"]
        parts.append(v.groupby("noc").mean())
        desc += [{"descriptor": c, "group": group} for c in cols]
    m = pd.concat(parts, axis=1).dropna()
    m.columns = [f"{g['group']}:{g['descriptor']}" for g in desc]
    return m, pd.DataFrame(desc).assign(key=m.columns)


def titles():
    """NOC unit-group titles and example job titles (for search)."""
    lead = _read("oasis_skills.csv")[["code", "label"]]
    lead["noc"] = lead["code"].str.replace(".", "", regex=False).str[:5]
    ex = pd.read_csv(C.RAW / "oasis_example_titles.csv", encoding="utf-8-sig", dtype=str)
    ex.columns = ["code", "n", "type", "title"]
    ex["noc"] = ex["code"].str.replace(".", "", regex=False).str[:5]
    return lead, ex


def requirements():
    """Per NOC: employment-requirement sentences and whether trade certification is compulsory in Ontario."""
    r = pd.read_csv(C.RAW / "oasis_employment_requirements.csv", encoding="utf-8-sig", dtype=str)
    r.columns = ["code", "text"]
    r["noc"] = r["code"].str.replace(".", "", regex=False).str[:5]

    def compulsory(s):
        m = re.search(r"compulsory in (.*?)(?:,? and available|, but voluntary|\.|$)", s)
        return bool(m and "Ontario" in m.group(1))

    def licence(s):
        return bool(re.search(r"licen[cs]e (?:is|are) required|must be licensed|registration with a regulatory", s, re.I))

    r["compulsory_on"] = r["text"].map(compulsory)
    r["licence"] = r["text"].map(licence)
    g = r.groupby("noc").agg(requirements=("text", lambda s: list(dict.fromkeys(s))),
                             compulsory_on=("compulsory_on", "any"), licence=("licence", "any"))
    return g


def teer(noc):
    return int(str(noc)[1])


def transfer(m, origin, targets=None):
    """Skill match of a worker from `origin` NOC to each target NOC.

    match = 100 x (1 - weighted shortfall), where shortfall is how far the worker's proficiency falls
    below the target's on each descriptor, weighted by the target's own proficiency (what the job leans on
    most counts most). Also returns the biggest gaps (target >= GAP_MIN_TARGET, gap >= GAP_MIN_DIFF)."""
    o = m.loc[origin].values
    t = m if targets is None else m.loc[[x for x in targets if x in m.index]]
    T = t.values
    short = np.clip(T - o, 0, None)
    readiness = 100 * (1 - (short * T).sum(1) / (T * T).sum(1))
    # Readiness alone rates every less demanding job as a perfect fit, so an electrician would "match"
    # baking. Relevance (cosine similarity of the centred profiles) rewards jobs that use the same kind
    # of skills; the match blends the two.
    oc, Tc = o - o.mean(), T - T.mean(1, keepdims=True)
    cos = (Tc @ oc) / (np.linalg.norm(Tc, axis=1) * np.linalg.norm(oc) + 1e-9)
    match = C.READINESS_WEIGHT * readiness + (1 - C.READINESS_WEIGHT) * 50 * (cos + 1)
    gaps = []
    for i in range(len(t)):
        diff = T[i] - o
        idx = np.where((T[i] >= C.GAP_MIN_TARGET) & (diff >= C.GAP_MIN_DIFF))[0]
        idx = idx[np.argsort(-diff[idx] * T[i][idx])]
        gaps.append([(t.columns[j], round(float(o[j]), 1), round(float(T[i][j]), 1)) for j in idx])
    return pd.DataFrame({"noc": t.index, "match": match.round(1), "readiness": readiness.round(1),
                         "relevance": (50 * (cos + 1)).round(1), "gaps": gaps})
