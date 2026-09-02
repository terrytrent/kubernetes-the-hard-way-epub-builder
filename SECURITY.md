# Security policy

## Reporting

Please report suspected vulnerabilities privately through this repository's
GitHub Security Advisories. Do not open a public issue for an undisclosed
vulnerability.

## Threat model

Upstream Markdown, images, Git tags, downloaded build tools, generated EPUB
contents, and CI artifacts are treated as untrusted until verified. Upstream
book commands are displayed as text and are never executed by this project.

The release pipeline fails closed when it encounters active or executable EPUB
content, unsafe archive structure, incomplete source conversion, a failed tool
checksum, a failed EPUBCheck result, or a failed internal validation.

Forbidden EPUB content includes JavaScript and other executable files, scripted
manifest items, inline event handlers, forms, frames, embeds, objects, canvas,
audio/video, SVG/MathML, unsafe or remote embedded resources, active CSS, DTDs,
entities, encrypted members, symbolic links, path traversal, duplicate archive
members, and excessive decompression ratios or sizes.

## Release protections

- Build jobs have read-only repository permissions.
- Publication occurs in a separate job with narrowly scoped write permission.
- All external GitHub Actions use immutable full commit SHAs.
- The Markdown parser and EPUBCheck are pinned and verified against published
  cryptographic hashes. The EPUB package is constructed directly by the builder.
- Local Docker fallback for EPUBCheck uses an immutable Temurin JRE image digest,
  no network, a read-only filesystem, no Linux capabilities, and a non-root user.
- Release candidates pass unit tests, source-completeness checks, active-content
  scanning, EPUBCheck, internal-link validation, and checksum generation.
- Published EPUBs receive GitHub artifact provenance attestations and ship with
  SHA-256 and JSON provenance files.

Repository administrators should enable branch protection for `main`, require
the CI status check and pull-request review, block force pushes and deletion,
require signed commits where practical, enable secret scanning and Dependabot,
and restrict Actions to approved, SHA-pinned actions.
