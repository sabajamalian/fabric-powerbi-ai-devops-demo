"""DuckDB oracle: computes expected answers for evaluation/questions.yaml directly from the CSVs.

The oracle never reads the semantic model, so it is an independent check on both the
model's measures and the agent's answers.
"""

from __future__ import annotations

import json
from pathlib import Path

import duckdb
import yaml

from . import datagen

COLUMN_TYPES = {
    "dim_date": {
        "cal_dt": "DATE",
        "yr": "INTEGER",
        "qtr": "VARCHAR",
        "yr_qtr": "VARCHAR",
        "mth_num": "INTEGER",
        "mth_nm": "VARCHAR",
        "yr_mth": "VARCHAR",
        "yr_mth_num": "INTEGER",
        "dow_num": "INTEGER",
        "dow_nm": "VARCHAR",
        "is_wkend": "VARCHAR",
    },
    "dim_store": {
        "store_key": "INTEGER",
        "store_cd": "VARCHAR",
        "store_nm": "VARCHAR",
        "city": "VARCHAR",
        "rgn": "VARCHAR",
        "store_typ": "VARCHAR",
        "open_dt": "DATE",
    },
    "dim_med": {
        "med_key": "INTEGER",
        "med_cd": "VARCHAR",
        "med_nm": "VARCHAR",
        "ther_cat": "VARCHAR",
        "dose_form": "VARCHAR",
        "gnrc_flg": "VARCHAR",
    },
    "fact_rx_fill": {
        "fill_id": "INTEGER",
        "fill_dt": "DATE",
        "store_key": "INTEGER",
        "med_key": "INTEGER",
        "fill_typ": "VARCHAR",
        "refill_no": "INTEGER",
        "qty": "INTEGER",
        "days_sply": "INTEGER",
        "payer_typ": "VARCHAR",
        "proc_mins": "DOUBLE",
    },
}

DECIMALS = 6


def load_questions(evaluation_dir: Path) -> dict:
    with (evaluation_dir / "questions.yaml").open(encoding="utf-8") as handle:
        return yaml.safe_load(handle)


def connect(generated_dir: Path) -> duckdb.DuckDBPyConnection:
    connection = duckdb.connect(database=":memory:")
    for table, columns in COLUMN_TYPES.items():
        csv_path = (generated_dir / datagen.TABLE_FILES[table]).as_posix().replace("'", "''")
        column_spec = ", ".join(f"'{name}': '{kind}'" for name, kind in columns.items())
        connection.execute(
            f"CREATE VIEW {table} AS SELECT * FROM read_csv('{csv_path}', header = true, "
            f"columns = {{{column_spec}}})"
        )
    return connection


def _clean(value):
    if isinstance(value, float):
        return round(value, DECIMALS)
    if hasattr(value, "isoformat"):
        return value.isoformat()
    return value


def run_question(connection: duckdb.DuckDBPyConnection, question: dict) -> dict:
    result = connection.execute(question["reference_sql"])
    columns = [description[0] for description in result.description]
    if columns != question["answer_columns"]:
        raise ValueError(
            f"{question['id']}: reference_sql returns {columns}, expected answer_columns {question['answer_columns']}"
        )
    rows = [{c: _clean(v) for c, v in zip(columns, record, strict=True)} for record in result.fetchall()]
    return {
        "question_id": question["id"],
        "question": question["question"],
        "generated_by": "pharmacy_demo.oracle (DuckDB over data/generated/*.csv)",
        "columns": columns,
        "rows": rows,
    }


def render_expected(root: Path) -> dict[str, bytes]:
    evaluation_dir = root / "evaluation"
    generated = root / "data" / "generated"
    questions = load_questions(evaluation_dir)
    connection = connect(generated)
    fingerprint = datagen.fingerprint(root / "data")
    outputs: dict[str, bytes] = {}
    for question in questions["questions"]:
        document = run_question(connection, question)
        document["data_fingerprint"] = fingerprint
        outputs[f"{question['id']}.json"] = (json.dumps(document, indent=2) + "\n").encode("utf-8")
    return outputs


def write_expected(root: Path) -> list[Path]:
    target_dir = root / "evaluation" / "expected"
    target_dir.mkdir(parents=True, exist_ok=True)
    written = []
    for name, content in render_expected(root).items():
        target = target_dir / name
        target.write_bytes(content)
        written.append(target)
    return written


def check_expected(root: Path) -> list[str]:
    target_dir = root / "evaluation" / "expected"
    rendered = render_expected(root)
    problems = []
    for name, content in rendered.items():
        target = target_dir / name
        if not target.exists():
            problems.append(f"missing: evaluation/expected/{name}")
        elif target.read_bytes() != content:
            problems.append(f"out of date: evaluation/expected/{name}")
    for existing in sorted(target_dir.glob("*.json")):
        if existing.name not in rendered:
            problems.append(f"no matching question: evaluation/expected/{existing.name}")
    return problems


def load_expected(root: Path) -> dict[str, dict]:
    target_dir = root / "evaluation" / "expected"
    return {
        path.stem: json.loads(path.read_text(encoding="utf-8")) for path in sorted(target_dir.glob("Q*.json"))
    }
