"""Deterministic synthetic data generator for the Contoso Pharmacy demo.

Every value is synthetic. There are no patients, prescribers, or people of any kind.

Only ``random.Random.random()`` is used, because the Mersenne Twister core is stable
across platforms and Python versions while helpers such as ``randint`` or ``gauss``
are not guaranteed to be. Output files are written with LF line endings and fixed
number formatting so they are byte-identical on Windows, macOS, and Linux.
"""

from __future__ import annotations

import hashlib
import json
import math
import random
from dataclasses import dataclass
from datetime import date, timedelta
from pathlib import Path

SEED = 20260101
START_DATE = date(2024, 1, 1)
END_DATE = date(2025, 12, 31)

REGIONS = ("North", "South", "East", "West")

# store_key, store_cd, store_nm, city, rgn, store_typ, open_dt, volume_weight, processing_factor
STORES = (
    (1, "S001", "Lakeview", "Lakeview", "North", "Standard", "2015-03-02", 1.10, 1.00),
    (2, "S002", "Pine Hollow", "Pine Hollow", "North", "Drive-thru", "2017-06-12", 0.90, 0.95),
    (3, "S003", "Riverbend", "Riverbend", "North", "24-hour", "2012-09-24", 1.25, 1.05),
    (4, "S004", "Stonebridge", "Stonebridge", "South", "Standard", "2016-01-18", 1.00, 0.90),
    (5, "S005", "Harbor Point", "Harbor Point", "South", "Drive-thru", "2019-04-08", 0.85, 1.10),
    (6, "S006", "Magnolia Square", "Magnolia Square", "South", "Standard", "2014-11-03", 1.05, 0.95),
    (7, "S007", "Oak Terrace", "Oak Terrace", "East", "24-hour", "2011-05-16", 1.30, 1.00),
    (8, "S008", "Sunset Mesa", "Sunset Mesa", "West", "Standard", "2018-08-27", 0.95, 1.70),
    (9, "S009", "Willow Creek", "Willow Creek", "East", "Standard", "2020-02-10", 0.80, 0.90),
    (10, "S010", "Granite Park", "Granite Park", "East", "Drive-thru", "2013-10-07", 1.00, 1.05),
    (11, "S011", "Bayside", "Bayside", "West", "24-hour", "2016-07-25", 1.15, 1.00),
    (12, "S012", "Fox Run", "Fox Run", "West", "Standard", "2021-03-15", 0.75, 0.95),
)

SLOW_STORE_CODE = "S008"
HIGH_REFILL_STORE_CODES = ("S003", "S010")
HIGH_REFILL_WINDOW = (date(2025, 10, 1), date(2025, 12, 31))

CATEGORIES = (
    "Cardiovascular",
    "Diabetes",
    "Respiratory",
    "Anti-infective",
    "Pain and Inflammation",
    "Mental Health",
    "Dermatology",
    "Gastrointestinal",
)

CATEGORY_SHARE = {
    "Cardiovascular": 0.22,
    "Diabetes": 0.14,
    "Respiratory": 0.12,
    "Anti-infective": 0.10,
    "Pain and Inflammation": 0.10,
    "Mental Health": 0.14,
    "Dermatology": 0.06,
    "Gastrointestinal": 0.12,
}

CATEGORY_REFILL_PROBABILITY = {
    "Cardiovascular": 0.74,
    "Diabetes": 0.74,
    "Respiratory": 0.45,
    "Anti-infective": 0.05,
    "Pain and Inflammation": 0.35,
    "Mental Health": 0.72,
    "Dermatology": 0.25,
    "Gastrointestinal": 0.66,
}

ACUTE_CATEGORIES = {"Anti-infective", "Pain and Inflammation", "Dermatology"}

# med_cd, med_nm, ther_cat, dose_form, gnrc_flg
MEDICATIONS = (
    ("M001", "Atorvastatin 20 mg", "Cardiovascular", "Tablet", "Y"),
    ("M002", "Lisinopril 10 mg", "Cardiovascular", "Tablet", "Y"),
    ("M003", "Amlodipine 5 mg", "Cardiovascular", "Tablet", "Y"),
    ("M004", "Metoprolol Succinate 50 mg", "Cardiovascular", "Tablet", "Y"),
    ("M005", "Losartan 50 mg", "Cardiovascular", "Tablet", "Y"),
    ("M006", "Rosuvastatin 10 mg", "Cardiovascular", "Tablet", "Y"),
    ("M007", "Hydrochlorothiazide 25 mg", "Cardiovascular", "Tablet", "Y"),
    ("M008", "Carvedilol 12.5 mg", "Cardiovascular", "Tablet", "Y"),
    ("M009", "Metformin 500 mg", "Diabetes", "Tablet", "Y"),
    ("M010", "Glipizide 5 mg", "Diabetes", "Tablet", "Y"),
    ("M011", "Sitagliptin 100 mg", "Diabetes", "Tablet", "N"),
    ("M012", "Pioglitazone 30 mg", "Diabetes", "Tablet", "Y"),
    ("M013", "Insulin Glargine 100 units/mL", "Diabetes", "Injection", "N"),
    ("M014", "Empagliflozin 10 mg", "Diabetes", "Tablet", "N"),
    ("M015", "Glimepiride 2 mg", "Diabetes", "Tablet", "Y"),
    ("M016", "Albuterol HFA Inhaler", "Respiratory", "Inhaler", "Y"),
    ("M017", "Montelukast 10 mg", "Respiratory", "Tablet", "Y"),
    ("M018", "Fluticasone Nasal Spray", "Respiratory", "Spray", "Y"),
    ("M019", "Budesonide and Formoterol Inhaler", "Respiratory", "Inhaler", "N"),
    ("M020", "Cetirizine 10 mg", "Respiratory", "Tablet", "Y"),
    ("M021", "Benzonatate 100 mg", "Respiratory", "Capsule", "Y"),
    ("M022", "Tiotropium Inhaler", "Respiratory", "Inhaler", "N"),
    ("M023", "Loratadine 10 mg", "Respiratory", "Tablet", "Y"),
    ("M024", "Amoxicillin 500 mg", "Anti-infective", "Capsule", "Y"),
    ("M025", "Azithromycin 250 mg", "Anti-infective", "Tablet", "Y"),
    ("M026", "Cephalexin 500 mg", "Anti-infective", "Capsule", "Y"),
    ("M027", "Doxycycline 100 mg", "Anti-infective", "Capsule", "Y"),
    ("M028", "Ciprofloxacin 500 mg", "Anti-infective", "Tablet", "Y"),
    ("M029", "Oseltamivir 75 mg", "Anti-infective", "Capsule", "Y"),
    ("M030", "Nitrofurantoin 100 mg", "Anti-infective", "Capsule", "Y"),
    ("M031", "Ibuprofen 800 mg", "Pain and Inflammation", "Tablet", "Y"),
    ("M032", "Naproxen 500 mg", "Pain and Inflammation", "Tablet", "Y"),
    ("M033", "Meloxicam 15 mg", "Pain and Inflammation", "Tablet", "Y"),
    ("M034", "Celecoxib 200 mg", "Pain and Inflammation", "Capsule", "Y"),
    ("M035", "Cyclobenzaprine 10 mg", "Pain and Inflammation", "Tablet", "Y"),
    ("M036", "Prednisone 10 mg", "Pain and Inflammation", "Tablet", "Y"),
    ("M037", "Diclofenac Sodium Gel", "Pain and Inflammation", "Gel", "Y"),
    ("M038", "Sertraline 50 mg", "Mental Health", "Tablet", "Y"),
    ("M039", "Escitalopram 10 mg", "Mental Health", "Tablet", "Y"),
    ("M040", "Fluoxetine 20 mg", "Mental Health", "Capsule", "Y"),
    ("M041", "Bupropion XL 150 mg", "Mental Health", "Tablet", "Y"),
    ("M042", "Trazodone 50 mg", "Mental Health", "Tablet", "Y"),
    ("M043", "Duloxetine 30 mg", "Mental Health", "Capsule", "Y"),
    ("M044", "Buspirone 10 mg", "Mental Health", "Tablet", "Y"),
    ("M045", "Venlafaxine ER 75 mg", "Mental Health", "Capsule", "Y"),
    ("M046", "Triamcinolone Cream 0.1%", "Dermatology", "Cream", "Y"),
    ("M047", "Hydrocortisone Cream 2.5%", "Dermatology", "Cream", "Y"),
    ("M048", "Clindamycin Gel 1%", "Dermatology", "Gel", "Y"),
    ("M049", "Tretinoin Cream 0.05%", "Dermatology", "Cream", "Y"),
    ("M050", "Mupirocin Ointment 2%", "Dermatology", "Ointment", "Y"),
    ("M051", "Ketoconazole Cream 2%", "Dermatology", "Cream", "Y"),
    ("M052", "Clobetasol Ointment 0.05%", "Dermatology", "Ointment", "Y"),
    ("M053", "Omeprazole 20 mg", "Gastrointestinal", "Capsule", "Y"),
    ("M054", "Pantoprazole 40 mg", "Gastrointestinal", "Tablet", "Y"),
    ("M055", "Famotidine 20 mg", "Gastrointestinal", "Tablet", "Y"),
    ("M056", "Ondansetron 4 mg", "Gastrointestinal", "Tablet", "Y"),
    ("M057", "Esomeprazole 40 mg", "Gastrointestinal", "Capsule", "Y"),
    ("M058", "Docusate Sodium 100 mg", "Gastrointestinal", "Capsule", "Y"),
    ("M059", "Dicyclomine 20 mg", "Gastrointestinal", "Tablet", "Y"),
    ("M060", "Lansoprazole 30 mg", "Gastrointestinal", "Capsule", "Y"),
)

PAYERS = (("Commercial", 0.52), ("Medicare", 0.28), ("Medicaid", 0.14), ("Cash", 0.06))

BASE_FILLS_PER_STORE_DAY = 4.6
DOW_FACTOR = (1.10, 1.08, 1.08, 1.10, 1.12, 0.80, 0.55)  # Monday first

MONTH_NAMES = (
    "January",
    "February",
    "March",
    "April",
    "May",
    "June",
    "July",
    "August",
    "September",
    "October",
    "November",
    "December",
)
DAY_NAMES = ("Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday")

TABLE_FILES = {
    "dim_date": "dim_date.csv",
    "dim_store": "dim_store.csv",
    "dim_med": "dim_med.csv",
    "fact_rx_fill": "fact_rx_fill.csv",
}


@dataclass(frozen=True)
class Column:
    name: str
    data_type: str
    description: str


SCHEMA: dict[str, list[Column]] = {
    "dim_date": [
        Column("cal_dt", "date", "Calendar date, one row per day from 2024-01-01 to 2025-12-31."),
        Column("yr", "int", "Calendar year."),
        Column("qtr", "string", "Calendar quarter label, Q1 to Q4."),
        Column("yr_qtr", "string", "Year and quarter, for example 2025-Q4."),
        Column("mth_num", "int", "Month number, 1 to 12."),
        Column("mth_nm", "string", "Month name, January to December."),
        Column("yr_mth", "string", "Year and month, for example 2025-12."),
        Column("yr_mth_num", "int", "Year and month as a sortable number, for example 202512."),
        Column("dow_num", "int", "Day of week number, 1 is Monday and 7 is Sunday."),
        Column("dow_nm", "string", "Day of week name."),
        Column("is_wkend", "string", "Y when the date is a Saturday or Sunday, otherwise N."),
    ],
    "dim_store": [
        Column("store_key", "int", "Surrogate key for the store."),
        Column("store_cd", "string", "Store code, S001 to S012."),
        Column("store_nm", "string", "Store name."),
        Column("city", "string", "Fictional city where the store is located."),
        Column("rgn", "string", "Sales region: North, South, East, or West."),
        Column("store_typ", "string", "Store format: Standard, Drive-thru, or 24-hour."),
        Column("open_dt", "date", "Date the store opened."),
    ],
    "dim_med": [
        Column("med_key", "int", "Surrogate key for the medication."),
        Column("med_cd", "string", "Medication code, M001 to M060. Not a real drug code."),
        Column("med_nm", "string", "Generic medication name and strength."),
        Column("ther_cat", "string", "Therapeutic category, one of eight."),
        Column("dose_form", "string", "Dosage form, for example Tablet or Inhaler."),
        Column("gnrc_flg", "string", "Y when a generic version is dispensed, otherwise N."),
    ],
    "fact_rx_fill": [
        Column("fill_id", "int", "Sequential identifier for the fill event. Not linked to any person."),
        Column("fill_dt", "date", "Date the prescription was filled."),
        Column("store_key", "int", "Store that filled the prescription."),
        Column("med_key", "int", "Medication dispensed."),
        Column("fill_typ", "string", "N for a new prescription, R for a refill."),
        Column("refill_no", "int", "Refill sequence number; 0 for new prescriptions."),
        Column("qty", "int", "Quantity dispensed, in units of the dosage form."),
        Column("days_sply", "int", "Days of therapy supplied."),
        Column("payer_typ", "string", "Payer type: Commercial, Medicare, Medicaid, or Cash."),
        Column("proc_mins", "decimal", "Minutes from intake to ready for pickup."),
    ],
}


def _daterange(start: date, end: date):
    current = start
    while current <= end:
        yield current
        current += timedelta(days=1)


def _poisson(rng: random.Random, lam: float) -> int:
    """Knuth's algorithm; lambda here is always small (under 3)."""
    limit = math.exp(-lam)
    k = 0
    p = 1.0
    while True:
        p *= rng.random()
        if p <= limit:
            return k
        k += 1


def _weighted_pick(rng: random.Random, items, weights):
    total = sum(weights)
    threshold = rng.random() * total
    running = 0.0
    for item, weight in zip(items, weights, strict=True):
        running += weight
        if threshold < running:
            return item
    return items[-1]


def _category_season(category: str, day: date) -> float:
    month = day.month
    factor = 1.0
    if category in ("Respiratory", "Anti-infective"):
        factor = {12: 1.25, 1: 1.30, 2: 1.20, 3: 1.05, 6: 0.85, 7: 0.80, 8: 0.85}.get(month, 1.0)
    elif category == "Dermatology":
        factor = {5: 1.15, 6: 1.20, 7: 1.20, 8: 1.10, 12: 0.90, 1: 0.90}.get(month, 1.0)
    # Engineered signals for the "largest volume change" question: December 2025 vs November 2025.
    if day.year == 2025 and month == 12:
        if category == "Respiratory":
            factor *= 1.55
        elif category == "Dermatology":
            factor *= 0.50
    return factor


def _trend(day: date) -> float:
    months_since_start = (day.year - START_DATE.year) * 12 + (day.month - 1)
    return 1.0 + 0.0035 * months_since_start


def _med_weights():
    by_category: dict[str, list[tuple[int, tuple]]] = {c: [] for c in CATEGORIES}
    for index, med in enumerate(MEDICATIONS, start=1):
        by_category[med[2]].append((index, med))
    weights: dict[str, list[float]] = {}
    for category, meds in by_category.items():
        # Earlier medications in each category are more common (1, 0.85, 0.72, ...).
        weights[category] = [0.85**position for position in range(len(meds))]
    return by_category, weights


def _days_supply(rng: random.Random, category: str) -> int:
    if category in ACUTE_CATEGORIES:
        return _weighted_pick(rng, (7, 10, 14, 30), (0.30, 0.35, 0.20, 0.15))
    return _weighted_pick(rng, (30, 90), (0.76, 0.24))


def _quantity(rng: random.Random, dose_form: str, days_supply: int) -> int:
    if dose_form in ("Tablet", "Capsule"):
        per_day = _weighted_pick(rng, (1, 2, 3), (0.62, 0.30, 0.08))
        return days_supply * per_day
    return 1 if days_supply <= 30 else 3


def _processing_minutes(rng: random.Random, fill_type: str, store_factor: float) -> float:
    base = 17.0 if fill_type == "N" else 8.0
    # Sum of three uniforms gives a smooth, bounded, right-shifted spread around the base.
    spread = (rng.random() + rng.random() + rng.random()) / 3.0
    minutes = base * store_factor * (0.55 + 0.9 * spread)
    return round(max(minutes, 1.0), 1)


def build_tables(seed: int = SEED) -> dict[str, list[dict[str, object]]]:
    rng = random.Random(seed)
    tables: dict[str, list[dict[str, object]]] = {}

    dates = []
    for day in _daterange(START_DATE, END_DATE):
        quarter = (day.month - 1) // 3 + 1
        dates.append(
            {
                "cal_dt": day.isoformat(),
                "yr": day.year,
                "qtr": f"Q{quarter}",
                "yr_qtr": f"{day.year}-Q{quarter}",
                "mth_num": day.month,
                "mth_nm": MONTH_NAMES[day.month - 1],
                "yr_mth": f"{day.year}-{day.month:02d}",
                "yr_mth_num": day.year * 100 + day.month,
                "dow_num": day.isoweekday(),
                "dow_nm": DAY_NAMES[day.weekday()],
                "is_wkend": "Y" if day.weekday() >= 5 else "N",
            }
        )
    tables["dim_date"] = dates

    tables["dim_store"] = [
        {
            "store_key": s[0],
            "store_cd": s[1],
            "store_nm": s[2],
            "city": s[3],
            "rgn": s[4],
            "store_typ": s[5],
            "open_dt": s[6],
        }
        for s in STORES
    ]

    tables["dim_med"] = [
        {
            "med_key": index,
            "med_cd": med[0],
            "med_nm": med[1],
            "ther_cat": med[2],
            "dose_form": med[3],
            "gnrc_flg": med[4],
        }
        for index, med in enumerate(MEDICATIONS, start=1)
    ]

    meds_by_category, med_weights = _med_weights()
    payer_names = tuple(p[0] for p in PAYERS)
    payer_weights = tuple(p[1] for p in PAYERS)

    fills: list[dict[str, object]] = []
    fill_id = 0
    for day in _daterange(START_DATE, END_DATE):
        dow = DOW_FACTOR[day.weekday()]
        trend = _trend(day)
        for store in STORES:
            store_key, store_cd, _, _, _, _, _, volume_weight, processing_factor = store
            total_lambda = BASE_FILLS_PER_STORE_DAY * volume_weight * dow * trend
            high_refill = (
                store_cd in HIGH_REFILL_STORE_CODES and HIGH_REFILL_WINDOW[0] <= day <= HIGH_REFILL_WINDOW[1]
            )
            for category in CATEGORIES:
                lam = total_lambda * CATEGORY_SHARE[category] * _category_season(category, day)
                count = _poisson(rng, lam)
                for _ in range(count):
                    med_index, med = _weighted_pick(rng, meds_by_category[category], med_weights[category])
                    refill_probability = CATEGORY_REFILL_PROBABILITY[category]
                    if high_refill:
                        refill_probability = min(0.95, refill_probability + 0.30)
                    fill_type = "R" if rng.random() < refill_probability else "N"
                    refill_number = 0 if fill_type == "N" else 1 + int(rng.random() * 5)
                    days_supply = _days_supply(rng, category)
                    fill_id += 1
                    fills.append(
                        {
                            "fill_id": fill_id,
                            "fill_dt": day.isoformat(),
                            "store_key": store_key,
                            "med_key": med_index,
                            "fill_typ": fill_type,
                            "refill_no": refill_number,
                            "qty": _quantity(rng, med[3], days_supply),
                            "days_sply": days_supply,
                            "payer_typ": _weighted_pick(rng, payer_names, payer_weights),
                            "proc_mins": _processing_minutes(rng, fill_type, processing_factor),
                        }
                    )
    tables["fact_rx_fill"] = fills
    return tables


def _format(value: object) -> str:
    if isinstance(value, float):
        return f"{value:.1f}"
    return str(value)


def render_csv(table: str, rows: list[dict[str, object]]) -> bytes:
    columns = [c.name for c in SCHEMA[table]]
    lines = [",".join(columns)]
    for row in rows:
        values = []
        for column in columns:
            text = _format(row[column])
            if any(ch in text for ch in ',"\n'):
                text = '"' + text.replace('"', '""') + '"'
            values.append(text)
        lines.append(",".join(values))
    return ("\n".join(lines) + "\n").encode("utf-8")


def render_schema() -> bytes:
    document = {
        "$comment": "Generated by pharmacy_demo.datagen. Synthetic data only; no person-level data.",
        "seed": SEED,
        "startDate": START_DATE.isoformat(),
        "endDate": END_DATE.isoformat(),
        "tables": {
            table: {
                "file": f"generated/{TABLE_FILES[table]}",
                "columns": [
                    {"name": c.name, "type": c.data_type, "description": c.description} for c in columns
                ],
            }
            for table, columns in SCHEMA.items()
        },
    }
    return (json.dumps(document, indent=2) + "\n").encode("utf-8")


def generate(data_dir: Path, seed: int = SEED) -> dict[str, bytes]:
    """Return every generated file as bytes keyed by path relative to ``data_dir``."""
    tables = build_tables(seed)
    outputs = {f"generated/{TABLE_FILES[t]}": render_csv(t, rows) for t, rows in tables.items()}
    outputs["schema/tables.json"] = render_schema()
    return outputs


def write(data_dir: Path, seed: int = SEED) -> list[Path]:
    written = []
    for relative, content in generate(data_dir, seed).items():
        target = data_dir / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(content)
        written.append(target)
    return written


def check(data_dir: Path, seed: int = SEED) -> list[str]:
    """Return a list of files that differ from a fresh generation (empty when current)."""
    problems = []
    for relative, content in generate(data_dir, seed).items():
        target = data_dir / relative
        if not target.exists():
            problems.append(f"missing: {relative}")
        elif target.read_bytes() != content:
            problems.append(f"out of date: {relative}")
    return problems


def fingerprint(data_dir: Path) -> str:
    digest = hashlib.sha256()
    for name in sorted(TABLE_FILES.values()):
        digest.update(name.encode("utf-8"))
        digest.update((data_dir / "generated" / name).read_bytes())
    return digest.hexdigest()
