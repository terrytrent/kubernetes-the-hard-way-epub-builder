#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import sys
from pathlib import Path


path = Path(sys.argv[1])
digest = hashlib.sha256(path.read_bytes()).hexdigest()
path.with_suffix(path.suffix + ".sha256").write_text(
    f"{digest}  {path.name}\n", encoding="ascii"
)
