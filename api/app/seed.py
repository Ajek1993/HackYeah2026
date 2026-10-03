"""Loads shelters from data/shelters.json into the database (implemented in T06)."""

from pathlib import Path

SHELTERS_FILE = Path(__file__).resolve().parent.parent / "data" / "shelters.json"


def main() -> None:
    if not SHELTERS_FILE.exists():
        print(f"No shelters file at {SHELTERS_FILE} - nothing to seed yet (T06).")
        return
    print("Shelter seeding is implemented in T06.")


if __name__ == "__main__":
    main()
