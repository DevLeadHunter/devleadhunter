"""
Database initialization script.

Runs migrations schema setup is expected separately via ``migrations/run_migrations.py``.
This script only seeds initial data (admin user, credit settings, credit transactions).
"""

from seeders.run_seeders import main

if __name__ == "__main__":
    main()
