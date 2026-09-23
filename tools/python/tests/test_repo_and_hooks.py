import json

from pharmacy_demo import hooks, labcheck, repo_checks


def test_repo_hygiene_passes(repo):
    assert repo_checks.run_all(repo) == []


def test_identifier_guard_flags_guid_and_secret(tmp_path):
    guid = "-".join(["3f2504e0", "4f89", "11d3", "9a0c", "0305e82c3301"])
    secret = "client_secret" + ' = "abcdefghijklmnopqrstuv12345"'
    (tmp_path / "notes.md").write_text(f"tenant {guid}\n{secret}\n", encoding="utf-8")
    problems = repo_checks.identifier_guard(["notes.md"], tmp_path)
    assert len(problems) >= 2


def test_prose_dashes_flagged_outside_code(tmp_path):
    (tmp_path / "a.md").write_text("Good line\nBad \u2014 line\n```\ncode \u2014 ok\n```\n", encoding="utf-8")
    problems = repo_checks.prose_style(["a.md"], tmp_path)
    assert [p.line for p in problems] == [2]


def test_forbidden_files(tmp_path):
    (tmp_path / "x").mkdir()
    for name in (".env", "x/cache.abf", ".env.example"):
        (tmp_path / name).write_text("x", encoding="utf-8")
    problems = repo_checks.forbidden_files([".env", "x/cache.abf", ".env.example"], tmp_path)
    assert {p.file for p in problems} == {".env", "x/cache.abf"}


def _decide(repo, payload, maintainer=False):
    return hooks.decide(payload, repo, maintainer)[0]


def test_hook_denies_generated_data_edit(repo):
    assert (
        _decide(repo, {"toolName": "edit", "toolArgs": {"path": str(repo / "data/generated/dim_store.csv")}})
        == "deny"
    )


def test_hook_accepts_string_args_and_windows_paths(repo):
    payload = {"toolName": "view", "toolArgs": json.dumps({"path": "evaluation\\expected\\Q01.json"})}
    assert _decide(repo, payload) == "deny"
    assert _decide(repo, payload, maintainer=True) is None


def test_hook_snake_case_payload(repo):
    payload = {
        "tool_name": "create_file",
        "tool_input": {"filePath": "fabric/ContosoPharmacy.SemanticModel/Copilot/x.md"},
    }
    assert _decide(repo, payload) == "deny"


def test_hook_shell_rules(repo):
    shell = lambda c: {"toolName": "bash", "toolArgs": {"command": c}}  # noqa: E731
    assert _decide(repo, shell("git push --force origin main")) == "deny"
    assert _decide(repo, shell("gh auth token")) == "deny"
    assert _decide(repo, shell("cat evaluation/questions.yaml")) == "deny"
    assert _decide(repo, shell("echo x > data/generated/a.csv")) == "deny"
    assert _decide(repo, shell("git reset --hard HEAD")) == "ask"
    assert _decide(repo, shell("python -m pharmacy_demo questions")) is None


def test_hook_allows_model_edits(repo):
    path = "fabric/ContosoPharmacy.SemanticModel/definition/tables/dim_store.tmdl"
    assert _decide(repo, {"toolName": "edit", "toolArgs": {"path": path}}) is None


def test_labcheck_contract_ids_are_implemented(repo):
    from pharmacy_demo.labcheck.checks import REGISTRY

    contract = labcheck.load_contract(repo)
    ids = [c["id"] for c in contract["checks"]]
    assert ids and set(ids) <= set(REGISTRY)
    assert len(ids) == len(set(ids))


def test_labcheck_stage_progression(stage_root):
    for stage, lab in ((1, "07"), (2, "08"), (3, "09")):
        results = labcheck.run(lab, stage_root(stage))
        assert labcheck.exit_code(results) == 0, [r.as_dict() for r in results if r.status == "FAIL"]
    assert labcheck.exit_code(labcheck.run("08", stage_root(1))) != 0


def test_hook_output_has_cli_and_vscode_shapes(repo, monkeypatch, capsys, tmp_path):
    import io

    (tmp_path / "out").mkdir()
    payload = {
        "hook_event_name": "PreToolUse",
        "tool_name": "create_file",
        "tool_input": {"filePath": "data/generated/x.csv"},
    }
    monkeypatch.setattr("sys.stdin", io.StringIO(json.dumps(payload)))
    assert hooks.main("pre-tool-use", tmp_path) == 0
    out = json.loads(capsys.readouterr().out)
    assert out["permissionDecision"] == "deny"
    assert out["hookSpecificOutput"]["hookEventName"] == "PreToolUse"
    assert out["hookSpecificOutput"]["permissionDecision"] == "deny"
    log = (tmp_path / "out" / "hooks" / "session.log").read_text(encoding="utf-8")
    assert '"decision": "deny"' in log


def test_hook_crash_fails_open(monkeypatch, capsys, tmp_path):
    import io

    from pharmacy_demo import cli

    def boom(*_):
        raise RuntimeError("bug")

    monkeypatch.setattr(hooks, "main", boom)
    monkeypatch.setattr("sys.stdin", io.StringIO("{}"))
    assert cli.main(["--root", str(tmp_path), "hook", "pre-tool-use"]) == 0
    assert "failed open" in capsys.readouterr().err


def _write(path, text):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def test_customizations_flag_common_mistakes(tmp_path):
    from pharmacy_demo import customizations

    gh = tmp_path / ".github"
    _write(gh / "copilot-instructions.md", "Run pwsh ./scripts/Missing.ps1\n")
    _write(gh / "instructions" / "x.instructions.md", "---\ndescription: no glob\n---\nBody\n")
    _write(
        gh / "skills" / "good-skill" / "SKILL.md",
        "---\nname: other-name\ndescription: d\n---\n[r](refs/nope.md)\n",
    )
    _write(
        gh / "agents" / "a.agent.md",
        "---\ndescription: d\ntools: [read]\nhandoffs:\n  - label: Go\n    agent: ghost\n---\nBody\n",
    )
    _write(gh / "agents" / "b.agent.md", "---\ndescription: d\n---\nBody\n")
    _write(gh / "prompts" / "p.prompt.md", "---\nagent: nobody\n---\nBody\n")
    _write(
        gh / "hooks" / "h.json",
        '{"version": 1, "hooks": {"preToolUse": [{"type": "command", "bash": "./scripts/x.sh"}]}}',
    )
    _write(tmp_path / "lab" / "checks.yaml", "shipped:\n  agents: [a, missing-agent]\n")
    text = "\n".join(customizations.check_all(tmp_path))
    for expected in (
        "references scripts/Missing.ps1",
        "applyTo",
        "must match the folder name",
        "refs/nope.md",
        "handoff target 'ghost'",
        "b.agent.md: tools must be",
        "p.prompt.md: description is required",
        "agent 'nobody'",
        "references scripts/x.sh",
        "shipped agent 'missing-agent'",
    ):
        assert expected in text, expected


def test_shipped_customizations_are_valid(repo):
    from pharmacy_demo import customizations

    problems = customizations.check_all(repo)
    assert problems == []
