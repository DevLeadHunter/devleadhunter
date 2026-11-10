"""Print the pip requirements of the product modules pinned in ``product-modules.json``.

Each module's ``api/`` folder is a Python distribution installed from its GitHub repository at the pinned tag::

    python api/scripts/product_module_requirements.py > api/product-module-requirements.txt
    pip install -r api/product-module-requirements.txt

The deploy and desktop-release workflows run it, so ``product-modules.json`` stays the only place a module's version
is bumped. To work on a module locally, install your clone instead: ``pip install -e ../<module-repo>/api``.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

_MANIFEST: Path = Path(__file__).resolve().parents[2] / "product-modules.json"


def requirement_lines(manifest_path: Path = _MANIFEST) -> list[str]:
    """
    The pip requirement of every pinned module that has a Python distribution.

    Args:
        manifest_path: The ``product-modules.json`` to read.

    Returns:
        One ``<distribution> @ git+https://github.com/<repository>@<ref>#subdirectory=api`` line per module.
    """
    manifest: dict[str, list[dict[str, object]]] = json.loads(manifest_path.read_text(encoding="utf-8"))
    return [
        f"{module['python_distribution']} @ git+https://github.com/{module['repository']}@{module['ref']}"
        "#subdirectory=api"
        for module in manifest["modules"]
        if module.get("python_distribution")
    ]


if __name__ == "__main__":
    sys.stdout.write("".join(f"{line}\n" for line in requirement_lines()))
