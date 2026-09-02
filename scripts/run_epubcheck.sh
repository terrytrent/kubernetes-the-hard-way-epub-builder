#!/bin/sh
set -eu

jar=$1
epub=$2

if command -v docker >/dev/null 2>&1; then
  image='eclipse-temurin@sha256:7a65df4b22d2de92d4e04056e884f3b9122d70b21e2847fd66084278bd0ce037'
  exec docker run --rm --network none \
    --read-only --cap-drop ALL --security-opt no-new-privileges \
    --tmpfs /tmp:rw,noexec,nosuid,size=64m \
    --user 65534:65534 -v "$PWD:/work:ro" -w /work \
    "$image" java -jar "$jar" "$epub"
fi

if command -v java >/dev/null 2>&1 && java -version >/dev/null 2>&1; then
  exec java -jar "$jar" "$epub"
fi

echo "EPUBCheck requires Java or Docker" >&2
exit 1
