#!/usr/bin/env python3
"""Run dependency-free repository quality and documentation checks."""

from __future__ import annotations

import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
TEXT_SUFFIXES = {".md", ".py", ".sh", ".yml", ".yaml", ".txt", ".css"}
ACTION_PIN = re.compile(r"^\s*(?:-\s*)?uses:\s*[^#\s]+@([0-9a-f]{40})(?:\s+#.*)?$")


def main() -> None:
    errors: list[str] = []
    ignored = {".git", ".venv", ".tools", "build", "dist", "__pycache__"}
    for path in sorted(ROOT.rglob("*")):
        if not path.is_file() or any(part in ignored for part in path.parts):
            continue
        if path.suffix not in TEXT_SUFFIXES and path.name not in {"Makefile", "VERSION", "LICENSE", "NOTICE"}:
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeError:
            continue
        relative = path.relative_to(ROOT)
        if not text.endswith("\n"):
            errors.append(f"{relative}: missing final newline")
        for number, line in enumerate(text.splitlines(), 1):
            if line.rstrip() != line:
                errors.append(f"{relative}:{number}: trailing whitespace")
            if relative.parts[:2] == (".github", "workflows") and "uses:" in line:
                if not ACTION_PIN.match(line):
                    errors.append(f"{relative}:{number}: action is not pinned to a full SHA")

    for filename in ("README.md", "AGENTS.md", "SECURITY.md", "CONTENT_LICENSE.md"):
        path = ROOT / filename
        text = path.read_text(encoding="utf-8")
        for target in re.findall(r"\[[^]]+\]\(([^)]+)\)|<img src=\"([^\"]+)\"", text):
            value = next(item for item in target if item)
            if "://" in value or value.startswith("#"):
                continue
            if not (ROOT / value).exists():
                errors.append(f"{filename}: missing local link or image: {value}")

    version = (ROOT / "VERSION").read_text(encoding="ascii").strip()
    if not re.fullmatch(r"[0-9]+\.[0-9]+\.[0-9]+", version):
        errors.append("VERSION is not MAJOR.MINOR.PATCH")

    if errors:
        raise SystemExit("Repository quality checks failed:\n- " + "\n- ".join(errors))
    print("Repository quality checks passed")


if __name__ == "__main__":
    main()
