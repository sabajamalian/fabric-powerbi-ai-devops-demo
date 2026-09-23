"""Convention and AI-readiness checks driven by rules/*.yaml.

These are not CI gates on main: the baseline model breaks them on purpose. Lab checks use them to
confirm a learner's progress, and the model-assessor agent uses the same rules as its checklist.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

import yaml

from . import paths, tmdl


@dataclass
class Issue:
    rule: str
    severity: str  # high | medium | low
    obj: str
    finding: str
    fix: str

    def as_dict(self) -> dict:
        return {
            "rule": self.rule,
            "severity": self.severity,
            "object": self.obj,
            "finding": self.finding,
            "fix": self.fix,
        }


RULE_TITLES = {
    "C01": "Business-friendly names",
    "C02": "Descriptions present",
    "C03": "Description length",
    "C04": "Keys and helpers hidden",
    "C05": "Default summarization",
    "C06": "Raw codes decoded",
    "C07": "Required relationships",
    "C08": "Single-direction filters",
    "C09": "Marked date table",
    "C10": "Auto date/time off",
    "C11": "Sort-by columns",
    "C12": "Required measures",
    "C13": "Measure format strings and folders",
    "C14": "Default labels",
    "C15": "Q&A and AI prep drafts",
}


def load_rules(root: Path | None = None) -> tuple[dict, dict]:
    root = root or paths.repo_root()
    with (root / "rules" / "naming-conventions.yaml").open(encoding="utf-8") as fh:
        naming = yaml.safe_load(fh)
    with (root / "rules" / "required-model-objects.yaml").open(encoding="utf-8") as fh:
        required = yaml.safe_load(fh)
    return naming, required


def _visible(node: tmdl.Node) -> bool:
    return node.props.get("isHidden") is not True


def _name_problems(name: str, naming: dict) -> list[str]:
    rules = naming["names"]
    problems = []
    if rules.get("forbid_underscores") and "_" in name:
        problems.append("uses underscores")
    if not re.match(rules["visible_object_pattern"], name):
        problems.append("isn't Title Case business wording")
    allowed = {s.casefold() for s in rules.get("allowed_short_forms", [])}
    words = re.split(r"[\s_()/%-]+", name)
    for word in words:
        if (
            word
            and word.casefold() in {a.casefold() for a in rules["forbidden_abbreviations"]}
            and word.casefold() not in allowed
        ):
            problems.append(f"uses the abbreviation '{word}'")
            break
    return problems


def assess(semantic_model_dir: Path, root: Path | None = None) -> list[Issue]:
    root = root or paths.repo_root()
    naming, required = load_rules(root)
    model = tmdl.load_model(semantic_model_dir)
    issues: list[Issue] = []
    hidden_patterns = [re.compile(p) for p in naming["columns"]["hidden_patterns"]]
    max_len = naming["descriptions"]["max_length"]

    for table_name, table in model.tables.items():
        problems = _name_problems(table_name, naming)
        if problems:
            issues.append(
                Issue(
                    "C01",
                    "high",
                    f"table {table_name}",
                    f"Table name {', '.join(problems)}.",
                    "Rename to a business term, for example 'Prescription Fill'.",
                )
            )
        if not table.description:
            issues.append(
                Issue(
                    "C02",
                    "high",
                    f"table {table_name}",
                    "Table has no description.",
                    "Add a /// description that says what one row is.",
                )
            )
        elif len(table.description) > max_len:
            issues.append(
                Issue(
                    "C03",
                    "low",
                    f"table {table_name}",
                    f"Description is {len(table.description)} characters.",
                    f"Keep it under {max_len}; Copilot reads only the start.",
                )
            )
        additive = naming["columns"]["additive"].get(table_name, {})
        codes = naming["columns"]["raw_code_columns"].get(table_name, {})
        columns = model.columns(table_name)
        for column in table.child("column"):
            ref = f"{table_name}[{column.name}]"
            visible = _visible(column)
            if visible:
                problems = _name_problems(column.name, naming)
                if problems:
                    issues.append(
                        Issue(
                            "C01",
                            "high",
                            f"column {ref}",
                            f"Column name {', '.join(problems)}.",
                            "Rename to business wording; keep sourceColumn unchanged.",
                        )
                    )
                if not column.description:
                    issues.append(
                        Issue(
                            "C02",
                            "medium",
                            f"column {ref}",
                            "Visible column has no description.",
                            "Add a short /// description.",
                        )
                    )
            if column.description and len(column.description) > max_len:
                issues.append(
                    Issue(
                        "C03",
                        "low",
                        f"column {ref}",
                        f"Description is {len(column.description)} characters.",
                        f"Keep it under {max_len}.",
                    )
                )
            if visible and any(p.search(column.name) for p in hidden_patterns):
                issues.append(
                    Issue("C04", "medium", f"column {ref}", "Key or sort helper is visible.", "Set isHidden.")
                )
            summarize = column.props.get("summarizeBy", "default")
            expected = additive.get(column.name, "none")
            if column.props.get("dataType") in {"int64", "double", "decimal"} and summarize != expected:
                issues.append(
                    Issue(
                        "C05",
                        "high" if summarize == "sum" else "medium",
                        f"column {ref}",
                        f"summarizeBy is {summarize}; expected {expected}.",
                        f"Set summarizeBy: {expected}.",
                    )
                )
            if column.name in codes and visible:
                decoded = codes[column.name]
                if decoded not in columns:
                    issues.append(
                        Issue(
                            "C06",
                            "medium",
                            f"column {ref}",
                            "Raw code column is visible with no decoded column.",
                            f"Add '{decoded}' with readable values and hide the code.",
                        )
                    )
        for measure in table.child("measure"):
            ref = f"{table_name}[{measure.name}]"
            if not measure.description:
                issues.append(
                    Issue(
                        "C02",
                        "high",
                        f"measure {ref}",
                        "Measure has no description.",
                        "Add a /// description with the business meaning and synonyms.",
                    )
                )
            elif len(measure.description) > max_len:
                issues.append(
                    Issue(
                        "C03",
                        "low",
                        f"measure {ref}",
                        f"Description is {len(measure.description)} characters.",
                        f"Keep it under {max_len}.",
                    )
                )
            if "formatString" not in measure.props:
                issues.append(
                    Issue(
                        "C13",
                        "medium",
                        f"measure {ref}",
                        "Measure has no formatString.",
                        "Add a formatString such as #,0 or 0.0%.",
                    )
                )
            if "displayFolder" not in measure.props:
                issues.append(
                    Issue(
                        "C13",
                        "low",
                        f"measure {ref}",
                        "Measure has no displayFolder.",
                        f"Use one of: {', '.join(naming['measures']['display_folders'])}.",
                    )
                )

    for name in required["tables"]:
        if name not in model.tables:
            issues.append(
                Issue(
                    "C01",
                    "high",
                    f"table {name}",
                    "Required table name not found.",
                    "Rename the matching table.",
                )
            )

    rels = []
    for rel in model.relationships:
        from_ = tmdl.parse_qualified(str(rel.props.get("fromColumn", "")))
        to = tmdl.parse_qualified(str(rel.props.get("toColumn", "")))
        rels.append((from_, to))
        if rel.props.get("crossFilteringBehavior") == "bothDirections" and required.get(
            "single_direction_only"
        ):
            issues.append(
                Issue(
                    "C08",
                    "high",
                    f"relationship {from_[0]} to {to[0]}",
                    "Relationship filters in both directions.",
                    "Remove crossFilteringBehavior: bothDirections.",
                )
            )
    for spec in required["relationships"]:
        want = (tuple(spec["from"]), tuple(spec["to"]))
        if want not in rels:
            issues.append(
                Issue(
                    "C07",
                    "high",
                    f"relationship {want[0][0]} to {want[1][0]}",
                    f"Missing relationship {want[0][0]}[{want[0][1]}] to {want[1][0]}[{want[1][1]}].",
                    "Add the many-to-one relationship.",
                )
            )

    date = required["date_table"]
    date_table = model.tables.get(date["table"])
    if (
        date_table is None
        or date_table.props.get("dataCategory") != date["data_category"]
        or not any(
            c.name == date["key_column"] and c.props.get("isKey") is True for c in date_table.child("column")
        )
    ):
        issues.append(
            Issue(
                "C09",
                "high",
                f"table {date['table']}",
                "Date table isn't marked as a date table.",
                f"Set dataCategory: Time and isKey on {date['key_column']}.",
            )
        )
    if date_table is not None:
        columns = model.columns(date["table"])
        for column, target in date["sort_by"].items():
            node = columns.get(column)
            if node is not None and tmdl.read_name(str(node.props.get("sortByColumn", "")))[0] != target:
                issues.append(
                    Issue(
                        "C11",
                        "medium",
                        f"column {date['table']}[{column}]",
                        "Column has no sort-by column.",
                        f"Set sortByColumn: '{target}'.",
                    )
                )
    if (
        model.model_annotations.get("__PBI_TimeIntelligenceEnabled", "1").strip() != "0"
        and not date["auto_date_time"]
    ):
        issues.append(
            Issue(
                "C10",
                "medium",
                "model",
                "Auto date/time is on; it adds hidden date tables.",
                "Set annotation __PBI_TimeIntelligenceEnabled = 0 (or turn it off in Desktop).",
            )
        )

    measures = model.measures()
    for folder, names in required["measures"]["required"].items():
        for name in names:
            if name not in measures:
                issues.append(
                    Issue(
                        "C12",
                        "high",
                        f"measure {required['measures']['table']}[{name}]",
                        "Required measure is missing.",
                        f"Add it in display folder '{folder}'.",
                    )
                )
            elif measures[name][1].props.get("displayFolder") != folder:
                issues.append(
                    Issue(
                        "C13",
                        "low",
                        f"measure {measures[name][0]}[{name}]",
                        f"Measure isn't in display folder '{folder}'.",
                        f"Set displayFolder: {folder}.",
                    )
                )

    for table_name, column in required["default_labels"].items():
        node = model.columns(table_name).get(column)
        if node is not None and node.props.get("isDefaultLabel") is not True:
            issues.append(
                Issue(
                    "C14",
                    "low",
                    f"column {table_name}[{column}]",
                    "Not marked as the default label.",
                    "Set isDefaultLabel.",
                )
            )

    ai_prep = required["ai_prep"]
    if ai_prep.get("qna_enabled") and not qna_enabled(semantic_model_dir):
        issues.append(
            Issue(
                "C15",
                "low",
                "model",
                "Q&A is off, so Copilot and Q&A can't use synonyms.",
                "Set settings.qnaEnabled: true in definition.pbism.",
            )
        )
    missing = [f for f in ai_prep["files"] if not (root / ai_prep["folder"] / f).exists()]
    if missing:
        issues.append(
            Issue(
                "C15",
                "low",
                "model",
                f"No Prep data for AI drafts in {ai_prep['folder']} (missing {', '.join(missing)}).",
                "Draft them with the prep-data-for-ai skill (/write-ai-prep-drafts).",
            )
        )
    return issues


def qna_enabled(semantic_model_dir: Path) -> bool:
    import json

    pbism = semantic_model_dir / "definition.pbism"
    if not pbism.exists():
        return False
    return bool(json.loads(pbism.read_text(encoding="utf-8")).get("settings", {}).get("qnaEnabled"))


def to_markdown(issues: list[Issue]) -> str:
    order = {"high": 0, "medium": 1, "low": 2}
    lines = ["| # | Rule | Severity | Object | Finding | Fix |", "|---|---|---|---|---|---|"]
    for n, issue in enumerate(sorted(issues, key=lambda i: (order[i.severity], i.rule, i.obj)), 1):
        lines.append(
            f"| {n} | {issue.rule} {RULE_TITLES[issue.rule]} | {issue.severity} | `{issue.obj}` | "
            f"{issue.finding} | {issue.fix} |"
        )
    return "\n".join(lines) + "\n"
