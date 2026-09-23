"""PBIR report binding check: every field a visual uses must exist in the semantic model."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from . import tmdl


@dataclass
class Binding:
    file: str
    kind: str  # Column | Measure | Hierarchy
    entity: str
    prop: str
    query_ref: str | None


@dataclass
class BindingProblem:
    file: str
    message: str

    def as_dict(self) -> dict:
        return {"file": self.file, "message": self.message}


def _walk(node, file: str, out: list[Binding], query_ref: str | None = None) -> None:
    if isinstance(node, dict):
        ref = node.get("queryRef", query_ref)
        for kind in ("Column", "Measure", "Hierarchy"):
            inner = node.get(kind)
            if isinstance(inner, dict) and "Property" in inner:
                source = inner.get("Expression", {}).get("SourceRef", {})
                entity = source.get("Entity")
                if entity is not None:
                    out.append(Binding(file, kind, entity, inner["Property"], node.get("queryRef")))
        for key, value in node.items():
            _walk(value, file, out, ref if key == "field" else None)
    elif isinstance(node, list):
        for item in node:
            _walk(item, file, out, query_ref)


def collect(report_dir: Path) -> list[Binding]:
    bindings: list[Binding] = []
    definition = report_dir / "definition"
    for path in sorted(definition.rglob("*.json")):
        document = json.loads(path.read_text(encoding="utf-8-sig"))
        _walk(document, path.relative_to(report_dir).as_posix(), bindings)
    return bindings


def _query_refs(report_dir: Path) -> list[tuple[str, str, dict]]:
    """(file, queryRef, field) for every projection."""
    found = []
    for path in sorted((report_dir / "definition").rglob("visual.json")):
        document = json.loads(path.read_text(encoding="utf-8-sig"))
        state = document.get("visual", {}).get("query", {}).get("queryState", {})
        for role in state.values():
            for projection in role.get("projections", []):
                found.append(
                    (
                        path.relative_to(report_dir).as_posix(),
                        projection.get("queryRef", ""),
                        projection.get("field", {}),
                    )
                )
    return found


def _expected_query_ref(field: dict) -> str | None:
    for kind in ("Column", "Measure"):
        inner = field.get(kind)
        if inner:
            return f"{inner['Expression']['SourceRef']['Entity']}.{inner['Property']}"
    agg = field.get("Aggregation")
    if agg:
        names = {0: "Sum", 1: "Avg", 2: "Count", 3: "Min", 4: "Max", 5: "CountNonNull", 6: "Median"}
        inner = agg["Expression"].get("Column")
        if inner and agg.get("Function") in names:
            return (
                f"{names[agg['Function']]}({inner['Expression']['SourceRef']['Entity']}.{inner['Property']})"
            )
    return None


def check(report_dir: Path, semantic_model_dir: Path) -> list[BindingProblem]:
    model = tmdl.load_model(semantic_model_dir)
    measures = model.measures()
    problems: list[BindingProblem] = []
    if not (report_dir / "definition").is_dir():
        return [BindingProblem(str(report_dir), "Report has no definition folder (PBIR format expected).")]
    for binding in collect(report_dir):
        if binding.entity not in model.tables:
            problems.append(
                BindingProblem(
                    binding.file,
                    f"{binding.kind} '{binding.entity}'[{binding.prop}]: "
                    f"table '{binding.entity}' isn't in the model.",
                )
            )
            continue
        if binding.kind == "Column" and binding.prop not in model.columns(binding.entity):
            problems.append(
                BindingProblem(binding.file, f"Column '{binding.entity}'[{binding.prop}] isn't in the model.")
            )
        elif binding.kind == "Measure":
            home = measures.get(binding.prop)
            if home is None:
                problems.append(BindingProblem(binding.file, f"Measure [{binding.prop}] isn't in the model."))
            elif home[0] != binding.entity:
                problems.append(
                    BindingProblem(
                        binding.file,
                        f"Measure [{binding.prop}] lives in '{home[0]}', not '{binding.entity}'.",
                    )
                )
        elif binding.kind == "Hierarchy":
            names = {h.name for h in model.tables[binding.entity].child("hierarchy")}
            if binding.prop not in names:
                problems.append(
                    BindingProblem(
                        binding.file, f"Hierarchy '{binding.entity}'[{binding.prop}] isn't in the model."
                    )
                )
    for file, query_ref, field in _query_refs(report_dir):
        expected = _expected_query_ref(field)
        if expected and query_ref != expected:
            problems.append(
                BindingProblem(
                    file, f"queryRef '{query_ref}' doesn't match its field; expected '{expected}'."
                )
            )
    return problems
