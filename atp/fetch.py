"""Download the open data the platform reads, from open.canada.ca.

- Job Bank: the latest C.JOBBANK_MONTHS monthly files of all postings (English), a rolling window. A month is
  re-downloaded if the portal reports a newer version; months that fall out of the window are removed.
- OaSIS 2022 v1.0 skills and occupation files, and ESDC's 2025 wages: fixed releases, downloaded once.

The StatCan boundary and road files are not fetched (their site refuses automated downloads); the small files
derived from them are in data/derived. Returns True when the set of postings changed.
"""
import json
import re
import shutil
import urllib.request

from . import config as C

UA = {"User-Agent": "atp/1.0 (monthly refresh; github.com/Zosmano/autoworker-transition-platform)"}
CKAN = "https://open.canada.ca/data/api/action/package_show?id="
JOBBANK = "ea639e28-c0fc-48bf-b5dd-b8899bd43072"
DS = "https://open.canada.ca/data/dataset/"
FIXED = {
    "oasis_abilities.csv": "eeb3e442-9f19-4d12-8b38-c488fe4f6e5e/resource/e1d0f684-4f3d-4f6a-adc8-b3a9d0e120fd/download/abilities_oasis_2022_v1.0.csv",
    "oasis_employment_requirements.csv": "eeb3e442-9f19-4d12-8b38-c488fe4f6e5e/resource/b12666f4-cba7-405e-9610-f36318e0f7d5/download/employment-requirements_oasis_2022_v1.0.csv",
    "oasis_example_titles.csv": "eeb3e442-9f19-4d12-8b38-c488fe4f6e5e/resource/266f49d4-59ba-4c50-8171-bc7fde509eda/download/example-titles_oasis-2022_v1.0.csv",
    "oasis_lead_statement.csv": "eeb3e442-9f19-4d12-8b38-c488fe4f6e5e/resource/f1b0b3c4-8982-4104-ba96-794044ad65e8/download/lead-statement_oasis_2022_v1.0.csv",
    "oasis_main_duties.csv": "eeb3e442-9f19-4d12-8b38-c488fe4f6e5e/resource/7453d044-7b41-44cc-b9c6-1112e9e886b5/download/main-duties_oasis-2022_v1.0.csv",
    "oasis_skills.csv": "eeb3e442-9f19-4d12-8b38-c488fe4f6e5e/resource/34eecbcc-c3aa-4568-8715-c946de99df33/download/skills_oasis_2022_v1.0.csv",
    "oasis_work_activities.csv": "eeb3e442-9f19-4d12-8b38-c488fe4f6e5e/resource/2315640d-6bb5-4914-9a46-e8226829e2c0/download/workactivities_oasis_2022_v1.0.csv",
    "oasis_work_context.csv": "eeb3e442-9f19-4d12-8b38-c488fe4f6e5e/resource/2eaf68a6-de91-4366-b3d0-d55f3732ec8c/download/workcontext_oasis_2022_v1.0.csv",
    "esdc_wages_2025.csv": "adad580f-76b0-4502-bd05-20c125de9116/resource/9da94d63-b178-4a64-aeb3-b6a3bd721ad2/download/2a71-das-wage2025opendata-esdc-all-19nov2025-vf.csv",
}
MONTHS = {m: i + 1 for i, m in enumerate(["january", "february", "march", "april", "may", "june", "july", "august",
                                           "september", "october", "november", "december"])}
STATE = C.RAW / "jobbank_source.json"


def _download(url, path):
    tmp = path.with_suffix(".part")
    with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=900) as r, open(tmp, "wb") as f:
        shutil.copyfileobj(r, f, length=1 << 20)
    tmp.replace(path)


def jobbank_months():
    """{'2026-10': (url, version)} for every English monthly file the portal lists."""
    with urllib.request.urlopen(urllib.request.Request(CKAN + JOBBANK, headers=UA), timeout=60) as r:
        res = json.load(r)["result"]["resources"]
    out = {}
    for x in res:
        m = re.match(r"\s*([A-Za-z]+) (\d{4}) Job Postings", x.get("name") or "")
        if not m or "en" not in (x.get("language") or []) or m.group(1).lower() not in MONTHS:
            continue
        key = f"{m.group(2)}-{MONTHS[m.group(1).lower()]:02d}"
        out[key] = (x["url"], x.get("last_modified") or x.get("metadata_modified") or x.get("created"))
    return out


def run():
    C.RAW.mkdir(parents=True, exist_ok=True)
    for name, path in FIXED.items():
        if not (C.RAW / name).exists():
            _download(DS + path, C.RAW / name)
            print(f"downloaded {name}")

    avail = jobbank_months()
    window = sorted(avail)[-C.JOBBANK_MONTHS:]
    state = json.loads(STATE.read_text(encoding="utf-8")) if STATE.exists() else {}
    changed = False
    for key in window:
        url, version = avail[key]
        path = C.RAW / f"jobbank_{key.replace('-', '_')}.csv"
        if path.exists() and state.get(key) == version:
            continue
        _download(url, path)
        state[key] = version
        STATE.write_text(json.dumps(state, indent=2), encoding="utf-8")
        changed = True
        print(f"downloaded Job Bank {key} ({path.stat().st_size / 1e6:.0f} MB)")
    keep = {f"jobbank_{k.replace('-', '_')}.csv" for k in window}
    for f in C.RAW.glob(C.JOBBANK_GLOB):
        if f.name not in keep:
            f.unlink()
            changed = True
            print(f"removed {f.name} (outside the {C.JOBBANK_MONTHS}-month window)")
    print(f"Job Bank window: {window[0]} to {window[-1]}")
    return changed
