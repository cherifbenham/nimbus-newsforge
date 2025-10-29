"""
Utility to convert the generated `weekly_response_pretty.json` into an Excel workbook that can be
uploaded to the Compose Weekly tool.

Usage:
    python scripts/excelfy_compose_weekly.py [input_json] [output_xlsx]

- input_json: path to weekly_response_pretty.json (defaults to repository root file)
- output_xlsx: desired Excel output path (defaults to compose_weekly_input.xlsx)
"""

from __future__ import annotations

import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, Iterable, List

from openpyxl import Workbook


DEFAULT_INPUT = Path("weekly_response_pretty.json")
DEFAULT_OUTPUT = Path("compose_weekly_input.xlsx")


def iso_date(value: str) -> str:
    """Normalise ISO timestamps to YYYY-MM-DD for easier reading."""
    if not value:
        return ""
    try:
        # Handle timestamps that may or may not include timezone suffixes.
        cleaned = value.replace("Z", "+00:00")
        return datetime.fromisoformat(cleaned).date().isoformat()
    except ValueError:
        return value


def _extract_basic_fields(item: Dict[str, str]) -> Dict[str, str]:
    """Pull the common fields and trim whitespace."""
    def pick(key: str) -> str:
        return str(item.get(key, "") or "").strip()

    return {
        "title": pick("title"),
        "abstract": pick("abstract"),
        "url": pick("url"),
        "reason": pick("reason"),
        "source": pick("website"),
    }


def iter_compose_rows(data: Dict) -> Iterable[Dict[str, str]]:
    """Flatten the weekly response structure into Compose Weekly rows."""
    sections = data.get("sections", {})
    default_date = iso_date(str(data.get("end_date", "")))

    def make_row(base: Dict[str, str], row_id: str, class_daily: str) -> Dict[str, str]:
        payload = {
            "id": row_id,
            "date": base.get("date") or default_date,
            "class_daily": class_daily,
        }
        payload.update(base)
        return payload

    # Top-level simple sections (arrays of news items)
    simple_sections = {
        "topNews": "Top News",
        "moreStories": "More Stories",
        "podcasts": "Podcasts",
    }

    for key, label in simple_sections.items():
        items: List[Dict] = sections.get(key, []) or []
        for index, raw_item in enumerate(items, start=1):
            fields = _extract_basic_fields(raw_item)
            if not fields["title"] and not fields["abstract"]:
                continue
            yield make_row(fields, f"{key}-{index}", label)

    # Regional news has nested groups with region labels.
    regional_items = sections.get("regionalNews", []) or []
    for group_index, group in enumerate(regional_items, start=1):
        region = str(group.get("region", "Regional News")).strip() or "Regional News"
        news_items = group.get("news", []) or []
        for item_index, raw_item in enumerate(news_items, start=1):
            fields = _extract_basic_fields(raw_item)
            if not fields["title"] and not fields["abstract"]:
                continue
            row_id = f"regional-{group_index}-{item_index}"
            class_daily = f"Regional News - {region}"
            yield make_row(fields, row_id, class_daily)


def write_excel(rows: Iterable[Dict[str, str]], output_path: Path) -> None:
    """Persist rows into a single-sheet Excel workbook."""
    workbook = Workbook()
    sheet = workbook.active
    sheet.title = "ComposeWeekly"

    rows = list(rows)
    if not rows:
        raise ValueError("No rows to write. Did the input file contain any news items?")

    # Ensure consistent column ordering.
    headers = [
        "id",
        "date",
        "class_daily",
        "title",
        "abstract",
        "url",
        "source",
        "reason",
    ]
    sheet.append(headers)

    for row in rows:
        sheet.append([row.get(column, "") for column in headers])

    workbook.save(output_path)


def main(input_path: Path, output_path: Path) -> None:
    if not input_path.exists():
        raise FileNotFoundError(f"Input JSON not found: {input_path}")

    with input_path.open("r", encoding="utf-8") as handle:
        data = json.load(handle)

    rows = list(iter_compose_rows(data))
    write_excel(rows, output_path)
    print(f"Wrote {len(rows)} rows to {output_path}")


if __name__ == "__main__":
    input_file = Path(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT_INPUT
    output_file = Path(sys.argv[2]) if len(sys.argv) > 2 else DEFAULT_OUTPUT
    main(input_file, output_file)
