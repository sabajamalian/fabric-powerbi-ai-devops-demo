# Data dictionary

Standard business names for every source column. Rename the model object to the business name and keep `sourceColumn` set to the source name.

## Tables

| Source table | Business name | Grain |
|---|---|---|
| `dim_date` | Date | One row per calendar day, 2024-01-01 to 2025-12-31 |
| `dim_store` | Store | One row per store (12 stores, 4 regions) |
| `dim_med` | Medication | One row per medication product |
| `fact_rx_fill` | Prescription Fill | One row per prescription fill, new or refill |

## Date

| Source | Business name | Notes |
|---|---|---|
| `cal_dt` | Date | Key of the marked date table |
| `yr` | Year | Don't summarize |
| `qtr` | Quarter | Q1 to Q4 |
| `yr_qtr` | Year Quarter | For example 2025-Q4 |
| `mth_num` | Month Number | Hidden; sort helper for Month |
| `mth_nm` | Month | Sort by Month Number |
| `yr_mth` | Year Month | For example 2025-12; sort by Year Month Number |
| `yr_mth_num` | Year Month Number | Hidden; sort helper |
| `dow_num` | Day of Week Number | Hidden; sort helper for Day of Week |
| `dow_nm` | Day of Week | Sort by Day of Week Number |
| `is_wkend` | Is Weekend | True on Saturday and Sunday |

## Store

| Source | Business name | Notes |
|---|---|---|
| `store_key` | Store Key | Hidden surrogate key |
| `store_cd` | Store Code | Synthetic code such as S003 |
| `store_nm` | Store Name | Default label |
| `city` | City | Fictional city |
| `rgn` | Region | North, South, East, or West |
| `store_typ` | Store Type | |
| `open_dt` | Open Date | Not related to the Date table |

## Medication

| Source | Business name | Notes |
|---|---|---|
| `med_key` | Medication Key | Hidden surrogate key |
| `med_cd` | Medication Code | Synthetic code |
| `med_nm` | Medication Name | Default label |
| `ther_cat` | Therapeutic Category | Also called drug category or medication category |
| `dose_form` | Dosage Form | |
| `gnrc_flg` | Generic Flag | |

## Prescription Fill

| Source | Business name | Notes |
|---|---|---|
| `fill_id` | Fill ID | Hidden; never summarize |
| `fill_dt` | Fill Date | Relates to Date[Date] |
| `store_key` | Store Key | Hidden foreign key |
| `med_key` | Medication Key | Hidden foreign key |
| `fill_typ` | Fill Type Code | N or R. Hidden once the decoded Fill Type column exists |
| (calculated) | Fill Type | New or Refill, decoded from Fill Type Code |
| `refill_no` | Refill Number | 0 for a new prescription; don't summarize |
| `qty` | Quantity | Units dispensed; sums |
| `days_sply` | Days Supply | Sums |
| `payer_typ` | Payer Type | |
| `proc_mins` | Processing Time (min) | Averages; never sum |
