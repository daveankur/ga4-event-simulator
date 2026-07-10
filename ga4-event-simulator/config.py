import json
import os
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent

load_dotenv(BASE_DIR / ".env")

GA4_MEASUREMENT_ID = os.environ.get("GA4_MEASUREMENT_ID")
GA4_API_SECRET = os.environ.get("GA4_API_SECRET")

with open(BASE_DIR / "data_pools.json") as f:
    DATA_POOLS = json.load(f)

# Cumulative % of simulated users reaching each step, per PRD 5.3.
DEFAULT_DROPOFF = {
    "signup_page_viewed": 100,
    "signup_step1_submitted": 80,
    "signup_step2_submitted": 65,
    "signup_verification": 55,
    "signup_completed": 45,
}


def parse_dropoff_override(arg):
    """Accepts either a path to a JSON file or an inline JSON string.

    Expected shape: {"signup_page_viewed": 100, "signup_step1_submitted": 80, ...}
    Missing keys fall back to DEFAULT_DROPOFF values.
    """
    if arg is None:
        return dict(DEFAULT_DROPOFF)

    path = Path(arg)
    if path.exists():
        with open(path) as f:
            override = json.load(f)
    else:
        override = json.loads(arg)

    merged = dict(DEFAULT_DROPOFF)
    merged.update(override)
    return merged


def require_credentials():
    if not GA4_MEASUREMENT_ID or not GA4_API_SECRET:
        raise SystemExit(
            "Missing GA4_MEASUREMENT_ID or GA4_API_SECRET. "
            "Copy .env.example to .env and fill in your practice property's credentials."
        )
