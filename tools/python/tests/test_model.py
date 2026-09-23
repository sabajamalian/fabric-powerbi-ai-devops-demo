import shutil

import pytest

from pharmacy_demo import conventions, paths, pbir, tmdl
from pharmacy_demo.modelgen import render


def _errors(sm_dir):
    return [f for f in tmdl.lint(sm_dir) if f.severity == "error"]


@pytest.mark.parametrize("stage", [0, 1, 2, 3])
def test_every_stage_lints_and_binds(stage_root, stage):
    root = stage_root(stage)
    assert _errors(paths.semantic_model_dir(root)) == []
    assert pbir.check(paths.report_dir(root), paths.semantic_model_dir(root)) == []


def test_repo_baseline_matches_stage_zero(repo):
    files = render(0)
    for relpath, text in files.items():
        on_disk = (repo / relpath).read_text(encoding="utf-8")
        assert on_disk == text, relpath


def test_conventions_improve_with_each_stage(stage_root):
    counts = [
        len(conventions.assess(paths.semantic_model_dir(stage_root(s)), stage_root(s))) for s in range(4)
    ]
    assert counts[0] > counts[1] > counts[2] > counts[3] == 0


def test_baseline_finds_the_planted_problems(repo):
    rules = {i.rule for i in conventions.assess(paths.semantic_model_dir(repo), repo)}
    assert {"C01", "C02", "C04", "C07", "C08", "C09", "C12"} <= rules


def test_to_markdown_has_table_columns(repo):
    text = conventions.to_markdown(conventions.assess(paths.semantic_model_dir(repo), repo))
    assert "| Rule | Severity | Object | Finding | Fix |" in text


def _copy_model(stage_root, tmp_path, stage=3):
    target = tmp_path / "sm"
    shutil.copytree(paths.semantic_model_dir(stage_root(stage)), target)
    return target


def _table_file(sm, name):
    return sm / "definition" / "tables" / f"{name}.tmdl"


def test_lint_catches_spaces_for_indent(stage_root, tmp_path):
    sm = _copy_model(stage_root, tmp_path)
    path = _table_file(sm, "Store")
    path.write_text(path.read_text(encoding="utf-8").replace("\t", "    ", 3), encoding="utf-8")
    assert _errors(sm)


def test_lint_catches_broken_dax_reference(stage_root, tmp_path):
    sm = _copy_model(stage_root, tmp_path)
    path = _table_file(sm, "Prescription Fill")
    text = path.read_text(encoding="utf-8")
    assert "'Prescription Fill'[Fill Type Code]" in text
    path.write_text(
        text.replace("'Prescription Fill'[Fill Type Code]", "'Prescription Fill'[Fill Kind]", 1),
        encoding="utf-8",
    )
    assert _errors(sm)


def test_lint_catches_missing_table_ref(stage_root, tmp_path):
    sm = _copy_model(stage_root, tmp_path)
    _table_file(sm, "Medication").unlink()
    assert any(f.rule for f in _errors(sm))


def test_lint_catches_relationship_to_missing_column(stage_root, tmp_path):
    sm = _copy_model(stage_root, tmp_path)
    path = sm / "definition" / "relationships.tmdl"
    text = path.read_text(encoding="utf-8")
    path.write_text(text.replace("'Store Key'", "'Store Id'", 1), encoding="utf-8")
    assert _errors(sm)


def test_bindings_catch_renamed_column(stage_root):
    # A stage 3 report against the stage 0 model has fields that no longer exist.
    problems = pbir.check(paths.report_dir(stage_root(3)), paths.semantic_model_dir(stage_root(0)))
    assert problems


def test_c15_flags_missing_ai_prep_and_qna(repo, stage_root):
    baseline = [i for i in conventions.assess(paths.semantic_model_dir(repo), repo) if i.rule == "C15"]
    assert len(baseline) == 2
    ready = stage_root(3)
    assert not [i for i in conventions.assess(paths.semantic_model_dir(ready), ready) if i.rule == "C15"]
