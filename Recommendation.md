# Recommendation (Utility-Facing Executive Summary)

**What was built.** A machine learning pipeline and Gradient Boosting disaggregation model that estimates washing-machine power minute-by-minute from whole-home smart-meter readings. The model was trained on 6 households (380,880 minutes) and evaluated on held-out test households (Houses 19 and 21) that were never seen during training or tuning.

**Suitable uses** (supported by test results: **76.4% cycle recall**, **80.8% on-state recall**):
- **Cohort-level load shifting**: Identifying when and how often communities of households run washing cycles (e.g. tracking the share of washing occurring during peak grid hours).
- **Time-of-Use engagement & customer insights**: Automated behavioral feedback in consumer apps, such as *"You ran 4 of your 6 wash cycles during peak evening hours this week. Switching them to after 21:00 would save £X/year."*
- **Targeted marketing for demand-side flexibility programs**: Pinpointing customers with high daytime or peak-hour discretionary washing who would benefit from automated smart-plug or delayed-start tariffs.

**Not suitable**:
- **Billing or sub-metered legal guarantees**: False positive rate (~4.1% cycle precision) and energy estimation errors on individual days mean disaggregated power cannot legally replace physical sub-metering for utility billing.
- **Single-minute peak-demand enforcement**: Second-by-second load tracking or hard cut-offs.
- **Direct deployment across geographies without recalibration**: UK households predominantly have front-loading machines with internal 2 kW water heaters. Indian homes often utilize cold-fill semi-automatic or top-loading units with distinct electrical profiles.

---

## Section 4: Practical Implications

### 1. Opportunity: Shifting Washing Out of the Evening Peak
- **Finding**: EDA across 10 households (5,587 cycles) reveals a prominent evening peak between **17:00 and 19:00 UTC** (378 starts at 18:00, 321 at 19:00), accounting for **17.5% of all washing cycles**. Evening washing directly compounds peak grid stress and generation costs.
- **Intervention**: A utility nudge campaign (app notifications + Time-of-Use tariff incentives) offering discounted off-peak rates (e.g., after 21:00 or morning 08:00–11:00) or encouraging the use of machine delay-start timers.
- **Measurement via a Randomized Controlled Trial (RCT)**:
  - Randomize a cohort of 2,000 smart-metered customers into **Treatment** (nudge + off-peak incentive) and **Control** (standard flat tariff).
  - Use a **Difference-in-Differences (DiD)** regression model:
    $$\Delta \text{PeakShare}_{i,t} = \alpha + \beta_1 \text{Treatment}_i + \beta_2 \text{Post}_t + \beta_3 (\text{Treatment}_i \times \text{Post}_t) + \epsilon_{i,t}$$
  - The coefficient $\beta_3$ measures the net reduction in the proportion of disaggregated washing cycles occurring in the 17:00–20:00 window.
  - Validate disaggregation accuracy against a small sub-metered validation cohort (~50 homes with IoT smart plugs).

### 2. Practical Limitations
- **Overlapping appliance signatures**: Kettles (2–3 kW), electric ovens (2–4 kW), and electric showers mask washer signatures. In our failure analysis, active washer MAE escalated from **62 W under light background load** to **254 W when overlapping load exceeded 2,000 W**.
- **Missing data and outages**: Network and sensor dropouts constituted 49.6% of raw House 1 records. Forward-filled gaps produce deceptive flatlines; pipelines must detect and flag outages rather than inferring consumption.
- **Household heterogeneity**: Cycle duration varied from 31 minutes to 94 minutes across homes, and median energy varied tenfold (56 Wh to 588 Wh). Models trained on one demographic cannot assume a universal cycle template.
- **UK vs India context**:
  - *Supply & Outages*: UK supply is relatively stable 230 V / 50 Hz; Indian grids experience frequent voltage fluctuations and power outages, causing interrupted cycles.
  - *Appliance Mechanics*: In India, semi-automatic twin-tub machines and cold-fill top-loaders dominate (drawing ~300–500 W for motor agitation without internal heating), unlike the 2 kW water-heating spikes typical in European front-loaders.
  - *Tariffs & Habits*: Household routines, laundry drying weather, and tariff structures differ significantly. Models must be retrained on local Indian smart-meter ground truth before deployment.

### 3. What Gets Harder with 15-Minute or 30-Minute Smart-Meter Data?
- A standard 45-to-60-minute washing cycle is compressed into only **2 to 4 data points** at 15-minute intervals, and just **1 to 2 points** at 30-minute intervals.
- **Transient features vanish**: The 2 kW heating spike (lasting 5–15 min), the 400 W spin bursts, and the characteristic low-power soaking pauses are averaged out with baseload, fridge cycling, and television use.
- **Implication**: Cycle-level detection and exact start-time identification become largely impossible. However, **aggregate energy estimation** over multi-week periods and **broad time-of-day shifting trends** can still be estimated using regression or energy-budgeting NILM methods.
