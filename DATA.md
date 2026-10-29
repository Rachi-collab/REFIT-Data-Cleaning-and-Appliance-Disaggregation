# DATA.md: raw-data coverage and quality

## Source
REFIT Electrical Load Measurements: 20 UK households, 2013-2015, aggregate + 9 appliance channels, active power (W) every ~8 s. Raw files have Unix timestamps; the cleaned files are DST-corrected, forward-filled and have an `Issues` flag. House 14 does not exist.

## Raw House 1: findings
| Check | Finding |
|---|---|
| Rows / time span | 4,140,886 rows; 2014-06-27 21:57:49 to 2015-07-10 11:56:32 UTC (377.6 days) |
| Sorted? out-of-order rows | 0 out-of-order rows (timestamps strictly non-decreasing) |
| Duplicate timestamps | 14,755 duplicate timestamp instances (0.36% of total rows) |
| Sampling interval (median, irregular share) | Median: 7.0 s. Irregular intervals: 3,901 intervals > 30 s; 72 intervals > 5 min |
| Missing intervals / longest outage | Longest gap: 207.57 hours (~8.65 days, from 2014-07-07 to 2014-07-21, 20,041 min). After 1-min resampling: 49.56% (269,476 min) flagged as long gaps (> 5 min); 8,310 min interpolated (<= 5 min gaps) |
| Negative / impossible values (> 20 kW) | 0 negative values. Spikes > 20,000 W: Aggregate (74), Appliance 1 (53), Appliance 2 (9), Appliance 3 (15), Appliance 4 (29), Appliance 5 (15), Appliance 6 (2), Appliance 7 (19), Appliance 8 (22), Appliance 9 (2). Maximum recorded power: 98,301 W |
| Aggregate vs appliance consistency | Appliance sum exceeded 1.05 × aggregate in only 0.29% of rows (overall highly physically consistent) |

## Cleaning steps (in order)
1. Sort by timestamp.
2. Drop duplicate timestamps, keeping the first reading (deterministic; 14,755 duplicates removed).
3. Set negative and > 20,000 W values to NaN (domestic UK single-phase cut-out limit is 100 A at 230 V ~ 23 kW).
4. Resample to 1-minute mean.
5. Linearly interpolate gaps <= 5 min and flag them (`was_filled`).
6. Flag gaps > 5 min as `long_gap` and leave them NaN (never filled, excluded from model training and scoring).

## Decisions on gaps and outliers
- Short gaps (<= 5 min) are interpolated because typical appliances (fridges, steady loads) do not radically shift state across a few minutes, making interpolation error minimal. Long gaps (> 5 min) represent network/hardware outages (the longest was ~8.6 days); filling them would synthesize phantom energy and distort training.
- Spikes > 20 kW are sensor/telemetry errors and set to missing. The official cleaned REFIT dataset similarly removes appliance spikes > 4,000 W.

## Washing-machine channel coverage (cleaned data)
The washing machine channel was evaluated across 10 households at 1-minute resolution:

| house | washer_channel | start | end | minutes | pct_missing | pct_flat_ffilled | pct_issues | usable_days | pct_washer_off_of_usable | cycles | cycles_per_usable_week | max_washer_W |
|------:|:---------------|:------|:----|--------:|------------:|-----------------:|-----------:|------------:|-------------------------:|-------:|-----------------------:|-------------:|
| 1 | Appliance5 | 2013-10-09 | 2015-07-10 | 920,091 | 12.64% | 0.21% | 1.81% | 545.3 | 98.58% | 443 | 5.69 | 2,428 W |
| 2 | Appliance2 | 2013-09-17 | 2015-05-28 | 889,078 | 24.62% | 0.77% | 1.51% | 451.4 | 95.66% | 391 | 6.06 | 2,251 W |
| 5 | Appliance3 | 2013-09-26 | 2015-07-06 | 933,593 | 9.34% | 0.41% | 7.59% | 537.7 | 93.47% | 999 | 13.01 | 2,316 W |
| 7 | Appliance5 | 2013-11-01 | 2015-07-08 | 882,970 | 12.58% | 0.56% | 4.06% | 507.9 | 93.13% | 1,069 | 14.73 | 2,208 W |
| 10 | Appliance5 | 2013-11-20 | 2015-06-30 | 845,257 | 11.20% | 8.23% | 1.65% | 463.3 | 91.12% | 836 | 12.63 | 2,192 W |
| 15 | Appliance3 | 2013-12-17 | 2015-07-08 | 817,007 | 13.66% | 0.79% | 1.40% | 477.4 | 97.84% | 455 | 6.67 | 2,341 W |
| 16 | Appliance5 | 2014-01-10 | 2015-07-08 | 782,833 | 17.33% | 1.73% | 0.81% | 435.7 | 96.30% | 330 | 5.30 | 2,185 W |
| 17 | Appliance4 | 2014-03-06 | 2015-06-19 | 676,710 | 6.15% | 2.25% | 4.01% | 412.0 | 98.44% | 399 | 6.78 | 2,281 W |
| 19 | Appliance2 | 2014-03-06 | 2015-06-20 | 677,470 | 6.46% | 0.56% | 3.85% | 420.1 | 97.28% | 363 | 6.05 | 2,354 W |
| 21 | Appliance3 | 2014-03-07 | 2015-07-10 | 705,337 | 9.38% | 7.89% | 4.92% | 381.1 | 97.60% | 302 | 5.55 | 2,260 W |

## Remaining concerns
- **Forward-filled outages**: The cleaned REFIT data forward-filled missing values, which turns sensor dropouts into artificial constant-load flatlines. Our heuristic flags constant runs >= 15 min (`FLAT_MIN`), but some real low baseloads could be filtered.
- **Sensor synchronisation**: Power readings were polled asynchronously every 6-8 s; aggregate and individual sub-meters can differ by a few seconds. 1-minute resampling largely averages this out.
- **Appliance sum > aggregate**: Sub-metering sum occasionally exceeded aggregate power (`Issues == 1`); these minutes are excluded.
- **Appliance mapping per house**: Washer channel numbering is not uniform (varies from Appliance 2 to Appliance 5) and must strictly follow the metadata documentation.
- **Geographic transferability**: UK households have 230 V single-phase supplies with largely front-loading automatic machines and high electric water heating spikes (~2 kW). Indian households often use cold-fill top-loaders or semi-automatic machines with distinct load profiles.
