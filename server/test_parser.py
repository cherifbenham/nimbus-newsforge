#!/usr/bin/env python3
"""Test email parser"""

import json

from email_parser import parse_eml_file

with open('../data/input/sample_news.eml', 'rb') as f:
    content = f.read()

items = parse_eml_file(content)
print(f'Found {len(items)} items\n')

for idx, item in enumerate(items[:5], 1):
    print(f"{idx}. Title: {item['title'][:60]}")
    print(f"   Class Daily: '{item.get('class_daily', 'MISSING')}'")
    print(f"   Date: {item['date']}")
    print(f"   URL: {item.get('url', 'N/A')[:50]}")
    print()

print("\n--- Full first item ---")
print(json.dumps(items[0] if items else {}, indent=2))
