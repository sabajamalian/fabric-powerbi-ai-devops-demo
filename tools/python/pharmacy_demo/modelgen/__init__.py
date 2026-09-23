"""Model generator for lab checkpoints. Maintainers only; agents are blocked from reading it by hooks."""

from __future__ import annotations

import shutil
from pathlib import Path

from .render import PROJECT, render, stage_name
from .spec import REQUIRED_MEASURES, STAGE_NAMES

__all__ = ["REQUIRED_MEASURES", "STAGE_NAMES", "managed_paths", "render", "stage_name", "write_stage"]


def managed_paths(root: Path) -> list[Path]:
    fabric = root / "fabric"
    return [
        fabric / f"{PROJECT}.pbip",
        fabric / f"{PROJECT}.SemanticModel",
        fabric / f"{PROJECT}.Report",
        fabric / "ai-prep",
    ]


def write_stage(root: Path, stage: int) -> list[Path]:
    """Replace the generated PBIP files under root/fabric with the given stage. Returns written files."""
    for path in managed_paths(root):
        if path.is_dir():
            shutil.rmtree(path)
        elif path.exists():
            path.unlink()
    written = []
    for relative, text in sorted(render(stage).items()):
        target = root.joinpath(*relative.split("/"))
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(text.encode("utf-8"))
        written.append(target)
    return written
