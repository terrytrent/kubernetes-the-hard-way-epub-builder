# Third-party notices

This repository does not vendor the following tools. The build installs or runs
pinned versions and verifies downloads as documented in the source files.

## Python-Markdown

- Version: 3.10.3
- Purpose: Markdown-to-XHTML conversion
- License: BSD-3-Clause
- Project: https://python-markdown.github.io/
- Distribution: https://pypi.org/project/Markdown/

## EPUBCheck

- Version: 5.3.0
- Purpose: official EPUB conformance validation
- License: BSD-3-Clause
- Project: https://github.com/w3c/epubcheck

## Eclipse Temurin

- Version selection: immutable container digest in `scripts/run_epubcheck.sh`
- Purpose: isolated Java runtime for EPUBCheck when Docker is available
- Project and license information: https://adoptium.net/

Generated EPUB content is separately governed by `CONTENT_LICENSE.md` and
`NOTICE`. The upstream tutorial is not vendored in this repository; the exact
current default-branch (`master`) commit is fetched from its Git history during a build.
