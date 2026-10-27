"""Build Next Shift end to end: job postings -> drive times -> skill matching -> plan -> app.

    python run_all.py              # uses cached postings and drive times when present
    python run_all.py --rebuild    # re-reads the Job Bank files and rebuilds the road graph
"""
import argparse
import json

import pandas as pd

from atp import config as C


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--rebuild", action="store_true")
    a = ap.parse_args()
    if a.rebuild:
        for f in ("jobs_on.pkl", "drive_nodes.pkl"):
            (C.CACHE / f).unlink(missing_ok=True)

    from atp import app, jobs, match, repurpose
    jobs.load()
    r = match.build()
    r["staffing"], rp = repurpose.build(r)
    C.OUT.mkdir(parents=True, exist_ok=True)
    names = r["names"]

    tp = r["transitions"].copy()
    tp["origin_name"], tp["target_name"] = tp["origin"].map(names), tp["noc"].map(names)
    tp["top_gaps"] = tp["gaps"].map(lambda g: "; ".join(x[0].split(":", 1)[1] for x in g[:5]))
    cols = ["plant", "origin", "origin_name", "noc", "target_name", "match", "readiness", "relevance",
            "vac_30", "vac_45", "vac_60", "vac_90", "wage_target", "wage_ratio", "train_months", "train_basis",
            "compulsory_on", "score", "top_gaps"]
    tp.sort_values(["plant", "origin", "score"], ascending=[True, True, False])[cols].to_csv(
        C.OUT / "transitions.csv", index=False)

    pl = r["planner"].copy()
    pl["origin_name"], pl["target_name"] = pl["origin"].map(names), pl["target"].map(names)
    pl.to_csv(C.OUT / "reemployment_plan.csv", index=False)

    progs = r["programs"].drop(columns=["lat", "lon"]).copy()
    progs["target_nocs"] = progs["target_nocs"].str.join(";")
    progs.to_csv(C.OUT / "training_programs_located.csv", index=False)

    summary = {}
    for key, p in C.PLANTS.items():
        x = pl[pl["plant"] == key]
        placed = int(x.loc[x["target"].notna(), "workers"].sum())
        total = int(x["workers"].sum())
        j = r["jobs"]
        summary[key] = {
            "plant": p["name"], "displaced": total, "placed_12m": placed, "not_placed": total - placed,
            "pay_kept_placed": round(float((x["workers"] * x["wage_ratio"]).sum() / max(placed, 1)), 3),
            "postings_within": {b: int((j[f"min_{key}"] <= b).sum()) for b in C.COMMUTE_BANDS},
            "top_destinations": x[x["target"].notna()].groupby("target_name")["workers"].sum()
                                 .sort_values(ascending=False).head(8).to_dict(),
        }
    flows = [dict(f, plant=x["plant"], product=x["product"]) for _, x in rp.iterrows() for f in x["flows"]]
    flows = pd.DataFrame(flows)
    flows["origin_name"], flows["role_name"] = flows["origin"].map(names), flows["role"].map(names)
    flows.to_csv(C.OUT / "repurposing_flows.csv", index=False)
    rp.drop(columns=["flows", "unfilled"]).to_csv(C.OUT / "repurposing.csv", index=False)
    for key in C.PLANTS:
        x = rp[rp["plant"] == key]
        summary[key]["products_by_quick_redeployment"] = dict(zip(x["product_name"], x["share_quick"]))

    summary["postings"] ={"rows": int(len(r["jobs"])), "located": round(float(r["jobs"]["lat"].notna().mean()), 4),
                           "window": [r["jobs"]["month"].min(), r["jobs"]["month"].max()]}
    (C.OUT / "summary.json").write_text(json.dumps(summary, indent=2))
    print(json.dumps(summary, indent=2))
    app.build(r)


if __name__ == "__main__":
    main()
