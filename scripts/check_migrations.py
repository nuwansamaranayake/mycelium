import os
import sys
from sqlalchemy import create_engine, text

EXPECTED = int(os.getenv("EXPECTED_TABLE_COUNT", "0"))


def main():
    if not EXPECTED:
        # A disarmed check must never print a green line (Standard 4). Deploys that
        # inject env vars directly instead of mounting .env used to silently skip this.
        print("MIGRATION CHECK NOT ARMED: EXPECTED_TABLE_COUNT is unset or 0; "
              "set it (see .env.example) - refusing to report MIGRATION OK unverified",
              file=sys.stderr)
        sys.exit(1)
    url = os.environ["DATABASE_URL"]
    with create_engine(url).connect() as c:
        n = c.execute(
            text("select count(*) from information_schema.tables where table_schema='public'")
        ).scalar_one()
    if n != EXPECTED:
        print(f"MIGRATION CHECK FAILED: expected {EXPECTED} tables, found {n}", file=sys.stderr)
        sys.exit(1)
    print(f"MIGRATION OK: {n} tables")


if __name__ == "__main__":
    main()
