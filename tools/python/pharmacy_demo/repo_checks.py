"""Repository hygiene checks: PHI guard, identifier and secret guard, forbidden files, prose style."""

from __future__ import annotations

import fnmatch
import re
import subprocess
from dataclasses import dataclass
from pathlib import Path

import yaml

from . import paths

SKIP_DIRS = {
    ".git",
    ".venv",
    "node_modules",
    "out",
    ".tools",
    "dist",
    ".astro",
    "apm_modules",
    "__pycache__",
    ".pytest_cache",
    ".ruff_cache",
}
BINARY_EXT = {
    ".png",
    ".jpg",
    ".jpeg",
    ".gif",
    ".ico",
    ".webp",
    ".woff",
    ".woff2",
    ".ttf",
    ".pdf",
    ".zip",
    ".mp4",
}
MAX_FILE_BYTES = 5 * 1024 * 1024

FORBIDDEN_GLOBS = [
    "*.pbix",
    "*.abf",
    "**/.pbi/localSettings.json",
    "**/.pbi/cache.abf",
    ".env",
    ".env.*",
    "*.pfx",
    "*.pem",
    "*.key",
    "*.publishsettings",
    "**/id_rsa*",
]
FORBIDDEN_ALLOW = {".env.example"}

GUID = re.compile(r"\b[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}\b")
EMAIL = re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b")
SECRETS = [
    (
        "GitHub token",
        re.compile(r"\b(ghp|gho|ghu|ghs|ghr)_[A-Za-z0-9]{30,}\b|\bgithub_pat_[A-Za-z0-9_]{40,}\b"),
    ),
    ("AWS access key", re.compile(r"\bAKIA[0-9A-Z]{16}\b")),
    ("private key", re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----")),
    ("Azure storage key", re.compile(r"AccountKey=[A-Za-z0-9+/=]{40,}")),
    ("SAS signature", re.compile(r"[?&]sig=[A-Za-z0-9%+/=]{30,}")),
    ("JWT", re.compile(r"\beyJ[A-Za-z0-9_-]{10,}\.eyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}")),
    ("client secret assignment", re.compile(r"(?i)client[_-]?secret\s*[:=]\s*['\"][^'\"<>{}$]{8,}['\"]")),
]
PHI_COLUMNS = re.compile(
    r"(?i)^(patient|pt_|member|mrn|ssn|dob|birth|first_?name|last_?name|full_?name|address|street|zip|postal|"
    r"phone|email|diagnosis|icd|npi|prescriber)"
)
SSN = re.compile(r"\b\d{3}-\d{2}-\d{4}\b")
DASHES = re.compile("[\u2013\u2014]")


@dataclass
class Problem:
    check: str
    file: str
    line: int
    message: str

    def as_dict(self) -> dict:
        return {"check": self.check, "file": self.file, "line": self.line, "message": self.message}


def list_files(root: Path) -> list[str]:
    try:
        result = subprocess.run(
            ["git", "-C", str(root), "ls-files", "-z", "--cached", "--others", "--exclude-standard"],
            capture_output=True,
            check=True,
        )
        files = [f for f in result.stdout.decode("utf-8").split("\0") if f]
        return sorted({f for f in files if (root / f).is_file()})
    except (OSError, subprocess.CalledProcessError):
        found = []
        for path in root.rglob("*"):
            if path.is_file() and not any(part in SKIP_DIRS for part in path.relative_to(root).parts):
                found.append(path.relative_to(root).as_posix())
        return sorted(found)


def _load_allowlist(root: Path) -> dict:
    path = root / "rules" / "identifier-allowlist.yaml"
    if not path.exists():
        return {"guid_line_contexts": [], "emails": [], "paths": []}
    with path.open(encoding="utf-8") as fh:
        return yaml.safe_load(fh)


def _read_text(path: Path) -> str | None:
    if path.suffix.lower() in BINARY_EXT:
        return None
    data = path.read_bytes()
    if b"\0" in data[:8192]:
        return None
    try:
        return data.decode("utf-8-sig")
    except UnicodeDecodeError:
        return None


def forbidden_files(files: list[str], root: Path) -> list[Problem]:
    problems = []
    for rel in files:
        name = rel.rsplit("/", 1)[-1]
        if name in FORBIDDEN_ALLOW:
            continue
        for pattern in FORBIDDEN_GLOBS:
            if fnmatch.fnmatch(rel, pattern) or fnmatch.fnmatch(name, pattern):
                problems.append(
                    Problem("forbidden-file", rel, 0, f"File type isn't allowed in this repo ({pattern}).")
                )
                break
        size = (root / rel).stat().st_size
        if size > MAX_FILE_BYTES:
            problems.append(Problem("large-file", rel, 0, f"File is {size // 1024} KB; the limit is 5 MB."))
    return problems


def identifier_guard(files: list[str], root: Path) -> list[Problem]:
    allow = _load_allowlist(root)
    contexts = allow.get("guid_line_contexts", [])
    email_ok = allow.get("emails", [])
    skip = allow.get("paths", [])
    problems = []
    for rel in files:
        if any(fnmatch.fnmatch(rel, p) for p in skip):
            continue
        text = _read_text(root / rel)
        if text is None:
            continue
        for n, line in enumerate(text.splitlines(), 1):
            if GUID.search(line) and not any(c in line for c in contexts):
                problems.append(
                    Problem(
                        "identifier",
                        rel,
                        n,
                        "GUID-shaped value. Tenant, workspace, and item IDs "
                        "must come from environment variables or placeholders.",
                    )
                )
            for match in EMAIL.finditer(line):
                address = match.group(0)
                if not any(address.endswith(ok) or ok in address for ok in email_ok):
                    problems.append(
                        Problem("identifier", rel, n, f"Email address '{address}'. Use a placeholder.")
                    )
            for label, pattern in SECRETS:
                if pattern.search(line):
                    problems.append(
                        Problem("secret", rel, n, f"Looks like a {label}. Remove it and rotate it.")
                    )
    return problems


def phi_guard(root: Path) -> list[Problem]:
    problems = []
    generated = root / "data" / "generated"
    for csv in sorted(generated.glob("*.csv")):
        rel = csv.relative_to(root).as_posix()
        with csv.open(encoding="utf-8") as fh:
            header = fh.readline().strip().split(",")
            for column in header:
                if PHI_COLUMNS.match(column):
                    problems.append(
                        Problem(
                            "phi",
                            rel,
                            1,
                            f"Column '{column}' looks like person data. "
                            "This repo holds synthetic, non-person data only.",
                        )
                    )
            for n, line in enumerate(fh, 2):
                if SSN.search(line):
                    problems.append(Problem("phi", rel, n, "Value shaped like a US Social Security number."))
                    break
    return problems


def _strip_code(text: str) -> list[tuple[int, str]]:
    out, fenced = [], False
    for n, line in enumerate(text.splitlines(), 1):
        if line.lstrip().startswith(("```", "~~~")):
            fenced = not fenced
            continue
        if not fenced:
            out.append((n, re.sub(r"`[^`]*`", "", line)))
    return out


def prose_style(files: list[str], root: Path) -> list[Problem]:
    """No em or en dashes in Markdown prose (repo writing style)."""
    problems = []
    for rel in files:
        if not rel.endswith((".md", ".mdx")):
            continue
        text = _read_text(root / rel) or ""
        for n, line in _strip_code(text):
            if DASHES.search(line):
                problems.append(
                    Problem(
                        "prose-dash",
                        rel,
                        n,
                        "Em or en dash in prose. Use a comma, colon, parentheses, or 'to'.",
                    )
                )
    return problems


def run_all(root: Path | None = None) -> list[Problem]:
    root = root or paths.repo_root()
    files = list_files(root)
    return (
        forbidden_files(files, root)
        + identifier_guard(files, root)
        + phi_guard(root)
        + prose_style(files, root)
    )
