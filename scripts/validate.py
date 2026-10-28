#!/usr/bin/env python3
"""Valida el contenido de content/ sin generar nada."""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from lib.content import load  # noqa: E402


def main() -> int:
    content = load()
    if content.errors:
        print(f"❌ {len(content.errors)} error(es) en content/:\n")
        for error in content.errors:
            print(f"  - {error}")
        return 1

    print("✅ content/ válido")
    print(f"   entradas: {len(content.entries)}")
    print(f"   grupos de skills: {len(content.skills)}")
    print(f"   skills: {sum(len(g['items']) for g in content.skills)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
