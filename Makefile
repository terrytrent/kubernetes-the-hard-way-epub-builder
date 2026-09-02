SOURCE_REPO ?= build/upstream
SOURCE_REF ?= 1.18.6
OUTPUT ?= dist/kubernetes-the-hard-way-$(SOURCE_REF).epub
PYTHON := .venv/bin/python
EPUBCHECK_VERSION := 5.3.0
EPUBCHECK_DIR := .tools/epubcheck-$(EPUBCHECK_VERSION)
EPUBCHECK_JAR := $(EPUBCHECK_DIR)/epubcheck.jar
.DEFAULT_GOAL := latest

.PHONY: latest fetch dependencies epub validate epubcheck checksum test quality clean

latest: fetch
	@tag="$$(git -C "$(SOURCE_REPO)" tag --sort=-version:refname | head -n 1)"; \
	test -n "$$tag" || { echo "No upstream tags found" >&2; exit 1; }; \
	echo "Building latest upstream tag: $$tag"; \
	$(MAKE) checksum SOURCE_REPO="$(SOURCE_REPO)" SOURCE_REF="$$tag"

fetch:
	@test -d "$(SOURCE_REPO)/.git" || git clone --filter=blob:none https://github.com/kelseyhightower/kubernetes-the-hard-way.git "$(SOURCE_REPO)"
	git -C "$(SOURCE_REPO)" fetch --tags --force origin

dependencies: .venv/.ready

.venv/.ready: requirements-build.txt
	python3 -m venv .venv
	.venv/bin/python -m pip install --disable-pip-version-check --require-hashes -r requirements-build.txt
	@touch $@

epub: dependencies
	$(PYTHON) scripts/build_epub.py --source-repo "$(SOURCE_REPO)" --source-ref "$(SOURCE_REF)" --output "$(OUTPUT)"

validate: epub
	python3 scripts/validate_epub.py "$(OUTPUT)" --tag "$(SOURCE_REF)" --source-repo "$(SOURCE_REPO)"

$(EPUBCHECK_JAR):
	./scripts/install_epubcheck.sh

epubcheck: validate $(EPUBCHECK_JAR)
	./scripts/run_epubcheck.sh "$(EPUBCHECK_JAR)" "$(OUTPUT)"

checksum: epubcheck
	python3 scripts/write_checksum.py "$(OUTPUT)"
	python3 scripts/verify_provenance.py "$(OUTPUT)" "$(OUTPUT).provenance.json" "$(OUTPUT).sha256" --tag "$(SOURCE_REF)"

test:
	python3 -m unittest discover -s tests -v

quality:
	PYTHONPYCACHEPREFIX=/tmp/kthw-pycache python3 -m compileall -q scripts tests
	sh -n scripts/*.sh
	python3 scripts/check_repo.py

clean:
	rm -rf build dist
