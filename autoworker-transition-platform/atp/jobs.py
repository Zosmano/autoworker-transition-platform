"""Ontario job postings from Job Bank open data: cleaned, de-duplicated, wage-normalised, located."""
import numpy as np
import pandas as pd

from . import config as C
from . import geo

COLS = {
    "WIC Job Location Snapshot ID": "id", "Job Title": "title", "NOC21 Code": "noc", "NOC21 Code Name": "noc_name",
    "External Indicator": "external", "First Posting Date": "date", "Vacancy Count": "vacancies",
    "Education LOS": "education", "Experience Level": "experience", "NAICS": "naics",
    "Province/Territory": "province", "City": "city", "Work Location Postal Code": "postal",
    "Economic  Region": "region", "Employment Type": "emp_type", "Salary Per": "per",
    "Salary Minimum": "smin", "Salary Maximum": "smax", "Hours Minimum": "hmin", "Hours Maximum": "hmax",
}
# Pay periods per year, to annualise; hourly rates use C.HOURS_PER_YEAR.
PER_YEAR = {"Year": 1, "Month": 12, "Bi-weekly": 26, "Week": 52, "Day": 260}


def _read():
    frames = []
    for f in sorted(C.RAW.glob(C.JOBBANK_GLOB)):
        d = pd.read_csv(f, encoding="utf-16", sep="\t", usecols=list(COLS), dtype=str).rename(columns=COLS)
        frames.append(d[d["province"] == "Ontario"].assign(month=f.stem[-7:].replace("_", "-")))
    return pd.concat(frames, ignore_index=True)


def _wage(d):
    lo, hi = pd.to_numeric(d["smin"], errors="coerce"), pd.to_numeric(d["smax"], errors="coerce")
    pay = hi.where(hi > 0).fillna(lo)
    pay = (lo + pay) / 2
    hourly = np.where(d["per"] == "Hour", pay, pay * d["per"].map(PER_YEAR) / C.HOURS_PER_YEAR)
    hourly = pd.Series(hourly, index=d.index)
    return hourly.where(hourly.between(15, 250))      # drop impossible values (Ontario minimum wage ~$17)


def load(rebuild=False):
    path = C.CACHE / "jobs_on.pkl"
    if path.exists() and not rebuild:
        return pd.read_pickle(path)
    d = _read()
    n0 = len(d)
    d["noc"] = d["noc"].str.zfill(5)
    d["date"] = pd.to_datetime(d["date"], format="%Y/%m/%d", errors="coerce")
    d["vacancies"] = pd.to_numeric(d["vacancies"], errors="coerce").fillna(1).clip(1, 50)
    d["external"] = d["external"] == "1"
    d["wage_hr"] = _wage(d)
    # Each monthly file holds postings first posted that month. Drop same-day copies of one job
    # (several aggregators, or one employer posting each vacancy separately).
    d = d.drop_duplicates(["title", "noc", "city", "postal", "smin", "smax", "per", "date"])
    d = d[d["noc"].str.fullmatch(r"\d{5}")]

    # Location: postal-code FSA centroid when given, else the posting's city.
    fsa = geo.fsa_centroids().set_index("fsa")
    d["fsa"] = d["postal"].str.replace(" ", "").str[:3].str.upper()
    d["lat"], d["lon"] = d["fsa"].map(fsa["lat"]), d["fsa"].map(fsa["lon"])
    d["loc_source"] = np.where(d["lat"].notna(), "postal code", None)
    city = d["city"].str.strip()
    pl = geo.places(city[d["lat"].isna()].dropna().unique().tolist())
    miss = d["lat"].isna()
    d.loc[miss, "lat"] = city[miss].map(lambda c: (pl.get(c) or [np.nan])[0])
    d.loc[miss, "lon"] = city[miss].map(lambda c: (pl.get(c) or [np.nan, np.nan])[1])
    d.loc[miss & d["lat"].notna(), "loc_source"] = "city"
    print(f"jobs: {n0:,} Ontario postings -> {len(d):,} after de-duplication; "
          f"located {d['lat'].notna().mean():.1%} (postal {(d['loc_source'] == 'postal code').mean():.1%})")

    from .roads import DriveTimes
    dt = DriveTimes()
    for key in C.PLANTS:
        d[f"min_{key}"] = dt.minutes(key, d["lat"].values, d["lon"].values).round(1)
    keep = ["id", "title", "noc", "noc_name", "date", "month", "vacancies", "education", "experience", "naics",
            "city", "fsa", "region", "emp_type", "external", "wage_hr", "lat", "lon", "loc_source"] + \
           [f"min_{k}" for k in C.PLANTS]
    d = d[keep].reset_index(drop=True)
    d.to_pickle(path)
    return d


def wages():
    """ESDC 2025 wages by NOC: hourly low/median/high for Ontario and each economic region."""
    w = pd.read_csv(C.WAGES_FILE, dtype=str)
    w = w[w["prov"] == "ON"].copy()
    w["noc"] = w["NOC_CNP"].str.replace("NOC_", "")
    for src, dst in [("Low_Wage_Salaire_Minium", "low"), ("Median_Wage_Salaire_Median", "median"),
                     ("High_Wage_Salaire_Maximal", "high")]:
        v = pd.to_numeric(w[src], errors="coerce")
        w[dst] = np.where(w["Annual_Wage_Flag_Salaire_annuel"] == "1", v / C.HOURS_PER_YEAR, v)
    return w[["noc", "ER_Code_Code_RE", "ER_Name", "low", "median", "high"]].rename(
        columns={"ER_Code_Code_RE": "er", "ER_Name": "er_name"})


def wage_lookup(w, noc, er, col="median"):
    """Regional wage, falling back to Ontario."""
    r = w[(w["noc"] == noc) & (w["er"] == er)][col]
    if len(r) and pd.notna(r.iloc[0]):
        return float(r.iloc[0])
    r = w[(w["noc"] == noc) & (w["er"] == "ER35")][col]
    return float(r.iloc[0]) if len(r) and pd.notna(r.iloc[0]) else np.nan
