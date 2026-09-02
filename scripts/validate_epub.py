#!/usr/bin/env python3
"""Validate a generated EPUB's structure and provenance."""

from __future__ import annotations

import argparse
import re
import stat
import subprocess
from pathlib import PurePosixPath
from urllib.parse import urlsplit
from xml.etree import ElementTree as ET
from zipfile import ZIP_STORED, ZipFile


XHTML = {"x": "http://www.w3.org/1999/xhtml"}
OPF = {"opf": "http://www.idpf.org/2007/opf"}
ACTIVE_ELEMENTS = {"script", "iframe", "object", "embed", "form", "input", "button", "textarea", "select", "canvas", "audio", "video", "source", "track", "svg", "math", "applet"}
EXECUTABLE_SUFFIXES = {".js", ".mjs", ".cjs", ".wasm", ".exe", ".dll", ".so", ".dylib", ".sh", ".bash", ".zsh", ".bat", ".cmd", ".ps1", ".py", ".rb", ".pl", ".php", ".jar", ".class", ".com", ".scr", ".msi"}
SCRIPT_MEDIA_TYPES = {"application/javascript", "application/ecmascript", "application/wasm", "text/javascript", "text/ecmascript", "image/svg+xml"}
XML_SUFFIXES = {".html", ".xhtml", ".xml", ".opf", ".ncx"}
MAX_MEMBERS = 2_000
MAX_MEMBER_BYTES = 25 * 1024 * 1024
MAX_TOTAL_BYTES = 150 * 1024 * 1024
MAX_COMPRESSION_RATIO = 200


def local_name(name: str) -> str:
    return name.rsplit("}", 1)[-1].lower()


def read_revision(source_repo: str, revision: str, path: str) -> str:
    return subprocess.check_output(["git", "show", f"{revision}:{path}"], cwd=source_repo, text=True)


def expected_source(source_repo: str, source_ref: str) -> tuple[int, set[str], str]:
    if source_ref != "master":
        raise ValueError("only the upstream default branch (master) is supported")
    commit = subprocess.check_output(
        ["git", "rev-parse", "refs/remotes/origin/master^{commit}"],
        cwd=source_repo,
        text=True,
    ).strip()
    readme = read_revision(source_repo, commit, "README.md")
    labs = readme.split("## Labs", 1)
    if len(labs) != 2:
        raise ValueError("upstream master README has no Labs section")
    documents = re.findall(r"\[[^]]+\]\((docs/[^)#]+\.md)(?:#[^)]+)?\)", labs[1])
    if not documents:
        raise ValueError("upstream master README lists no labs")
    images: set[str] = set()
    for document in documents:
        markdown = read_revision(source_repo, commit, document)
        for target in re.findall(r"!\[[^]]*\]\(([^)]+)\)", markdown):
            path = target.partition("#")[0]
            if ":" not in path:
                images.add(PurePosixPath(path).name)
    return len(documents), images, commit


def validate_epub(epub: str, source_ref: str, source_repo: str | None = None) -> list[str]:
    errors: list[str] = []
    try:
        archive = ZipFile(epub)
    except Exception as exc:
        return [f"cannot open EPUB ZIP: {exc}"]
    with archive:
        infos = archive.infolist()
        names = [info.filename for info in infos]
        if len(infos) > MAX_MEMBERS:
            errors.append(f"too many ZIP members: {len(infos)}")
        if len(names) != len(set(names)):
            errors.append("duplicate ZIP member names")
        total_size = 0
        for info in infos:
            total_size += info.file_size
            path = PurePosixPath(info.filename)
            if info.filename.startswith(("/", "\\")) or "\\" in info.filename or ".." in path.parts:
                errors.append(f"unsafe ZIP member path: {info.filename}")
            if info.flag_bits & 0x1:
                errors.append(f"encrypted ZIP member: {info.filename}")
            if stat.S_ISLNK(info.external_attr >> 16):
                errors.append(f"symbolic link ZIP member: {info.filename}")
            if info.file_size > MAX_MEMBER_BYTES:
                errors.append(f"oversized ZIP member: {info.filename}")
            if info.compress_size and info.file_size / info.compress_size > MAX_COMPRESSION_RATIO:
                errors.append(f"excessive compression ratio: {info.filename}")
            if path.suffix.lower() in EXECUTABLE_SUFFIXES:
                errors.append(f"executable file type is forbidden: {info.filename}")
        if total_size > MAX_TOTAL_BYTES:
            errors.append(f"EPUB uncompressed size exceeds limit: {total_size}")
        if not infos or infos[0].filename != "mimetype":
            errors.append("mimetype is not the first archive member")
        elif infos[0].compress_type != ZIP_STORED:
            errors.append("mimetype must be stored without compression")
        if "mimetype" not in names or archive.read("mimetype") != b"application/epub+zip":
            errors.append("invalid EPUB mimetype")
        if "META-INF/encryption.xml" in names:
            errors.append("encrypted content is forbidden")

        documents: dict[str, tuple[ET.Element, set[str]]] = {}
        all_text: list[str] = []
        code_blocks = 0
        h1_count = 0
        for info in infos:
            suffix = PurePosixPath(info.filename).suffix.lower()
            if suffix in XML_SUFFIXES:
                raw = archive.read(info.filename)
                lowered = raw.lower()
                if b"<!doctype" in lowered or b"<!entity" in lowered:
                    errors.append(f"DTD/entity declaration is forbidden: {info.filename}")
                try:
                    root = ET.fromstring(raw)
                except ET.ParseError as exc:
                    errors.append(f"malformed XML/XHTML in {info.filename}: {exc}")
                    continue
                if suffix not in {".html", ".xhtml"}:
                    for node in root.iter():
                        for attribute, value in node.attrib.items():
                            if local_name(attribute) in {"href", "src", "data", "action"} and urlsplit(value.strip()).scheme:
                                errors.append(f"remote/active XML resource is forbidden: {info.filename}")
                if suffix in {".html", ".xhtml"}:
                    ids = {node.get("id") for node in root.iter() if node.get("id")}
                    documents[info.filename] = (root, ids)
                    all_text.append(" ".join(root.itertext()))
                    code_blocks += len(root.findall(".//x:pre/x:code", XHTML))
                    h1_count += len(root.findall(".//x:h1", XHTML))
                    for node in root.iter():
                        element = local_name(node.tag)
                        if element in ACTIVE_ELEMENTS:
                            errors.append(f"active element <{element}> is forbidden: {info.filename}")
                        for attribute, value in node.attrib.items():
                            attr = local_name(attribute)
                            clean_value = value.strip().lower()
                            if attr.startswith("on") or attr in {"srcdoc", "formaction"}:
                                errors.append(f"active attribute {attr} is forbidden: {info.filename}")
                            if attr in {"href", "src", "poster", "data", "action"}:
                                scheme = urlsplit(clean_value).scheme
                                if scheme in {"javascript", "vbscript", "data", "file"}:
                                    errors.append(f"unsafe URL scheme in {info.filename}: {scheme}")
                                if attr != "href" and scheme:
                                    errors.append(f"remote embedded resource is forbidden: {info.filename}")
                                if attr != "href" and not scheme and clean_value:
                                    target = str(PurePosixPath(info.filename).parent / clean_value.partition("#")[0])
                                    if target not in names:
                                        errors.append(f"missing embedded resource: {info.filename} -> {value}")
                            if attr == "style" and re.search(r"expression\s*\(|(?:javascript|vbscript|data)\s*:|url\s*\(\s*['\"]?https?://", clean_value, re.I):
                                errors.append(f"unsafe inline CSS is forbidden: {info.filename}")
                            if element == "meta" and attr == "http-equiv" and clean_value != "content-type":
                                errors.append(f"HTTP-equivalent meta directive is forbidden: {info.filename}")
                            if element == "link" and attr == "href" and urlsplit(clean_value).scheme:
                                errors.append(f"remote stylesheet is forbidden: {info.filename}")
            elif suffix == ".css":
                css = archive.read(info.filename).decode("utf-8", "replace")
                if re.search(r"@import|expression\s*\(|-moz-binding|(?:javascript|vbscript|data)\s*:|url\s*\(\s*['\"]?https?://", css, re.I):
                    errors.append(f"unsafe or remote CSS is forbidden: {info.filename}")
                for declaration in re.finditer(r"(?<![-\w])(?:color|background(?:-color)?)\s*:\s*([^;}]+)", css, re.I):
                    value = declaration.group(1).strip().lower()
                    if not value.startswith(("inherit", "transparent", "currentcolor")):
                        errors.append(f"fixed foreground/background color breaks reader themes: {info.filename}")
                        break

        for name, (root, _) in documents.items():
            for anchor in root.findall(".//x:a", XHTML):
                href = anchor.get("href", "")
                if not href or urlsplit(href).scheme in {"http", "https", "mailto"}:
                    continue
                filename, marker, fragment = href.partition("#")
                target = str(PurePosixPath(name).parent / filename) if filename else name
                if target not in documents:
                    errors.append(f"broken internal link: {name} -> {href}")
                elif marker and fragment and fragment not in documents[target][1]:
                    errors.append(f"broken fragment: {name} -> {href}")

        text = " ".join(all_text)
        for required in (f"Source branch: {source_ref}", "This is an unofficial adaptation", "cover artwork is AI-generated", "Kubernetes® is a registered trademark", "not affiliated with, sponsored by, or endorsed by"):
            if required not in text:
                errors.append(f"required provenance/disclosure text is absent: {required}")
        if "Next:" in text:
            errors.append("chapter-ending Next link remains")
        if code_blocks == 0:
            errors.append("no code blocks found")

        opf_name = next((name for name in names if name.endswith(".opf")), None)
        if not opf_name:
            errors.append("package document is missing")
        else:
            try:
                opf = ET.fromstring(archive.read(opf_name))
                if opf.find(".//opf:metadata/opf:meta[@name='cover']", OPF) is None:
                    errors.append("cover metadata is missing")
                for item in opf.findall(".//opf:manifest/opf:item", OPF):
                    media_type = (item.get("media-type") or "").lower()
                    properties = (item.get("properties") or "").lower().split()
                    href = item.get("href") or ""
                    if media_type in SCRIPT_MEDIA_TYPES or "scripted" in properties:
                        errors.append(f"scripted/active manifest item is forbidden: {href}")
                    if urlsplit(href).scheme:
                        errors.append(f"remote manifest resource is forbidden: {href}")
            except ET.ParseError:
                pass

        if source_repo:
            try:
                lab_count, expected_images, commit = expected_source(source_repo, source_ref)
                if h1_count != lab_count + 2:
                    errors.append(f"chapter count mismatch: expected {lab_count + 2}, found {h1_count}")
                archived_basenames = {PurePosixPath(name).name for name in names}
                missing_images = expected_images - archived_basenames
                if missing_images:
                    errors.append("missing referenced images: " + ", ".join(sorted(missing_images)))
                if f"Source commit: {commit}" not in text:
                    errors.append("exact source commit is absent from book content")
            except (subprocess.CalledProcessError, ValueError) as exc:
                errors.append(f"cannot verify source completeness: {exc}")
    return errors


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("epub")
    parser.add_argument("--ref", required=True)
    parser.add_argument("--source-repo")
    args = parser.parse_args()
    errors = validate_epub(args.epub, args.ref, args.source_repo)
    if errors:
        raise SystemExit("EPUB validation failed:\n- " + "\n- ".join(errors))
    print(f"Validated {args.epub} for upstream branch {args.ref}")


if __name__ == "__main__":
    main()
