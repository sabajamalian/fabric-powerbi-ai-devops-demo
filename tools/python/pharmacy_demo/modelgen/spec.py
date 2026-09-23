"""Model spec for every lab stage. Maintainers only.

Stages:
    0 baseline   What learners start with. Contains the documented defects (B01 to B12).
    1 lab07      Names, descriptions, hidden keys, summarization, rebound report.
    2 lab08      Relationships, marked date table, auto date/time off, measures, decoded fill type.
    3 ai-ready   Q&A enabled, default labels, and Prep data for AI drafts in fabric/ai-prep/.

Agents in the learner's workspace must not read this package: it describes the target model.
The preToolUse hook denies reads unless CPDEMO_MAINTAINER=1.
"""

from __future__ import annotations

from dataclasses import dataclass, field

STAGE_NAMES = {0: "baseline", 1: "lab07", 2: "lab08", 3: "ai-ready"}


@dataclass
class ColumnSpec:
    name: str
    data_type: str
    source: str | None = None
    expression: str | None = None
    description: str | None = None
    hidden: bool = False
    summarize: str = "none"
    format_string: str | None = None
    sort_by: str | None = None
    display_folder: str | None = None
    is_key: bool = False
    default_label: bool = False


@dataclass
class MeasureSpec:
    name: str
    expression: str
    format_string: str
    description: str | None = None
    display_folder: str | None = None


@dataclass
class HierarchySpec:
    name: str
    levels: list[str]
    description: str | None = None


@dataclass
class TableSpec:
    name: str
    csv: str
    description: str | None = None
    data_category: str | None = None
    columns: list[ColumnSpec] = field(default_factory=list)
    measures: list[MeasureSpec] = field(default_factory=list)
    hierarchies: list[HierarchySpec] = field(default_factory=list)


@dataclass
class RelationshipSpec:
    name: str
    from_table: str
    from_column: str
    to_table: str
    to_column: str
    both_directions: bool = False
    date_join: bool = False


@dataclass
class ModelSpec:
    stage: int
    tables: list[TableSpec]
    relationships: list[RelationshipSpec]
    auto_date_time: bool
    qna_enabled: bool


# CSV column kind -> (M type, TMDL dataType)
M_TYPES = {
    "int": ("Int64.Type", "int64"),
    "string": ("type text", "string"),
    "date": ("type date", "dateTime"),
    "decimal": ("type number", "double"),
}


def _baseline_column(name: str, kind: str, summarize: str) -> ColumnSpec:
    data_type = M_TYPES[kind][1]
    format_string = {"int64": "0", "dateTime": "Long Date", "double": None, "string": None}[data_type]
    return ColumnSpec(
        name=name, data_type=data_type, source=name, summarize=summarize, format_string=format_string
    )


def _baseline_tables(schema) -> list[TableSpec]:
    """Stage 0: straight from the CSVs, the way a quick "Get data" import looks."""
    # B07 and B08: keys, IDs, years, and month numbers are summed; processing minutes summed.
    summed = {
        "yr",
        "mth_num",
        "yr_mth_num",
        "dow_num",
        "store_key",
        "med_key",
        "fill_id",
        "refill_no",
        "qty",
        "days_sply",
        "proc_mins",
    }
    tables = []
    for table, columns in schema.items():
        specs = []
        for column in columns:
            summarize = "sum" if column.name in summed else "none"
            specs.append(_baseline_column(column.name, column.data_type, summarize))
        tables.append(TableSpec(name=table, csv=f"{table}.csv", columns=specs))
    return tables


RENAMES = {
    "dim_date": (
        "Date",
        {
            "cal_dt": "Date",
            "yr": "Year",
            "qtr": "Quarter",
            "yr_qtr": "Year Quarter",
            "mth_num": "Month Number",
            "mth_nm": "Month",
            "yr_mth": "Year Month",
            "yr_mth_num": "Year Month Number",
            "dow_num": "Day of Week Number",
            "dow_nm": "Day of Week",
            "is_wkend": "Is Weekend",
        },
    ),
    "dim_store": (
        "Store",
        {
            "store_key": "Store Key",
            "store_cd": "Store Code",
            "store_nm": "Store Name",
            "city": "City",
            "rgn": "Region",
            "store_typ": "Store Type",
            "open_dt": "Open Date",
        },
    ),
    "dim_med": (
        "Medication",
        {
            "med_key": "Medication Key",
            "med_cd": "Medication Code",
            "med_nm": "Medication Name",
            "ther_cat": "Therapeutic Category",
            "dose_form": "Dosage Form",
            "gnrc_flg": "Generic Flag",
        },
    ),
    "fact_rx_fill": (
        "Prescription Fill",
        {
            "fill_id": "Fill ID",
            "fill_dt": "Fill Date",
            "store_key": "Store Key",
            "med_key": "Medication Key",
            "fill_typ": "Fill Type Code",
            "refill_no": "Refill Number",
            "qty": "Quantity",
            "days_sply": "Days Supply",
            "payer_typ": "Payer Type",
            "proc_mins": "Processing Time (min)",
        },
    ),
}

TABLE_DESCRIPTIONS = {
    "Date": "Calendar of every day from 1 Jan 2024 to 31 Dec 2025. Use for all time analysis; the latest complete month is December 2025.",
    "Store": "One row per Contoso Pharmacy store (12 stores in 4 regions). Use for store, city, region, and store type analysis.",
    "Medication": "One row per medication dispensed (60 generic products in 8 therapeutic categories). Synthetic catalog.",
    "Prescription Fill": "One row per prescription fill (new or refill) at a store. Synthetic; no patient data. Use its measures for volume, refills, and processing time.",
}

COLUMN_DESCRIPTIONS = {
    ("Date", "Date"): "Calendar date. Key of the Date table; relate fact dates to this column.",
    ("Date", "Year"): "Calendar year, for example 2025.",
    ("Date", "Quarter"): "Calendar quarter label, Q1 to Q4. Combine with Year, or use Year Quarter.",
    (
        "Date",
        "Year Quarter",
    ): "Year and quarter, for example 2025-Q4. Use for quarter-level questions such as latest quarter.",
    ("Date", "Month Number"): "Month number 1 to 12. Used to sort Month; not for display.",
    (
        "Date",
        "Month",
    ): "Month name, January to December. Sorted by Month Number. Combine with Year, or use Year Month.",
    (
        "Date",
        "Year Month",
    ): "Year and month as YYYY-MM, for example 2025-12. Preferred column for monthly trends.",
    ("Date", "Year Month Number"): "Year and month as a number, for example 202512. Used to sort Year Month.",
    (
        "Date",
        "Day of Week Number",
    ): "Day of week number, 1 is Monday and 7 is Sunday. Used to sort Day of Week.",
    ("Date", "Day of Week"): "Day of week name, Monday to Sunday.",
    ("Date", "Is Weekend"): "Y for Saturday or Sunday, N for weekdays.",
    ("Store", "Store Key"): "Surrogate key. Technical; hidden.",
    ("Store", "Store Code"): "Store code S001 to S012. Use Store Name for display.",
    ("Store", "Store Name"): "Store name, for example Riverbend. Default label for a store.",
    ("Store", "City"): "Fictional city where the store is located.",
    ("Store", "Region"): "Sales region of the store: North, South, East, or West.",
    ("Store", "Store Type"): "Store format: Standard, Drive-thru, or 24-hour.",
    ("Store", "Open Date"): "Date the store opened. Not related to the Date table.",
    ("Medication", "Medication Key"): "Surrogate key. Technical; hidden.",
    ("Medication", "Medication Code"): "Synthetic medication code M001 to M060. Not a real drug code.",
    (
        "Medication",
        "Medication Name",
    ): "Generic medication name and strength, for example Amoxicillin 500 mg. Default label.",
    (
        "Medication",
        "Therapeutic Category",
    ): "One of 8 therapeutic categories, for example Respiratory or Dermatology. Also called drug or medication category.",
    ("Medication", "Dosage Form"): "Dosage form such as Tablet, Capsule, Inhaler, or Cream.",
    ("Medication", "Generic Flag"): "Y when a generic version is dispensed, N for brand.",
    (
        "Prescription Fill",
        "Fill ID",
    ): "Sequential fill identifier. Technical; hidden. Count fills with the Prescriptions Filled measure.",
    (
        "Prescription Fill",
        "Fill Date",
    ): "Date the prescription was filled. Use the Date table for time analysis.",
    ("Prescription Fill", "Store Key"): "Foreign key to Store. Technical; hidden.",
    ("Prescription Fill", "Medication Key"): "Foreign key to Medication. Technical; hidden.",
    (
        "Prescription Fill",
        "Fill Type Code",
    ): "Raw code: N new prescription, R refill. Use Fill Type for display.",
    (
        "Prescription Fill",
        "Refill Number",
    ): "Refill sequence number; 0 for new prescriptions. An attribute, not something to sum.",
    (
        "Prescription Fill",
        "Quantity",
    ): "Quantity dispensed, in units of the dosage form (tablets, inhalers, tubes).",
    ("Prescription Fill", "Days Supply"): "Days of therapy supplied by the fill, for example 30 or 90.",
    ("Prescription Fill", "Payer Type"): "Payer for the fill: Commercial, Medicare, Medicaid, or Cash.",
    (
        "Prescription Fill",
        "Processing Time (min)",
    ): "Minutes from intake to ready for pickup for one fill. Use Avg Processing Time (min) for averages; never sum.",
    (
        "Prescription Fill",
        "Fill Type",
    ): "New or Refill, decoded from Fill Type Code. Use for new versus refill analysis.",
}

HIDDEN_COLUMNS = {
    ("Store", "Store Key"),
    ("Medication", "Medication Key"),
    ("Prescription Fill", "Fill ID"),
    ("Prescription Fill", "Store Key"),
    ("Prescription Fill", "Medication Key"),
    ("Date", "Month Number"),
    ("Date", "Year Month Number"),
    ("Date", "Day of Week Number"),
}

SUMMARIZE_AFTER_LAB07 = {
    ("Prescription Fill", "Quantity"): "sum",
    ("Prescription Fill", "Days Supply"): "sum",
    ("Prescription Fill", "Processing Time (min)"): "average",
}

FORMAT_AFTER_LAB07 = {
    ("Prescription Fill", "Processing Time (min)"): "0.0",
    ("Prescription Fill", "Quantity"): "#,0",
    ("Prescription Fill", "Days Supply"): "#,0",
    ("Date", "Date"): "yyyy-mm-dd",
}

SORT_BY = {
    ("Date", "Month"): "Month Number",
    ("Date", "Year Month"): "Year Month Number",
    ("Date", "Day of Week"): "Day of Week Number",
}

FACT = "Prescription Fill"

MEASURES = [
    MeasureSpec(
        "Prescriptions Filled",
        "COUNTROWS('Prescription Fill')",
        "#,0",
        "Number of prescription fills, new and refill. The standard volume measure; also called fills, scripts, or prescription volume.",
        "Volume",
    ),
    MeasureSpec(
        "New Prescriptions",
        "CALCULATE([Prescriptions Filled], 'Prescription Fill'[Fill Type Code] = \"N\")",
        "#,0",
        "Fills of new prescriptions (Fill Type = New).",
        "Volume",
    ),
    MeasureSpec(
        "Refills",
        "CALCULATE([Prescriptions Filled], 'Prescription Fill'[Fill Type Code] = \"R\")",
        "#,0",
        "Fills that are refills of an existing prescription (Fill Type = Refill).",
        "Refills",
    ),
    MeasureSpec(
        "Refill Rate",
        "DIVIDE([Refills], [Prescriptions Filled])",
        "0.0%",
        "Refills divided by all fills. Use to compare refill activity between stores or periods.",
        "Refills",
    ),
    MeasureSpec(
        "Refill Rate Index vs Chain",
        "DIVIDE([Refill Rate], CALCULATE([Refill Rate], REMOVEFILTERS('Store')))",
        "0.00",
        "Refill Rate divided by the chain-wide Refill Rate for the same period. 1.00 is the chain average; 1.25 or more is unusually high.",
        "Refills",
    ),
    MeasureSpec(
        "High Refill Activity Flag",
        "IF([Refill Rate Index vs Chain] >= 1.25, 1, 0)",
        "0",
        "1 when Refill Rate Index vs Chain is 1.25 or more, otherwise 0. Use with Store to find unusually high refill activity.",
        "Refills",
    ),
    MeasureSpec(
        "Avg Processing Time (min)",
        "AVERAGE('Prescription Fill'[Processing Time (min)])",
        "0.0",
        "Average minutes from intake to ready for pickup per fill. Lower is better. Use for processing time questions.",
        "Processing",
    ),
    MeasureSpec(
        "Prescriptions Filled PM",
        "CALCULATE([Prescriptions Filled], DATEADD('Date'[Date], -1, MONTH))",
        "#,0",
        "Prescriptions Filled in the previous month. Filter a month (for example Year Month 2025-12) to compare.",
        "Time Comparison",
    ),
    MeasureSpec(
        "MoM Change",
        "[Prescriptions Filled] - [Prescriptions Filled PM]",
        "+#,0;-#,0;0",
        "Month-over-month change in Prescriptions Filled. Previous period means previous month unless stated.",
        "Time Comparison",
    ),
    MeasureSpec(
        "MoM %",
        "DIVIDE([MoM Change], [Prescriptions Filled PM])",
        "+0.0%;-0.0%;0.0%",
        "Month-over-month percent change in Prescriptions Filled.",
        "Time Comparison",
    ),
    MeasureSpec(
        "Prescriptions Filled PY",
        "CALCULATE([Prescriptions Filled], SAMEPERIODLASTYEAR('Date'[Date]))",
        "#,0",
        "Prescriptions Filled in the same period of the previous year.",
        "Time Comparison",
    ),
    MeasureSpec(
        "YoY %",
        "DIVIDE([Prescriptions Filled] - [Prescriptions Filled PY], [Prescriptions Filled PY])",
        "+0.0%;-0.0%;0.0%",
        "Year-over-year percent change in Prescriptions Filled.",
        "Time Comparison",
    ),
]

REQUIRED_MEASURES = [m.name for m in MEASURES]


def _renamed_tables(schema, stage: int) -> list[TableSpec]:
    tables = []
    for source_table, columns in schema.items():
        table_name, renames = RENAMES[source_table]
        specs = []
        for column in columns:
            name = renames[column.name]
            key = (table_name, name)
            data_type = M_TYPES[column.data_type][1]
            format_string = FORMAT_AFTER_LAB07.get(key)
            if format_string is None:
                format_string = {"int64": "0", "dateTime": "Long Date", "double": "0.0", "string": None}[
                    data_type
                ]
            hidden = key in HIDDEN_COLUMNS
            if stage >= 2 and key in {(FACT, "Fill Date"), (FACT, "Fill Type Code")}:
                hidden = True
            specs.append(
                ColumnSpec(
                    name=name,
                    data_type=data_type,
                    source=column.name,
                    description=COLUMN_DESCRIPTIONS[key],
                    hidden=hidden,
                    summarize=SUMMARIZE_AFTER_LAB07.get(key, "none"),
                    format_string=format_string,
                    sort_by=SORT_BY.get(key) if stage >= 2 else None,
                    is_key=stage >= 2 and key == ("Date", "Date"),
                    default_label=stage >= 3
                    and key in {("Store", "Store Name"), ("Medication", "Medication Name")},
                )
            )
        table = TableSpec(
            name=table_name,
            csv=f"{source_table}.csv",
            description=TABLE_DESCRIPTIONS[table_name],
            columns=specs,
        )
        if stage >= 2 and table_name == "Date":
            table.data_category = "Time"
            table.hierarchies.append(
                HierarchySpec(
                    "Calendar",
                    ["Year", "Year Quarter", "Year Month", "Date"],
                    "Drill from year to quarter to month to day.",
                )
            )
        if stage >= 2 and table_name == FACT:
            specs.append(
                ColumnSpec(
                    name="Fill Type",
                    data_type="string",
                    expression='IF(\'Prescription Fill\'[Fill Type Code] = "N", "New", "Refill")',
                    description=COLUMN_DESCRIPTIONS[(FACT, "Fill Type")],
                )
            )
            table.measures = list(MEASURES)
        tables.append(table)
    return tables


def build(stage: int, schema) -> ModelSpec:
    if stage == 0:
        return ModelSpec(
            stage=0,
            tables=_baseline_tables(schema),
            relationships=[
                RelationshipSpec(
                    "fact_rx_fill to dim_date",
                    "fact_rx_fill",
                    "fill_dt",
                    "dim_date",
                    "cal_dt",
                    date_join=True,
                ),
                # B05: bidirectional filtering to the store dimension.
                RelationshipSpec(
                    "fact_rx_fill to dim_store",
                    "fact_rx_fill",
                    "store_key",
                    "dim_store",
                    "store_key",
                    both_directions=True,
                ),
                # B04: no relationship to dim_med.
            ],
            auto_date_time=True,
            qna_enabled=False,
        )
    tables = _renamed_tables(schema, stage)
    relationships = [
        RelationshipSpec("Prescription Fill to Date", FACT, "Fill Date", "Date", "Date", date_join=True),
        RelationshipSpec(
            "Prescription Fill to Store", FACT, "Store Key", "Store", "Store Key", both_directions=stage < 2
        ),
    ]
    if stage >= 2:
        relationships.append(
            RelationshipSpec(
                "Prescription Fill to Medication", FACT, "Medication Key", "Medication", "Medication Key"
            )
        )
    return ModelSpec(
        stage=stage,
        tables=tables,
        relationships=relationships,
        auto_date_time=stage < 2,
        qna_enabled=stage >= 3,
    )
