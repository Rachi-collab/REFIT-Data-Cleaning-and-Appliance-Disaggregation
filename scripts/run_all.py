"""Run the whole pipeline end to end:  python scripts/run_all.py            (real data in ./data)
Smoke test without the real data:      python scripts/run_all.py --synthetic   (NOT results)"""
import os
import subprocess
import sys
from pathlib import Path

root = Path(__file__).resolve().parents[1]
env = dict(os.environ)
if "--synthetic" in sys.argv:
    out = root / "data" / "synthetic"
    subprocess.check_call([sys.executable, str(root / "scripts" / "make_synthetic_data.py"), str(out)])
    env["REFIT_DATA_DIR"] = str(out)
for s in ["01_clean_house1_raw.py", "02_washing_machine_eda.py", "03_disaggregate.py"]:
    print(f"\n===== {s} =====")
    subprocess.check_call([sys.executable, str(root / "scripts" / s)], env=env)
print("\nAll done. Tables are in results/, figures in figures/.")
