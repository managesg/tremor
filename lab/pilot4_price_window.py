"""Check a finite Pilot 4 UTC window against a pinned local price sheet."""

import argparse
from datetime import datetime
import json
from pathlib import Path
import re

from murmuration import spend


def _utc_instant(value, endpoint):
    if not isinstance(value, str) or not re.fullmatch(
        r"[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}(?:\.[0-9]{1,6})?(?:Z|\+00:00)", value,
    ):
        raise ValueError(f"{endpoint} requires an explicit UTC timestamp")
    try:
        return datetime.fromisoformat(value)
    except ValueError as error:
        raise ValueError(f"{endpoint} is not a valid UTC timestamp") from error


def verify(price_sheet, *, price_sheet_sha256, starts_at, ends_at):
    """Validate both endpoint dates using the stock loader and the same external pin."""
    if not isinstance(price_sheet_sha256, str) or not re.fullmatch(r"[0-9a-f]{64}", price_sheet_sha256):
        raise ValueError("expected the independently retained price-sheet SHA-256")
    start, end = _utc_instant(starts_at, "start"), _utc_instant(ends_at, "end")
    if end <= start:
        raise ValueError("end must follow start")
    for endpoint, instant in (("start", start), ("end", end)):
        try:
            sheet = spend.PriceSheet.load(price_sheet, today=instant.date())
        except spend.PriceSheetRefused as error:
            raise ValueError(f"{endpoint} price-sheet check failed: {error}") from error
        if sheet.sha256 != price_sheet_sha256:
            raise ValueError(f"{endpoint} price-sheet digest differs from the independent pin")
    return {
        "status": "price_sheet_valid_for_window",
        "price_sheet_sha256": price_sheet_sha256,
        "starts_at": start.isoformat(),
        "ends_at": end.isoformat(),
        "valid_through_utc_date": sheet.expires_on().isoformat(),
        "authorizes_execution": False,
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("price_sheet", type=Path)
    parser.add_argument("--price-sheet-sha256", required=True)
    parser.add_argument("--starts-at", required=True, help="UTC start timestamp")
    parser.add_argument("--ends-at", required=True, help="UTC end timestamp")
    try:
        result = verify(**vars(parser.parse_args(argv)))
    except ValueError as error:
        parser.error(str(error))
    print(json.dumps(result, sort_keys=True))


if __name__ == "__main__":
    main()
