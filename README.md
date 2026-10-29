# REFIT: data cleaning and washing-machine disaggregation

Flock Energy take-home. The pipeline runs end to end from the raw REFIT files to cleaning, EDA, model predictions and evaluation.

> **Status of numbers:** every number in `results/` and `figures/` comes from running the scripts on the real REFIT data. `--synthetic` mode exists only to smoke-test the code and must never be quoted as a result.

## What I built
| Step | Script | Output |
|---|---|---|
| 1. Raw House 1 inspection and cleaning to 1-minute | `scripts/01_clean_house1_raw.py` | `results/section1_findings.*`, `data/processed/house1_1min.csv`, `figures/s1_*` |
| 2. Washing-machine EDA, 4+ houses (cleaned data) | `scripts/02_washing_machine_eda.py` | `results/eda_*.csv|md`, `figures/s2_*` |
| 3. Aggregate to washer power model + evaluation | `scripts/03_disaggregate.py` | `results/model_*.csv`, `results/failure_*.csv`, `figures/s3_*` |
| All of it | `scripts/run_all.py` | |

**Notebook:** `REFIT_Analysis.ipynb` runs the same pipeline with narrative cells and displays tables and plots (open in Jupyter or Google Colab, Run All, then File → Print → Save as PDF, or `jupyter nbconvert --to pdf REFIT_Analysis.ipynb`). Regenerate it with `python scripts/build_notebook.py`.

Library code is in `refit_nilm/` (`io`, `cleaning`, `cycles`, `features`, `metrics`, `config`).

## Setup and run
```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
python scripts/download_data.py      # fetches raw + cleaned REFIT into ./data (or download manually, see below)
python scripts/run_all.py            # ~ a few minutes
```
If the downloader reports HTTP 403, the REFIT host is blocking the request; this is not a pip or Python setup issue. Download the raw and cleaned archives from the [official REFIT dataset pages](https://pureportal.strath.ac.uk/en/datasets/refit-electrical-load-measurements/) in a browser and save `REFIT_RAW_081116.7z` and `CLEAN_REFIT_081116.7z` directly into `data/`. Then rerun `python scripts/download_data.py` to extract them. Alternatively, extract the raw archive into `data/raw/` (containing `House1.csv`) and the cleaned archive into `data/clean/` (containing `CLEAN_House<N>.csv`). Set `REFIT_DATA_DIR` to use another folder.
Code check without data: `python scripts/run_all.py --synthetic` (fake data in REFIT format; **not a result**).

All settings (thresholds, houses, window) are in `refit_nilm/config.py`. **Check `WASHER_CHANNEL` against the dataset readme before running**; the appliance column number differs per house.

## Assumptions
- Timestamps are Unix seconds and treated as UTC. Cleaned data are already DST-corrected (readme).
- Washing machine is "on" above `ON_W` = 10 W. A cycle is an on-run of at least `MIN_CYCLE_MIN` = 10 min; on-runs separated by up to `MERGE_GAP_MIN` = 5 min are merged (wash, rinse and spin phases have low-power pauses).
- Values above `MAX_PLAUSIBLE_W` = 20,000 W or negative are sensor errors.

## Preprocessing decisions
- Sort by time, drop duplicate timestamps (keep first; rule stated in DATA.md).
- 1-minute mean. Gaps up to `MAX_FILL_MIN` = 5 min are linearly interpolated and marked `was_filled`; longer gaps stay NaN and are flagged `long_gap` (never filled, never used for training or scoring).
- In the *cleaned* data, missing values were forward-filled by the publishers, so outages look like flat lines. I detect runs of identical aggregate values (`FLAT_MIN` = 15 min) and exclude them. Rows with `Issues` = 1 are excluded.

## Validation design (no leakage)
- **Split by household**, not by random rows: train houses 1, 2, 5, 7, 10, 15; validation 16, 17; test 19, 21 (`config.py`). Neighbouring minutes are almost identical, so a random split would leak.
- Hyper-parameters chosen on validation houses only; test houses scored once at the end.
- Training sees all "on" minutes plus 10% of "off" minutes (the washer is off ~96-98% of the time); evaluation uses **all** usable minutes.
- Model: gradient boosting (`HistGradientBoostingRegressor`) on a 31-minute window of the aggregate (+ summary stats, hour, weekday), predicting washer power at the centre minute (seq2point style, but tree-based so it trains on a laptop CPU). Post-processing: clip to [0, aggregate], zero values < 5 W, drop on-runs shorter than 10 min.
- Baselines: always-off; weekday x hour mean profile.
- Metrics: MAE, RMSE, SAE (total-energy error), on/off precision, recall, F1, and cycle-level recall/precision. MAE alone looks great for "always off" because the washer is mostly off.

## Trade-offs
- Trees over a neural net: fast, explainable, robust with few houses; a CNN/seq2point network may separate overlapping loads better.
- Few test houses (2): results carry wide uncertainty; I report per-house, not only the mean.
- Short-run filter removes false alarms but would also remove genuinely short cycles (eco/quick programmes).

## AI tools used
Claude (Anthropic) assisted in drafting and debugging the code and documentation structure. **[Edit this section to state precisely what you used AI for and confirm you reviewed and understood all code.]**

## Possible improvements
Add a CNN/seq2point model for comparison; more test houses and leave-one-house-out cross-validation; use other appliances' known behaviour; per-house calibration with a few labelled cycles; probabilistic outputs; test with 15/30-minute resampling.

## References
- Murray, D., Stankovic, L., Stankovic, V. (2017). An electrical load measurements dataset of United Kingdom households from a two-year longitudinal study. *Scientific Data* 4, 160122 (REFIT).
- Hart, G. W. (1992). Nonintrusive appliance load monitoring. *Proc. IEEE* 80(12).
- Kelly, J., Knottenbelt, W. (2015). Neural NILM: Deep neural networks applied to energy disaggregation. *BuildSys*.
- Zhang, C. et al. (2018). Sequence-to-point learning with neural networks for non-intrusive load monitoring. *AAAI*.
- Batra, N. et al. (2014). NILMTK: an open source toolkit for non-intrusive load monitoring. *e-Energy*.
- REFIT cleaned-data readme (Strathclyde).
