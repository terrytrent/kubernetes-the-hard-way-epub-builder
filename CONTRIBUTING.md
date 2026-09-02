# Contributing

Thank you for helping improve Kubernetes The Hard Way EPUB Builder. This project
changes presentation and packaging; technical corrections to the tutorial belong
in the [upstream repository](https://github.com/kelseyhightower/kubernetes-the-hard-way).

## Before opening a change

- Read `AGENTS.md`, `SECURITY.md`, `CONTENT_LICENSE.md`, and the relevant code.
- Open an issue first for changes that affect licensing, trademarks, release
  policy, supported source structure, security boundaries, or generated-book
  behavior.
- Never include generated `dist/` files, fetched `build/` content, `.venv/`, or
  `.tools/` in a pull request.
- Do not replace either image in `assets/` without prior maintainer agreement.

## Development

Use Python 3.10 or newer. Run the fast checks while iterating:

```sh
make quality
make test
```

Changes to conversion, packaging, styling, validation, dependencies, or release
automation must also pass the complete fixture build:

```sh
make fetch
make checksum SOURCE_REF=1.18.6
```

The completed build must pass the project scanner and official EPUBCheck without
errors. Add focused regression tests for bug and security fixes.

## Pull requests

Keep pull requests narrow and explain:

- the problem and intended behavior;
- security, licensing, trademark, or reproducibility implications;
- commands used for verification; and
- user-facing documentation changed.

By contributing, you agree that builder code and documentation are provided
under Apache-2.0. Do not submit content you do not have the right to license.

## Security reports

Do not disclose suspected vulnerabilities in a public issue. Follow the private
reporting instructions in `SECURITY.md`.
