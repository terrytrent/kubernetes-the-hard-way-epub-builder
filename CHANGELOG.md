# Changelog

This changelog records changes to the EPUB builder. Generated EPUB release names
follow upstream tutorial tags independently of the builder's semantic version.

## 1.0.0 - 2026-09-01

- Added direct, deterministic EPUB 3 construction without Calibre.
- Added light/dark reader-responsive styling, semantic tables, native navigation,
  cover packaging, and removal of redundant `Next:` links.
- Added exact upstream tag and commit provenance in the book and adjacent JSON.
- Added fail-closed source and EPUB security validation for active content,
  executable files, unsafe archives, unsafe CSS, remote resources, and malformed
  images.
- Added official pinned EPUBCheck, SHA-256 output, provenance verification, unit
  tests, and reproducibility coverage.
- Added six-hour upstream tag discovery and separated read-only build and
  write-scoped release jobs with artifact attestations.
- Added licensing, trademark, security, contribution, and agent guidance.
