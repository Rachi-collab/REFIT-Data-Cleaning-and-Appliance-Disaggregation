"""All tunable choices in one place, so every decision is visible and reproducible."""
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = Path(os.environ.get("REFIT_DATA_DIR", ROOT / "data"))
RAW_DIR = DATA_DIR / "raw" if (DATA_DIR / "raw").exists() else (DATA_DIR / "REFIT_RAW_081116" if (DATA_DIR / "REFIT_RAW_081116").exists() else DATA_DIR / "raw")
CLEAN_DIR = DATA_DIR / "clean" if (DATA_DIR / "clean").exists() else (DATA_DIR / "CLEAN_REFIT_081116" if (DATA_DIR / "CLEAN_REFIT_081116").exists() else DATA_DIR / "clean")
PROCESSED_DIR = DATA_DIR / "processed"
RESULTS_DIR = ROOT / "results"
FIG_DIR = ROOT / "figures"
SEED = 42

# Washing-machine channel (ApplianceN) per house, from CLEAN_READ_ME_081116.txt (appliance list at the start of the study).
# House 4 has two machines (4 and 5); we use channel 4. House 12 has none. VERIFY by plotting each channel (see 02 script).
WASHER_CHANNEL = {1: 5, 2: 2, 3: 6, 4: 4, 5: 3, 6: 2, 7: 5, 8: 4, 9: 3, 10: 5, 11: 3,
                  13: 3, 15: 3, 16: 5, 17: 4, 18: 5, 19: 2, 20: 4, 21: 3}

# ---- Section 1: raw-data cleaning (House 1) ----
RAW_HOUSE = 1
RESAMPLE = "1min"
MAX_FILL_MIN = 5            # interpolate gaps up to this many minutes; longer gaps are FLAGGED, not filled
MAX_PLAUSIBLE_W = 20000     # a UK home cannot sustain more than ~20 kW (100 A supply at 230 V is ~23 kW)

# ---- Washing-machine cycle rule ----
ON_W = 10.0                 # power above this = machine drawing power (standby is a few watts)
MIN_CYCLE_MIN = 10          # shorter runs are treated as spikes/noise, not a wash
MERGE_GAP_MIN = 5           # pauses shorter than this (soak/drain) stay inside the same cycle
FLAT_MIN = 15               # aggregate identical for this many minutes => forward-filled outage in CLEAN data

# ---- Section 2/3: which houses (the script skips any house whose file you did not download) ----
EDA_HOUSES = [1, 2, 5, 7, 10, 15, 16, 17, 19, 21]
TRAIN_HOUSES = [1, 2, 5, 7, 10, 15]
VAL_HOUSES = [16, 17]       # used only to choose hyper-parameters
TEST_HOUSES = [19, 21]      # never touched until the final evaluation => tests generalisation to UNSEEN homes

# ---- Model ----
WINDOW = 31                 # minutes of aggregate context (centred on the target minute)
OFF_KEEP_FRAC = 0.10        # TRAINING ONLY: keep this fraction of 'machine off' rows (evaluation uses all rows)
MAX_TRAIN_ROWS = 500_000
