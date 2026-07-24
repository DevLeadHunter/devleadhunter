"""Run all database seeders in order.

Seeders are idempotent: existing records are skipped when already present.
"""

from __future__ import annotations

import importlib
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from core.database import init_db

# Order matters: credit settings before users, users before transactions.
SEEDERS: list[tuple[str, str, str]] = [
    ("credit_settings", "seeders.credit_settings_seeder", "seed_credit_settings"),
    ("users", "seeders.user_seeder", "seed_admin_user"),
    ("credit_transactions", "seeders.credit_transaction_seeder", "seed_credit_transactions"),
    ("resend_config", "seeders.resend_config_seeder", "seed_resend_config"),
    ("email_templates", "seeders.email_template_seeder", "seed_email_templates"),
]


def _load_dotenv() -> None:
    try:
        from dotenv import load_dotenv
    except ImportError:
        return
    load_dotenv(_ROOT / ".env")


def _run_seeder(module_name: str, function_name: str) -> None:
    module = importlib.import_module(module_name)
    seed_fn = getattr(module, function_name, None)
    if seed_fn is None:
        raise RuntimeError(f"{module_name} must define {function_name}()")
    seed_fn()


def main() -> None:
    _load_dotenv()

    print("Ensuring base schema from SQLAlchemy models...")
    init_db()
    print("Base schema ensured.\n")

    for seeder_name, module_name, function_name in SEEDERS:
        print(f"Seeding: {seeder_name}")
        _run_seeder(module_name, function_name)
        print()

    print("All seeders complete.")


if __name__ == "__main__":
    main()
