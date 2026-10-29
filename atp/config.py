"""Every assumption and input path in one place."""
import os
import pathlib

ROOT = pathlib.Path(__file__).resolve().parent.parent
RAW = ROOT / "data" / "raw"
CACHE = ROOT / "data" / "cache"
OUT = ROOT / "outputs"
TRAINING_FILE = ROOT / "data" / "training_programs.csv"

# Large StatCan files shared with the Canada Post project; override with environment variables.
_CP = ROOT.parent / "Canada Post Analysis"
FSA_BOUNDARY_ZIP = pathlib.Path(os.environ.get("ATP_FSA_BOUNDARY", _CP / "Boundary_File_lfsa000a21a_e.zip"))
ROAD_NETWORK_ZIP = pathlib.Path(os.environ.get("ATP_ROAD_NETWORK", _CP / "lrnf000r21a_e.zip"))

JOBBANK_GLOB = "jobbank_*.csv"
WAGES_FILE = RAW / "esdc_wages_2025.csv"

# --- The two plants -------------------------------------------------------------------------------
# Coordinates: NRCan geolocation service on the street address.
PLANTS = {
    "brampton": {
        "name": "Stellantis Brampton Assembly",
        "short": "Brampton",
        "address": "2000 Williams Parkway East, Brampton, ON",
        "lat": 43.75040, "lon": -79.71267,
        "economic_region": "ER3530",     # Toronto
        "union": "Unifor Local 1285",
        # About 3,000 hourly workers idle since Feb 2025 (Unifor, Aug 2026); ~240 moved to Windsor.
        "displaced": 2760,
        "status": "Idle since February 2025. Stellantis signed a preliminary agreement (MOU) to sell the plant "
                  "to armoured-vehicle maker Roshel; Unifor opposes the sale. Laid-off workers would get first "
                  "consideration for any Roshel jobs.",
    },
    "cami": {
        "name": "GM CAMI Assembly, Ingersoll",
        "short": "Ingersoll",
        "address": "300 Ingersoll Street South, Ingersoll, ON",
        "lat": 43.02153, "lon": -80.88763,
        "economic_region": "ER3560",     # London
        "union": "Unifor Local 88",
        "displaced": 1200,
        "status": "Idle since May 2025; GM ended BrightDrop van production in October 2025. A federal-provincial "
                  "working group with GM and Unifor is evaluating options, including military vehicles.",
    },
}

# --- Plant workforce mix (ASSUMPTION) -------------------------------------------------------------
# No public table gives the occupation mix of an Ontario assembly plant (NAICS 3361 x NOC unit group is
# not published). This is a typical body-paint-assembly plant profile: production ~80%, skilled trades
# ~13%, supervision ~3%. Replace with the union's seniority list when available.
WORKFORCE_MIX = {
    "94200": 0.700,   # Motor vehicle assemblers, inspectors and testers
    "75101": 0.070,   # Material handlers
    "94213": 0.030,   # Industrial painters and coaters
    "72400": 0.045,   # Industrial mechanics (millwrights)
    "72201": 0.040,   # Industrial electricians
    "72101": 0.015,   # Tool and die makers
    "72106": 0.020,   # Welders
    "72301": 0.010,   # Pipefitters
    "72410": 0.010,   # Mechanical repairers, motor vehicle manufacturing
    "92020": 0.030,   # Supervisors, motor vehicle assembling
    "22301": 0.015,   # Mechanical / manufacturing engineering technicians
    "65310": 0.015,   # Cleaners / plant services
}

# --- Commuting --------------------------------------------------------------------------------------
# Free-flow speeds (km/h) by Road Network File CLASS; peak congestion multiplies travel time.
ROAD_SPEED_KMH = {"10": 100, "11": 90, "12": 80, "13": 70, "20": 60, "21": 55, "22": 50, "23": 40,
                  "24": 20, "25": 50, "26": 40, "27": 40, "28": 20}
DEFAULT_SPEED_KMH = 40
PEAK_FACTOR = {"brampton": 1.35, "cami": 1.10}     # GTA rush hour vs Oxford County
ACCESS_SPEED_KMH = 30                                 # from road graph to the destination point
ROAD_BUFFER_KM = 160                                  # road graph covers this radius around each plant
COMMUTE_BANDS = [30, 45, 60, 90]                      # minutes
DEFAULT_COMMUTE_MIN = 60

# --- Skills matching --------------------------------------------------------------------------------
DESCRIPTOR_FILES = {"skills": "oasis_skills.csv", "abilities": "oasis_abilities.csv",
                    "work_activities": "oasis_work_activities.csv"}
GAP_MIN_TARGET = 3          # a gap counts only where the target needs proficiency >= 3 (of 5)
GAP_MIN_DIFF = 1            # ...and the target exceeds the worker by at least this much
READINESS_WEIGHT = 0.6      # match = 0.6 x readiness (no shortfall) + 0.4 x relevance (same kind of work)
GOOD_FIT = 80               # skill match >= this is a "good fit"

# Training time by target TEER (second digit of NOC 2021), in months; worker's own TEER or lower = 0-3.
TEER_TRAINING_MONTHS = {0: 24, 1: 42, 2: 24, 3: 12, 4: 3, 5: 1}
TRAINING_MAX_MIN = 75       # a program counts as "nearby" within this many minutes of the plant

# Ranking weights for the default worker view (the app lets the worker re-weight).
RANK_WEIGHTS = {"skill": 0.45, "demand": 0.25, "wage": 0.20, "training": 0.10}
MIN_MATCH_LISTED = 60       # transitions below this skill match are not shown
POSTINGS_PER_TARGET = 25    # sample postings shown per plant and occupation

# --- Absorption planner (ASSUMPTIONS) ---------------------------------------------------------------
PLANNING_MONTHS = 12        # horizon for re-employment
CAPTURE_SHARE = 0.10        # share of local openings displaced workers can realistically win
PLANNER_COMMUTE_MIN = 60
PLANNER_MIN_MATCH = 75      # good-fit destinations only (75 admits truck driving for assemblers: 78)
PLANNER_MIN_WAGE_RATIO = 0.60
PLANNER_MAX_TRAIN_MONTHS = 6     # longer routes count as retraining, not quick placement

# --- Wages ------------------------------------------------------------------------------------------
HOURS_PER_YEAR = 2080
# OEM assembly pay sits near the top of the regional range for assemblers; we use ESDC's "high" wage
# (90th percentile) for NOC 94200 in the plant's economic region as the default current wage.
CURRENT_WAGE_PERCENTILE = "high"

BETTER_JOBS_ONTARIO = {
    "max_short": 28000, "max_long": 35000, "living_allowance_week": 500,
    "url": "https://www.ontario.ca/page/better-jobs-ontario",
}
