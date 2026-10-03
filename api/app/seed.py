"""Triggers initial data fetch from all sources."""

import logging

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")


def main() -> None:
    from app.sources.shelters import fetch_shelters
    from app.sources.tauron import fetch_tauron_outages
    from app.sources.imgw import fetch_imgw_hydro, fetch_imgw_warnings

    print("=== Seeding shelters ===")
    result = fetch_shelters.apply().get(timeout=120)
    print(f"  Result: {result}")

    print("=== Seeding Tauron outages ===")
    result = fetch_tauron_outages.apply().get(timeout=60)
    print(f"  Result: {result}")

    print("=== Seeding IMGW hydro stations ===")
    result = fetch_imgw_hydro.apply().get(timeout=60)
    print(f"  Result: {result}")

    print("=== Seeding IMGW warnings ===")
    result = fetch_imgw_warnings.apply().get(timeout=60)
    print(f"  Result: {result}")

    print("=== Seed complete ===")


if __name__ == "__main__":
    main()
