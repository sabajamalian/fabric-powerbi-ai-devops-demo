"""Build the committed, illustrative sample runs (evaluation/runs/sample-*.json). Maintainers only.

The baseline sample shows the mistakes an agent typically makes against the baseline model; the
AI-ready sample shows correct answers. Both are labeled illustrative and graded by the real grader.
"""

from __future__ import annotations

import json
from pathlib import Path

from . import evaluation, oracle, paths


def _rows(connection, sql: str) -> list[dict]:
    cursor = connection.execute(sql)
    names = [d[0] for d in cursor.description]
    out = []
    for record in cursor.fetchall():
        row = {}
        for name, value in zip(names, record, strict=True):
            row[name] = round(value, 6) if isinstance(value, float) else value
        out.append(row)
    return out


def baseline_answers(root: Path) -> list[dict]:
    connection = oracle.connect(paths.generated_dir(root))
    expected = oracle.load_expected(root)
    chain = _rows(
        connection,
        """
        SELECT count(*) FILTER (WHERE strftime(fill_dt, '%Y-%m') = '2025-11') AS prior,
               count(*) FILTER (WHERE strftime(fill_dt, '%Y-%m') = '2025-12') AS latest
        FROM fact_rx_fill""",
    )[0]
    categories = [r["c"] for r in _rows(connection, "SELECT DISTINCT ther_cat AS c FROM dim_med ORDER BY 1")]
    return [
        {
            "question_id": "Q01",
            "answer_text": "Monthly fills by region, 96 rows (4 regions x 24 months).",
            "dax": 'EVALUATE SUMMARIZECOLUMNS(dim_store[rgn], dim_date[yr_mth], "prescriptions_filled", '
            "COUNTROWS(fact_rx_fill))",
            "assumptions": ["rgn is the region column.", "yr_mth is year and month."],
            "rows": [
                {
                    "region": r["region"],
                    "year_month": r["year_month"],
                    "prescriptions_filled": r["prescriptions_filled"],
                }
                for r in expected["Q01"]["rows"]
            ],
        },
        {
            "question_id": "Q02",
            "answer_text": "Every category changed by the same amount, +291, from November to December 2025.",
            "dax": 'EVALUATE SUMMARIZECOLUMNS(dim_med[ther_cat], "prior_month_fills", '
            'CALCULATE(COUNTROWS(fact_rx_fill), dim_date[yr_mth] = "2025-11"), "latest_month_fills", '
            'CALCULATE(COUNTROWS(fact_rx_fill), dim_date[yr_mth] = "2025-12"))',
            "assumptions": [
                "ther_cat is the medication category.",
                "Latest month is 2025-12. The identical values per category weren't investigated.",
            ],
            "rows": [
                {
                    "category": c,
                    "prior_month_fills": chain["prior"],
                    "latest_month_fills": chain["latest"],
                    "change": chain["latest"] - chain["prior"],
                    "change_pct": round((chain["latest"] - chain["prior"]) / chain["prior"], 6),
                }
                for c in categories
            ],
        },
        {
            "question_id": "Q03",
            "answer_text": "Processing time by store, using the default summarization of proc_mins.",
            "dax": 'EVALUATE SUMMARIZECOLUMNS(dim_store[store_nm], "avg_processing_minutes", SUM(fact_rx_fill[proc_mins]))',
            "assumptions": ["proc_mins summarizes by sum in the model, so the default aggregation was used."],
            "rows": _rows(
                connection,
                """
                SELECT s.store_nm AS store, sum(f.proc_mins) AS avg_processing_minutes
                FROM fact_rx_fill f JOIN dim_store s USING (store_key)
                GROUP BY 1 ORDER BY 2 DESC, 1""",
            ),
        },
        {
            "question_id": "Q04",
            "answer_text": "The three stores with the most refills.",
            "dax": 'EVALUATE TOPN(3, SUMMARIZECOLUMNS(dim_store[store_nm], "refills", '
            'CALCULATE(COUNTROWS(fact_rx_fill), fact_rx_fill[fill_typ] = "R")), [refills], DESC)',
            "assumptions": [
                "fill_typ R means refill.",
                "High activity means the highest refill count, all dates.",
            ],
            "rows": _rows(
                connection,
                """
                WITH by_store AS (
                    SELECT s.store_nm AS store,
                           count(*) FILTER (WHERE fill_typ = 'R') AS refills,
                           avg(CASE WHEN fill_typ = 'R' THEN 1.0 ELSE 0.0 END) AS refill_rate
                    FROM fact_rx_fill f JOIN dim_store s USING (store_key) GROUP BY 1)
                SELECT store, refill_rate, NULL AS refill_rate_index
                FROM by_store ORDER BY refills DESC, store LIMIT 3""",
            ),
        },
        {
            "question_id": "Q05",
            "answer_text": "2025 volume compared with 2024.",
            "dax": 'EVALUATE SUMMARIZECOLUMNS(dim_date[yr], "prescriptions_filled", COUNTROWS(fact_rx_fill))',
            "assumptions": ["Previous period means the previous year."],
            "rows": _rows(
                connection,
                """
                WITH y AS (SELECT count(*) FILTER (WHERE year(fill_dt) = 2025) AS latest,
                                  count(*) FILTER (WHERE year(fill_dt) = 2024) AS prior FROM fact_rx_fill)
                SELECT '2025' AS period, latest AS prescriptions_filled, prior AS previous_period_fills,
                       latest - prior AS change, (latest - prior) / prior AS change_pct FROM y""",
            ),
        },
    ]


def ai_ready_answers(root: Path) -> list[dict]:
    questions = {q["id"]: q for q in oracle.load_questions(root / "evaluation")["questions"]}
    expected = oracle.load_expected(root)
    texts = {
        "Q01": "Prescriptions Filled by Region and Year Month for January 2024 to December 2025.",
        "Q02": "December 2025 vs November 2025: Respiratory rose most; Dermatology fell most.",
        "Q03": "Avg Processing Time (min) by store for all dates. Sunset Mesa is the slowest.",
        "Q04": "Stores with Refill Rate Index vs Chain of 1.25 or more in 2025-Q4: Riverbend and Granite Park.",
        "Q05": "December 2025 compared with November 2025 (previous month).",
    }
    answers = []
    for qid, question in questions.items():
        answers.append(
            {
                "question_id": qid,
                "answer_text": texts[qid],
                "dax": question.get("reference_dax", "").strip(),
                "assumptions": [question["default_interpretation"]],
                "rows": expected[qid]["rows"],
            }
        )
    return answers


def build(root: Path) -> dict[str, dict]:
    runs = {
        "sample-baseline": {
            "label": "sample-baseline",
            "model_state": "baseline",
            "illustrative": True,
            "created": "2026-01-15T00:00:00Z",
            "agent": "question-tester",
            "surface": "generated",
            "notes": "Illustrative: typical mistakes against the baseline model (missing relationship, summed "
            "minutes, wrong period, count instead of rate). Not live agent output.",
            "answers": baseline_answers(root),
        },
        "sample-ai-ready": {
            "label": "sample-ai-ready",
            "model_state": "ai-ready",
            "illustrative": True,
            "created": "2026-01-15T00:00:00Z",
            "agent": "question-tester",
            "surface": "generated",
            "notes": "Illustrative: answers from the AI-ready model using its measures. Not live agent output.",
            "answers": ai_ready_answers(root),
        },
    }
    for run in runs.values():
        grade = evaluation.grade_run(root, run)
        grade["graded"] = "2026-01-15T00:00:00Z"
        run["grade"] = grade
    return runs


def write(root: Path) -> list[Path]:
    written = []
    for label, run in build(root).items():
        path = root / "evaluation" / "runs" / f"{label}.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(run, indent=2) + "\n", encoding="utf-8", newline="\n")
        written.append(path)
    return written
