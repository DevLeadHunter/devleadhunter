"""Convert export interface to export type (skip extends) under web/app."""
from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1] / "web" / "app"
SKIP_DIRS = {"node_modules", ".nuxt"}


def convert_file(text: str) -> str:
    lines = text.split("\n")
    out: list[str] = []
    for line in lines:
        if re.match(r"^\s*export interface \w+.*\s+extends\s+", line):
            out.append(line)
            continue
        out.append(
            re.sub(
                r"^(\s*)export interface (\w+(?:<[^>]+>)?)\s*\{?\s*$",
                r"\1export type \2 = {",
                line,
            )
        )
    return "\n".join(out)


def main() -> None:
    changed: list[str] = []
    for path in sorted(ROOT.rglob("*.ts")):
        if any(part in SKIP_DIRS for part in path.parts):
            continue
        original = path.read_text(encoding="utf-8")
        updated = convert_file(original)
        if updated != original:
            path.write_text(updated, encoding="utf-8")
            changed.append(str(path.relative_to(ROOT)))
    print(f"Updated {len(changed)} files")
    for name in changed:
        print(f"  - {name}")


if __name__ == "__main__":
    main()
