import copy
import json

from pharmacy_demo import evaluation, oracle


def _run(repo, label):
    return json.loads((repo / "evaluation" / "runs" / f"{label}.json").read_text(encoding="utf-8"))


def test_samples_validate_and_grade(repo):
    baseline, ai_ready = _run(repo, "sample-baseline"), _run(repo, "sample-ai-ready")
    for run in (baseline, ai_ready):
        assert evaluation.validate_run(run, repo / "evaluation") == []
    assert evaluation.grade_run(repo, baseline)["total"] == 3
    assert evaluation.grade_run(repo, ai_ready)["total"] == 10


def test_committed_grades_are_current(repo):
    for label in ("sample-baseline", "sample-ai-ready"):
        run = _run(repo, label)
        fresh = evaluation.grade_run(repo, run)
        assert run["grade"]["total"] == fresh["total"]
        assert {k: v["score"] for k, v in run["grade"]["by_question"].items()} == {
            k: v["score"] for k, v in fresh["by_question"].items()
        }


def test_rates_accept_percent_and_names_normalize(repo):
    run = copy.deepcopy(_run(repo, "sample-ai-ready"))
    for answer in run["answers"]:
        if answer["question_id"] == "Q04":
            answer["rows"] = [
                {
                    "Store": r["store"],
                    "Refill Rate": r["refill_rate"] * 100,
                    "Refill Rate Index": r["refill_rate_index"],
                }
                for r in answer["rows"]
            ]
    assert evaluation.grade_run(repo, run)["by_question"]["Q04"]["score"] == 2


def test_extra_row_loses_full_credit(repo):
    run = copy.deepcopy(_run(repo, "sample-ai-ready"))
    for answer in run["answers"]:
        if answer["question_id"] == "Q04":
            answer["rows"].append({"store": "Lakeview", "refill_rate": 0.5, "refill_rate_index": 0.9})
    assert evaluation.grade_run(repo, run)["by_question"]["Q04"]["score"] == 1


def test_ranking_order_matters(repo):
    run = copy.deepcopy(_run(repo, "sample-ai-ready"))
    for answer in run["answers"]:
        if answer["question_id"] == "Q03":
            answer["rows"] = list(reversed(answer["rows"]))
    assert evaluation.grade_run(repo, run)["by_question"]["Q03"]["score"] < 2


def test_missing_answer_scores_zero(repo):
    run = copy.deepcopy(_run(repo, "sample-ai-ready"))
    run["answers"] = [a for a in run["answers"] if a["question_id"] != "Q01"]
    assert evaluation.grade_run(repo, run)["by_question"]["Q01"]["score"] == 0


def test_override_wins(repo):
    run = copy.deepcopy(_run(repo, "sample-baseline"))
    run["answers"][1]["grade_override"] = {"score": 1, "reason": "Reviewer accepted the explanation."}
    assert evaluation.grade_run(repo, run)["by_question"]["Q02"]["score"] == 1


def test_compare_table(repo):
    text = evaluation.compare(repo, _run(repo, "sample-baseline"), _run(repo, "sample-ai-ready"))
    assert "**3 / 10**" in text and "**10 / 10**" in text and "+7" in text


def test_reference_sql_columns_match_answer_columns(repo):
    connection = oracle.connect(repo / "data" / "generated")
    for question in oracle.load_questions(repo / "evaluation")["questions"]:
        result = oracle.run_question(connection, question)
        assert result["columns"] == question["answer_columns"]
