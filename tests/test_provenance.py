import hashlib
import importlib.util
import json
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "verify_provenance", ROOT / "scripts" / "verify_provenance.py"
)
provenance = importlib.util.module_from_spec(SPEC)
assert SPEC.loader
SPEC.loader.exec_module(provenance)


class ProvenanceTests(unittest.TestCase):
    def fixture(self, root: Path):
        epub = root / "book.epub"
        epub.write_bytes(b"safe epub")
        digest = hashlib.sha256(epub.read_bytes()).hexdigest()
        manifest = root / "book.epub.provenance.json"
        manifest.write_text(json.dumps({
            "schema_version": 2,
            "builder_version": "1.0.0",
            "title": "Book",
            "source_repository": provenance.SOURCE_REPOSITORY,
            "source_branch": "master",
            "source_commit": "a" * 40,
            "source_commit_date": "2020-07-18T00:00:00Z",
            "builder_commit": "b" * 40,
            "build_date_utc": "2026-09-01T00:00:00+00:00",
            "epub_filename": epub.name,
            "epub_sha256": digest,
            "license": "CC-BY-NC-SA-4.0",
        }), encoding="utf-8")
        checksum = root / "book.epub.sha256"
        checksum.write_text(f"{digest}  {epub.name}\n", encoding="ascii")
        return epub, manifest, checksum

    def test_matching_release_files_pass(self):
        with tempfile.TemporaryDirectory() as folder:
            files = self.fixture(Path(folder))
            provenance.verify(*files, "master")

    def test_tampered_epub_is_rejected(self):
        with tempfile.TemporaryDirectory() as folder:
            files = self.fixture(Path(folder))
            files[0].write_bytes(b"tampered")
            with self.assertRaisesRegex(ValueError, "SHA-256"):
                provenance.verify(*files, "master")

    def test_wrong_source_branch_is_rejected(self):
        with tempfile.TemporaryDirectory() as folder:
            files = self.fixture(Path(folder))
            with self.assertRaisesRegex(ValueError, "source branch"):
                provenance.verify(*files, "release")

    def test_wrong_selected_commit_is_rejected(self):
        with tempfile.TemporaryDirectory() as folder:
            files = self.fixture(Path(folder))
            with self.assertRaisesRegex(ValueError, "selected by the build job"):
                provenance.verify(*files, "master", "c" * 40)

    def test_unexpected_field_is_rejected(self):
        with tempfile.TemporaryDirectory() as folder:
            epub, manifest, checksum = self.fixture(Path(folder))
            data = json.loads(manifest.read_text())
            data["untrusted"] = True
            manifest.write_text(json.dumps(data))
            with self.assertRaisesRegex(ValueError, "unexpected provenance"):
                provenance.verify(epub, manifest, checksum, "master")


if __name__ == "__main__":
    unittest.main()
