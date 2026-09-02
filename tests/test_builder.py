import importlib.util
import tempfile
import unittest
from pathlib import Path
from zipfile import ZIP_STORED, ZipFile


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("build_epub", ROOT / "scripts" / "build_epub.py")
build_epub = importlib.util.module_from_spec(SPEC)
assert SPEC.loader
SPEC.loader.exec_module(build_epub)


class BuilderTests(unittest.TestCase):
    def test_pipe_table_becomes_semantic_html(self):
        source = "| Name | CPU |\n|---|---:|\n| node | 2 |\n"
        result = build_epub.convert_pipe_tables(source)
        self.assertIn("<table>", result)
        self.assertIn("<th>Name</th>", result)
        self.assertIn("<td>node</td>", result)

    def test_markdown_links_become_chapter_links(self):
        result = build_epub.rewrite_links(
            "See [Workers](09-workers.md#install).", Path("docs/08-control.md")
        )
        self.assertEqual(result, "See [Workers](#chapter-09-workers).")

    def test_fenced_active_markup_is_safe_as_an_example(self):
        build_epub.validate_source_safety(
            "```html\n<script>alert(1)</script>\n```", "example.md"
        )

    def test_active_raw_markup_is_rejected(self):
        threats = [
            "<script>alert(1)</script>",
            '<img src="https://attacker.invalid/pixel">',
            '<p onclick="alert(1)">x</p>',
            '<iframe src="https://attacker.invalid"></iframe>',
            '<a href="javascript:alert(1)">x</a>',
            "<!ENTITY xxe SYSTEM 'file:///etc/passwd'>",
        ]
        for threat in threats:
            with self.subTest(threat=threat), self.assertRaises(ValueError):
                build_epub.validate_source_safety(threat, "unsafe.md")

    def test_remote_markdown_image_is_rejected(self):
        with self.assertRaises(ValueError):
            build_epub.validate_source_safety(
                "![tracking](https://attacker.invalid/pixel.png)", "unsafe.md"
            )

    def test_tag_input_rejects_path_characters(self):
        self.assertIsNotNone(build_epub.re.fullmatch(r"[0-9A-Za-z][0-9A-Za-z._-]*", "1.18.6"))
        self.assertIsNone(build_epub.re.fullmatch(r"[0-9A-Za-z][0-9A-Za-z._-]*", "../main"))

    def test_png_dimensions_are_checked_without_decoding(self):
        png = b"\x89PNG\r\n\x1a\n" + b"\x00" * 8 + (10).to_bytes(4, "big") + (20).to_bytes(4, "big")
        build_epub.validate_image_bytes(png, "safe.png")

    def test_unsupported_image_is_rejected(self):
        with self.assertRaises(ValueError):
            build_epub.validate_image_bytes(b"<svg/>", "unsafe.svg")

    def test_direct_epub_package_is_complete_and_reproducible(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            cover = root / "cover.png"
            cover.write_bytes(b"\x89PNG\r\n\x1a\nfixture")
            first = root / "first.epub"
            second = root / "second.epub"
            arguments = dict(
                body='<h1 id="book-introduction">Book</h1><pre><code>safe</code></pre>',
                cover=cover,
                source_ref="1.18.6",
                revision="a" * 40,
                source_date="2020-07-18T00:00:00Z",
                source_epoch=1_595_030_400,
                images={"diagram.png": b"fixture"},
                toc=[("book-introduction", "Book")],
            )
            build_epub.write_epub(first, **arguments)
            build_epub.write_epub(second, **arguments)
            self.assertEqual(first.read_bytes(), second.read_bytes())
            with ZipFile(first) as archive:
                self.assertEqual(archive.namelist()[0], "mimetype")
                self.assertEqual(archive.getinfo("mimetype").compress_type, ZIP_STORED)
                self.assertEqual(archive.read("mimetype"), b"application/epub+zip")
                for required in (
                    "META-INF/container.xml", "OEBPS/package.opf",
                    "OEBPS/content.xhtml", "OEBPS/nav.xhtml",
                    "OEBPS/cover.xhtml", "OEBPS/styles/epub.css",
                    "OEBPS/images/cover.png", "OEBPS/images/diagram.png",
                ):
                    self.assertIn(required, archive.namelist())


if __name__ == "__main__":
    unittest.main()
