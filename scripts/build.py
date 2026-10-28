#!/usr/bin/env python3
"""Genera profile.json y CV_Abraham_Escalona.md desde content/."""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from lib.content import ROOT, load  # noqa: E402
from lib.render import render_cv, render_profile_json, render_readme  # noqa: E402


def main() -> int:
    content = load()
    if content.errors:
        print(f"❌ {len(content.errors)} error(es) en content/:\n")
        for error in content.errors:
            print(f"  - {error}")
        return 1

    data = render_profile_json(content)
    profile_path = ROOT / "profile.json"
    profile_path.write_text(
        json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )

    cv_path = ROOT / "CV_Abraham_Escalona.md"
    cv_path.write_text(render_cv(content), encoding="utf-8")

    readme_path = ROOT / "README.md"
    readme_path.write_text(render_readme(content), encoding="utf-8")

    print("✅ Generado")
    print(f"   {profile_path.relative_to(ROOT)}")
    print(f"   {cv_path.relative_to(ROOT)}")
    print(f"   {readme_path.relative_to(ROOT)}")
    print(f"   timeline: {len(data['timeline'])} entradas")
    print(f"   projects: {len(data['projects'])} entradas")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
