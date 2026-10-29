"""Export the engine's data and build the self-contained worker/planner app (outputs/next_shift.html)."""
import datetime as dt
import json

import numpy as np
import pandas as pd

from . import config as C
from . import repurpose as RP

TEMPLATE = C.ROOT / "atp" / "app_template.html"


def _r(x, n=2):
    return None if x is None or (isinstance(x, float) and not np.isfinite(x)) else round(float(x), n)


def payload(r):
    jobs, m, desc, req, w = r["jobs"], r["profiles"], r["descriptors"], r["requirements"], r["wages"]
    names, titles, programs = r["names"], r["titles"], r["programs"]
    nocs = list(m.index)
    ex = titles[titles["type"] != "Lead statement"].groupby("noc")["title"].apply(lambda s: list(dict.fromkeys(s))[:6])
    ers = {k: p["economic_region"] for k, p in C.PLANTS.items()}

    def wage(noc, er, col):
        s = w[(w["noc"] == noc) & (w["er"] == er)][col]
        return _r(s.iloc[0]) if len(s) and pd.notna(s.iloc[0]) else None

    occ = []
    for n in nocs:
        rq = req.loc[n] if n in req.index else None
        occ.append({
            "noc": n, "name": names.get(n, n), "teer": int(n[1]),
            "compulsory": bool(rq["compulsory_on"]) if rq is not None else False,
            "licence": bool(rq["licence"]) if rq is not None else False,
            "req": (rq["requirements"][:4] if rq is not None else []),
            "titles": ex.get(n, []),
            "wage": {k: {"median": wage(n, er, "median"), "high": wage(n, er, "high")} for k, er in ers.items()}
                    | {"on": {"median": wage(n, "ER35", "median"), "high": wage(n, "ER35", "high")}},
        })

    demand, samples = {}, {}
    for key in C.PLANTS:
        d = r["plants"][key]["demand"]
        demand[key] = {n: [_r(d.at[n, f"vac_{b}"]) for b in C.COMMUTE_BANDS]
                       + [int(d.at[n, f"post_{b}"]) for b in C.COMMUTE_BANDS]
                       + [_r(d.at[n, "wage_posted"]), _r(d.at[n, "no_degree"]), _r(d.at[n, "low_exp"])]
                       for n in d.index}
        near = jobs[jobs[f"min_{key}"] <= max(C.COMMUTE_BANDS)].sort_values([f"min_{key}", "date"],
                                                                                  ascending=[True, False])
        s = near.groupby("noc").head(C.POSTINGS_PER_TARGET)
        samples[key] = {n: [[t, c, _r(wg), _r(mi, 0), str(dd)[:10], int(v)]
                            for t, c, wg, mi, dd, v in zip(g["title"], g["city"], g["wage_hr"], g[f"min_{key}"],
                                                           g["date"], g["vacancies"])]
                        for n, g in s.groupby("noc")}

    prog = [{k: (None if isinstance(v, float) and not np.isfinite(v) else v) for k, v in p.items()
             if k not in ("lat", "lon")} for p in programs.to_dict("records")]
    months = sorted(jobs["month"].unique())
    return {
        "generated": dt.date.today().isoformat(),
        "window": [months[0], months[-1]], "n_months": len(months),
        "n_postings": int(len(jobs)), "n_located": int(jobs["lat"].notna().sum()),
        "plants": {k: {kk: v for kk, v in p.items()} for k, p in C.PLANTS.items()},
        "mix": C.WORKFORCE_MIX, "bands": C.COMMUTE_BANDS,
        "cfg": {"readiness_weight": C.READINESS_WEIGHT, "gap_min_target": C.GAP_MIN_TARGET,
                "gap_min_diff": C.GAP_MIN_DIFF, "min_match": C.MIN_MATCH_LISTED, "weights": C.RANK_WEIGHTS,
                "teer_months": C.TEER_TRAINING_MONTHS, "training_max_min": C.TRAINING_MAX_MIN,
                "default_commute": C.DEFAULT_COMMUTE_MIN, "capture": C.CAPTURE_SHARE,
                "planning_months": C.PLANNING_MONTHS, "planner_commute": C.PLANNER_COMMUTE_MIN,
                "planner_min_match": C.PLANNER_MIN_MATCH, "planner_min_wage": C.PLANNER_MIN_WAGE_RATIO,
                "planner_max_train": C.PLANNER_MAX_TRAIN_MONTHS,
                "peak": C.PEAK_FACTOR, "bjo": C.BETTER_JOBS_ONTARIO},
        "descriptors": [{"name": d, "group": g} for d, g in zip(desc["descriptor"], desc["group"])],
        "occ": occ,
        "profiles": [[int(round(v * 10)) for v in m.loc[n].values] for n in nocs],
        "demand": demand, "samples": samples, "programs": prog,
        "products": [{k: p[k] for k in ("id", "name", "proxy", "carries", "signals")}
                     | {"roles": {n: round(s, 4) for n, s in r["staffing"][p["id"]]["roles"].items()},
                        "salaried": r["staffing"][p["id"]]["salaried_per_100"]} for p in RP.PRODUCTS],
        "rp": {"quick_months": RP.QUICK_MAX_MONTHS, "quick_match": RP.QUICK_MIN_MATCH,
               "retrain_months": RP.RETRAIN_MAX_MONTHS, "retrain_match": RP.RETRAIN_MIN_MATCH,
               "headcount": RP.HEADCOUNT_SHARE},
    }


def build(r):
    """Write outputs/next_shift.html (opens in any browser) and next_shift_artifact.html (page body only,
    for publishing where the host adds the document wrapper)."""
    data = payload(r)
    body = TEMPLATE.read_text(encoding="utf-8")
    blob = json.dumps(data, separators=(",", ":"), ensure_ascii=False).replace("</", "<\\/")
    body = body.replace("/*__DATA__*/null", blob)
    C.OUT.mkdir(parents=True, exist_ok=True)
    head, rest = body.split("<style>", 1)
    full = ('<!doctype html>\n<html lang="en"><head><meta charset="utf-8">'
            '<meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">\n'
            + head + "<style>" + rest.replace("</style>", "</style></head><body>", 1) + "\n</body></html>")
    for name, html in [("next_shift.html", full), ("next_shift_artifact.html", body)]:
        (C.OUT / name).write_text(html, encoding="utf-8")
    out = C.OUT / "next_shift.html"
    print(f"-> {out} ({out.stat().st_size / 1e6:.2f} MB)")
    return out
