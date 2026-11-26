"""
Project-wide parameters. Values here mirror docs/preregistration.md.
Changing any of them after the first commit requires an entry in docs/deviations.md.
"""

from datetime import date, timedelta
from pathlib import Path

# --- Paths ---
ROOT = Path(__file__).resolve().parent
DATA = ROOT / "data"
RAW = DATA / "raw"
RAW_ITAD = RAW / "itad"
RAW_STEAM_APPDETAILS = RAW / "steam_appdetails"
RAW_STEAM_REVIEWS = RAW / "steam_reviews"
MANUAL = DATA / "manual"
INTERIM = DATA / "interim"
PROCESSED = DATA / "processed"
OUTPUT = ROOT / "output"
FIGURES = OUTPUT / "figures"
TABLES = OUTPUT / "tables"
DOCS = ROOT / "docs"

# --- Sample period (D1, D13) ---
SAMPLE_START = date(2016, 1, 1)
DATA_COLLECTION_DATE = None  # set to the date you download price histories, e.g. date(2026, 9, 7)
MIN_HISTORY_DAYS = 180
HOLDOUT_START = date(2025, 1, 1)


def sample_end():
    if DATA_COLLECTION_DATE is None:
        raise ValueError("Set DATA_COLLECTION_DATE in config.py before building the sample.")
    return DATA_COLLECTION_DATE - timedelta(days=MIN_HISTORY_DAYS)


# --- Eligibility (D2, D3) ---
MIN_LAUNCH_PRICE_USD = 39.99
MAX_PC_LAG_DAYS = 30          # PC launch within 30 days of first release on any platform
REFERENCE_REGION = "US"
REFERENCE_SHOP = "steam"      # confirm ITAD's shop identifier and record it in docs/data_log.md

# --- Discount measurement (D5, D6, D15) ---
LAUNCH_DISCOUNT_DAYS = 14
DEPTH_DAYS = [45, 90, 180]
PRIMARY_DEPTH_DAY = 90
FIRST_CUT_THRESHOLD = 0.20
EARLY_CUT_MAX_DAY = 90
MIN_NORM_GAMES = 5
DAILY_SERIES_DAYS = 365

# --- Tentpoles (D4) ---
TENTPOLE_QUANTILE = 0.75
TENTPOLE_LOOKBACK_YEARS = 3
MIN_TENTPOLE_GAMES = 4
SIZE_WINDOW_DAYS = 30

# --- Event study (D7, D8, D9) ---
EST_WINDOW = (-250, -30)
CAR_E_WINDOW = (-1, 1)
CAR_D_WINDOWS = [(0, 2), (0, 10)]
PLOT_WINDOW = (-10, 20)
US_EXCHANGES = {"Nasdaq", "NYSE"}   # day 0 = discount date for these (D9)
PRE_EVENT_RETURN_DAYS = 60

# --- Trading rule (D12) ---
COST_BPS = 20
COST_BPS_ROBUSTNESS = [10, 40]
PLACEBO_RUNS = 1000
PLACEBO_MIN_GAP_DAYS = 60

# --- Inference ---
BOOTSTRAP_RUNS = 10_000
RANDOM_SEED = 42

# --- Data collection ---
REQUEST_DELAY_SECONDS = 1.0

# --- Pilot publishers (build order: start small) ---
PILOT_PUBLISHERS = ["Capcom", "Ubisoft", "Square Enix"]
