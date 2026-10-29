# RESULTS.md: Disaggregation Findings and Model Evaluation

## 1. Washing-Machine EDA (Section 2)
- **Households analysed**: 10 houses (Houses 1, 2, 5, 7, 10, 15, 16, 17, 19, 21). Total observed minutes: 8,122,806 across 4,688 usable days (average 469 usable days per house).
- **Summary table**: See `results/eda_house_summary.md`. Across all homes, the washing machine operates between **5.3 and 14.7 cycles per usable week** and spends **91.1% to 98.6% of usable time completely OFF** (inactive).
- **Usage by hour and weekday (`figures/s2_usage_by_hour_dow.png`)**:
  - **Weekly patterns**: Washing peaks sharply on **Saturday (1,079 cycles, 19.3% of total)** and **Friday (886 cycles, 15.9%)**. Midweek days show moderate, steady activity (655 to 748 cycles/day).
  - **Diurnal patterns**: Two distinct peaks are observed:
    1. A dominant **morning peak between 08:00 and 11:00 UTC** (peaking at 08:00 with 500 cycles).
    2. A secondary **evening peak between 17:00 and 19:00 UTC** (378 starts at 18:00, 321 at 19:00), coinciding with household return-from-work and peak UK grid demand.
    3. Nighttime activity (00:00–05:00) is minimal (under 2% per hour).
- **24-hour aggregate + washer trace (`figures/s2_representative_24h.png`)**:
  - Plotted for House 7 (a highly active home with 1,069 cycles). Individual wash cycles show short bursts of sharp heating (2,000 W) followed by periodic motor drum rotation pulses (150–400 W), clearly distinct from steady background base load.
- **Detected cycles overlay (`figures/s2_detected_cycles.png`)**:
  - Cycle detection using `power > 10 W`, `duration >= 10 min`, and merging pauses `<= 5 min` accurately isolates entire washing programmes, bridging wash, soak, rinse, and spin cycles without splitting.
- **Cross-house comparison (`figures/s2_cross_house_comparison.png`, `results/eda_cycle_characteristics_by_house.csv`)**:
  - **Duration**: Median cycle length varies widely from **31–36 min** in Houses 1, 5, 15, 17 (quick wash / eco programmes) to **72–94 min** in Houses 2, 10, 16 (standard intensive programmes).
  - **Peak Power**: Houses 1, 2, 7, 10, 15, 16 exhibit median peaks of **2,002 W to 2,226 W**, reflecting internal electric resistive water heating. In contrast, Houses 5, 17, 19, 21 exhibit median peaks of **364 W to 565 W**, pointing to cold-fill/low-temp washes or hot-water supply plumbing.
  - **Energy per cycle**: Median cycle energy ranges from **56–123 Wh** for low-temperature machines up to **524–588 Wh** for long heated cycles (House 2: 524 Wh, House 10: 554 Wh, House 16: 588 Wh).

---

## 2. Cleaning (Section 1)
- **Outputs**: `figures/s1_before_after_day.png`, `figures/s1_coverage_overview.png`, `results/section1_findings.md`.
- **Visible changes after cleaning**:
  - The raw ~7-second irregular polling and 14,755 duplicate timestamps are eliminated.
  - Telemetry corruption spikes (> 20 kW, reaching up to 98.3 kW) are removed without distorting real appliance pulses.
  - Linear interpolation smoothly fills short gaps (8,310 minutes), while network outages (269,476 minutes, 49.56% of the 377-day span) are explicitly flagged as `long_gap` and preserved as NaNs, ensuring models do not train on phantom interpolated data.

---

## 3. Disaggregation Model Results (Section 3)

### Validation & Split Design
- **Household-level split (zero temporal leakage)**:
  - **Train houses**: 1, 2, 5, 7, 10, 15 (380,880 balanced training minutes; machine-off rows subsampled to 10% to prevent class imbalance degeneration).
  - **Validation houses**: 16, 17 (used strictly for hyper-parameter tuning; selected `learning_rate=0.1`, `max_leaf_nodes=15`, `max_iter=200`, `l2_regularization=1.0`).
  - **Test houses**: 19, 21 (held-out homes, never seen during training or tuning).
- **Baselines**:
  1. *Always-Off Baseline*: Always predicts 0 W.
  2. *Hour × Day-of-Week Profile Baseline*: Predicts the empirical mean washer power for that weekday and hour learned from training homes.

### Test Set Performance (Unseen Houses 19 and 21)

#### Mean Performance Across Test Houses (`results/model_test_metrics_mean_over_houses.csv`):
| Predictor | MAE (W) | RMSE (W) | SAE | Precision | Recall (On-State) | F1 (On-State) | Cycle Recall | Cycle Precision |
|---|---|---|---|---|---|---|---|---|
| **Always Off** | **0.698** | **21.390** | 1.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 |
| **Hour × Day Profile** | 5.782 | 23.539 | 10.747 | 0.008 | 0.403 | 0.016 | 0.358 | 0.021 |
| **Gradient Boosting (NILM)** | 10.801 | 47.228 | 11.912 | **0.033** | **0.808** | **0.062** | **0.764** | **0.041** |

#### Per-House Breakdown (`results/model_test_metrics.csv` & `model_test_cycle_level.csv`):
- **House 19 (Unseen)**:
  - Total ground-truth cycles: 30 cycles (1,480 Wh total actual energy).
  - Gradient Boosting: **Cycle Recall = 70.0%** (21/30 cycles detected), On-State Recall = 75.0%, MAE = 2.56 W, RMSE = 23.72 W.
  - Profile Baseline: Cycle Recall = 23.3% (7/30 cycles detected).
- **House 21 (Unseen)**:
  - Total ground-truth cycles: 87 cycles (7,067 Wh total actual energy).
  - Gradient Boosting: **Cycle Recall = 82.8%** (72/87 cycles detected), On-State Recall = 86.6%, MAE = 19.04 W, RMSE = 70.74 W.
  - Profile Baseline: Cycle Recall = 48.3% (42/87 cycles detected).

### Key Takeaways & Metric Interpretation
1. **The MAE/RMSE "Always Off" Paradox**: Always predicting 0 W yields an artificially tiny MAE (0.70 W) and RMSE (21.4 W) because washers are OFF over 97% of the year. Standard regression loss treats predicting 0 W as nearly perfect, proving that MAE/RMSE alone are inadequate for NILM evaluation.
2. **Detection Power**: The Gradient Boosting model successfully captures **80.8% of active washer minutes** and **76.4% of actual washing cycles** in completely unseen households.
3. **Precision and False Alarms**: Precision is low (~3.3% minute-level, 4.1% cycle-level). When multiple household appliances draw power simultaneously, temporary 200–500 W motor pulses or 2 kW heater pulses from other devices (kettles, ovens, heaters) trigger false positive cycles.
4. **Energy Tracking (`figures/s3_daily_energy_scatter.png`)**: Daily energy predictions follow overall household usage trends but exhibit positive bias on days with heavy overall electricity consumption due to overlapping loads.

---

## 4. Failure Analysis
- **Outputs**: `results/failure_error_by_other_load.csv`, `figures/s3_failure_error_vs_other_load.png`, `results/failure_missed_cycles.csv`.
- **Impact of Overlapping Background Load**:
  | House | Overlapping Load Bin | Active Washer Minutes | MAE while Washer ON (W) | Mean Error (W) |
  |:------|:---------------------|----------------------:|------------------------:|---------------:|
  | 19 | < 300 W | 143 | 141.8 W | -141.8 W |
  | 19 | 300–800 W | 633 | 74.0 W | -71.7 W |
  | 19 | 800–2,000 W | 44 | 61.8 W | -13.4 W |
  | 19 | > 2,000 W | 71 | **225.6 W** | **+205.7 W** |
  | 21 | < 300 W | 211 | 161.5 W | -161.5 W |
  | 21 | 300–800 W | 788 | 129.3 W | -121.3 W |
  | 21 | 800–2,000 W | 1,319 | 77.3 W | -34.8 W |
  | 21 | > 2,000 W | 433 | **254.2 W** | **+62.4 W** |

- **Concrete Failure Modes**:
  1. **Over-prediction during high aggregate load (> 2,000 W)**: When concurrent high-power appliances run (e.g. electric cooker, kettle, immersion heater), error jumps above 225–254 W with a strong positive bias (+205 W in House 19). The model attributes parts of the massive aggregate step-changes to the washer.
  2. **Missed low-power cycles (24 missed cycles across test homes)**:
     - Example: In House 19 on `2014-08-01 13:08 UTC` (peak 81 W, 14 min) and `2014-05-16 07:31 UTC` (peak 110 W, 25 min), the machine ran cold rinse/spin cycles without water heating.
     - With background load at 260–360 W, an 80 W signal has a signal-to-noise ratio < 0.3 and is completely swallowed by the baseline noise.

---

## 5. Validation Approach and Caveats
- Splitting strictly by household guarantees that the evaluation reflects generalization to new homes, avoiding the leakage of temporal autocorrelation.
- Because only two homes were held out for final testing, confidence bounds around exact percentage metrics are wide. However, the consistent >70% cycle recall across both test homes confirms the model learns genuine physical load dynamics rather than household-specific memorization.
