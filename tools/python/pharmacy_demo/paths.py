"""Repository path helpers. Every path is built with pathlib so Windows, macOS, and Linux behave the same."""

from __future__ import annotations

import os
from pathlib import Path


def repo_root(start: Path | None = None) -> Path:
    """Find the repository root.

    Order: the CPDEMO_REPO_ROOT environment variable, then the nearest parent of ``start``
    (or the current directory) that contains ``evaluation/questions.yaml``, then the
    location of this package inside the repo.
    """
    override = os.environ.get("CPDEMO_REPO_ROOT")
    if override:
        return Path(override).resolve()
    candidate = (start or Path.cwd()).resolve()
    for folder in (candidate, *candidate.parents):
        if (folder / "evaluation" / "questions.yaml").is_file() and (folder / "tools" / "python").is_dir():
            return folder
    return Path(__file__).resolve().parents[3]


def data_dir(root: Path) -> Path:
    return root / "data"


def generated_dir(root: Path) -> Path:
    return root / "data" / "generated"


def evaluation_dir(root: Path) -> Path:
    return root / "evaluation"


def semantic_model_dir(root: Path) -> Path:
    return root / "fabric" / "ContosoPharmacy.SemanticModel"


def report_dir(root: Path) -> Path:
    return root / "fabric" / "ContosoPharmacy.Report"


def relative(path: Path, root: Path) -> str:
    """Repo-relative path with forward slashes, for stable messages on every OS."""
    try:
        return path.resolve().relative_to(root.resolve()).as_posix()
    except ValueError:
        return path.as_posix()
