"""Command line entry point: python -m pharmacy_demo <command>. PowerShell scripts in scripts/ wrap these."""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

from . import paths

VALIDATION_STEPS = ["data", "expected", "questions", "runs", "tmdl", "bindings", "customizations", "hygiene"]


def _print_json(value) -> None:
    print(json.dumps(value, indent=2))


def _root(args) -> Path:
    return Path(args.root).resolve() if getattr(args, "root", None) else paths.repo_root()


def cmd_data(args) -> int:
    from . import datagen

    root = _root(args)
    if args.action == "generate":
        for path in datagen.write(paths.data_dir(root)):
            print(f"wrote {paths.relative(path, root)}")
        return 0
    if args.action == "fingerprint":
        print(datagen.fingerprint(paths.data_dir(root)))
        return 0
    problems = datagen.check(paths.data_dir(root))
    for problem in problems:
        print(f"FAIL data: {problem}")
    if not problems:
        print("PASS data matches seed")
    return 1 if problems else 0


def cmd_expected(args) -> int:
    from . import oracle

    root = _root(args)
    if args.action == "generate":
        for path in oracle.write_expected(root):
            print(f"wrote {paths.relative(path, root)}")
        return 0
    problems = oracle.check_expected(root)
    for problem in problems:
        print(f"FAIL expected: {problem}")
    if not problems:
        print("PASS expected answers are current")
    return 1 if problems else 0


def cmd_samples(args) -> int:
    from . import samples

    root = _root(args)
    for path in samples.write(root):
        print(f"wrote {paths.relative(path, root)}")
    return 0


def _validate_questions(root: Path) -> list[str]:
    import jsonschema
    import yaml

    schema = json.loads((root / "evaluation" / "questions.schema.json").read_text(encoding="utf-8"))
    with (root / "evaluation" / "questions.yaml").open(encoding="utf-8") as fh:
        document = yaml.safe_load(fh)
    validator = jsonschema.Draft202012Validator(schema)
    problems = [
        f"questions.yaml {'/'.join(map(str, e.absolute_path))}: {e.message}"
        for e in validator.iter_errors(document)
    ]
    ids = [q["id"] for q in document.get("questions", [])]
    if len(ids) != len(set(ids)):
        problems.append("questions.yaml has duplicate ids")
    return problems


def _validate_runs(root: Path) -> list[str]:
    from . import evaluation

    problems = []
    for path in sorted((root / "evaluation" / "runs").glob("*.json")):
        run = evaluation.load_run(path)
        for problem in evaluation.validate_run(run, root / "evaluation"):
            problems.append(f"{paths.relative(path, root)}: {problem}")
    return problems


def run_validation(root: Path, only: list[str] | None = None) -> list[dict]:
    from . import datagen, oracle, pbir, repo_checks, tmdl

    steps = only or VALIDATION_STEPS
    results = []

    def record(step: str, problems: list[str], warnings: list[str] | None = None) -> None:
        results.append(
            {
                "step": step,
                "status": "FAIL" if problems else "PASS",
                "problems": problems,
                "warnings": warnings or [],
            }
        )

    sm, report = paths.semantic_model_dir(root), paths.report_dir(root)
    if "data" in steps:
        record("data", datagen.check(paths.data_dir(root)))
    if "expected" in steps:
        record("expected", oracle.check_expected(root))
    if "questions" in steps:
        record("questions", _validate_questions(root))
    if "runs" in steps:
        record("runs", _validate_runs(root))
    if "tmdl" in steps:
        findings = tmdl.lint(sm)
        record(
            "tmdl",
            [f"{f.rule} {f.file}:{f.line} {f.message}" for f in findings if f.severity == "error"],
            [f"{f.rule} {f.file}:{f.line} {f.message}" for f in findings if f.severity != "error"],
        )
    if "bindings" in steps:
        record("bindings", [f"{p.file}: {p.message}" for p in pbir.check(report, sm)])
    if "customizations" in steps:
        from . import customizations

        record("customizations", customizations.check_all(root))
    if "hygiene" in steps:
        record("hygiene", [f"{p.check} {p.file}:{p.line} {p.message}" for p in repo_checks.run_all(root)])
    return results


def cmd_validate(args) -> int:
    root = _root(args)
    results = run_validation(root, args.only)
    if args.json:
        _print_json(results)
    else:
        for result in results:
            print(f"{result['status']:4}  {result['step']}")
            for problem in result["problems"][:50]:
                print(f"      {problem}")
            for warning in result["warnings"][:20]:
                print(f"      warning: {warning}")
    return 1 if any(r["status"] == "FAIL" for r in results) else 0


def cmd_lint(args) -> int:
    from . import tmdl

    root = _root(args)
    target = Path(args.path).resolve() if args.path else paths.semantic_model_dir(root)
    findings = tmdl.lint(target)
    if args.json:
        _print_json([f.as_dict() for f in findings])
    else:
        for f in findings:
            print(f"{f.severity:7} {f.rule} {f.file}:{f.line} {f.message}")
        if not findings:
            print("PASS no TMDL findings")
    return 1 if tmdl.errors(findings) else 0


def cmd_bindings(args) -> int:
    from . import pbir

    root = _root(args)
    problems = pbir.check(paths.report_dir(root), paths.semantic_model_dir(root))
    if args.json:
        _print_json([p.as_dict() for p in problems])
    else:
        for p in problems:
            print(f"FAIL {p.file}: {p.message}")
        if not problems:
            print("PASS every report field exists in the model")
    return 1 if problems else 0


def cmd_conventions(args) -> int:
    from . import conventions

    root = _root(args)
    issues = conventions.assess(paths.semantic_model_dir(root), root)
    if args.rule:
        issues = [i for i in issues if i.rule in set(args.rule)]
    if args.json:
        _print_json([i.as_dict() for i in issues])
    elif args.markdown:
        print(conventions.to_markdown(issues), end="")
    else:
        for i in issues:
            print(f"{i.rule} {i.severity:6} {i.obj}: {i.finding} Fix: {i.fix}")
        print(f"{len(issues)} finding(s)")
    return 1 if (issues and args.strict) else 0


def cmd_hygiene(args) -> int:
    from . import repo_checks

    root = _root(args)
    problems = repo_checks.run_all(root)
    if args.json:
        _print_json([p.as_dict() for p in problems])
    else:
        for p in problems:
            print(f"FAIL {p.check} {p.file}:{p.line} {p.message}")
        if not problems:
            print("PASS no hygiene problems")
    return 1 if problems else 0


def cmd_grade(args) -> int:
    from . import evaluation

    root = _root(args)
    path = evaluation.resolve_run(root, args.run)
    run = evaluation.grade_file(root, path, write=not args.no_write)
    grade = run["grade"]
    if args.json:
        _print_json(grade)
    else:
        for qid, result in grade["by_question"].items():
            print(f"{qid}  {result['score']} / 2  {result.get('reason', '')}")
        print(f"Total {grade['total']} / {grade['max']}")
    return 0


def cmd_compare(args) -> int:
    from . import evaluation

    root = _root(args)
    before = evaluation.load_run(evaluation.resolve_run(root, args.before))
    after = evaluation.load_run(evaluation.resolve_run(root, args.after))
    text = evaluation.compare(root, before, after)
    if args.out:
        out = Path(args.out)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(text, encoding="utf-8", newline="\n")
    print(text, end="")
    return 0


def cmd_labcheck(args) -> int:
    from . import labcheck

    root = _root(args)
    results = labcheck.run(args.lab, root, args.only)
    if args.json:
        _print_json([r.as_dict() for r in results])
    else:
        width = max((len(r.id) for r in results), default=10)
        for r in results:
            print(f"{r.status:4}  {r.id:<{width}}  {r.description}")
            if r.detail:
                print(f"      {r.detail}")
            if r.status in {"FAIL", "WARN"}:
                print(f"      Hint: {r.hint}")
                print(f"      Help: {r.link}")
        passed = sum(r.status == "PASS" for r in results)
        print(f"\nLab {int(args.lab):02d}: {passed} of {len(results)} checks passed.")
    return labcheck.exit_code(results)


def cmd_modelgen(args) -> int:
    if os.environ.get("CPDEMO_MAINTAINER") != "1":
        print(
            "modelgen is a maintainer tool that writes lab answers. Set CPDEMO_MAINTAINER=1 to use it.",
            file=sys.stderr,
        )
        return 2
    from . import modelgen

    root = _root(args)
    for path in modelgen.write_stage(root, args.stage):
        print(f"wrote {paths.relative(path, root)}")
    return 0


def cmd_questions(args) -> int:
    """Print the question set without reference answers (what agents are allowed to see)."""
    from . import oracle

    root = _root(args)
    document = oracle.load_questions(root / "evaluation")
    # Only what a business user would say, plus the output shape the grader needs. Interpretation,
    # grading, and reference answers stay hidden so the model metadata has to do the work.
    visible = ("id", "question", "paraphrases", "answer_columns")
    public = {"questions": [{k: q[k] for k in visible if k in q} for q in document["questions"]]}
    if args.json:
        _print_json(public)
    else:
        import yaml

        print(yaml.safe_dump(public, sort_keys=False, allow_unicode=True), end="")
    return 0


def cmd_dax_queries(args) -> int:
    """Emit reference DAX for scripts/Invoke-DaxQuestionTests.ps1. Agents are denied this by the hook."""
    from . import oracle

    document = oracle.load_questions(_root(args) / "evaluation")
    _print_json(
        [{"id": q["id"], "dax": q["reference_dax"]} for q in document["questions"] if q.get("reference_dax")]
    )
    return 0


def cmd_daxcheck(args) -> int:
    """Grade raw DAX results ({questions: [{question_id, columns, rows: [[...]]}]}) against expected answers."""
    from . import evaluation, oracle

    root = _root(args)
    raw = json.loads(Path(args.input).read_text(encoding="utf-8-sig"))
    questions = {q["id"]: q for q in oracle.load_questions(root / "evaluation")["questions"]}
    expected = oracle.load_expected(root)
    results = []
    for item in raw.get("questions", []):
        qid = item["question_id"]
        question = questions[qid]
        if item.get("error"):
            results.append({"question_id": qid, "status": "FAIL", "detail": item["error"]})
            continue
        names = question["answer_columns"]
        if len(item.get("columns", [])) != len(names):
            detail = f"Query returned {len(item.get('columns', []))} columns; expected {len(names)} ({', '.join(names)})."
            results.append({"question_id": qid, "status": "FAIL", "detail": detail})
            continue
        answer = {
            "question_id": qid,
            "rows": [dict(zip(names, row, strict=True)) for row in item.get("rows", [])],
        }
        grade = evaluation.grade_answer(question, expected[qid], answer)
        status = "PASS" if grade.score == 2 else "FAIL"
        results.append({"question_id": qid, "status": status, "detail": grade.reason})
    out = Path(args.out) if args.out else root / "out" / "dax-tests.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps({"results": results}, indent=2) + "\n", encoding="utf-8")
    for r in results:
        print(f"{r['status']:<5} {r['question_id']}  {r['detail']}")
    print(f"wrote {paths.relative(out, root) if out.is_relative_to(root) else out}")
    return 0 if results and all(r["status"] == "PASS" for r in results) else 1


def cmd_hook(args) -> int:
    from . import hooks

    # Copilot treats a crashing preToolUse hook as a deny for every tool call. A bug in this lab
    # handler shouldn't lock the learner out, so internal errors are reported and fail open.
    try:
        return hooks.main(args.event, _root(args))
    except Exception as exc:  # noqa: BLE001
        print(f"pharmacy_demo hook {args.event} failed open: {exc}", file=sys.stderr)
        return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="pharmacy_demo", description="Contoso Pharmacy lab tools.")
    parser.add_argument("--root", help="Repository root (default: auto-detect).")
    sub = parser.add_subparsers(dest="command", required=True)

    p = sub.add_parser("data", help="Generate or check the synthetic data.")
    p.add_argument("action", choices=["generate", "check", "fingerprint"])
    p.set_defaults(func=cmd_data)

    p = sub.add_parser("expected", help="Generate or check evaluation/expected/*.json.")
    p.add_argument("action", choices=["generate", "check"])
    p.set_defaults(func=cmd_expected)

    p = sub.add_parser("samples", help="Regenerate the illustrative sample runs (maintainers).")
    p.set_defaults(func=cmd_samples)

    p = sub.add_parser("validate", help="Run every tenant-free validation step.")
    p.add_argument("--only", nargs="+", choices=VALIDATION_STEPS)
    p.add_argument("--json", action="store_true")
    p.set_defaults(func=cmd_validate)

    p = sub.add_parser("lint", help="TMDL structural lint.")
    p.add_argument("--path", help="Semantic model folder (default: fabric/ContosoPharmacy.SemanticModel).")
    p.add_argument("--json", action="store_true")
    p.set_defaults(func=cmd_lint)

    p = sub.add_parser("bindings", help="Check that report fields exist in the model.")
    p.add_argument("--json", action="store_true")
    p.set_defaults(func=cmd_bindings)

    p = sub.add_parser("conventions", help="Convention and AI-readiness findings (rules/*.yaml).")
    p.add_argument("--rule", nargs="+")
    p.add_argument("--json", action="store_true")
    p.add_argument("--markdown", action="store_true")
    p.add_argument("--strict", action="store_true", help="Exit 1 when there are findings.")
    p.set_defaults(func=cmd_conventions)

    p = sub.add_parser("hygiene", help="PHI guard, identifier guard, forbidden files, prose style.")
    p.add_argument("--json", action="store_true")
    p.set_defaults(func=cmd_hygiene)

    p = sub.add_parser("grade", help="Grade a question run.")
    p.add_argument("run", help="Run label (evaluation/runs/<label>.json) or a path.")
    p.add_argument("--no-write", action="store_true")
    p.add_argument("--json", action="store_true")
    p.set_defaults(func=cmd_grade)

    p = sub.add_parser("compare", help="Compare two graded runs.")
    p.add_argument("--before", required=True)
    p.add_argument("--after", required=True)
    p.add_argument("--out")
    p.set_defaults(func=cmd_compare)

    p = sub.add_parser("labcheck", help="Verify a lab.")
    p.add_argument("--lab", required=True)
    p.add_argument("--only", nargs="+")
    p.add_argument("--json", action="store_true")
    p.set_defaults(func=cmd_labcheck)

    p = sub.add_parser("modelgen", help="Write a checkpoint model stage (maintainers).")
    p.add_argument("--stage", type=int, choices=[0, 1, 2, 3], required=True)
    p.set_defaults(func=cmd_modelgen)

    p = sub.add_parser("questions", help="Print the business questions without reference answers.")
    p.add_argument("--json", action="store_true")
    p.set_defaults(func=cmd_questions)

    p = sub.add_parser(
        "dax-queries", help="Print reference DAX as JSON (used by Invoke-DaxQuestionTests.ps1)."
    )
    p.set_defaults(func=cmd_dax_queries)

    p = sub.add_parser("daxcheck", help="Grade raw DAX results and write out/dax-tests.json.")
    p.add_argument("--input", required=True)
    p.add_argument("--out")
    p.set_defaults(func=cmd_daxcheck)

    p = sub.add_parser("hook", help="Agent hook handler; reads the hook payload on stdin.")
    p.add_argument("event", choices=["session-start", "pre-tool-use", "post-tool-use", "session-end"])
    p.set_defaults(func=cmd_hook)
    return parser


def main(argv: list[str] | None = None) -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    args = build_parser().parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
