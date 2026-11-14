"""The pip requirements of the product modules: the public ones from GitHub, a private one left to its deploy key."""

import json
from pathlib import Path

from scripts.product_module_requirements import requirement_lines


def test_a_private_module_is_left_out_of_the_pip_requirements(tmp_path: Path) -> None:
    manifest: Path = tmp_path / "product-modules.json"
    manifest.write_text(
        json.dumps(
            {
                "modules": [
                    {
                        "key": "site-care",
                        "repository": "DevLeadHunter/devleadhunter-module-site-care",
                        "ref": "v1.1.1",
                        "python_distribution": "devleadhunter-site-care",
                        "layers": ["web"],
                    },
                    {
                        "key": "missions",
                        "repository": "DevLeadHunter/devleadhunter-module-missions",
                        "ref": "v1.0.0",
                        "python_distribution": "devleadhunter-missions",
                        "layers": ["web"],
                        "private": True,
                    },
                ]
            }
        ),
        encoding="utf-8",
    )

    assert requirement_lines(manifest) == [
        "devleadhunter-site-care @ git+https://github.com/DevLeadHunter/devleadhunter-module-site-care@v1.1.1"
        "#subdirectory=api"
    ]
