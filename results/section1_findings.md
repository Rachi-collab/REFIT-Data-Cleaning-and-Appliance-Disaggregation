# Section 1 findings (auto-generated; copy into DATA.md)

| Check | Result |
|---|---|
| rows | 4140886 |
| start | 2014-06-27 21:57:49+00:00 |
| end | 2015-07-10 11:56:32+00:00 |
| span_days | 377.6 |
| rows_out_of_time_order | 0 |
| duplicate_timestamps | 14755 |
| median_interval_s | 7.0 |
| intervals_gt_30s | 3901 |
| intervals_gt_5min | 72 |
| longest_gap_hours | 207.57 |
| missing_pct_by_col | {'Aggregate': 4.56, 'Appliance1': 10.57, 'Appliance2': 11.1, 'Appliance3': 7.53, 'Appliance4': 12.34, 'Appliance5': 12.01, 'Appliance6': 8.27, 'Appliance7': 5.62, 'Appliance8': 9.44, 'Appliance9': 46.17} |
| negative_values_by_col | {'Aggregate': 0, 'Appliance1': 0, 'Appliance2': 0, 'Appliance3': 0, 'Appliance4': 0, 'Appliance5': 0, 'Appliance6': 0, 'Appliance7': 0, 'Appliance8': 0, 'Appliance9': 0} |
| values_gt_20000W_by_col | {'Aggregate': 74, 'Appliance1': 53, 'Appliance2': 9, 'Appliance3': 15, 'Appliance4': 29, 'Appliance5': 15, 'Appliance6': 2, 'Appliance7': 19, 'Appliance8': 22, 'Appliance9': 2} |
| max_W_by_col | {'Aggregate': 29159.0, 'Appliance1': 76677.0, 'Appliance2': 66685.0, 'Appliance3': 73725.0, 'Appliance4': 98301.0, 'Appliance5': 73725.0, 'Appliance6': 37610.0, 'Appliance7': 73725.0, 'Appliance8': 98301.0, 'Appliance9': 32737.0} |
| pct_rows_appliance_sum_gt_aggregate_x1.05 | 0.29 |
| file | RAW_House1_Part2.csv |
| cleaned_minutes | 543720 |
| minutes_interpolated_(<=5 min gaps) | 8310 |
| minutes_flagged_long_gap_(not filled) | 269476 |
| pct_minutes_flagged_long_gap | 49.56 |
| longest_outages_(start,end,minutes) | [('2014-07-07 15:08:00+00:00', '2014-07-21 13:08:00+00:00', 20041), ('2014-11-10 13:21:00+00:00', '2014-11-20 15:26:00+00:00', 14526), ('2015-05-10 23:42:00+00:00', '2015-05-19 15:09:00+00:00', 12448), ('2015-06-10 13:24:00+00:00', '2015-06-18 01:38:00+00:00', 10815), ('2014-11-01 01:27:00+00:00', '2014-11-07 10:31:00+00:00', 9185), ('2014-08-27 23:24:00+00:00', '2014-09-01 16:54:00+00:00', 6811), ('2015-04-03 01:49:00+00:00', '2015-04-07 10:17:00+00:00', 6269), ('2014-11-20 15:33:00+00:00', '2014-11-24 09:07:00+00:00', 5375), ('2014-10-28 13:55:00+00:00', '2014-11-01 00:00:00+00:00', 4926), ('2014-11-07 14:38:00+00:00', '2014-11-10 13:14:00+00:00', 4237)] |