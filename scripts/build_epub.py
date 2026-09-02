#!/usr/bin/env python3
"""Build a reading-oriented EPUB from the upstream Markdown labs."""

from __future__ import annotations

import argparse
import hashlib
import html
import json
import re
import struct
import subprocess
import zipfile
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SOURCE_URL = "https://github.com/kelseyhightower/kubernetes-the-hard-way"
SOURCE_REPO = ROOT / "build" / "upstream"
SOURCE_REF = "master"
ACTIVE_SOURCE_PATTERNS = (
    r"<\s*(?:script|iframe|object|embed|form|input|button|textarea|select|link|meta|base|img|svg|math|style)\b",
    r"\bon[a-z]+\s*=",
    r"(?:javascript|vbscript)\s*:",
    r"<!\s*(?:doctype|entity)",
    r"<\?xml",
)
MAX_IMAGE_BYTES = 20 * 1024 * 1024
MAX_IMAGE_PIXELS = 25_000_000


def git_text(source_repo: Path, source_ref: str, path: str) -> str:
    return subprocess.check_output(
        ["git", "show", f"{source_ref}:{path}"], cwd=source_repo
    ).decode("utf-8")


def resolve_source_revision(source_repo: Path, source_ref: str) -> str:
    if source_ref != "master":
        raise ValueError("Only the upstream default branch (master) is supported")
    return subprocess.check_output(
        ["git", "rev-parse", "refs/remotes/origin/master^{commit}"],
        cwd=source_repo,
        text=True,
    ).strip()


def source_documents(source_repo: Path, source_ref: str) -> list[str]:
    readme = git_text(source_repo, source_ref, "README.md")
    labs = readme.split("## Labs", 1)
    if len(labs) != 2:
        raise ValueError("Upstream README has no Labs section")
    documents = re.findall(r"\[[^]]+\]\((docs/[^)#]+\.md)(?:#[^)]+)?\)", labs[1])
    if not documents or len(documents) != len(set(documents)):
        raise ValueError("Upstream README has no labs or contains duplicate lab links")
    for document in documents:
        subprocess.run(
            ["git", "cat-file", "-e", f"{source_ref}:{document}"],
            cwd=source_repo,
            check=True,
        )
    return documents


def validate_source_safety(text: str, source_name: str) -> None:
    """Reject active raw markup outside fenced examples before conversion."""
    without_fences = re.sub(
        r"^```[^\n]*\n.*?^```[ \t]*$", "", text, flags=re.MULTILINE | re.DOTALL
    )
    for pattern in ACTIVE_SOURCE_PATTERNS:
        if re.search(pattern, without_fences, flags=re.IGNORECASE):
            raise ValueError(f"Unsafe active markup in {source_name}: {pattern}")
    for _label, target in re.findall(r"!\[([^]]*)\]\(([^)]+)\)", without_fences):
        path = target.partition("#")[0]
        if ":" in path or path.startswith(("/", "..")):
            raise ValueError(f"Remote or unsafe image reference in {source_name}: {target}")


def validate_image_bytes(data: bytes, source_name: str) -> None:
    """Accept bounded PNG/JPEG/GIF raster images without invoking an image codec."""
    if len(data) > MAX_IMAGE_BYTES:
        raise ValueError(f"Image exceeds size limit: {source_name}")
    width = height = 0
    if data.startswith(b"\x89PNG\r\n\x1a\n") and len(data) >= 24:
        width, height = struct.unpack(">II", data[16:24])
    elif data.startswith((b"GIF87a", b"GIF89a")) and len(data) >= 10:
        width, height = struct.unpack("<HH", data[6:10])
    elif data.startswith(b"\xff\xd8"):
        index = 2
        while index + 9 < len(data):
            if data[index] != 0xFF:
                index += 1
                continue
            marker = data[index + 1]
            index += 2
            if marker in {0xD8, 0xD9}:
                continue
            if index + 2 > len(data):
                break
            length = int.from_bytes(data[index:index + 2], "big")
            if marker in {0xC0, 0xC1, 0xC2, 0xC3, 0xC5, 0xC6, 0xC7, 0xC9, 0xCA, 0xCB, 0xCD, 0xCE, 0xCF} and index + 7 <= len(data):
                height = int.from_bytes(data[index + 3:index + 5], "big")
                width = int.from_bytes(data[index + 5:index + 7], "big")
                break
            if length < 2:
                break
            index += length
    else:
        raise ValueError(f"Unsupported or malformed raster image: {source_name}")
    if not width or not height or width * height > MAX_IMAGE_PIXELS:
        raise ValueError(f"Invalid or excessive image dimensions in {source_name}: {width}x{height}")


def slug(path: str | Path) -> str:
    # EPUB 2 IDs are XML Names, so an ID cannot begin with the numeric lab
    # prefix used by upstream filenames (for example, 01-prerequisites).
    return f"chapter-{Path(path).stem}"


def rewrite_links(text: str, source: Path) -> str:
    def replace(match: re.Match[str]) -> str:
        label, target = match.group(1), match.group(2)
        path, _marker, _fragment = target.partition("#")
        if not path.endswith(".md"):
            return match.group(0)
        if path == "../README.md":
            destination = "book-introduction"
        else:
            destination = slug(path)
        return f"[{label}](#{destination})"

    return re.sub(r"\[([^]]+)\]\(([^)]+)\)", replace, text)


def source_markdown(source_repo: Path, source_ref: str, revision: str) -> str:
    readme = git_text(source_repo, revision, "README.md")
    readme = re.sub(r"<a rel=.+?</a><br\s*/?>", "", readme, flags=re.DOTALL)
    validate_source_safety(readme, "README.md")
    introduction = readme.split("## Labs", 1)[0]
    parts = [
        '<a id="book-introduction"></a>',
        introduction.strip(),
        "",
        '<p class="edition-note">This EPUB is a reading-format adaptation of '
        '<em>Kubernetes The Hard Way</em> by Kelsey Hightower. '
        "Commands and technical content remain those of the upstream project. "
        "This is an unofficial adaptation and is not affiliated with, sponsored "
        "by, or endorsed by the Linux Foundation, the Cloud Native Computing "
        "Foundation, the Kubernetes project, or Kelsey Hightower.</p>",
        "",
        "## Edition source",
        "",
        f"- Repository: [{SOURCE_URL}]({SOURCE_URL})",
        f"- Upstream branch: `{source_ref}`",
        f"- Commit: `{revision}`",
    ]
    for document in source_documents(source_repo, revision):
        text = git_text(source_repo, revision, document)
        validate_source_safety(text, document)
        text = re.sub(r"(?m)^Next:\s*\[[^]]+\]\([^)]+\)\s*$", "", text)
        text = rewrite_links(text, Path(document))
        parts.extend([
            "",
            '<div class="chapter-break"></div>',
            f'<a id="{slug(document)}"></a>',
            text.strip(),
        ])
    copyright_text = git_text(source_repo, revision, "COPYRIGHT.md")
    copyright_text = re.sub(r"<a rel=.+?</a><br\s*/?>", "", copyright_text, flags=re.DOTALL)
    validate_source_safety(copyright_text, "COPYRIGHT.md")
    parts.extend([
        "",
        '<div class="chapter-break"></div>',
        '<a id="license-and-attribution"></a>',
        copyright_text.strip(),
        "",
        "This EPUB adaptation is distributed under the same "
        "[Creative Commons Attribution-NonCommercial-ShareAlike 4.0 International License]"
        "(https://creativecommons.org/licenses/by-nc-sa/4.0/).",
        "",
        f"Upstream source: {SOURCE_URL}",
        f"Source branch: {source_ref}",
        f"Source commit: {revision}",
        "",
        "## Adaptation and trademark notice",
        "",
        "This unofficial EPUB adaptation is provided free of charge. Its cover "
        "artwork is AI-generated and uses a stylized Kubernetes helm mark for a "
        "noncommercial educational publication.",
        "",
        "Kubernetes® is a registered trademark of The Linux Foundation in the "
        "United States and other countries. This publication is not affiliated "
        "with, sponsored by, or endorsed by The Linux Foundation, the Cloud "
        "Native Computing Foundation, or the Kubernetes project.",
        "",
        "Trademark usage guidance: "
        "https://www.linuxfoundation.org/legal/tm-usage",
    ])
    return "\n".join(parts) + "\n"


def protect_fenced_code(text: str) -> str:
    """Turn GitHub-style fences into escaped HTML code blocks."""
    def replace(match: re.Match[str]) -> str:
        language = re.sub(r"[^a-zA-Z0-9_-]", "", match.group(1).strip())
        class_name = f' class="language-{language}"' if language else ""
        return f"\n<pre><code{class_name}>{html.escape(match.group(2))}</code></pre>\n"

    return re.sub(r"^```([^\n]*)\n(.*?)^```[ \t]*$", replace, text, flags=re.MULTILINE | re.DOTALL)


def convert_pipe_tables(text: str) -> str:
    """Convert GitHub-style pipe tables into semantic HTML."""
    lines = text.splitlines()
    output: list[str] = []
    index = 0

    def cells(line: str) -> list[str]:
        return [cell.strip() for cell in line.strip().strip("|").split("|")]

    def separator(line: str) -> bool:
        parts = cells(line)
        return bool(parts) and all(re.fullmatch(r":?-{3,}:?", part) for part in parts)

    while index < len(lines):
        if index + 1 < len(lines) and "|" in lines[index] and separator(lines[index + 1]):
            headers = cells(lines[index])
            rows: list[list[str]] = []
            index += 2
            while index < len(lines) and "|" in lines[index] and lines[index].strip():
                rows.append(cells(lines[index]))
                index += 1
            table = ["<table>", "<thead><tr>"]
            table.extend(f"<th>{html.escape(cell)}</th>" for cell in headers)
            table.extend(["</tr></thead>", "<tbody>"])
            for row in rows:
                padded = (row + [""] * len(headers))[:len(headers)]
                table.append("<tr>" + "".join(f"<td>{html.escape(cell)}</td>" for cell in padded) + "</tr>")
            table.extend(["</tbody>", "</table>"])
            output.extend(table)
            continue
        output.append(lines[index])
        index += 1
    return "\n".join(output)


def zip_info(name: str, source_epoch: int, *, stored: bool = False) -> zipfile.ZipInfo:
    # ZIP timestamps cannot represent dates before 1980 and use local-time-shaped tuples.
    stamp = datetime.fromtimestamp(max(source_epoch, 315532800), timezone.utc)
    info = zipfile.ZipInfo(name, stamp.timetuple()[:6])
    info.compress_type = zipfile.ZIP_STORED if stored else zipfile.ZIP_DEFLATED
    info.external_attr = 0o100644 << 16
    info.create_system = 3
    return info


def xhtml_page(title: str, body: str, *, stylesheet: bool = True) -> bytes:
    css = '<link rel="stylesheet" type="text/css" href="styles/epub.css" />' if stylesheet else ""
    document = (
        '<?xml version="1.0" encoding="utf-8"?>\n'
        '<html xmlns="http://www.w3.org/1999/xhtml" lang="en" xml:lang="en">'
        f'<head><title>{html.escape(title)}</title>{css}</head><body>{body}</body></html>'
    )
    return document.encode("utf-8")


def write_epub(
    output: Path,
    body: str,
    cover: Path,
    source_ref: str,
    revision: str,
    source_date: str,
    source_epoch: int,
    images: dict[str, bytes],
    toc: list[tuple[str, str]],
) -> None:
    title = "Kubernetes The Hard Way — Unofficial EPUB Adaptation"
    identifier = f"{SOURCE_URL}/tree/{revision}"
    modified = datetime.fromtimestamp(source_epoch, timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    cover_suffix = cover.suffix.lower()
    cover_type = "image/png" if cover_suffix == ".png" else "image/jpeg"
    cover_name = f"images/cover{cover_suffix}"
    image_items = []
    for index, name in enumerate(sorted(images), 1):
        media = {".png": "image/png", ".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".gif": "image/gif"}[Path(name).suffix.lower()]
        image_items.append(f'<item id="image-{index}" href="images/{html.escape(name)}" media-type="{media}" />')
    package = f'''<?xml version="1.0" encoding="utf-8"?>
<package xmlns="http://www.idpf.org/2007/opf" version="3.0" unique-identifier="book-id" xml:lang="en">
<metadata xmlns:dc="http://purl.org/dc/elements/1.1/">
<dc:identifier id="book-id">{html.escape(identifier)}</dc:identifier>
<dc:title>{html.escape(title)}</dc:title><dc:creator>Kelsey Hightower</dc:creator>
<dc:language>en</dc:language><dc:date>{html.escape(source_date[:10])}</dc:date>
<dc:rights>CC BY-NC-SA 4.0</dc:rights><meta property="dcterms:modified">{modified}</meta>
<meta name="cover" content="cover-image" />
</metadata><manifest>
<item id="content" href="content.xhtml" media-type="application/xhtml+xml" />
<item id="cover-page" href="cover.xhtml" media-type="application/xhtml+xml" />
<item id="nav" href="nav.xhtml" media-type="application/xhtml+xml" properties="nav" />
<item id="css" href="styles/epub.css" media-type="text/css" />
<item id="cover-image" href="{cover_name}" media-type="{cover_type}" properties="cover-image" />
{''.join(image_items)}</manifest>
<spine><itemref idref="cover-page" linear="yes" /><itemref idref="content" /></spine>
</package>'''
    nav_items = "".join(
        f'<li><a href="content.xhtml#{html.escape(anchor)}">{html.escape(label)}</a></li>'
        for anchor, label in toc
    )
    nav = xhtml_page(title, f'<nav xmlns:epub="http://www.idpf.org/2007/ops" epub:type="toc" id="toc"><h2>Contents</h2><ol>{nav_items}</ol></nav>')
    cover_body = f'<section class="cover" epub:type="cover" xmlns:epub="http://www.idpf.org/2007/ops"><img src="{cover_name}" alt="Cover of {html.escape(title)}" /></section>'
    container = b'''<?xml version="1.0" encoding="UTF-8"?>
<container version="1.0" xmlns="urn:oasis:names:tc:opendocument:xmlns:container"><rootfiles><rootfile full-path="OEBPS/package.opf" media-type="application/oebps-package+xml" /></rootfiles></container>'''
    output.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(output, "w") as archive:
        archive.writestr(zip_info("mimetype", source_epoch, stored=True), b"application/epub+zip")
        archive.writestr(zip_info("META-INF/container.xml", source_epoch), container)
        archive.writestr(zip_info("OEBPS/package.opf", source_epoch), package.encode("utf-8"))
        archive.writestr(zip_info("OEBPS/content.xhtml", source_epoch), xhtml_page(title, body))
        archive.writestr(zip_info("OEBPS/nav.xhtml", source_epoch), nav)
        archive.writestr(zip_info("OEBPS/cover.xhtml", source_epoch), xhtml_page(title, cover_body))
        archive.writestr(zip_info("OEBPS/styles/epub.css", source_epoch), (ROOT / "epub.css").read_bytes())
        archive.writestr(zip_info(f"OEBPS/{cover_name}", source_epoch), cover.read_bytes())
        for name, data in sorted(images.items()):
            archive.writestr(zip_info(f"OEBPS/images/{name}", source_epoch), data)


def main() -> None:
    import markdown

    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--cover",
        type=Path,
        default=ROOT / "assets" / "cover.png",
        help="PNG or JPEG cover image (default: assets/cover.png)",
    )
    parser.add_argument("--source-repo", type=Path, default=SOURCE_REPO)
    parser.add_argument("--source-ref", default=SOURCE_REF)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()

    if args.source_ref != "master":
        raise SystemExit("Only --source-ref master is supported")

    if args.cover and not args.cover.is_file():
        raise SystemExit(f"Cover image not found: {args.cover}")
    if args.cover:
        validate_image_bytes(args.cover.read_bytes(), str(args.cover))
    source_repo = args.source_repo.resolve()
    if not (source_repo / ".git").exists():
        raise SystemExit(f"Upstream Git repository not found: {source_repo}")
    output = args.output or ROOT / "dist" / f"kubernetes-the-hard-way-{args.source_ref}.epub"

    revision = resolve_source_revision(source_repo, args.source_ref)
    source_date = subprocess.check_output(
        ["git", "show", "-s", "--format=%cI", revision], cwd=source_repo, text=True
    ).strip()
    build_dir = ROOT / "build"
    build_dir.mkdir(exist_ok=True)
    images: dict[str, bytes] = {}
    image_paths = subprocess.check_output(
        ["git", "ls-tree", "-r", "--name-only", revision, "docs/images"],
        cwd=source_repo,
        text=True,
    ).splitlines()
    for image_path in image_paths:
        relative = Path(image_path).relative_to("docs/images")
        image_data = subprocess.check_output(["git", "show", f"{revision}:{image_path}"], cwd=source_repo)
        validate_image_bytes(image_data, image_path)
        images[relative.as_posix()] = image_data
    output.parent.mkdir(parents=True, exist_ok=True)
    combined = build_dir / "book.html"
    source = source_markdown(source_repo, args.source_ref, revision)
    body = markdown.markdown(convert_pipe_tables(protect_fenced_code(source)), output_format="xhtml")
    combined.write_text(
        '<!DOCTYPE html><html lang="en"><head><meta charset="utf-8" />'
        "<title>Kubernetes The Hard Way</title></head><body>"
        + body
        + "</body></html>",
        encoding="utf-8",
    )

    source_epoch = int(subprocess.check_output(
        ["git", "show", "-s", "--format=%ct", revision], cwd=source_repo, text=True
    ).strip())
    toc = [("book-introduction", "Kubernetes The Hard Way")]
    for document in source_documents(source_repo, revision):
        chapter = git_text(source_repo, revision, document)
        heading = re.search(r"(?m)^#\s+(.+?)\s*$", chapter)
        toc.append((slug(document), heading.group(1) if heading else Path(document).stem))
    toc.append(("license-and-attribution", "Copyright and attribution"))
    write_epub(
        output, body, args.cover, args.source_ref, revision, source_date,
        source_epoch, images, toc,
    )

    builder_commit = subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=ROOT, text=True, capture_output=True
    )
    manifest = {
        "schema_version": 2,
        "builder_version": (ROOT / "VERSION").read_text(encoding="utf-8").strip(),
        "title": "Kubernetes The Hard Way — Unofficial EPUB Adaptation",
        "source_repository": SOURCE_URL,
        "source_branch": args.source_ref,
        "source_commit": revision,
        "source_commit_date": source_date,
        "builder_commit": builder_commit.stdout.strip() if builder_commit.returncode == 0 else "uncommitted",
        "build_date_utc": datetime.now(timezone.utc).isoformat(),
        "epub_filename": output.name,
        "epub_sha256": hashlib.sha256(output.read_bytes()).hexdigest(),
        "license": "CC-BY-NC-SA-4.0",
    }
    output.with_suffix(output.suffix + ".provenance.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    print(output)


if __name__ == "__main__":
    main()
