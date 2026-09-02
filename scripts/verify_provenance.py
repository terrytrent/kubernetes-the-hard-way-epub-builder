#!/usr/bin/env python3
"""Verify that a release EPUB, checksum, and provenance manifest agree."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path


SOURCE_REPOSITORY = "https://github.com/kelseyhightower/kubernetes-the-hard-way"
SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
COMMIT_RE = re.compile(r"^[0-9a-f]{40}$")


def verify(
    epub: Path,
    provenance: Path,
    checksum: Path,
    expected_ref: str | None,
    expected_commit: str | None = None,
) -> None:
    errors: list[str] = []
    digest = hashlib.sha256(epub.read_bytes()).hexdigest()
    try:
        data = json.loads(provenance.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise ValueError(f"invalid provenance JSON: {exc}") from exc

    required = {
        "schema_version", "builder_version", "title", "source_repository",
        "source_branch", "source_commit", "source_commit_date", "builder_commit",
        "build_date_utc", "epub_filename", "epub_sha256", "license",
    }
    missing = required - data.keys()
    extra = data.keys() - required
    if missing:
        errors.append("missing provenance fields: " + ", ".join(sorted(missing)))
    if extra:
        errors.append("unexpected provenance fields: " + ", ".join(sorted(extra)))
    if data.get("schema_version") != 2:
        errors.append("unsupported provenance schema_version")
    if data.get("source_repository") != SOURCE_REPOSITORY:
        errors.append("unexpected source repository")
    if expected_ref is not None and data.get("source_branch") != expected_ref:
        errors.append("source branch does not match requested release")
    if data.get("epub_filename") != epub.name:
        errors.append("provenance filename does not match EPUB")
    recorded_digest = data.get("epub_sha256")
    if not isinstance(recorded_digest, str) or not SHA256_RE.fullmatch(recorded_digest):
        errors.append("provenance EPUB SHA-256 is malformed")
    elif recorded_digest != digest:
        errors.append("provenance EPUB SHA-256 does not match artifact")
    source_commit = data.get("source_commit")
    if not isinstance(source_commit, str) or not COMMIT_RE.fullmatch(source_commit):
        errors.append("source commit is not a full lowercase Git SHA")
    elif expected_commit is not None and source_commit != expected_commit:
        errors.append("source commit does not match the commit selected by the build job")
    if data.get("license") != "CC-BY-NC-SA-4.0":
        errors.append("unexpected content license")

    try:
        checksum_parts = checksum.read_text(encoding="ascii").strip().split()
    except (OSError, UnicodeError) as exc:
        errors.append(f"cannot read checksum: {exc}")
    else:
        if len(checksum_parts) != 2 or checksum_parts[0] != digest or checksum_parts[1] != epub.name:
            errors.append("checksum file does not match EPUB filename and SHA-256")

    if errors:
        raise ValueError("; ".join(errors))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("epub", type=Path)
    parser.add_argument("provenance", type=Path)
    parser.add_argument("checksum", type=Path)
    parser.add_argument("--ref")
    parser.add_argument("--commit")
    args = parser.parse_args()
    verify(args.epub, args.provenance, args.checksum, args.ref, args.commit)
    print(f"Verified release provenance for {args.epub}")


if __name__ == "__main__":
    main()
