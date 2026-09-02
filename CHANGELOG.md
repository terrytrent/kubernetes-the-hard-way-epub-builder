# Changelog

This changelog records changes to the EPUB builder. The stable `epub-master`
release tracks upstream independently of the builder's semantic version.

## Unreleased

- Changed generated EPUBs and six-hour automation to track the exact current
  commit of upstream default branch `master` instead of upstream version tags.
- Updated pinned checkout, artifact-download, and provenance-attestation Actions
  to their current major releases.

## 1.0.0 - 2026-09-01

- Added direct, deterministic EPUB 3 construction without Calibre.
- Added light/dark reader-responsive styling, semantic tables, native navigation,
  cover packaging, and removal of redundant `Next:` links.
- Added exact upstream source and commit provenance in the book and adjacent JSON.
- Added fail-closed source and EPUB security validation for active content,
  executable files, unsafe archives, unsafe CSS, remote resources, and malformed
  images.
- Added official pinned EPUBCheck, SHA-256 output, provenance verification, unit
  tests, and reproducibility coverage.
- Added six-hour upstream monitoring and separated read-only build and
  write-scoped release jobs with artifact attestations.
- Added licensing, trademark, security, contribution, and agent guidance.
