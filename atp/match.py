"""The matching engine: for each plant and plant occupation, rank Ontario occupations a displaced worker
can move into, with local openings, pay, skill gaps and training; then size re-employment for planners."""
import numpy as np
import pandas as pd

from . import config as C
from . import jobs as J
from . import skills as S
from . import training as T

NO_DEGREE = {"No degree, certificate or diploma", "Secondary (high) school graduation certificate"}
LOW_EXPERIENCE = {"No experience", "1 to less than 7 months", "7 months to less than 1 year"}


def _names(w):
    n = pd.read_csv(C.WAGES_FILE, usecols=["NOC_CNP", "NOC_Title_eng"], dtype=str).drop_duplicates("NOC_CNP")
    return dict(zip(n["NOC_CNP"].str[4:], n["NOC_Title_eng"]))


def demand(jobs, key):
    """Per target NOC: openings (vacancies) within each commute band over the data window, and pay."""
    m = jobs[f"min_{key}"]
    rows = {}
    for b in C.COMMUTE_BANDS:
        rows[f"vac_{b}"] = jobs[m <= b].groupby("noc")["vacancies"].sum()
        rows[f"post_{b}"] = jobs[m <= b].groupby("noc").size()
    near = jobs[m <= max(C.COMMUTE_BANDS)]
    rows["wage_posted"] = near.groupby("noc")["wage_hr"].median()
    rows["no_degree"] = near.assign(x=near["education"].isin(NO_DEGREE) | near["education"].isna()).groupby("noc")["x"].mean()
    rows["low_exp"] = near.assign(x=near["experience"].isin(LOW_EXPERIENCE) | near["experience"].isna()).groupby("noc")["x"].mean()
    d = pd.DataFrame(rows).fillna({f"vac_{b}": 0 for b in C.COMMUTE_BANDS} | {f"post_{b}": 0 for b in C.COMMUTE_BANDS})
    months = jobs["month"].nunique()
    for b in C.COMMUTE_BANDS:
        d[f"vac_{b}"] = d[f"vac_{b}"] / months           # per month
    return d


def score(df, band, weights=C.RANK_WEIGHTS):
    skill = ((df["match"] - 50) / 50).clip(0, 1)
    dem = np.log1p(df[f"vac_{band}"]) / np.log1p(max(df[f"vac_{band}"].max(), 1))
    wage = ((df["wage_ratio"].fillna(0.8) - 0.5) / 0.7).clip(0, 1)
    train = 1 - (df["train_months"] / 48).clip(0, 1)
    return 100 * (weights["skill"] * skill + weights["demand"] * dem + weights["wage"] * wage + weights["training"] * train)


def build():
    jobs = J.load()
    w = J.wages()
    names = _names(w)
    m, desc = S.profiles()
    req = S.requirements()
    lead, ex = S.titles()
    from .roads import DriveTimes
    programs = T.load(DriveTimes())
    prog_list = programs.to_dict("records")

    targets = sorted(set(jobs["noc"]) & set(m.index))
    plants, transitions, planner = {}, [], []
    for key, p in C.PLANTS.items():
        dem = demand(jobs, key)
        cur = {o: J.wage_lookup(w, o, p["economic_region"], C.CURRENT_WAGE_PERCENTILE) for o in C.WORKFORCE_MIX}
        rows = []
        for origin, share in C.WORKFORCE_MIX.items():
            tr = S.transfer(m, origin, targets)
            tr = tr[tr["match"] >= C.MIN_MATCH_LISTED].copy()
            tr["origin"], tr["plant"] = origin, key
            tr = tr.join(dem, on="noc")
            tr["wage_esdc"] = [J.wage_lookup(w, t, p["economic_region"]) for t in tr["noc"]]
            tr["wage_target"] = tr["wage_posted"].fillna(tr["wage_esdc"])
            tr["wage_ratio"] = (tr["wage_target"] / cur[origin]).round(3)
            comp = (tr["noc"].map(req["compulsory_on"]).fillna(False).astype(bool)
                    | tr["noc"].map(req["licence"]).fillna(False).astype(bool))
            tm = [T.months_for(t, origin, c, mt, prog_list, key) for t, c, mt in zip(tr["noc"], comp, tr["match"])]
            tr["train_months"] = [x[0] for x in tm]
            tr["train_basis"] = [x[1] for x in tm]
            tr["compulsory_on"] = comp.values
            tr["score"] = score(tr, C.DEFAULT_COMMUTE_MIN).round(1)
            rows.append(tr)
        tp = pd.concat(rows, ignore_index=True)
        transitions.append(tp)
        planner.append(absorb(tp, key, p))
        plants[key] = {"current_wage": cur, "demand": dem}

    tp = pd.concat(transitions, ignore_index=True)
    return {"jobs": jobs, "transitions": tp, "planner": pd.concat(planner, ignore_index=True), "plants": plants,
            "names": names, "profiles": m, "descriptors": desc, "requirements": req, "titles": ex,
            "programs": programs, "wages": w}


def absorb(tp, key, p):
    """Greedy re-employment estimate for one plant over PLANNING_MONTHS.

    Displaced workers per occupation (WORKFORCE_MIX x displaced) are placed into good-fit destination
    occupations within PLANNER_COMMUTE_MIN, best score first. Each destination can absorb CAPTURE_SHARE of
    its openings over the horizon, shared by every plant occupation. Origins with the fewest good options
    are placed first so the scarce openings go to those who need them most."""
    band = C.PLANNER_COMMUTE_MIN
    ok = tp[(tp["match"] >= C.PLANNER_MIN_MATCH) & (tp["wage_ratio"].fillna(0) >= C.PLANNER_MIN_WAGE_RATIO)
            & (tp[f"vac_{band}"] > 0) & (tp["train_months"] <= C.PLANNER_MAX_TRAIN_MONTHS)].copy()
    cap = (ok.drop_duplicates("noc").set_index("noc")[f"vac_{band}"] * C.PLANNING_MONTHS * C.CAPTURE_SHARE).to_dict()
    workers = {o: round(s * p["displaced"]) for o, s in C.WORKFORCE_MIX.items()}
    order = sorted(workers, key=lambda o: (ok["origin"] == o).sum())
    out = []
    for o in order:
        left = workers[o]
        for _, r in ok[ok["origin"] == o].sort_values("score", ascending=False).iterrows():
            if left <= 0:
                break
            take = min(left, int(cap.get(r["noc"], 0)))
            if take <= 0:
                continue
            cap[r["noc"]] -= take
            left -= take
            out.append({"plant": key, "origin": o, "target": r["noc"], "workers": take, "match": r["match"],
                        "wage_ratio": r["wage_ratio"], "train_months": r["train_months"]})
        if left > 0:
            out.append({"plant": key, "origin": o, "target": None, "workers": left, "match": np.nan,
                        "wage_ratio": np.nan, "train_months": np.nan})
    return pd.DataFrame(out)
