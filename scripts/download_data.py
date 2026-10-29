"""Download and extract the REFIT archives (raw + cleaned) and the readme into data/."""
import sys
from pathlib import Path
import requests
import py7zr

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from refit_nilm import config as C

FILES = {
    "raw": ("https://pureportal.strath.ac.uk/files/62090177/REFIT_RAW_081116.7z", "REFIT_RAW_081116.7z"),
    "clean": ("https://pureportal.strath.ac.uk/files/62090184/CLEAN_REFIT_081116.7z", "CLEAN_REFIT_081116.7z"),
}
README_URL = "https://pureportal.strath.ac.uk/files/62090183/CLEAN_READ_ME_081116.txt"


def fetch(url, dest):
    if dest.exists() and dest.stat().st_size > 0:
        print("already have", dest.name); return
    print("downloading", url)
    with requests.get(url, stream=True, timeout=60) as r:
        r.raise_for_status()
        with open(dest, "wb") as f:
            for chunk in r.iter_content(1 << 20):
                f.write(chunk)


if __name__ == "__main__":
    C.DATA_DIR.mkdir(parents=True, exist_ok=True)
    try:
        fetch(README_URL, C.DATA_DIR / "CLEAN_READ_ME_081116.txt")
    except requests.RequestException as e:
        print("readme download failed (get it in a browser):", e)
    failures = []
    for kind, (url, name) in FILES.items():
        archive = C.DATA_DIR / name
        try:
            fetch(url, archive)
        except requests.RequestException as e:
            failures.append(f"{name}: {e}")
            print(f"!! could not download {name}: {e}")
            continue
        target = C.RAW_DIR if kind == "raw" else C.CLEAN_DIR
        if not target.exists() or not any(target.rglob("*.csv")):
            print("extracting", name)
            with py7zr.SevenZipFile(archive) as z:
                z.extractall(target)
    csv_count = len(list(C.DATA_DIR.rglob("*.csv")))
    missing = [
        kind for kind in FILES
        if not (C.RAW_DIR if kind == "raw" else C.CLEAN_DIR).exists()
        or not any((C.RAW_DIR if kind == "raw" else C.CLEAN_DIR).rglob("*.csv"))
    ]
    if missing:
        details = "\n".join(f"  - {failure}" for failure in failures)
        if not details:
            details = "  - The archive(s) downloaded but did not produce the expected CSV files."
        sys.exit(
            f"REFIT data setup incomplete: missing CSV data for {', '.join(missing)} "
            f"({csv_count} CSV file(s) found).\n{details}\n"
            f"Download the missing archive(s) from the official REFIT dataset page "
            f"in a browser, save them in {C.DATA_DIR}, then rerun this script to extract them."
        )
    print("done. CSV files found:", csv_count)
