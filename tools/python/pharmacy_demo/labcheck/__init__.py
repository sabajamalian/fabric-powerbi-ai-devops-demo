"""Lab progress checks. Contract: lab/checks.yaml. Entry point: python -m pharmacy_demo.labcheck --lab 07."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

import yaml

from .. import paths

PASS, FAIL, SKIP, WARN = "PASS", "FAIL", "SKIP", "WARN"
DEFAULT_SITE_URL = "https://sabajamalian.github.io/fabric-powerbi-ai-devops-demo/"


@dataclass
class Result:
    id: str
    lab: str
    description: str
    status: str
    detail: str
    hint: str
    link: str
    required: bool

    def as_dict(self) -> dict:
        return dict(self.__dict__)


def load_contract(root: Path) -> dict:
    with (root / "lab" / "checks.yaml").open(encoding="utf-8") as fh:
        return yaml.safe_load(fh)


def site_url(contract: dict) -> str:
    url = os.environ.get("CPDEMO_SITE_URL") or contract.get("site_url") or DEFAULT_SITE_URL
    return url if url.endswith("/") else url + "/"


def run(lab: str, root: Path | None = None, only: list[str] | None = None) -> list[Result]:
    from . import checks as implementations

    root = root or paths.repo_root()
    contract = load_contract(root)
    lab = f"{int(lab):02d}"
    base = site_url(contract)
    slug = contract["labs"][lab]["slug"]
    results = []
    for check in contract["checks"]:
        if check["lab"] != lab or (only and check["id"] not in only):
            continue
        required = check.get("required", True)
        link = f"{base}{slug}/#{check.get('anchor', 'verify-your-work')}"
        func = implementations.REGISTRY.get(check["id"])
        if func is None:
            status, detail = FAIL, "No implementation for this check id."
        elif check.get("windows_only") and os.name != "nt":
            status, detail = SKIP, "Windows only. Skipped on this OS."
        else:
            try:
                status, detail = func(root, contract)
            except Exception as exc:  # noqa: BLE001 - a broken check must report, not crash the table
                status, detail = FAIL, f"Check raised {type(exc).__name__}: {exc}"
        if status == FAIL and not required:
            status = WARN
        results.append(
            Result(check["id"], lab, check["description"], status, detail, check["hint"], link, required)
        )
    return results


def exit_code(results: list[Result]) -> int:
    return 1 if any(r.status == FAIL and r.required for r in results) else 0
