from typing import Dict, List, Any, Optional
from datetime import datetime
import json


class Newsletter:
    _CONVERSION_TABLE_SERIALIZE = {
        'topNews': 'Top News of the Day',
        'podcasts': 'Podcasts of the Day',
        'moreStories': 'More Stories',
        'regionalNews': 'Regional News'
    }
    _CONVERSION_TABLE_TRANSFORM = {v: k for k,
                                   v in _CONVERSION_TABLE_SERIALIZE.items()}

    def __init__(self, start_date: str, end_date: str, sections: Dict[str, Any]):
        self.start_date: datetime = start_date
        self.end_date: datetime = end_date
        self.sections = sections

    def to_dict(self) -> Dict[str, Any]:
        """Returns a dictionary representation of the newsletter, with formatted dates."""

        return {
            "start_date": self.start_date.isoformat(),
            "end_date": self.end_date.isoformat(),
            "sections": self.sections
        }

    def get_news(self) -> List[Dict[str, Any]]:
        """Returns a flattened list of all news items across all sections."""
        all_news = []
        for section, items in self.sections.items():
            if isinstance(items, list) and len(items) > 0:
                if 'region' in items[0].keys():
                    for regionalItems in items:
                        all_news.extend(regionalItems.get('news', []))
                else:
                    all_news.extend(items)

        return all_news

    def serialize(self) -> Dict[str, Any]:
        serialized = {
            "date": self.start_date.strftime("%d-%m-%Y"),
            "categories": {}
        }

        for section, items in self.sections.items():
            if items:
                section_name = self._CONVERSION_TABLE_SERIALIZE.get(section)
                if section_name is None:
                    continue
                serialized["categories"][section_name] = []
                if section == "regionalNews":
                    for region_section in items:
                        region = region_section["region"]
                        region_items = region_section["news"]
                        serialized["categories"][section_name].append(
                            {
                                region: region_items
                            }
                        )
                else:
                    for item in items:
                        serialized_item = item
                        if "publishDate" in item and item["publishDate"]:
                            serialized_item["publishDate"] = item["publishDate"].strftime(
                                "%Y-%m-%d")
                        serialized["categories"][section_name].append(
                            serialized_item)

        return serialized

    @classmethod
    def from_serialized(cls, serialized_data: Dict) -> "Newsletter":
        """Creates a Newsletter object from serialized JSON data."""
        try:

            if not isinstance(serialized_data, dict) or "json_data" not in serialized_data:
                raise ValueError(
                    "Invalid serialized data: Missing 'categories' key")

            # Extract date (handle potential errors)
            try:
                start_date = serialized_data.get("start_date")
                end_date = serialized_data.get("end_date")

            except (KeyError, ValueError) as e:
                raise ValueError(
                    f"Invalid serialized data: Error parsing date - {e}")

            # Transform the categories section
            if 'json_data' in serialized_data:
                newsletter_json = json.loads(serialized_data['json_data'])

            if 'categories' in newsletter_json:
                sections = cls._transform_categories(
                    newsletter_json['categories'])

            return cls(start_date=start_date, end_date=end_date, sections=sections)

        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON data: {e}")

    @staticmethod
    def _transform_categories(categories: Dict[str, Any]) -> Dict[str, Any]:
        """Transforms the 'categories' section of serialized data."""
        output = {"topNews": [], "podcasts": [],
                  "regionalNews": [], "moreStories": []}
        convertion_table = {
            v: k for k, v in Newsletter._CONVERSION_TABLE_SERIALIZE.items()}

        for category_name, category_items in categories.items():
            section_name = convertion_table.get(category_name)
            if section_name is None:
                continue

            if section_name == "regionalNews":  # Special handling for regional news
                for region_data in category_items:  # Iterate through the list of regional dictionaries
                    for region_name, news_items in region_data.items():  # Iterate through the region dict
                        region_output = {"region": region_name, "news": []}
                        for item in news_items:
                            if "url" in item:
                                region_output['news'].append(item)
                        output[section_name].append(region_output)

            elif isinstance(category_items, list):
                for item in category_items:
                    if "url" in item:
                        output[section_name].append(item)

        return output
