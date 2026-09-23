"""Grade question runs against the oracle's expected answers and compare runs.

Scoring follows evaluation/rubric.md: 2 correct, 1 partially correct, 0 wrong or missing.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path

import jsonschema

from . import oracle

RATE_SUFFIXES = ("_pct", "_rate", "_index")


def normalize_name(name: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", str(name).strip().lower()).strip("_")


def normalize_key(value) -> str:
    return re.sub(r"\s+", " ", str(value).strip().lower())


def _is_rate(column: str) -> bool:
    return column.endswith(RATE_SUFFIXES) or column in ("refill_rate", "refill_rate_index")


def _to_number(value):
    if isinstance(value, bool):
        return None
    if isinstance(value, int | float):
        return float(value)
    if isinstance(value, str):
        text = value.strip().replace(",", "")
        percent = text.endswith("%")
        text = text.rstrip("%").strip()
        try:
            number = float(text)
        except ValueError:
            return None
        return number / 100.0 if percent else number
    return None


def values_match(column: str, expected, actual, tolerance: float) -> bool:
    expected_number = _to_number(expected)
    if expected_number is None or isinstance(expected, str):
        return normalize_key(expected) == normalize_key(actual)
    actual_number = _to_number(actual)
    if actual_number is None:
        return False
    slack = tolerance + 1e-9
    if abs(actual_number - expected_number) <= slack:
        return True
    if _is_rate(column) and abs(actual_number / 100.0 - expected_number) <= slack:
        return True
    return False


def _normalize_rows(rows: list[dict]) -> list[dict]:
    return [{normalize_name(k): v for k, v in row.items()} for row in rows if isinstance(row, dict)]


def _key(row: dict, key_columns: list[str]) -> tuple:
    return tuple(normalize_key(row.get(column, "")) for column in key_columns)


@dataclass
class QuestionGrade:
    question_id: str
    score: int
    reason: str
    matched_rows: int = 0
    expected_rows: int = 0
    override: dict | None = None
    details: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        result = {
            "score": self.score,
            "reason": self.reason,
            "matched_rows": self.matched_rows,
            "expected_rows": self.expected_rows,
        }
        if self.override:
            result["override"] = self.override
        if self.details:
            result["details"] = self.details[:10]
        return result


def grade_answer(question: dict, expected: dict, answer: dict | None) -> QuestionGrade:
    qid = question["id"]
    expected_rows = expected["rows"]
    if answer is None:
        return QuestionGrade(qid, 0, "no answer", 0, len(expected_rows))
    override = answer.get("grade_override")
    grading = question["grading"]
    key_columns = grading["key_columns"]
    tolerance = question.get("tolerance", {})
    value_columns = [c for c in question["answer_columns"] if c not in key_columns]
    actual_rows = _normalize_rows(answer.get("rows", []))
    details: list[str] = []

    actual_by_key: dict[tuple, dict] = {}
    for row in actual_rows:
        actual_by_key.setdefault(_key(row, key_columns), row)

    matched_keys: list[tuple] = []
    for row in expected_rows:
        key = _key(row, key_columns)
        actual = actual_by_key.get(key)
        if actual is None:
            details.append(f"missing row {key}")
            continue
        mismatched = [
            column
            for column in value_columns
            if not values_match(column, row[column], actual.get(column), tolerance.get(column, 0))
        ]
        if mismatched:
            details.append(f"row {key}: wrong {', '.join(mismatched)}")
        else:
            matched_keys.append(key)

    expected_keys = {_key(row, key_columns) for row in expected_rows}
    extra_keys = [key for key in actual_by_key if key not in expected_keys]
    if extra_keys:
        details.append(f"{len(extra_keys)} unexpected row(s), for example {extra_keys[0]}")

    full = len(matched_keys) == len(expected_rows) and not extra_keys
    if full and grading["type"] == "ranking":
        order = [_key(row, key_columns) for row in actual_rows if _key(row, key_columns) in expected_keys]
        expected_order = [_key(row, key_columns) for row in expected_rows]
        if order != expected_order:
            full = False
            details.append("rows present but not in the expected order")

    if full:
        grade = QuestionGrade(qid, 2, "matches the expected answer", len(matched_keys), len(expected_rows))
    elif _partial(question, expected_rows, actual_rows, matched_keys, extra_keys, key_columns, tolerance):
        grade = QuestionGrade(
            qid, 1, f"partial ({grading['partial']['type']})", len(matched_keys), len(expected_rows)
        )
    else:
        grade = QuestionGrade(qid, 0, "does not match", len(matched_keys), len(expected_rows))
    grade.details = details

    if override:
        grade.override = {"from": grade.score, "to": override["score"], "reason": override["reason"]}
        grade.score = override["score"]
        grade.reason = f"override: {override['reason']}"
    return grade


def _partial(question, expected_rows, actual_rows, matched_keys, extra_keys, key_columns, tolerance) -> bool:
    rule = question["grading"]["partial"]
    kind = rule["type"]
    if not actual_rows:
        return False
    if kind == "row_fraction":
        return len(matched_keys) >= rule.get("min", 0.5) * len(expected_rows)
    if kind == "top_key":
        return bool(expected_rows) and _key(actual_rows[0], key_columns) == _key(
            expected_rows[0], key_columns
        )
    if kind == "any_key":
        expected_keys = {_key(row, key_columns) for row in expected_rows}
        present = [row for row in actual_rows if _key(row, key_columns) in expected_keys]
        return bool(present) and len(extra_keys) <= 1
    if kind == "column_match":
        column = rule["column"]
        return any(
            values_match(column, expected_rows[0][column], row.get(column), tolerance.get(column, 0))
            for row in actual_rows
        )
    return False


def load_run(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def validate_run(run: dict, evaluation_dir: Path) -> list[str]:
    schema = json.loads((evaluation_dir / "run.schema.json").read_text(encoding="utf-8"))
    validator = jsonschema.Draft202012Validator(schema)
    return [
        f"{'/'.join(str(p) for p in error.absolute_path) or '(root)'}: {error.message}"
        for error in validator.iter_errors(run)
    ]


def grade_run(root: Path, run: dict) -> dict:
    questions = oracle.load_questions(root / "evaluation")["questions"]
    expected = oracle.load_expected(root)
    answers = {a["question_id"]: a for a in run.get("answers", [])}
    by_question = {}
    total = 0
    for question in questions:
        grade = grade_answer(question, expected[question["id"]], answers.get(question["id"]))
        by_question[question["id"]] = grade.to_dict()
        total += grade.score
    return {
        "total": total,
        "max": 2 * len(questions),
        "graded": datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "by_question": by_question,
    }


def grade_file(root: Path, path: Path, write: bool = True) -> dict:
    run = load_run(path)
    problems = validate_run(run, root / "evaluation")
    if problems:
        raise ValueError("run file does not match evaluation/run.schema.json:\n  " + "\n  ".join(problems))
    run["grade"] = grade_run(root, run)
    if write:
        path.write_text(json.dumps(run, indent=2) + "\n", encoding="utf-8")
    return run


def resolve_run(root: Path, label_or_path: str) -> Path:
    candidate = Path(label_or_path)
    if candidate.suffix == ".json" and candidate.exists():
        return candidate
    by_label = root / "evaluation" / "runs" / f"{label_or_path}.json"
    if by_label.exists():
        return by_label
    raise FileNotFoundError(f"no run file for '{label_or_path}' (looked for {by_label.as_posix()})")


def compare(root: Path, before: dict, after: dict) -> str:
    questions = oracle.load_questions(root / "evaluation")["questions"]
    before_grade = before.get("grade") or grade_run(root, before)
    after_grade = after.get("grade") or grade_run(root, after)
    lines = [
        f"# Question results: {before['label']} vs {after['label']}",
        "",
        f"| Question | {before['label']} | {after['label']} | Change |",
        "|---|---|---|---|",
    ]
    for question in questions:
        qid = question["id"]
        b = before_grade["by_question"].get(qid, {"score": 0})
        a = after_grade["by_question"].get(qid, {"score": 0})
        delta = a["score"] - b["score"]
        marker = f"+{delta}" if delta > 0 else str(delta)
        lines.append(f"| {qid}: {question['question']} | {b['score']} / 2 | {a['score']} / 2 | {marker} |")
    lines.append(
        f"| **Total** | **{before_grade['total']} / {before_grade['max']}** | "
        f"**{after_grade['total']} / {after_grade['max']}** | "
        f"**{after_grade['total'] - before_grade['total']:+d}** |"
    )
    notes = [r for r in (before, after) if r.get("illustrative")]
    if notes:
        lines += ["", "Runs marked illustrative are committed samples, not live agent output."]
    return "\n".join(lines) + "\n"
