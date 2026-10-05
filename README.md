# Kubernetes The Hard Way EPUB Builder

[![CI](https://github.com/terrytrent/kubernetes-the-hard-way-epub-builder/actions/workflows/ci.yml/badge.svg)](https://github.com/terrytrent/kubernetes-the-hard-way-epub-builder/actions/workflows/ci.yml)
[![Release automation](https://github.com/terrytrent/kubernetes-the-hard-way-epub-builder/actions/workflows/build-release.yml/badge.svg)](https://github.com/terrytrent/kubernetes-the-hard-way-epub-builder/actions/workflows/build-release.yml)
[![Builder version](https://img.shields.io/badge/builder-v1.0.0-007ec6.svg)](CHANGELOG.md)
[![License: Apache-2.0](https://img.shields.io/badge/license-Apache--2.0-blue.svg)](LICENSE)
[![Generated content: CC BY-NC-SA 4.0](https://img.shields.io/badge/generated%20content-CC%20BY--NC--SA%204.0-lightgrey.svg)](CONTENT_LICENSE.md)

An automated, security-conscious builder for producing readable EPUB editions
of Kelsey Hightower's
[Kubernetes The Hard Way](https://github.com/kelseyhightower/kubernetes-the-hard-way).

<p align="center">
  <img src="assets/cover.png" alt="Cover for the unofficial Kubernetes The Hard Way EPUB adaptation" width="360">
</p>

This repository is an **unofficial, noncommercial reading-format adaptation**.
It is not a fork of the tutorial, a replacement for the upstream repository, or
an official Kubernetes publication. Its purpose is to reproducibly transform
the current upstream default-branch (`master`) commit into a standards-compliant EPUB while keeping
the technical content, attribution, source identity, and license visible.

- **Builder version:** 1.0.0
- **Builder license:** Apache-2.0
- **Generated-content license:** CC-BY-NC-SA-4.0
- **Supported platforms:** macOS, Linux, and Windows environments providing
  Python, Git, Make, and optional Docker or Java for EPUBCheck

Generated books record the upstream repository, branch, and exact commit; retain
the upstream attribution and CC BY-NC-SA 4.0 license; remove redundant `Next:`
links; preserve code and images; and use theme-safe styling in light and dark
reading modes.

## What the builder does

For the upstream `master` branch, the builder:

1. Fetches `origin/master` and resolves it to an exact Git commit.
2. Reads the ordered lab list from that commit's `README.md` instead of assuming a
   filename pattern.
3. Converts the introduction and every listed lab to semantic XHTML.
4. Preserves fenced commands, tables, links, and validated raster images.
5. Removes chapter-ending `Next:` links because the EPUB has a native table of
   contents.
6. Adds the upstream repository, branch, commit, license, adaptation notice, and
   trademark disclaimer to the book.
7. Packages the content directly as EPUB 3, without Calibre or another ebook
   library application.
8. Runs source-completeness, internal-link, theme-safety, archive-security, and
   active-content checks followed by official W3C EPUBCheck.
9. Writes an adjacent SHA-256 checksum and JSON provenance manifest.

The EPUB is suitable for standards-compliant readers and library applications.
The builder does not modify upstream, execute tutorial commands, create a
Kubernetes cluster, or claim that historical tutorial releases remain current.

## Project layout

| Path | Purpose |
| --- | --- |
| `AGENTS.md` | Repository-specific operating instructions for coding agents. |
| `VERSION`, `CHANGELOG.md` | Builder semantic version and release history. |
| `CONTRIBUTING.md`, `CODE_OF_CONDUCT.md` | Contribution workflow and community expectations. |
| `Makefile` | Local entry points for fetching, building, validating, and testing. |
| `requirements-build.txt` | Hash-pinned Python Markdown build dependency. |
| `scripts/build_epub.py` | Reads the exact upstream `master` commit and constructs EPUB 3 directly. |
| `scripts/validate_epub.py` | Applies archive, content, link, provenance, and active-content checks. |
| `scripts/install_epubcheck.sh` | Downloads and verifies the pinned official EPUBCheck release. |
| `scripts/run_epubcheck.sh` | Runs EPUBCheck with pinned Docker isolation or local Java fallback. |
| `scripts/write_checksum.py` | Writes the portable adjacent SHA-256 file. |
| `scripts/verify_provenance.py` | Verifies EPUB, checksum, branch, filename, and JSON provenance agreement. |
| `scripts/check_repo.py` | Applies dependency-free repository and documentation quality checks. |
| `epub.css` | Reader-responsive styling for typography, code, and tables. |
| `assets/cover.png` | AI-generated cover included in generated EPUBs. |
| `assets/buy_me_a_book.png` | Donation button displayed in this README. |
| `tests/test_builder.py` | Source conversion, table, link, image, and input-safety tests. |
| `tests/test_security.py` | Clean and malicious EPUB regression fixtures. |
| `.github/workflows/ci.yml` | Read-only test and fixture-build verification. |
| `.github/workflows/build-release.yml` | Six-hour upstream-main polling, validation, attestation, and publishing. |
| `.github/dependabot.yml` | Scheduled Python and GitHub Actions dependency monitoring. |
| `.github/CODEOWNERS` | Maintainer ownership for general and security-sensitive files. |
| `.github/ISSUE_TEMPLATE/`, `.github/PULL_REQUEST_TEMPLATE.md` | Structured contribution intake. |
| `SECURITY.md` | Threat model, reporting policy, and repository protection guidance. |
| `LICENSE`, `NOTICE` | Apache-2.0 builder licensing and attribution notices. |
| `CONTENT_LICENSE.md` | Generated-book, artwork, attribution, and trademark terms. |
| `THIRD_PARTY_NOTICES.md` | Pinned build-tool purposes, sources, and licenses. |
| `dist/` | Generated artifacts; intentionally not committed. |
| `build/upstream/` | Local upstream checkout; intentionally not committed. |
| `.tools/`, `.venv/` | Ignored, pinned local tools and Python environment. |

## Status, license, and trademarks

This is an **unofficial, noncommercial reading-format adaptation**. It is not
affiliated with, sponsored by, or endorsed by The Linux Foundation, the Cloud
Native Computing Foundation, the Kubernetes project, or Kelsey Hightower. All
downloads are provided free of charge; payment or donations are not required.

The generated EPUB is an adaptation distributed under the upstream project's
[Creative Commons Attribution-NonCommercial-ShareAlike 4.0 license](https://creativecommons.org/licenses/by-nc-sa/4.0/).
It identifies the upstream repository, `master` branch and exact commit, preserves
attribution, and describes the formatting changes.

The cover artwork is AI-generated. Its stylized Kubernetes helm mark is used for
a noncommercial educational publication; it is not a Certified Kubernetes mark
and makes no certification claim.

Kubernetes® is a registered trademark of The Linux Foundation in the United
States and other countries. Use of the mark is governed by the
[Kubernetes branding guidelines](https://github.com/kubernetes/kubernetes/blob/master/logo/usage_guidelines.md)
and [Linux Foundation trademark guidelines](https://www.linuxfoundation.org/legal/tm-usage).

## Local build

> **Calibre is not required.** This repository constructs the EPUB package
> directly with Python. The generated book is not tied to Calibre or any other
> ebook library or reader.

### Requirements for building the EPUB

- Python 3.11 or newer
- Git and `make`
- Network access for the initial dependency installation and upstream clone;
  later builds can use the existing `.venv` and source checkout

The sole Python dependency is pinned with a SHA-256 hash in
`requirements-build.txt` and installed into `.venv`.

### Additional requirement for a fully validated release build

The default `make` command and the `epubcheck` and `checksum` targets require
either Docker or Java to run official EPUBCheck. Docker or Java is **not** needed
for `make epub` or the Python unit tests.

EPUBCheck is pinned and hash-verified. When Docker is available, it runs in an
immutable JRE image with no network, a read-only root filesystem, no Linux
capabilities, and a non-root user.

### Quick start

```sh
make
```

The default command fetches upstream `master`, resolves its exact commit, and
builds, validates, EPUBChecks, and checksums its EPUB. Outputs are written to
`dist/` along with SHA-256 and JSON provenance files.

To run the complete build explicitly:

```sh
make fetch
make checksum
```

To construct only the EPUB, without running EPUBCheck or creating its checksum:

```sh
make fetch
make epub
```

Run the unit and malicious-EPUB regression suite with `make test`.

### Build targets

| Command | Result |
| --- | --- |
| `make` or `make all` | Fetch and fully verify the current upstream `master` commit. |
| `make fetch` | Clone upstream if needed and refresh `origin/master`. |
| `make dependencies` | Create `.venv` and install hash-verified Python dependencies. |
| `make epub` | Construct the EPUB from the fetched upstream `master` commit. |
| `make validate` | Build and run the strict project scanner. |
| `make epubcheck` | Also run official EPUBCheck. |
| `make checksum` | Complete all gates and write the checksum. |
| `make test` | Run unit and malicious-input regression tests. |

For development or offline builds, override the source checkout and output:

```sh
make checksum \
  SOURCE_REPO=/path/to/kubernetes-the-hard-way \
  OUTPUT=dist/custom-name.epub
```

The supplied source checkout must have `refs/remotes/origin/master`. The builder
resolves that remote-tracking ref once and reads all content from the resulting
immutable commit, so an upstream update cannot mix revisions within one build.

`make clean` removes `build/` and `dist/`, but preserves `.venv` and the pinned
tool cache.

## Generated artifacts and verification

A successful build produces:

```text
dist/kubernetes-the-hard-way-master.epub
dist/kubernetes-the-hard-way-master.epub.sha256
dist/kubernetes-the-hard-way-master.epub.provenance.json
```

The book contains its repository URL, `master` branch, exact source commit, source date,
attribution, license, and adaptation/trademark notices. The external provenance
manifest records the source identity, builder commit, filename, and EPUB
SHA-256. It describes the content and builder, not an ebook-library application.

Verify a downloaded artifact on a system with `sha256sum`:

```sh
sha256sum --check kubernetes-the-hard-way-master.epub.sha256
```

On macOS, compare the output of `shasum -a 256 FILE.epub` with the adjacent
`.sha256` file.

## Readability and formatting

The stylesheet does not force page foreground or background colors, so reader
preferences for light, dark, sepia, fonts, and margins remain in control. Code,
inline code, tables, links, and callouts use inherited or theme-responsive
colors. Wide commands and tables scroll within their own containers rather than
forcing the whole page beyond the viewport. The fixed cover image does not
change with the reader theme; all reflowable content does.

## Automated releases

The GitHub Actions workflow checks upstream every six hours. It compares the
exact `origin/master` commit with the commit recorded in the stable `epub-master`
release. When the commits differ, it builds, validates, EPUBChecks, checksums,
attests, and replaces the release assets. A manual run can force a rebuild.

Cross-repository branch updates do not trigger workflows here, so scheduled
polling is used. Verified files cross into a separate publication job; only that job has
release-write permission. Published EPUBs also receive a GitHub build-provenance
attestation.

GitHub automatically disables scheduled workflows in inactive public
repositories after an extended inactivity period. To recover, enable and run it
from the Actions page or use:

```sh
gh workflow enable build-release.yml
gh workflow run build-release.yml
```

Once the GitHub remote is created, add the CI and release-workflow badges using
that repository's final owner/name URLs.

Repository administrators should enable the branch protection, review, Actions,
secret-scanning, and dependency-monitoring controls in [SECURITY.md](SECURITY.md).
Those settings live on GitHub and cannot be enforced by files in this checkout.

## Security and release integrity

Upstream files are treated as untrusted data. The builder never executes book
commands. It rejects active raw markup before conversion and scans the finished
EPUB for executable files, JavaScript, scripted content, event handlers, forms,
frames, embeds, objects, canvas, media, SVG/MathML, unsafe CSS, unsafe URL
schemes, remote embedded resources, DTDs/entities, encryption, symbolic links,
path traversal, duplicate ZIP members, and decompression abuse.

Raster images are limited to bounded PNG, JPEG, or GIF files and their dimensions
are checked without invoking an image decoder. The finished-book scanner also
checks source chapter counts, referenced images, internal destinations, cover
metadata, required disclosure text, and removal of stale `Next:` links. Either a
project-validator error or an EPUBCheck error stops the release.

Releases also require source-completeness checks, internal-link validation,
theme-safe CSS checks, the official W3C EPUBCheck, SHA-256, a JSON provenance
manifest, and a GitHub artifact provenance attestation. Build jobs are read-only;
only the isolated publication job receives release write permission. See
[SECURITY.md](SECURITY.md) for the threat model and recommended repository
settings.

## Repository licensing

Builder code and documentation use Apache-2.0; see [LICENSE](LICENSE). Generated
books and the cover use CC-BY-NC-SA-4.0 subject to the trademark limitations in
[CONTENT_LICENSE.md](CONTENT_LICENSE.md) and [NOTICE](NOTICE).

Downloads are free. Donations support maintenance of this separate builder;
they are not payment for upstream content or for use of Kubernetes trademarks.

## Reporting problems

For a build failure, include the operating system, Python version, upstream
commit, failing make target, and complete validator output. Report suspected
vulnerabilities privately through GitHub Security Advisories as described in
[SECURITY.md](SECURITY.md), rather than attaching an untrusted EPUB publicly.

Report errors in the tutorial itself through the
[upstream issue tracker](https://github.com/kelseyhightower/kubernetes-the-hard-way/issues).
This project changes presentation and packaging, not the technical instructions.

## Support this project

If these EPUB editions make *Kubernetes The Hard Way* easier to read, you can
support continued development, testing, documentation, and maintenance of this
unofficial builder:

<p align="center">
  <a href="https://www.buymeacoffee.com/terry.trent" target="_blank"><img src="assets/buy_me_a_book.png" alt="Buy me a book!" height="60" width="217"></a>
</p>
