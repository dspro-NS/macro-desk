from __future__ import annotations

import argparse
import json
import logging
import sys
from typing import List, Optional

from macro_desk.config import load_settings
from macro_desk.db.repository import DocumentRepository, connect, initialize
from macro_desk.ingestion.pipeline import ingest_rbi_press_releases


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Macro Desk utilities")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("ingest", help="Fetch and persist the official RBI press-release RSS feed")
    args = parser.parse_args(argv)

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )

    if args.command == "ingest":
        settings = load_settings()
        connection = connect(settings.database_path)
        try:
            initialize(connection)
            result = ingest_rbi_press_releases(settings, DocumentRepository(connection))
        finally:
            connection.close()
        print(
            json.dumps(
                {
                    "fetched": result.fetched,
                    "inserted": result.inserted,
                    "skipped": result.skipped,
                    "failed": result.failed,
                    "errors": result.errors,
                },
                indent=2,
            )
        )
        return 1 if result.failed and result.inserted == 0 and result.skipped == 0 else 0

    return 0


if __name__ == "__main__":
    sys.exit(main())
