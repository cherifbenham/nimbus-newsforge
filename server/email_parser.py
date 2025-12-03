"""
Email Parser for Industry News Review
Extracts news items from .eml files
"""

import email
import logging
import re
from datetime import datetime
from email import policy
from email.parser import BytesParser
from typing import Dict, List, Optional

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(levelname)s:%(name)s:%(message)s'
)


def parse_eml_file(file_content: bytes) -> List[Dict[str, str]]:
    """
    Parse an .eml file and extract news items

    Args:
        file_content: Raw bytes of the .eml file

    Returns:
        List of news items with date, url, title, abstract
    """
    # Parse the email
    msg = BytesParser(policy=policy.default).parsebytes(file_content)

    # Extract the plain text body
    text_body = extract_text_body(msg)

    if not text_body:
        return []

    # Extract news items from the text
    news_items = extract_news_from_text(text_body)

    return news_items


def extract_text_body(msg) -> str:
    """Extract plain text body from email message"""
    text_body = ""

    if msg.is_multipart():
        for part in msg.walk():
            content_type = part.get_content_type()
            content_disposition = str(part.get("Content-Disposition"))

            # Look for plain text parts
            if content_type == "text/plain" and "attachment" not in content_disposition:
                try:
                    payload = part.get_payload(decode=True)
                    if payload:
                        text_body = payload.decode('utf-8', errors='ignore')
                        break
                except:
                    continue
    else:
        # Not multipart, just get the payload
        try:
            payload = msg.get_payload(decode=True)
            if payload:
                text_body = payload.decode('utf-8', errors='ignore')
        except:
            pass

    return text_body


def extract_news_from_text(text: str) -> List[Dict[str, str]]:
    """
    Extract news items from email text body

    Expected format:
    Section Header (e.g., "Top News of the Day", "North America", etc.)
    Title (date)
    Abstract text...
    Full story: Source
    URL
    """
    news_items = []

    logging.info(f"Email text length: {len(text)} characters")

    # Clean up the text - remove quoted-printable encoding artifacts
    text = text.replace('=3D', '=')
    text = text.replace('=E2=80=99', "'")
    text = text.replace('=E2=80=9C', '"')
    text = text.replace('=E2=80=9D', '"')
    text = text.replace('=E2=80=93', '-')
    text = text.replace('=20\n', ' ')
    text = text.replace('=\n', '')

    # Define section patterns (case-insensitive)
    section_patterns = [
        r'^Top News of the Day$',
        r'^North America$',
        r'^South America$',
        r'^Europe$',
        r'^Asia Pacific$',
        r'^Middle East$',
        r'^Africa$',
        r'^Regional News Review$',
        r'^More [Ss]tories$',  # Match both "More stories" and "More Stories"
        r'^Technology$',
        r'^Sustainability$',
        r'^Travel Providers$',
        r'^Airlines$',
        r'^Hospitality$',
    ]

    # Split by common section headers to focus on news content
    lines = text.split('\n')

    current_item = None
    current_section = ''
    i = 0

    while i < len(lines):
        line = lines[i].strip()

        # Skip empty lines and separators
        if not line or line.startswith('=') or line.startswith('-'):
            i += 1
            continue

        # Check if this line is a section header
        is_section = False
        for pattern in section_patterns:
            if re.match(pattern, line, re.IGNORECASE):
                current_section = line
                is_section = True
                logging.info(f"Found section header: {current_section}")
                break

        # Log lines that might be section headers but don't match
        if not is_section and not re.search(r'\(\d{1,2}\s+\w+\s+\d{4}', line):
            # This line doesn't have a date pattern, might be a section header
            if len(line) < 50 and line[0].isupper():
                logging.debug(f"Potential section header (not matched): '{line}'")

        if is_section:
            i += 1
            continue

        # Check if this line contains a date pattern
        # Format 1: Title (DD Mon YYYY) - regular articles
        # Format 2: Title (DD Mon YYYY, Source) - "More Stories" articles
        # Format 3: Multi-line "More Stories": Title on previous line, ] (DD Mon YYYY, Source) on current line
        date_match = re.search(r'\((\d{1,2}\s+\w+\s+\d{4})(?:,\s*([^)]+))?\)', line)

        if date_match:
            # This looks like a title line
            if current_item:
                # Save the previous item
                news_items.append(current_item)

            # Extract title and date
            title = line[:date_match.start()].strip()
            date_str = date_match.group(1)
            source = date_match.group(2) if date_match.group(2) else None

            # Check if this is a multi-line More Stories article (title is just ']')
            is_more_stories_multiline = False
            article_url = ''

            if title == ']' and i > 0:
                # Look back to previous line for actual title
                prev_line = lines[i - 1].strip()
                # Previous line should not be a section header or have a date pattern
                if prev_line and not any(re.match(p, prev_line, re.IGNORECASE) for p in section_patterns):
                    if not re.search(r'\(\d{1,2}\s+\w+\s+\d{4}', prev_line):
                        # Check if previous line is a URL (More Stories format: Title → URL → ] (date, source))
                        if prev_line.startswith('http'):
                            is_more_stories_multiline = True
                            article_url = prev_line.split('?')[0]  # Store URL, remove tracking params
                            # URL line - look back one more line for the actual title
                            if i > 1:
                                title_line = lines[i - 2].strip()
                                if title_line and not any(re.match(p, title_line, re.IGNORECASE) for p in section_patterns):
                                    if not re.search(r'\(\d{1,2}\s+\w+\s+\d{4}', title_line):
                                        title = title_line.rstrip('[').strip()  # Remove trailing '[' character
                                        logging.debug(f"Multi-line More Stories with URL detected. Using title from 2 lines back: '{title}'")
                                    else:
                                        # Fallback to source-based title
                                        title = f"{source} article" if source else "More Stories article"
                                        logging.debug(f"Could not find valid title, using fallback: '{title}'")
                                else:
                                    # Fallback to source-based title
                                    title = f"{source} article" if source else "More Stories article"
                                    logging.debug(f"Title line is section header or invalid, using fallback: '{title}'")
                            else:
                                # Not enough lines to look back
                                title = f"{source} article" if source else "More Stories article"
                                logging.debug(f"Not enough lines to look back, using fallback: '{title}'")
                        else:
                            # Use previous line as title (actual text title)
                            title = prev_line
                            logging.debug(f"Multi-line More Stories detected. Using previous line as title: '{title}'")

            # Debug: log the raw line and extracted title
            logging.debug(f"Raw line: '{line}'")
            logging.debug(f"Extracted title: '{title}'")

            # For More Stories articles, use title as abstract (instead of just source)
            abstract_text = title if is_more_stories_multiline else (source if source else '')

            current_item = {
                'title': title,
                'date': date_str,
                'abstract': abstract_text,
                'url': article_url,  # Use URL if already found
                'class_daily': current_section
            }
            logging.info(f"Found article in section '{current_section}': {title[:50] if title else '[EMPTY TITLE]'}..." + (f" (source: {source})" if source else ""))

            # Skip look-ahead for multi-line More Stories articles (we already have title and URL)
            if is_more_stories_multiline:
                i += 1
                continue

            # Look ahead for abstract and URL
            i += 1
            abstract_lines = []

            while i < len(lines):
                next_line = lines[i].strip()

                # Check if we hit a section header
                is_next_section = False
                for pattern in section_patterns:
                    if re.match(pattern, next_line, re.IGNORECASE):
                        is_next_section = True
                        break

                if is_next_section:
                    # Don't increment i, let outer loop handle section
                    break

                # Stop at URL or next news item
                if not next_line or next_line.startswith('Full story:'):
                    i += 1
                    continue
                elif next_line.startswith('http'):
                    if current_item:
                        current_item['url'] = next_line.split('?')[0]  # Remove tracking params
                    i += 1
                    break
                elif re.search(r'\(\d{1,2}\s+\w+\s+\d{4}\)', next_line):
                    # Next news item, don't increment i
                    break
                else:
                    # Part of abstract
                    abstract_lines.append(next_line)
                    i += 1

            if current_item and abstract_lines:
                current_item['abstract'] = ' '.join(abstract_lines)
        else:
            i += 1

    # Don't forget the last item
    if current_item:
        news_items.append(current_item)

    # Filter out invalid items
    valid_items = []
    for idx, item in enumerate(news_items):
        if item.get('title') and len(item['title']) > 10:
            # Generate an ID
            item['id'] = f"eml_{idx}_{hash(item['title']) % 10000}"
            valid_items.append(item)

    return valid_items


def clean_url(url: str) -> str:
    """Remove tracking parameters from URL"""
    if '?' in url:
        return url.split('?')[0]
    return url
