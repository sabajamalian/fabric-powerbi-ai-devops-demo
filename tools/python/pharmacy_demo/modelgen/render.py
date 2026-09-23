"""Render a ModelSpec into PBIP files (TMDL semantic model plus PBIR report). Maintainers only."""

from __future__ import annotations

import hashlib
import json
import uuid

from .. import datagen
from . import aiprep
from .spec import M_TYPES, STAGE_NAMES, ModelSpec, TableSpec, build

PROJECT = "ContosoPharmacy"
SM = f"{PROJECT}.SemanticModel"
RPT = f"{PROJECT}.Report"
DATA_FOLDER_DEFAULT = "C:\\ContosoPharmacyDemo\\data\\"
SCHEMA_BASE = "https://developer.microsoft.com/json-schemas/fabric"


def quote(name: str) -> str:
    if name and all(ch.isalnum() or ch == "_" for ch in name) and not name[0].isdigit():
        return name
    return "'" + name.replace("'", "''") + "'"


def _logical_id(kind: str) -> str:
    # Deterministic, not tied to any tenant or workspace. Fabric Git integration uses it to match items.
    return str(uuid.uuid5(uuid.NAMESPACE_URL, f"contoso-pharmacy-demo/{kind}"))


def _hex_id(seed: str) -> str:
    return hashlib.sha1(seed.encode("utf-8")).hexdigest()[:20]


def _json(document) -> str:
    return json.dumps(document, indent=2) + "\n"


def _m_source(table: TableSpec, schema) -> list[str]:
    source_table = table.csv.removesuffix(".csv")
    columns = schema[source_table]
    types = ", ".join(f'{{"{c.name}", {M_TYPES[c.data_type][0]}}}' for c in columns)
    return [
        "let",
        f'    Source = Csv.Document(File.Contents(DataFolderPath & "{table.csv}"), '
        f'[Delimiter = ",", Columns = {len(columns)}, Encoding = 65001, QuoteStyle = QuoteStyle.Csv]),',
        "    PromotedHeaders = Table.PromoteHeaders(Source, [PromoteAllScalars = true]),",
        f'    ChangedType = Table.TransformColumnTypes(PromotedHeaders, {{{types}}}, "en-US")',
        "in",
        "    ChangedType",
    ]


def render_table(table: TableSpec, schema) -> str:
    t = "\t"
    lines: list[str] = []
    if table.description:
        lines.append(f"/// {table.description}")
    lines.append(f"table {quote(table.name)}")
    if table.data_category:
        lines.append(f"{t}dataCategory: {table.data_category}")
    lines.append("")

    for measure in table.measures:
        if measure.description:
            lines.append(f"{t}/// {measure.description}")
        lines.append(f"{t}measure {quote(measure.name)} = {measure.expression}")
        lines.append(f"{t}{t}formatString: {measure.format_string}")
        if measure.display_folder:
            lines.append(f"{t}{t}displayFolder: {measure.display_folder}")
        lines.append("")

    for column in table.columns:
        if column.description:
            lines.append(f"{t}/// {column.description}")
        if column.expression:
            lines.append(f"{t}column {quote(column.name)} = {column.expression}")
        else:
            lines.append(f"{t}column {quote(column.name)}")
        lines.append(f"{t}{t}dataType: {column.data_type}")
        if column.is_key:
            lines.append(f"{t}{t}isKey")
        if column.hidden:
            lines.append(f"{t}{t}isHidden")
        if column.default_label:
            lines.append(f"{t}{t}isDefaultLabel")
        if column.format_string:
            lines.append(f"{t}{t}formatString: {column.format_string}")
        if column.display_folder:
            lines.append(f"{t}{t}displayFolder: {column.display_folder}")
        lines.append(f"{t}{t}summarizeBy: {column.summarize}")
        if column.source:
            lines.append(f"{t}{t}sourceColumn: {column.source}")
        if column.sort_by:
            lines.append(f"{t}{t}sortByColumn: {quote(column.sort_by)}")
        lines.append("")
        lines.append(f"{t}{t}annotation SummarizationSetBy = User")
        if column.data_type == "dateTime":
            lines.append("")
            lines.append(f"{t}{t}annotation UnderlyingDateTimeDataType = Date")
        lines.append("")

    for hierarchy in table.hierarchies:
        if hierarchy.description:
            lines.append(f"{t}/// {hierarchy.description}")
        lines.append(f"{t}hierarchy {quote(hierarchy.name)}")
        lines.append("")
        for level in hierarchy.levels:
            lines.append(f"{t}{t}level {quote(level)}")
            lines.append(f"{t}{t}{t}column: {quote(level)}")
            lines.append("")

    lines.append(f"{t}partition {quote(table.name)} = m")
    lines.append(f"{t}{t}mode: import")
    lines.append(f"{t}{t}source =")
    for m_line in _m_source(table, schema):
        lines.append(f"{t}{t}{t}{m_line}")
    lines.append("")
    return "\n".join(lines)


def render_relationships(spec: ModelSpec) -> str:
    lines: list[str] = []
    for rel in spec.relationships:
        lines.append(f"relationship {quote(rel.name)}")
        if rel.both_directions:
            lines.append("\tcrossFilteringBehavior: bothDirections")
        if rel.date_join:
            lines.append("\tjoinOnDateBehavior: datePartOnly")
        lines.append(f"\tfromColumn: {quote(rel.from_table)}.{quote(rel.from_column)}")
        lines.append(f"\ttoColumn: {quote(rel.to_table)}.{quote(rel.to_column)}")
        lines.append("")
    return "\n".join(lines)


def render_model(spec: ModelSpec) -> str:
    lines = [
        "model Model",
        "\tculture: en-US",
        "\tdefaultPowerBIDataSourceVersion: powerBI_V3",
        "\tsourceQueryCulture: en-US",
        "\tdataAccessOptions",
        "\t\tlegacyRedirects",
        "\t\treturnErrorValuesAsNull",
        "",
        f"annotation __PBI_TimeIntelligenceEnabled = {1 if spec.auto_date_time else 0}",
        "",
    ]
    for table in spec.tables:
        lines.append(f"ref table {quote(table.name)}")
    lines += ["", "ref cultureInfo en-US", ""]
    return "\n".join(lines)


def render_semantic_model(spec: ModelSpec, schema) -> dict[str, str]:
    files: dict[str, str] = {}
    base = f"fabric/{SM}"
    files[f"{base}/definition.pbism"] = _json(
        {
            "$schema": f"{SCHEMA_BASE}/item/semanticModel/definitionProperties/1.0.0/schema.json",
            "version": "4.2",
            "settings": {"qnaEnabled": spec.qna_enabled},
        }
    )
    files[f"{base}/.platform"] = _json(
        {
            "$schema": f"{SCHEMA_BASE}/gitIntegration/platformProperties/2.0.0/schema.json",
            "metadata": {"type": "SemanticModel", "displayName": PROJECT},
            "config": {"version": "2.0", "logicalId": _logical_id("semantic-model")},
        }
    )
    files[f"{base}/definition/database.tmdl"] = (
        f"database {PROJECT}\n\tcompatibilityLevel: 1600\n\tcompatibilityMode: powerBI\n\tlanguage: 1033\n"
    )
    files[f"{base}/definition/model.tmdl"] = render_model(spec)
    files[f"{base}/definition/relationships.tmdl"] = render_relationships(spec)
    files[f"{base}/definition/expressions.tmdl"] = (
        "/// Folder that holds the synthetic CSV files. Created by scripts/Set-LocalDataLink.ps1.\n"
        f'expression DataFolderPath = "{DATA_FOLDER_DEFAULT}" '
        'meta [IsParameterQuery = true, Type = "Text", IsParameterQueryRequired = true]\n'
    )
    files[f"{base}/definition/cultures/en-US.tmdl"] = "cultureInfo en-US\n"
    for table in spec.tables:
        files[f"{base}/definition/tables/{table.name}.tmdl"] = render_table(table, schema)
    return files


# ---------- report ----------


def _column_field(entity: str, prop: str) -> dict:
    return {"Column": {"Expression": {"SourceRef": {"Entity": entity}}, "Property": prop}}


def _projection_column(entity: str, prop: str) -> dict:
    return {"field": _column_field(entity, prop), "queryRef": f"{entity}.{prop}", "nativeQueryRef": prop}


def _projection_measure(entity: str, prop: str) -> dict:
    return {
        "field": {"Measure": {"Expression": {"SourceRef": {"Entity": entity}}, "Property": prop}},
        "queryRef": f"{entity}.{prop}",
        "nativeQueryRef": prop,
    }


AGG_NAMES = {0: ("Sum", "Sum of"), 1: ("Avg", "Average of"), 5: ("CountNonNull", "Count of")}


def _projection_agg(entity: str, prop: str, function: int) -> dict:
    fn, label = AGG_NAMES[function]
    return {
        "field": {"Aggregation": {"Expression": _column_field(entity, prop), "Function": function}},
        "queryRef": f"{fn}({entity}.{prop})",
        "nativeQueryRef": f"{label} {prop}",
    }


def _title(text: str) -> dict:
    return {
        "title": [
            {
                "properties": {
                    "show": {"expr": {"Literal": {"Value": "true"}}},
                    "text": {"expr": {"Literal": {"Value": "'" + text.replace("'", "''") + "'"}}},
                }
            }
        ]
    }


def _visual(
    page: str,
    slug: str,
    visual_type: str,
    position: tuple[int, int, int, int],
    roles: dict,
    title: str,
    index: int,
) -> tuple[str, dict]:
    name = _hex_id(f"{page}/{slug}")
    x, y, w, h = position
    document = {
        "$schema": f"{SCHEMA_BASE}/item/report/definition/visualContainer/2.9.0/schema.json",
        "name": name,
        "position": {"x": x, "y": y, "z": 1000 * index, "height": h, "width": w, "tabOrder": 1000 * index},
        "visual": {
            "visualType": visual_type,
            "query": {"queryState": {role: {"projections": items} for role, items in roles.items()}},
            "visualContainerObjects": _title(title),
            "drillFilterOtherVisuals": True,
        },
    }
    return name, document


def _report_pages(spec: ModelSpec) -> list[tuple[str, str, list[tuple[str, dict]]]]:
    if spec.stage == 0:
        fact, store, date = "fact_rx_fill", "dim_store", "dim_date"
        count = _projection_agg(fact, "fill_id", 5)
        region, month, store_name = (
            _projection_column(store, "rgn"),
            _projection_column(date, "yr_mth"),
            _projection_column(store, "store_nm"),
        )
        processing = _projection_agg(fact, "proc_mins", 0)
    elif spec.stage == 1:
        fact, store, date = "Prescription Fill", "Store", "Date"
        count = _projection_agg(fact, "Fill ID", 5)
        region, month, store_name = (
            _projection_column(store, "Region"),
            _projection_column(date, "Year Month"),
            _projection_column(store, "Store Name"),
        )
        processing = _projection_agg(fact, "Processing Time (min)", 1)
    else:
        fact, store, date = "Prescription Fill", "Store", "Date"
        count = _projection_measure(fact, "Prescriptions Filled")
        region, month, store_name = (
            _projection_column(store, "Region"),
            _projection_column(date, "Year Month"),
            _projection_column(store, "Store Name"),
        )
        processing = _projection_measure(fact, "Avg Processing Time (min)")

    overview = "overview"
    visuals = [
        _visual(
            overview,
            "total-fills",
            "cardVisual",
            (20, 20, 300, 140),
            {"Data": [count]},
            "Prescriptions filled",
            1,
        ),
        _visual(
            overview,
            "fills-by-region",
            "clusteredColumnChart",
            (340, 20, 920, 320),
            {"Category": [region], "Y": [count]},
            "Prescriptions filled by region",
            2,
        ),
        _visual(
            overview,
            "fills-by-month",
            "lineChart",
            (20, 360, 820, 340),
            {"Category": [month], "Y": [count]},
            "Prescriptions filled by month",
            3,
        ),
        _visual(
            overview,
            "processing-by-store",
            "tableEx",
            (860, 360, 400, 340),
            {"Values": [store_name, processing]},
            "Processing time by store",
            4,
        ),
    ]
    pages = [(overview, "Overview", visuals)]
    if spec.stage >= 2:
        refill_page = "refills-and-categories"
        category = _projection_column("Medication", "Therapeutic Category")
        pages.append(
            (
                refill_page,
                "Refills and categories",
                [
                    _visual(
                        refill_page,
                        "refill-index-by-store",
                        "tableEx",
                        (20, 20, 600, 680),
                        {
                            "Values": [
                                store_name,
                                _projection_measure(fact, "Refill Rate"),
                                _projection_measure(fact, "Refill Rate Index vs Chain"),
                                _projection_measure(fact, "High Refill Activity Flag"),
                            ]
                        },
                        "Refill rate index by store",
                        1,
                    ),
                    _visual(
                        refill_page,
                        "mom-change-by-category",
                        "clusteredColumnChart",
                        (640, 20, 620, 680),
                        {"Category": [category], "Y": [_projection_measure(fact, "MoM Change")]},
                        "Month-over-month change by therapeutic category",
                        2,
                    ),
                ],
            )
        )
    return pages


def render_report(spec: ModelSpec) -> dict[str, str]:
    base = f"fabric/{RPT}"
    theme_name = "ContosoPharmacy.json"
    files: dict[str, str] = {
        f"{base}/.platform": _json(
            {
                "$schema": f"{SCHEMA_BASE}/gitIntegration/platformProperties/2.0.0/schema.json",
                "metadata": {"type": "Report", "displayName": PROJECT},
                "config": {"version": "2.0", "logicalId": _logical_id("report")},
            }
        ),
        f"{base}/definition.pbir": _json(
            {
                "$schema": f"{SCHEMA_BASE}/item/report/definitionProperties/2.0.0/schema.json",
                "version": "4.0",
                "datasetReference": {"byPath": {"path": f"../{SM}"}},
            }
        ),
        f"{base}/definition/version.json": _json(
            {
                "$schema": f"{SCHEMA_BASE}/item/report/definition/versionMetadata/1.0.0/schema.json",
                "version": "2.0.0",
            }
        ),
        f"{base}/definition/report.json": _json(
            {
                "$schema": f"{SCHEMA_BASE}/item/report/definition/report/3.1.0/schema.json",
                "themeCollection": {
                    "customTheme": {
                        "name": theme_name,
                        "reportVersionAtImport": {"visual": "2.6.0", "report": "3.1.0", "page": "2.3.0"},
                        "type": "RegisteredResources",
                    }
                },
                "resourcePackages": [
                    {
                        "name": "RegisteredResources",
                        "type": "RegisteredResources",
                        "items": [{"name": theme_name, "path": theme_name, "type": "CustomTheme"}],
                    }
                ],
                "settings": {
                    "useStylableVisualContainerHeader": True,
                    "defaultDrillFilterOtherVisuals": True,
                },
            }
        ),
        f"{base}/StaticResources/RegisteredResources/{theme_name}": _json(
            {
                "name": theme_name,
                "dataColors": [
                    "#0F6CBD",
                    "#C239B3",
                    "#107C10",
                    "#CA5010",
                    "#5C2E91",
                    "#038387",
                    "#986F0B",
                    "#4F6BED",
                ],
                "background": "#FFFFFF",
                "foreground": "#242424",
                "tableAccent": "#0F6CBD",
            }
        ),
    }
    pages = _report_pages(spec)
    page_ids = []
    for slug, display, visuals in pages:
        page_id = _hex_id(f"page/{slug}")
        page_ids.append(page_id)
        files[f"{base}/definition/pages/{page_id}/page.json"] = _json(
            {
                "$schema": f"{SCHEMA_BASE}/item/report/definition/page/2.1.0/schema.json",
                "name": page_id,
                "displayName": display,
                "displayOption": "FitToPage",
                "height": 720,
                "width": 1280,
            }
        )
        for name, document in visuals:
            files[f"{base}/definition/pages/{page_id}/visuals/{name}/visual.json"] = _json(document)
    files[f"{base}/definition/pages/pages.json"] = _json(
        {
            "$schema": f"{SCHEMA_BASE}/item/report/definition/pagesMetadata/1.0.0/schema.json",
            "pageOrder": page_ids,
            "activePageName": page_ids[0],
        }
    )
    return files


def render_project() -> dict[str, str]:
    return {
        f"fabric/{PROJECT}.pbip": _json(
            {
                "$schema": f"{SCHEMA_BASE}/pbip/pbipProperties/1.0.0/schema.json",
                "version": "1.0",
                "artifacts": [{"report": {"path": RPT}}],
                "settings": {"enableAutoRecovery": True},
            }
        ),
        f"fabric/{SM}/.pbi/editorSettings.json": _json(
            {
                "version": "1.0",
                "autodetectRelationships": False,
                "parallelQueryLoading": True,
                "typeDetectionEnabled": True,
                "relationshipImportEnabled": True,
                "shouldNotifyUserOfNameConflictResolution": True,
            }
        ),
    }


def render(stage: int) -> dict[str, str]:
    schema = datagen.SCHEMA
    spec = build(stage, schema)
    files = {}
    files.update(render_project())
    files.update(render_semantic_model(spec, schema))
    files.update(render_report(spec))
    if stage >= 3:
        files.update(aiprep.render())
    return files


def stage_name(stage: int) -> str:
    return STAGE_NAMES[stage]
