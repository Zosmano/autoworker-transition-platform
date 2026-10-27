"""Plant repurposing: which new products best fit each plant's workforce.

Each candidate product gets an hourly staffing pattern: US BLS OEWS industry staffing (May 2025) for the
closest industry, crosswalked from SOC to NOC 2021. Each plant's displaced workers (WORKFORCE_MIX) are then
redeployed into the product's jobs with the same skill-match and training rules as the worker view:
first into jobs reachable with short training, then with longer retraining. What is left is hired outside."""
import json

import numpy as np
import pandas as pd

from . import config as C
from . import jobs as J
from . import skills as S
from . import training as T

STAFFING_FILE = C.ROOT / "data" / "bls_oews_2025_staffing.json"

# Hourly production, maintenance and logistics jobs (SOC major groups 37, 47, 49, 51, 53). The rest
# (managers, engineers, office staff) are salaried and reported as outside hires per 100 hourly jobs.
HOURLY_SOC = ("37-", "47-", "49-", "51-", "53-")

# SOC 2018 -> NOC 2021 for the hourly occupations in the staffing tables (hand-built from both titles and
# OaSIS lead statements; there is no official crosswalk).
SOC_NOC = {
    "37-2011": "65312", "47-2031": "72310", "47-2061": "75110", "47-2111": "72201", "47-2152": "72301",
    "47-2181": "73110", "47-2211": "72102", "49-1011": "72020", "49-2091": "22313", "49-2092": "72422",
    "49-2094": "72422", "49-3011": "72404", "49-3021": "72411", "49-3023": "72410", "49-3031": "72410",
    "49-3043": "72403", "49-3052": "72423", "49-3092": "72410", "49-9041": "72400", "49-9043": "72400",
    "49-9044": "72400", "49-9071": "73201", "51-1011": "92023", "51-2011": "93200", "51-2021": "94203",
    "51-2028": "94202", "51-2031": "94204", "51-2041": "72105", "51-2051": "94212", "51-2090": "94204",
    "51-4021": "94105", "51-4031": "94105", "51-4033": "94106", "51-4034": "94106", "51-4041": "72100",
    "51-4072": "94101", "51-4081": "94106", "51-4111": "72101", "51-4121": "72106", "51-4122": "72106",
    "51-4191": "94104", "51-7011": "72311", "51-7041": "94120", "51-7042": "94124", "51-7099": "94211",
    "51-9061": "94204", "51-9124": "94213", "51-9161": "94106", "51-9198": "95109", "51-9199": "95109",
    "53-1047": "72024", "53-3032": "73300", "53-3033": "75201", "53-7051": "75101", "53-7061": "65312",
    "53-7062": "75101", "53-7063": "95109", "53-7064": "95109", "53-7065": "75101",
}
# Where NOC splits assemblers, inspectors and supervisors by product, the industry decides.
INDUSTRY_NOC = {
    "336100": {"51-2090": "94200", "51-9061": "94200", "51-1011": "92020"},
    "336200": {},                                                   # trucks, buses, trailers: 94204
    "336300": {},
    "336400": {"51-2090": "93200", "51-9061": "93200", "51-2028": "94201"},
    "336500": {},
    "336900": {"51-1011": "92020"},
    "335300": {"51-2090": "94203", "51-2028": "94203", "51-9061": "94203", "51-1011": "92021"},
    "335900": {"51-2090": "94205", "51-9061": "94205", "51-1011": "92021"},
    "333600": {},
    "321900": {"51-2090": "94211", "51-9061": "94211", "51-1011": "92024"},
}

# --- Candidate products (staffing proxies are ASSUMPTIONS; signals are dated news, not forecasts) ----------
PRODUCTS = [
    {"id": "defence", "name": "Armoured and military vehicles",
     "industries": {"336900": 0.5, "336200": 0.5},
     "proxy": "US NAICS 3369 (includes military armoured vehicles) and 3362 (truck bodies, where armouring a commercial chassis sits), weighted equally",
     "carries": "Body shop welding, paint shop, final assembly and test track carry over. Low volumes mean more bench work and fewer moving-line jobs per vehicle; ballistic steel needs new cutting and welding procedures.",
     "signals": [
         ["Stellantis signed an MOU in September 2026 to sell Brampton to Roshel, which says it would bring more than 2,000 jobs and ballistic-steel production and give laid-off workers priority.",
          "https://www.cp24.com/local/peel/2026/09/11/stellantis-signs-mou-with-roshel-on-potential-sale-of-brampton-plant"],
         ["Under its 2026 agreement with Unifor, GM named CAMI the plant of first consideration for any Canadian Armed Forces work it wins.",
          "https://vancouverisland.ctvnews.ca/london/article/cami-plant-to-remain-open-hope-for-potential-armoured-vehicle-production/"],
         ["Canada's Defence Industrial Strategy (February 2026) aims for 70% of defence contracts to go to Canadian firms and lists combat vehicles as a build-in-Canada priority.",
          "https://www.advisor.ca/economy/policy/carney-rolls-out-plans-to-build-up-domestic-defence-sector/"]]},
    {"id": "auto", "name": "Another car or light-truck program",
     "industries": {"336100": 1.0},
     "proxy": "US NAICS 3361, motor vehicle manufacturing (the plants' own industry: a check on the method)",
     "carries": "Everything carries over: body, paint and general assembly. The barrier is an automaker committing a vehicle, not skills.",
     "signals": [
         ["Neither automaker has assigned a new vehicle. Reporting in August 2026 said CAMI would need heavy investment to build vehicles again.",
          "https://gmauthority.com/blog/2026/08/gm-cami-plant-will-need-heavy-investments-to-build-vehicles-again/"]]},
    {"id": "bus", "name": "Trucks, buses and specialty bodies",
     "industries": {"336200": 1.0},
     "proxy": "US NAICS 3362, motor vehicle body and trailer manufacturing",
     "carries": "Paint shop, assembly halls and cranes carry over. Much more welding and fabrication than car assembly.",
     "signals": [
         ["New Flyer opened a facility in Winnipeg in March 2026 so transit buses for Canadian agencies can be built entirely in Canada, targeting 240 a year by 2027.",
          "https://electricautonomy.ca/fleets/municipal-fleets/2026-03-12/new-flyer-expands-winnipeg-factory/"]]},
    {"id": "battery", "name": "Battery modules and energy-storage packs",
     "industries": {"335900": 1.0},
     "proxy": "US NAICS 3359, other electrical equipment (includes battery manufacturing)",
     "carries": "Floor space, power and material handling carry over. Pack assembly needs dry rooms, high-voltage safety training and electrical testing.",
     "signals": [
         ["NextStar Energy's Windsor battery plant employs over 1,300, targets 2,500, and has shifted output toward energy-storage cells as EV demand softened.",
          "https://battery-news.de/en/2026/03/09/nextstar-energy-inaugurates-battery-factory-in-canada/"]]},
    {"id": "grid", "name": "Grid equipment (transformers, switchgear)",
     "industries": {"335300": 1.0},
     "proxy": "US NAICS 3353, electrical equipment manufacturing",
     "carries": "Large halls, cranes and the paint shop suit transformer tanks and enclosures. Coil winding and high-voltage testing are new skills.",
     "signals": [
         ["Hitachi Energy announced a C$479 million transformer insulation factory in London, Ontario (October 2026), citing a transformer shortage slowing grid and housing projects.",
          "https://www.hitachienergy.com/news-and-events/press-releases/2026/10/hitachi-energy-invests-479-million-cad-to-bring-critical-transformer-manufacturing-capability-to-canada"],
         ["CES Transformers opened an expanded Markham plant in January 2026, tripling capacity with 150+ jobs planned by 2030.",
          "https://transformer-technology.com/ces-transformers-expands-markham-plant-to-meet-rising-power-demand/"]]},
    {"id": "rail", "name": "Rail and transit vehicles",
     "industries": {"336500": 1.0},
     "proxy": "US NAICS 3365, railroad rolling stock manufacturing",
     "carries": "Paint shop and long assembly bays carry over if rail access can be added. Heavier welding and electrical integration.",
     "signals": [
         ["Alstom will do final assembly in Thunder Bay for VIA Rail's C$4.7 billion fleet (September 2026) and the TTC's C$2.3 billion order for 70 subway trains.",
          "https://railwaynews.net/alstom-wins-toronto-subway-deal-siemens-to-power-tri-rail.html"]]},
    {"id": "parts", "name": "EV and auto parts",
     "industries": {"336300": 1.0},
     "proxy": "US NAICS 3363, motor vehicle parts manufacturing",
     "carries": "Stamping, welding and machining would need new equipment; assembly and logistics skills carry over directly.",
     "signals": []},
    {"id": "aero", "name": "Aerospace structures and parts",
     "industries": {"336400": 1.0},
     "proxy": "US NAICS 3364, aerospace product and parts manufacturing",
     "carries": "Assembly discipline and quality systems carry over. Aerospace certification, machining and composite work are new; the industry hires many engineers.",
     "signals": [
         ["The Defence Industrial Strategy also prioritises domestic aerospace production.",
          "https://dsm.forecastinternational.com/2026/02/24/canada-pushes-for-greater-self-reliance-in-defense-acquisition/"]]},
    {"id": "power", "name": "Engines, turbines and drivetrains",
     "industries": {"333600": 1.0},
     "proxy": "US NAICS 3336, engine, turbine and power transmission equipment",
     "carries": "Assembly lines adapt well; precision machining is the main new capability.",
     "signals": []},
    {"id": "housing", "name": "Factory-built housing",
     "industries": {"321900": 1.0},
     "proxy": "US NAICS 3219, other wood products (includes manufactured and prefabricated buildings)",
     "carries": "Large flat floors and material handling suit modular housing. Woodworking and carpentry are new; pay is typically lower than auto.",
     "signals": [
         ["Build Canada Homes has a C$13 billion initial budget and favours modular and factory-built methods, starting with six federal sites including Toronto's Downsview.",
          "https://www.canada.ca/en/housing-infrastructure-communities/news/2026/02/build-canada-homes-launches-request-for-information-on-modern-methods-of-construction.html"]]},
]

QUICK_MAX_MONTHS = C.PLANNER_MAX_TRAIN_MONTHS   # redeploy with short training
QUICK_MIN_MATCH = C.PLANNER_MIN_MATCH
RETRAIN_MAX_MONTHS = 24                         # ...or with up to two years of retraining
RETRAIN_MIN_MATCH = 65
HEADCOUNT_SHARE = 1.0                           # product sized to employ every displaced worker


def staffing(nocs):
    """Per product: hourly job shares by NOC, and salaried jobs per 100 hourly."""
    raw = json.loads(STAFFING_FILE.read_text())["industries"]
    out = {}
    for p in PRODUCTS:
        hourly, salaried = {}, 0.0
        for ind, wt in p["industries"].items():
            occ = raw[ind]["occ"]
            h = {s: v for s, v in occ.items() if s.startswith(HOURLY_SOC)}
            tot_h = sum(h.values())
            salaried += wt * (sum(occ.values()) - tot_h) / tot_h
            for s, v in h.items():
                noc = INDUSTRY_NOC[ind].get(s, SOC_NOC[s])
                assert noc in nocs, (s, noc)
                hourly[noc] = hourly.get(noc, 0) + wt * v / tot_h
        out[p["id"]] = {"roles": dict(sorted(hourly.items(), key=lambda x: -x[1])),
                        "salaried_per_100": round(100 * salaried, 1)}
    return out


def _assign(supply, demand, opts):
    """Greedy: workers first keep their own occupation where the product has it; then roles with the fewest
    eligible sources are filled first, each from its best-matching sources."""
    supply, need, out = dict(supply), dict(demand), []
    for role in need:
        own = [x for x in opts.get(role, []) if x[0] == role]
        if own and supply.get(role, 0) > 0 and need[role] > 0:
            take = min(supply[role], need[role])
            supply[role] -= take
            need[role] -= take
            out.append((role, role, take, own[0][1], own[0][2]))
    for role in sorted(need, key=lambda r: len(opts.get(r, []))):
        for o, match, months in opts.get(role, []):
            take = min(supply[o], need[role])
            if take <= 0:
                continue
            supply[o] -= take
            need[role] -= take
            out.append((o, role, take, match, months))
    return out, supply, need


def fit(m, req, prog_list, wages, key, plant, product, roles, headcount_share=HEADCOUNT_SHARE):
    """Redeploy one plant's workforce into one product's hourly jobs."""
    supply = {o: s * plant["displaced"] for o, s in C.WORKFORCE_MIX.items()}
    jobs = headcount_share * plant["displaced"]
    demand = {r: sh * jobs for r, sh in roles.items()}
    pairs, gaps = [], {}
    for o in C.WORKFORCE_MIX:
        tr = S.transfer(m, o, list(roles)).set_index("noc")
        for r in roles:
            mt = float(tr.at[r, "match"])
            gaps[o, r] = tr.at[r, "gaps"]
            comp = bool(req["compulsory_on"].get(r, False) or req["licence"].get(r, False))
            months = T.months_for(r, o, comp, mt, prog_list, key)[0]
            pairs.append((o, r, mt, months))

    def options(min_match, max_months):
        d = {}
        for o, r, mt, mo in pairs:
            if mt >= min_match and mo <= max_months:
                d.setdefault(r, []).append((o, mt, mo))
        return {r: sorted(v, key=lambda x: (-x[1], x[2])) for r, v in d.items()}

    quick, sup, need = _assign(supply, demand, options(QUICK_MIN_MATCH, QUICK_MAX_MONTHS))
    retrain, sup, need = _assign(sup, need, options(RETRAIN_MIN_MATCH, RETRAIN_MAX_MONTHS))
    q, rt = sum(x[2] for x in quick), sum(x[2] for x in retrain)
    moved = quick + retrain
    er = plant["economic_region"]
    wage = lambda n: J.wage_lookup(wages, n, er, "median")
    def avg_wage(shares):
        x = [(s, wage(n)) for n, s in shares.items()]
        x = [(s, v) for s, v in x if np.isfinite(v)]
        return sum(s * v for s, v in x) / sum(s for s, _ in x)
    pay_product, pay_plant = avg_wage(roles), avg_wage(C.WORKFORCE_MIX)

    # Skills to build across the redeployed workforce: each move's gaps, weighted by workers and gap size.
    need_w = {}
    for o, r, n, _, _ in moved:
        for d, have, want in gaps[o, r]:
            need_w[d] = need_w.get(d, 0) + n * (want - have) * want
    top = sorted(need_w, key=need_w.get, reverse=True)[:5]
    return {
        "plant": key, "product": product["id"], "product_name": product["name"], "jobs": round(jobs),
        "filled_quick": round(q), "filled_retrain": round(rt), "outside_hires": round(jobs - q - rt),
        "share_quick": round(q / jobs, 3), "share_total": round((q + rt) / jobs, 3),
        "avg_match": round(sum(x[2] * x[3] for x in moved) / max(q + rt, 1), 1),
        "train_person_months": round(sum(x[2] * x[4] for x in moved)),
        "trained_workers": round(sum(x[2] for x in moved if x[4] > 1)),
        "pay_vs_auto": round(pay_product / pay_plant, 3),
        "top_gaps": "; ".join(d.split(":", 1)[1] for d in top),
        "flows": [{"origin": o, "role": r, "workers": round(n, 1), "match": mt, "months": mo,
                   "stage": "quick" if i < len(quick) else "retrain"} for i, (o, r, n, mt, mo) in enumerate(moved)],
        "unfilled": {r: round(v, 1) for r, v in need.items() if v >= 0.5},
    }


def build(r):
    """Fit of every product to every plant; returns (staffing patterns, results table, flows)."""
    m, req, w = r["profiles"], r["requirements"], r["wages"]
    prog_list = r["programs"].to_dict("records")
    staff = staffing(set(m.index))
    rows = []
    for key, plant in C.PLANTS.items():
        for p in PRODUCTS:
            rows.append(fit(m, req, prog_list, w, key, plant, p, staff[p["id"]]["roles"]))
    res = pd.DataFrame(rows)
    res["salaried_per_100"] = res["product"].map(lambda p: staff[p]["salaried_per_100"])
    return staff, res.sort_values(["plant", "share_quick", "share_total"], ascending=[True, False, False])
