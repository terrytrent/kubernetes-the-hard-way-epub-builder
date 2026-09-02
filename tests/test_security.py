import importlib.util
import tempfile
import unittest
from pathlib import Path
from zipfile import ZIP_STORED, ZipFile, ZipInfo


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("validate_epub", ROOT / "scripts" / "validate_epub.py")
validator = importlib.util.module_from_spec(SPEC)
assert SPEC.loader
SPEC.loader.exec_module(validator)

SAFE_TEXT = (
    "Source tag: 1.18.6 Source commit: abc This is an unofficial adaptation "
    "cover artwork is AI-generated Kubernetes® is a registered trademark "
    "not affiliated with, sponsored by, or endorsed by"
)


def make_epub(path: Path, extra_name=None, extra_data=b"", body_extra="", css=""):
    html = f'''<html xmlns="http://www.w3.org/1999/xhtml"><head><title>x</title></head>
    <body><h1>Book</h1><p>{SAFE_TEXT}</p><pre><code>echo safe</code></pre>{body_extra}</body></html>'''
    opf = '''<package xmlns="http://www.idpf.org/2007/opf" version="2.0"><metadata>
    <meta name="cover" content="cover"/></metadata><manifest>
    <item id="book" href="book.xhtml" media-type="application/xhtml+xml"/>
    <item id="cover" href="cover.png" media-type="image/png"/>
    </manifest><spine><itemref idref="book"/></spine></package>'''
    with ZipFile(path, "w") as archive:
        mimetype = ZipInfo("mimetype")
        mimetype.compress_type = ZIP_STORED
        archive.writestr(mimetype, b"application/epub+zip")
        archive.writestr("book.xhtml", html)
        archive.writestr("content.opf", opf)
        archive.writestr("cover.png", b"png")
        if css:
            archive.writestr("style.css", css)
        if extra_name:
            archive.writestr(extra_name, extra_data)


class SecurityValidationTests(unittest.TestCase):
    def scan(self, **kwargs):
        with tempfile.TemporaryDirectory() as folder:
            epub = Path(folder) / "book.epub"
            make_epub(epub, **kwargs)
            return validator.validate_epub(str(epub), "1.18.6")

    def assert_rejected(self, phrase, **kwargs):
        errors = self.scan(**kwargs)
        self.assertTrue(any(phrase in error for error in errors), errors)

    def test_clean_minimal_epub_passes_security_checks(self):
        self.assertEqual(self.scan(), [])

    def test_javascript_file_is_rejected(self):
        self.assert_rejected("executable file type", extra_name="payload.js", extra_data=b"alert(1)")

    def test_script_element_is_rejected(self):
        self.assert_rejected("active element <script>", body_extra="<script>alert(1)</script>")

    def test_event_handler_is_rejected(self):
        self.assert_rejected("active attribute onclick", body_extra='<p onclick="alert(1)">x</p>')

    def test_remote_embedded_image_is_rejected(self):
        self.assert_rejected("remote embedded resource", body_extra='<img src="https://attacker.invalid/x.png"/>')

    def test_unsafe_css_is_rejected(self):
        self.assert_rejected("unsafe or remote CSS", css='body { background: url("https://attacker.invalid/x"); }')

    def test_fixed_theme_color_is_rejected(self):
        self.assert_rejected("breaks reader themes", css="body { color: #eee; }")

    def test_remote_inline_style_is_rejected(self):
        self.assert_rejected(
            "unsafe inline CSS",
            body_extra='<p style="background:url(https://attacker.invalid/x)">x</p>',
        )

    def test_path_traversal_is_rejected(self):
        self.assert_rejected("unsafe ZIP member path", extra_name="../payload.txt", extra_data=b"x")

    def test_encryption_manifest_is_rejected(self):
        self.assert_rejected("encrypted content", extra_name="META-INF/encryption.xml", extra_data=b"<encryption/>")

    def test_svg_is_rejected(self):
        self.assert_rejected("active element <svg>", body_extra='<svg xmlns="http://www.w3.org/2000/svg"/>')

    def test_meta_refresh_is_rejected(self):
        self.assert_rejected(
            "HTTP-equivalent meta directive",
            body_extra='<meta http-equiv="refresh" content="0;url=https://attacker.invalid"/>',
        )


if __name__ == "__main__":
    unittest.main()
