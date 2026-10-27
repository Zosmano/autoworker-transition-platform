# Next Shift: Autoworker Transition Platform

About 2,760 hourly workers at **Stellantis Brampton Assembly** (idle since February 2025, with a sale to Roshel pending) and 1,200 at **GM CAMI Ingersoll** (idle since BrightDrop production ended in October 2025) need new work. Next Shift matches each worker's skills to real job openings within driving distance, shows the pay and skill gaps, and points to nearby training and funding. It also gives planners an estimate of how many workers local openings can absorb and where retraining money does the most good. It also tests which new products each plant's workforce could build if the plant were retooled.

Independent analysis built on public data. Not produced by or affiliated with Stellantis, General Motors, Unifor, or any government.

## What it does

**For a worker** (the "Find my next job" tab):
1. Pick your plant and your job, or search any job title, then enter your hourly pay and the longest drive you'd make.
2. You get a ranked list of the occupations you could move into. Each one shows:
   - skill match (0–100)
   - openings per month within your commute
   - typical pay against yours
   - training time, and whether a licence is needed
3. Open a row to see the specific skills to build, what employers ask for, training programs nearby with drive times, and recent postings.

**For union, Employment Ontario and government planners** (the "Re-employment plan" tab):
1. Estimates how many displaced workers good-fit local openings can absorb in 12 months, broken down by plant job.
2. Shows where those workers go.
3. Shows which training routes have openings left for the workers not yet placed.
4. Every assumption is a slider.

**For anyone weighing what the plants could make next** (the "New products" tab):
1. Ten candidate products, from armoured vehicles and buses to battery packs, transformers, rail cars, aerospace parts and factory-built housing.
2. For each, how much of its hourly workforce the laid-off workers could fill with short training, how many need longer retraining (and into which jobs), and how many must be hired from outside.
3. Shows typical pay against auto jobs, salaried hires needed, the skills to build, what plant equipment carries over, and dated news on demand for each product in Canada.

## Results (default assumptions)

| | Brampton | Ingersoll |
|---|---|---|
| Displaced workers | 2,759 | 1,200 |
| Job postings within a 60-minute rush-hour drive (Apr–Sep 2026) | 38,537 | 4,968 |
| Placed in good-fit local jobs within 12 months | ~1,440 (52%) | ~390 (33%) |
| Pay kept by those placed | ~83% | ~69% |

- **Skilled trades and material handlers all place.** Millwrights, electricians, welders and tool and die makers move into local jobs, typically keeping 65–95% of their plant pay. Plant pay is set at the region's high wage for each job, so the true figure depends on each worker's actual rate.
- **Assemblers are the hard group.** They are about 70% of each plant. In Brampton, about a third (≈645 of 1,932) place within a year; in Ingersoll, fewer than 1 in 10 (≈66 of 840). Their closest jobs either pay much less (assembly elsewhere, food processing) or need training: Class A truck driving takes about a month, while welding, machining and the trades take 8–12 months.
- **Ingersoll is the harder case.** It has an eighth of Brampton's openings within an hour, and lower posted pay, so retraining, support for longer commutes and new production at the plant matter more there.

### New products (plant sized to re-employ every laid-off worker)

| Product | Ready within 6 months | After up to 2 years' retraining | Typical pay vs auto jobs (Brampton / Ingersoll) | Salaried hires per 100 hourly |
|---|---|---|---|---|
| Grid equipment (transformers, switchgear) | 97% | 1% | 82% / 75% | 58 |
| Battery modules and storage packs | 95% | 1–2% | 80% / 72% | 55 |
| Another car or light-truck program | 95% | 3% | 100% / 100% | 13 |
| EV and auto parts | 94% | 4% | 85% / 80% | 25 |
| Factory-built housing | 92–93% | 5–6% | 80% / 71% | 17 |
| Armoured and military vehicles | 84% | 14% | 86% / 80% | 31 |
| Engines, turbines and drivetrains | 82% | 17% | 88% / 83% | 62 |
| Trucks, buses and specialty bodies | 81% | 17% | 87% / 81% | 20 |
| Rail and transit vehicles | 75% | 24% | 91% / 83% | 50 |
| Aerospace structures and parts | 39% | 57% | 113% / 90% | 129 |

- **Skills are rarely the barrier.** Assembly, material handling and trades skills carry over to almost any line-based product. For all but aerospace, at least three-quarters of the jobs can be filled within six months, and nearly all after retraining.
- **Welding is the main retraining need for vehicle products.** Armoured vehicles, buses and rail cars need many more welders than car assembly. For armoured vehicles, about 280 Brampton and 120 Ingersoll assemblers would retrain as welders, which takes 7–8 months at a nearby college. For rail, the figures are about 450 and 200.
- **Armoured vehicles combine a good skills fit with the strongest current demand signal.** Roshel's proposed purchase of Brampton, GM naming CAMI its first choice for any defence work, and the 2026 Defence Industrial Strategy all point that way. Their pay is about 85% of auto-job pay on regional medians.
- **Electrical products (grid equipment, batteries) fit best but pay less**, and they need about four times as many salaried engineers and staff per hourly job.
- **Aerospace is a poor fit.** It needs aircraft assemblers and mechanics with formal training, and more salaried staff than hourly.
- **Both plants rank the same** because both use the same estimated workforce mix. Only pay and nearby training differ, so Ingersoll's lower regional wages show up as lower pay ratios. Each union's seniority list would separate them.

These are model estimates. See **Limits**.

## Run it

```bash
python -m pip install -r requirements.txt
```

```bash
python run_all.py
```

- **Input data is not in the repository** because it is large (about 300 MB). Download it into `data/raw/` and point `ATP_FSA_BOUNDARY` and `ATP_ROAD_NETWORK` at the two StatCan zips. The file names are in the Data table below.
  - [Job Bank job postings](https://open.canada.ca/data/en/dataset/ea639e28-c0fc-48bf-b5dd-b8899bd43072): the monthly files, saved as `jobbank_YYYY_MM.csv`
  - [OaSIS](https://open.canada.ca/data/en/dataset/eeb3e442-9f19-4d12-8b38-c488fe4f6e5e)
  - [ESDC Wages](https://open.canada.ca/data/en/dataset/adad580f-76b0-4502-bd05-20c125de9116)
  - [StatCan 2021 boundary files](https://www12.statcan.gc.ca/census-recensement/2021/geo/sip-pis/boundary-limites/index2021-eng.cfm): forward sortation areas
  - [StatCan 2021 Road Network File](https://www12.statcan.gc.ca/census-recensement/2021/geo/sip-pis/rnf-frr/index2021-eng.cfm)
  - The training list and the BLS staffing file are included in `data/`.
- **Run time:** about 30 seconds once caches exist. Use `--rebuild` to re-read the Job Bank files and rebuild the road graph.
- **Output:** `outputs/next_shift.html` is the self-contained app (about 1.5 MB). It works offline in any browser.

## Data

| Input | Source | Used for |
|---|---|---|
| `data/raw/jobbank_2026_04..09.csv` | ESDC **Job Bank open data**, all postings, April to September 2026 | 89,557 Ontario postings after removing same-day duplicates; 98.9% located by postal code (38%) or town |
| `data/raw/oasis_*.csv` | ESDC **OaSIS 2022** (Occupational and Skills Information System) | Ratings from 0 to 5 on 122 descriptors (33 skills, 49 abilities, 40 work activities) for 516 occupations; employment requirements; example job titles |
| `data/raw/esdc_wages_2025.csv` | ESDC **Wages 2025** by occupation and economic region | Default plant pay (the region's "high" wage for each job) and pay where postings give none |
| `Boundary_File_lfsa000a21a_e.zip` | StatCan 2021 FSA boundary file | Locating postings by postal code |
| `lrnf000r21a_e.zip` | StatCan 2021 Road Network File | Rush-hour drive times from each plant (373K road segments) |
| NRCan geonames and geolocation services | Natural Resources Canada | Locating towns, the plants and the college campuses (cached in `data/cache/`) |
| `data/bls_oews_2025_staffing.json` | US BLS **Occupational Employment and Wage Statistics**, May 2025 national industry-specific estimates, for 10 industries (retrieved October 2026) | Hourly workforce of each candidate product. No Canadian occupation-by-industry table exists at this detail |
| `data/training_programs.csv` | Curated from college and Ontario government pages; every link checked | 26 programs across Sheridan, Humber, Conestoga, Fanshawe and provincial routes |

The Job Bank, OaSIS and wage files are under the Open Government Licence – Canada. The two large StatCan files are read from the sibling `Canada Post Analysis` folder by default; set `ATP_FSA_BOUNDARY` and `ATP_ROAD_NETWORK` to point elsewhere.

## Method

**Skill match** compares a worker's occupation `o` with a target occupation `t`, using ratings `o_d` and `t_d` on each descriptor:

- **Readiness** = 100 × (1 − Σ max(0, t_d − o_d)·t_d / Σ t_d²). This is the share of what the job relies on that the worker already has.
- **Relevance** = 50 × (1 + correlation of the two profiles). This captures whether the job uses the same kind of skills. Without it, every less demanding job would score as a perfect fit.
- **Match** = 0.6 × readiness + 0.4 × relevance.
- **Gaps** are descriptors where the job needs 3+ and the worker is a full level or more short.

**Ranking** blends four things, each re-weightable in the app:
- skill match
- openings within the commute (on a log scale)
- pay relative to the worker's
- training time

**Training time** depends on the target job:
- **A few weeks** when the job is at or below the worker's skill level (TEER), is low-formal-training or in the same occupational field, has a match of 85+, and needs no licence.
- **The shortest listed program** within 75 minutes of the plant, otherwise.
- **A typical length for the job's TEER**, when no program is listed.

**Re-employment plan** takes four steps:
1. Split the displaced workers across plant jobs using an estimated workforce mix.
2. Give each destination occupation room for 10% of its openings over 12 months.
3. Place workers, starting with the plant jobs that have the fewest good options. A good option needs a match of 75+, at least 60% of current pay, and no more than 6 months of training.
4. Count everyone left over as the retraining and outreach target.

The app recomputes all of this live. The Python version, `atp/match.py`, writes the same tables to CSV, and the two agree within about 1%.

**New products** (`atp/repurpose.py`) take five steps:
1. Take each product's staffing from its closest US industry (BLS OEWS). Keep the hourly production, maintenance and logistics jobs, and count managers, engineers and office staff as salaried hires.
2. Map US occupations (SOC) to NOC 2021 by hand, using OaSIS titles and lead statements. Where NOC splits assemblers by product, the industry decides: aircraft assemblers for aerospace, transformer assemblers for grid equipment, and so on.
3. Size the product to employ every laid-off worker; the app's slider changes this.
4. Fill the product's jobs. Workers whose own job exists in the product keep it. Then the jobs with the fewest eligible workers are filled first, each from the best-matching plant jobs. The first pass needs a match of 75+ and up to 6 months of training (the worker view's rules), and the second allows a match of 65+ and up to 24 months.
5. Count anything left as outside hires.

Pay compares ESDC regional median wages for the product's jobs with those for the plant's jobs.

## Code (`atp/`)

| File | What it does |
|---|---|
| `config.py` | Every assumption, including plants, workforce mix, speeds, weights and planner settings |
| `geo.py` | FSA centroids, place-name and address geocoding (cached) |
| `roads.py` | Road graph and Dijkstra drive times from each plant |
| `jobs.py` | Loading, de-duplicating, annualising wages, locating and timing the Job Bank postings; ESDC wages |
| `skills.py` | OaSIS profiles, requirements (including whether a trade is compulsory in Ontario), and transferability |
| `training.py` | Training catalogue and training-time rules |
| `match.py` | The engine: ranked transitions per plant and job, and the absorption plan |
| `repurpose.py` | Candidate products, their staffing, and workforce fit for each plant |
| `app.py`, `app_template.html` | The self-contained app |

## Outputs (`outputs/`)

| File | What it is |
|---|---|
| `next_shift.html` | The app |
| `transitions.csv` | Every plant × plant job × target occupation with match 60+: match, openings by commute band, pay, training, score, top gaps |
| `reemployment_plan.csv` | Placements by plant job and destination, and unplaced workers |
| `training_programs_located.csv` | Programs with drive times from each plant |
| `repurposing.csv` | Every plant × product: jobs filled quickly, after retraining and from outside; pay; salaried hires; skills to build |
| `repurposing_flows.csv` | Which plant jobs move into which product jobs, with match and training months |
| `summary.json` | Headline numbers |

## Limits

- **Postings are not hires.** Job Bank under-covers some employers, including the automakers' own hiring sites, and some postings are re-posts.
- **Occupations, not people.** OaSIS rates occupations. A worker's own tickets, seniority and other experience can change their fit a lot, so treat the list as a starting point for a counselling conversation.
- **The workforce mix is assumed.** No public table breaks down an Ontario assembly plant by occupation. The union's seniority list would replace `WORKFORCE_MIX`.
- **The 10% share of openings won is assumed.** Placement outcomes from the action centres would calibrate it.
- **Drive times assume a car,** with a rush-hour factor applied to free-flow road speeds.
- **The new-products analysis measures workforce fit only.** Whether a product is viable at a plant also depends on buyers, capital, retooling and the owner's plans. The news items are context, not a forecast. Staffing comes from US industries that are broader than the products (for example, NAICS 3369 includes motorcycles as well as armoured vehicles), and US plants may staff differently from Ontario ones.

## Next steps for a real deployment

1. Load the members' actual job classifications and home postal codes, so commutes are measured from home rather than the plant.
2. Add a weekly Job Bank refresh, and job feeds from Roshel and other employers committed to hiring.
3. Have counsellors record outcomes (applied, hired, enrolled) to calibrate the planner's assumptions.
