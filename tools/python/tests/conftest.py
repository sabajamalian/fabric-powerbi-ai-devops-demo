from __future__ import annotations

import shutil
from pathlib import Path

import pytest

from pharmacy_demo import paths
from pharmacy_demo.modelgen import write_stage

REPO = paths.repo_root(Path(__file__).parent)


@pytest.fixture(scope="session")
def repo() -> Path:
    return REPO


@pytest.fixture(scope="session")
def stage_root(tmp_path_factory):
    """Return a function that builds a throwaway repo root holding one model stage."""
    cache: dict[int, Path] = {}

    def build(stage: int) -> Path:
        if stage not in cache:
            root = tmp_path_factory.mktemp(f"stage{stage}")
            for folder in ("rules", "lab", "evaluation", "data"):
                shutil.copytree(REPO / folder, root / folder)
            write_stage(root, stage)
            cache[stage] = root
        return cache[stage]

    return build
