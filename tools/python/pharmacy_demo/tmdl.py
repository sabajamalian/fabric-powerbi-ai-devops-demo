"""Small TMDL reader and structural linter.

Covers the subset of TMDL this repo uses: tables, columns, measures, hierarchies, partitions,
relationships, expressions, annotations, and model refs. It isn't a full TMDL implementation; the
authoritative check is opening the project in Power BI Desktop.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

OBJECT_KEYWORDS = {
    "table",
    "column",
    "measure",
    "hierarchy",
    "level",
    "partition",
    "relationship",
    "expression",
    "model",
    "database",
    "cultureInfo",
    "annotation",
    "calculationGroup",
    "calculationItem",
    "role",
    "perspective",
    "linguisticMetadata",
    "extendedProperty",
    "changedProperty",
    "tablePermission",
    "dataAccessOptions",
    "queryGroup",
    "ref",
    "translation",
    "variation",
    "attributeHierarchy",
}
MAX_DESCRIPTION = 200


@dataclass
class Finding:
    rule: str
    severity: str  # error | warning
    file: str
    line: int
    message: str

    def as_dict(self) -> dict:
        return {
            "rule": self.rule,
            "severity": self.severity,
            "file": self.file,
            "line": self.line,
            "message": self.message,
        }


@dataclass
class Node:
    kind: str
    name: str
    depth: int
    line: int
    file: str
    description: str | None = None
    expression: str | None = None
    props: dict[str, str | bool] = field(default_factory=dict)
    children: list[Node] = field(default_factory=list)

    def child(self, kind: str) -> list[Node]:
        return [c for c in self.children if c.kind == kind]


@dataclass
class Model:
    root: Path
    tables: dict[str, Node] = field(default_factory=dict)
    relationships: list[Node] = field(default_factory=list)
    expressions: list[Node] = field(default_factory=list)
    model_node: Node | None = None
    model_annotations: dict[str, str] = field(default_factory=dict)
    table_refs: list[tuple[str, int]] = field(default_factory=list)
    table_files: dict[str, str] = field(default_factory=dict)
    findings: list[Finding] = field(default_factory=list)

    def columns(self, table: str) -> dict[str, Node]:
        node = self.tables.get(table)
        return {c.name: c for c in node.child("column")} if node else {}

    def measures(self) -> dict[str, tuple[str, Node]]:
        found = {}
        for table_name, table in self.tables.items():
            for measure in table.child("measure"):
                found[measure.name] = (table_name, measure)
        return found


def read_name(text: str) -> tuple[str, str]:
    """Read one TMDL name from the start of text. Returns (name, remainder)."""
    text = text.lstrip()
    if text.startswith("'"):
        out, i = [], 1
        while i < len(text):
            if text[i] == "'":
                if i + 1 < len(text) and text[i + 1] == "'":
                    out.append("'")
                    i += 2
                    continue
                return "".join(out), text[i + 1 :]
            out.append(text[i])
            i += 1
        return "".join(out), ""
    match = re.match(r"[^\s=.:]+", text)
    if not match:
        return "", text
    return match.group(0), text[match.end() :]


def parse_qualified(text: str) -> tuple[str, str]:
    table, rest = read_name(text)
    rest = rest.lstrip()
    if not rest.startswith("."):
        return table, ""
    column, _ = read_name(rest[1:])
    return table, column


def _leading_tabs(raw: str) -> tuple[int, str]:
    count = len(raw) - len(raw.lstrip("\t"))
    return count, raw[count:]


def parse_file(path: Path, display: str) -> tuple[list[Node], list[Finding]]:
    findings: list[Finding] = []
    raw_lines = path.read_text(encoding="utf-8-sig").splitlines()
    roots: list[Node] = []
    stack: list[Node] = []
    pending_description: list[str] = []
    i = 0

    def add(node: Node) -> None:
        while stack and stack[-1].depth >= node.depth:
            stack.pop()
        if stack:
            stack[-1].children.append(node)
        else:
            roots.append(node)
        stack.append(node)

    def read_expression(start: int, body_depth: int, first: str) -> tuple[str, int]:
        """Collect an expression that starts after '=' on line start. Returns (text, next index).

        Text after '=' is a single-line expression. Otherwise the body is every following line
        indented at least body_depth tabs, or a ``` fenced block.
        """
        first = first.strip()
        if first.startswith("```"):
            body = []
            j = start + 1
            while j < len(raw_lines) and raw_lines[j].strip() != "```":
                body.append(raw_lines[j])
                j += 1
            if j >= len(raw_lines):
                findings.append(
                    Finding("TMDL002", "error", display, start + 1, "Unclosed ``` expression block.")
                )
            return "\n".join(body), j + 1
        if first:
            return first, start + 1
        body: list[str] = []
        j = start + 1
        while j < len(raw_lines):
            line = raw_lines[j]
            if line.strip() == "":
                j += 1
                body.append("")
                continue
            tabs, _ = _leading_tabs(line)
            if tabs < body_depth:
                break
            body.append(line.strip())
            j += 1
        while body and body[-1] == "":
            body.pop()
        return "\n".join(body), j

    while i < len(raw_lines):
        raw = raw_lines[i]
        line_no = i + 1
        if raw.strip() == "":
            i += 1
            continue
        tabs, rest = _leading_tabs(raw)
        if rest[:1] == " ":
            findings.append(
                Finding(
                    "TMDL001",
                    "error",
                    display,
                    line_no,
                    "Indentation uses spaces. TMDL outside expressions must be indented with tabs.",
                )
            )
            rest = rest.lstrip(" ")
        if rest.startswith("///"):
            pending_description.append(rest[3:].strip())
            i += 1
            continue
        if rest.startswith("//"):
            findings.append(
                Finding(
                    "TMDL003",
                    "error",
                    display,
                    line_no,
                    "'//' comments aren't valid TMDL. Use '///' for a description or remove the line.",
                )
            )
            i += 1
            continue

        keyword = rest.split(None, 1)[0] if rest.split() else ""
        after = rest[len(keyword) :]
        if keyword in OBJECT_KEYWORDS and not after.startswith(":"):
            description = " ".join(pending_description) if pending_description else None
            pending_description = []
            if keyword == "ref":
                kind, remainder = (
                    after.strip().split(None, 1) if len(after.split()) > 1 else (after.strip(), "")
                )
                name, _ = read_name(remainder)
                add(Node("ref:" + kind, name, tabs, line_no, display))
                i += 1
                continue
            if keyword == "annotation":
                key, remainder = read_name(after)
                value = remainder.split("=", 1)[1].strip() if "=" in remainder else ""
                add(Node("annotation", key, tabs, line_no, display, expression=value))
                i += 1
                continue
            name, remainder = read_name(after)
            node = Node(keyword, name, tabs, line_no, display, description=description)
            if remainder.strip().startswith("="):
                expression, i = read_expression(i, tabs + 2, remainder.strip()[1:])
                node.expression = expression
                add(node)
                continue
            add(node)
            i += 1
            continue

        if pending_description:
            findings.append(
                Finding(
                    "TMDL004",
                    "warning",
                    display,
                    line_no,
                    "Description ('///') isn't directly above an object declaration.",
                )
            )
            pending_description = []
        owner = stack[-1] if stack else None
        while owner is not None and stack and stack[-1].depth >= tabs:
            stack.pop()
            owner = stack[-1] if stack else None
        if owner is None:
            findings.append(
                Finding("TMDL005", "error", display, line_no, f"Property outside any object: {rest!r}")
            )
            i += 1
            continue
        if ":" in rest and (rest.find(":") < rest.find("=") or "=" not in rest):
            key, value = rest.split(":", 1)
            owner.props[key.strip()] = value.strip()
            i += 1
        elif "=" in rest:
            key, value = rest.split("=", 1)
            expression, i = read_expression(i, tabs + 1, value)
            owner.props[key.strip()] = expression
        else:
            owner.props[rest.strip()] = True
            i += 1
    return roots, findings


def load_model(semantic_model_dir: Path) -> Model:
    definition = semantic_model_dir / "definition"
    model = Model(root=semantic_model_dir)
    if not definition.is_dir():
        model.findings.append(
            Finding("TMDL010", "error", str(semantic_model_dir), 0, "Missing definition folder.")
        )
        return model
    for path in sorted(definition.rglob("*.tmdl")):
        display = path.relative_to(semantic_model_dir).as_posix()
        roots, findings = parse_file(path, display)
        model.findings.extend(findings)
        for node in roots:
            if node.kind == "table":
                if node.name.casefold() in {t.casefold() for t in model.tables}:
                    model.findings.append(
                        Finding(
                            "TMDL011",
                            "error",
                            display,
                            node.line,
                            f"Table '{node.name}' is declared more than once.",
                        )
                    )
                model.tables[node.name] = node
                model.table_files[node.name] = display
            elif node.kind == "relationship":
                model.relationships.append(node)
            elif node.kind == "expression":
                model.expressions.append(node)
            elif node.kind == "model":
                model.model_node = node
            elif node.kind == "annotation" and display.endswith("model.tmdl"):
                model.model_annotations[node.name] = node.expression or ""
            elif node.kind == "ref:table":
                model.table_refs.append((node.name, node.line))
    return model


_STRING = re.compile(r'"(?:[^"]|"")*"')
_QUALIFIED = re.compile(r"('(?:[^']|'')+'|\b[A-Za-z_][A-Za-z0-9_]*)\[([^\]]+)\]")


def dax_references(expression: str) -> tuple[list[tuple[str, str]], list[str]]:
    """Return (qualified column refs, bare refs) found in a DAX expression."""
    text = _STRING.sub('""', expression)
    qualified = []
    for match in _QUALIFIED.finditer(text):
        table = match.group(1)
        if table.startswith("'"):
            table = table[1:-1].replace("''", "'")
        qualified.append((table, match.group(2)))
    stripped = _QUALIFIED.sub(" ", text)
    bare = [m.group(1) for m in re.finditer(r"\[([^\]]+)\]", stripped)]
    return qualified, bare


def lint(semantic_model_dir: Path) -> list[Finding]:
    model = load_model(semantic_model_dir)
    findings = list(model.findings)
    table_names = set(model.tables)
    measures = model.measures()

    referenced = {name for name, _ in model.table_refs}
    model_file = "definition/model.tmdl"
    for name, line in model.table_refs:
        if name not in table_names:
            findings.append(
                Finding(
                    "TMDL012", "error", model_file, line, f"'ref table {name}' has no matching table file."
                )
            )
    for name in table_names - referenced:
        findings.append(
            Finding(
                "TMDL013",
                "error",
                model.table_files[name],
                model.tables[name].line,
                f"Table '{name}' isn't referenced in model.tmdl ('ref table {name}').",
            )
        )

    for table_name, table in model.tables.items():
        file = model.table_files[table_name]
        seen: dict[str, int] = {}
        columns = model.columns(table_name)
        for node in table.child("column") + table.child("measure"):
            key = node.name.casefold()
            if key in seen:
                findings.append(
                    Finding(
                        "TMDL014",
                        "error",
                        file,
                        node.line,
                        f"'{node.name}' duplicates another column or measure in '{table_name}'.",
                    )
                )
            seen[key] = node.line
        for node in table.child("column") + table.child("measure") + [table]:
            if node.description and len(node.description) > MAX_DESCRIPTION:
                findings.append(
                    Finding(
                        "TMDL020",
                        "warning",
                        file,
                        node.line,
                        f"Description of '{node.name}' is {len(node.description)} characters. "
                        f"Copilot reads only the first {MAX_DESCRIPTION}.",
                    )
                )
        for measure in table.child("measure"):
            if "formatString" not in measure.props and "formatStringDefinition" not in measure.props:
                findings.append(
                    Finding(
                        "TMDL021",
                        "warning",
                        file,
                        measure.line,
                        f"Measure '{measure.name}' has no formatString.",
                    )
                )
        for column in table.child("column"):
            sort_by = column.props.get("sortByColumn")
            if isinstance(sort_by, str):
                target, _ = read_name(sort_by)
                if target not in columns:
                    findings.append(
                        Finding(
                            "TMDL015",
                            "error",
                            file,
                            column.line,
                            f"sortByColumn '{target}' on '{column.name}' isn't a column in '{table_name}'.",
                        )
                    )
            if "dataType" not in column.props:
                findings.append(
                    Finding("TMDL016", "error", file, column.line, f"Column '{column.name}' has no dataType.")
                )
        for hierarchy in table.child("hierarchy"):
            for level in hierarchy.child("level"):
                target = level.props.get("column")
                if isinstance(target, str):
                    name, _ = read_name(target)
                    if name not in columns:
                        findings.append(
                            Finding(
                                "TMDL017",
                                "error",
                                file,
                                level.line,
                                f"Hierarchy level '{level.name}' points to missing column '{name}'.",
                            )
                        )
        if not table.child("partition") and not any(c.expression for c in table.child("column")):
            findings.append(
                Finding("TMDL018", "warning", file, table.line, f"Table '{table_name}' has no partition.")
            )

        for node in table.child("measure") + [c for c in table.child("column") if c.expression]:
            qualified, bare = dax_references(node.expression or "")
            for ref_table, ref_column in qualified:
                if ref_table not in table_names:
                    findings.append(
                        Finding(
                            "TMDL030",
                            "error",
                            file,
                            node.line,
                            f"DAX in '{node.name}' references unknown table '{ref_table}'.",
                        )
                    )
                elif ref_column not in model.columns(ref_table) and ref_column not in measures:
                    findings.append(
                        Finding(
                            "TMDL031",
                            "error",
                            file,
                            node.line,
                            f"DAX in '{node.name}' references unknown column '{ref_table}'[{ref_column}].",
                        )
                    )
            for ref in bare:
                if ref not in measures and ref not in columns:
                    findings.append(
                        Finding(
                            "TMDL032",
                            "error",
                            file,
                            node.line,
                            f"DAX in '{node.name}' references unknown measure or column [{ref}].",
                        )
                    )

    for rel in model.relationships:
        file = rel.file
        for prop in ("fromColumn", "toColumn"):
            value = rel.props.get(prop)
            if not isinstance(value, str):
                findings.append(
                    Finding("TMDL040", "error", file, rel.line, f"Relationship '{rel.name}' has no {prop}.")
                )
                continue
            table, column = parse_qualified(value)
            if table not in table_names:
                findings.append(
                    Finding(
                        "TMDL041",
                        "error",
                        file,
                        rel.line,
                        f"Relationship '{rel.name}' {prop} uses unknown table '{table}'.",
                    )
                )
            elif column not in model.columns(table):
                findings.append(
                    Finding(
                        "TMDL042",
                        "error",
                        file,
                        rel.line,
                        f"Relationship '{rel.name}' {prop} uses unknown column '{table}'.'{column}'.",
                    )
                )
    return findings


def errors(findings: list[Finding]) -> list[Finding]:
    return [f for f in findings if f.severity == "error"]
