from pharmacy_demo import datagen, oracle, paths


def test_generated_data_matches_seed(repo):
    assert datagen.check(paths.data_dir(repo)) == []


def test_generation_is_deterministic():
    first = datagen.generate(paths.data_dir(paths.repo_root()))
    second = datagen.generate(paths.data_dir(paths.repo_root()))
    assert first == second


def test_no_person_columns():
    for table, columns in datagen.SCHEMA.items():
        for column in columns:
            assert not any(word in column.name for word in ("patient", "name_first", "dob", "ssn", "mrn")), (
                table
            )


def test_expected_answers_are_current(repo):
    assert oracle.check_expected(repo) == []


def test_engineered_signals(repo):
    expected = oracle.load_expected(repo)
    q02 = expected["Q02"]["rows"]
    assert q02[0]["category"] == "Respiratory" and q02[0]["change"] > 0
    assert any(r["category"] == "Dermatology" and r["change"] < 0 for r in q02[:3])
    assert expected["Q03"]["rows"][0]["store"] == "Sunset Mesa"
    assert {r["store"] for r in expected["Q04"]["rows"]} == {"Riverbend", "Granite Park"}
    q05 = expected["Q05"]["rows"][0]
    assert (q05["period"], q05["prescriptions_filled"], q05["previous_period_fills"]) == (
        "2025-12",
        2052,
        1761,
    )
