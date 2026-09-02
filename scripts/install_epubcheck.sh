#!/bin/sh
set -eu

version=5.3.0
archive="epubcheck-$version.zip"
expected=6c07e68584b2e2ce2f89fe06e1246dfead3eb36b46b340e7d93524f29dcff6c5
tools_dir=.tools
destination="$tools_dir/epubcheck-$version"

test -f "$destination/epubcheck.jar" && exit 0
mkdir -p "$tools_dir"
curl --fail --location --proto '=https' --tlsv1.2 \
  --output "$tools_dir/$archive" \
  "https://github.com/w3c/epubcheck/releases/download/v$version/$archive"
python3 - "$tools_dir/$archive" "$expected" <<'PY'
import hashlib
import pathlib
import sys
path = pathlib.Path(sys.argv[1])
actual = hashlib.sha256(path.read_bytes()).hexdigest()
if actual != sys.argv[2]:
    raise SystemExit(f"EPUBCheck checksum mismatch: {actual}")
PY
rm -rf "$destination"
unzip -q "$tools_dir/$archive" -d "$tools_dir"
rm "$tools_dir/$archive"
test -f "$destination/epubcheck.jar"
