import vertexai
import json
from vertexai.generative_models import GenerativeModel
import os
import copy
from datetime import datetime, date
import json_repair
import logging
from firebase_helpers import get_last_week_newsletters, save_digest, get_news_by_date_range, get_config, get_past_digests
from utils import fix_json_formatting, MODEL_FLASH
from urllib.parse import urlparse
from typing import Any, Dict, List, Optional
from pydantic import BaseModel
from newsletter_generation import *
from classes.Newsletter import *
from utils import parse_iso_date


PROJECT_ID = os.getenv("PROJECT_ID", "demo-project")
LOCATION = os.getenv("REGION", "us-central1")
MAX_PAGES = 5

vertexai.init(project=PROJECT_ID, location=LOCATION)


class News(BaseModel):
    url: str
    title: str
    abstract: Optional[str]
    website: str
    key_message: str
    context: str
    publish_date: Optional[datetime] = None

    def to_dict(self) -> Dict:
        return self.model_dump(exclude_unset=True, exclude_none=True)


class DigestSubSection(BaseModel):
    name: str
    news: List[News]


class DigestSection(BaseModel):
    name: str
    subSections: Optional[List[DigestSubSection]] = None
    news: Optional[List[News]] = None


class DigestHighlightNews(BaseModel):
    url: str
    title: str
    ref: int
    abstract: Optional[str]
    website: str


class DigestHighlight(BaseModel):
    text: str
    markdown_text: str
    news: List[DigestHighlightNews]


class Digest(BaseModel):
    start_date: datetime
    end_date: datetime
    highlight: DigestHighlight
    sections: List[DigestSection]

    def to_dict(self) -> Dict:
        return self.model_dump(exclude_unset=True, exclude_none=True)

    @classmethod
    def from_dict(cls, digestDict: Dict) -> "Digest":
        try:
            start_date = digestDict['start_date'],
            end_date = digestDict['end_date'],
            start_date = str(start_date)
            if type(start_date) == str:
                start_date = parse_iso_date(start_date)
            if type(end_date) == str:
                end_date = parse_iso_date(end_date)
            sections = digestDict['sections'],
            highlight = digestDict['highlight']
            return cls(start_date=start_date, end_date=end_date, sections=sections, highlight=highlight)
        except Exception as e:
            print("Error loading the Digest object:" + str(e))


def generate_weekly_digest_text(newsletter_list):
    """Generates a structured weekly digest text from a list of daily newsletters
    using Gemini Pro for content creation.

    Args:
        newsletter_list (list): A list of dictionaries, with each dictionary containing 
                          news from a specific website.

    Returns:
        str: The formatted digest text.
    """

    prompt = """
    {}

    The output format should be a well formatted JSON object. Do not place the complete output text in brackets ("[]"). The categories should formatted as follows:
    {{
    "start_date": "DD-MM-YYYY",
    "end_date": "DD-MM-YYYY",
    "categories": {{
        "Digest Sections": {{
            "Section name which containts subsecions (Competitors, Travel Providers)": {{
                "Subsection name (i.e Industry)": [
                    {{
                        "abstract": "article abstract. leave blank if missing from original news item",
                        "key_message": "text contents of article key message",
                        "context": "additional context or description",
                        "title": "title of the article",
                        "url": "link to the full article"
                        "website": "source website"
                    }}
                    // ... more articles as needed
                ]
                // .... more subsections as needed
            }}
            "Section name which does not contain subsecions (Industry / Regulations, M&A and Investment, Financial Reports / Info, Research and Reports)": [
                {{
                    "abstract": "article abstract. leave blank if missing from original news item",
                    "key_message": "text contents of article key message",
                    "context": "additional context or description",
                    "title": "title of the article",
                    "url": "link to the full article"
                    "website": "source website"
                }}
                // ... more articles as needed
            ]
        }},
    }}
    }}

    **Newsletters:**
        {}

The following section contains examples of previously generated and approved digests. 
Use them to help make decisions on whether to include certain articles
in this digest. Do not use the actual examples in this digest. 
    ** Generated Past Digests:**
        {}
    
    """

    config = get_config()
    if not config or not config['prompt_weekly']:
        raise Exception('Invalid configuration or prompt_weekly is not set')

    formatted_newsletter_data = json.dumps(newsletter_list, default=str)

    # Retrieve past digests from firestore
    past_digests = get_past_digests(7)
    # check if there are any documents in the collection
    if not past_digests:
        past_digests = ""

    past_digests = json.dumps(past_digests, default=str)

    generation_config = {"temperature": 0,
                         "response_mime_type": "application/json"}
    model = GenerativeModel(model_name=MODEL_FLASH,
                            generation_config=generation_config)

    responses = model.generate_content(
        [prompt.format(config['prompt_weekly'],
                       formatted_newsletter_data, past_digests)],
    )

    digest = responses.text.strip()
    digest = digest.replace("```json", "").replace("```", "").strip()
    if digest.startswith("[") and digest.endswith("]"):
        digest = digest[1:-1]
    try:
        digest_json = json_repair.loads(digest)
    except Exception as e:
        digest_json = fix_json_formatting(digest, e)

    return digest_json


def generate_highlights(digest_text):
    """Generates a 'Highlights of the Week' section for the digest using Gemini Pro.

    Args:
        digest_text: The digest JSON object.

    Returns:
        A JSON object containing the 'Highlights of the Week' section.
    """

    prompt = """
    {}   
        
   The output format should be a well formatted JSON object. Do not place the complete output text in brackets ("[]"). The output should formatted as follows:
    {{
        "Highlights of the Week": {{
            "text": "complete text contents of the 'highlights of the week' section, with reference numbers to relevant articles in brackets.",
            "markdown_text": "Organize the content of this section clearly and use appealing formatting to catch the readers eye. Give each highlight a short intro title, and prefix the title with an engaging icon. Place a colon between the title and the highilght contents.
            The title and icon should NOT be in a header format, but should be bold. Separate each highlight with a new line. Do not include the title "Highlights of the Week" in the markdown text. The hyperlinks should be in bold font and redirect to the article when clicked.
            The reference numbers should start at '1' and increase sequentially (eg. [1], [2], [3]...) 
            (hyperlink markdown example: "**[1](https://www.example.com)**")"
            "news": [
                {{
                    "url": "link to the full article",
                    "title": "title of the news",
                    "ref": "reference number from the 'highlights of the week' section"
                    "abstract": "abstract of the news",
                    "website": "source website"
                }}
                // ... more news articles
            ]
        }}

    ** Digest contents **:
    {}
The following section contains examples of previously generated and approved digests. 
Use them to help make decisions on whether to include certain articles
in the highlights section, and how to format it. Do not use the actual examples in this digest. 

    ** Past Digests **:
    {}
    """
    config = get_config()

    past_digests = get_past_digests(7)
    # check if there are any documents in the collection
    if not past_digests:
        past_digests = ""

    past_digests = json.dumps(past_digests, default=str)

    generation_config = {"temperature": 0,
                         "response_mime_type": "application/json"}
    model = GenerativeModel(model_name=MODEL_FLASH,
                            generation_config=generation_config)
    responses = model.generate_content(
        [prompt.format(config['prompt_weekly_highlights'],
                       digest_text, past_digests)],
    )

    digest = responses.text.strip()
    digest = digest.replace("```json", "").replace("```", "").strip()
    if digest.startswith("[") and digest.endswith("]"):
        digest = digest[1:-1]
    try:
        digest_json = json_repair.loads(digest)
    except Exception as e:
        digest_json = fix_json_formatting(digest, e)

    return digest_json


def regenerate_digest_highlights(digest: Digest):
    """Regenerates the 'Highlights of the Week' section of the digest using only articles included in the 'Highlights News Items' section.

    Args:
        digest: The digest JSON object.


    Returns:
        A JSON object containing the regenerated 'Highlights of the Week' section.
    """

    prompt = """
    Rewrite the 'Highlights of the Week' section of the digest below using only articles included in the 'Highlights News Items' section below.
    Remove all highlights that do not reference items in the news list, and add new highlights for items in the news list not yet referenced.
    
    The output format should be a well formatted JSON object. Do not place the complete output text in brackets ("[]"). The output should formatted as follows:
    {{
            "text": "complete text contents of the 'highlights of the week' section, with reference numbers to relevant articles in brackets.",
            "markdown_text": "Organize the content of this section clearly and use appealing formatting to catch the readers eye. Give each highlight a short intro title, and prefix the title with an engaging icon. Place a colon between the title and the highilght contents.
            The title and icon should NOT be in a header format, but should be bold. Separate each highlight with a new line. Do not include the title "Highlights of the Week" in the markdown text. The hyperlinks should be in bold font and redirect to the article when clicked.
            The reference numbers should start at '1' and increase sequentially (eg. [1], [2], [3]...) 
            (hyperlink markdown example: "**[1](https://www.example.com)**")"
            "news": [
                {{
                    "url": "link to the full article",
                    "title": "title of the news",
                    "ref": "reference number from the 'highlights of the week' section", as number
                    "website": "source website"
                }}
                // ... more news articles
            ]
    }}

    ** Digest **:
    {}

    ** Highlights News Items**
    {}
    """

    highlights_news_list = digest["highlight"]["news"]

    formatted_digest = json.dumps(digest, default=str)

    generation_config = {"temperature": 0,
                         "response_mime_type": "application/json"}
    model = GenerativeModel(model_name=MODEL_FLASH,
                            generation_config=generation_config)

    responses = model.generate_content(
        [prompt.format(formatted_digest, highlights_news_list)],
    )

    highlights = responses.text.strip()
    highlights = highlights.replace("```json", "").replace("```", "").strip()
    if highlights.startswith("[") and highlights.endswith("]"):
        highlights = highlights[1:-1]
    try:
        highlights_json = json_repair.loads(highlights)
    except Exception as e:
        highlights_json = fix_json_formatting(highlights, e)
    return highlights_json


def generate_digest_metadata(nl_article):
    """
    Reformats article from newsletter format to digest format. Generates key_message and context fields.

    Args:
        nl_article: Article dictionary in newsletter form: {'abstract':'', 'title':'', 'website':'', 'full_text':'', 'published_at':''}

    Returns:
        digest_article: Article dictionary in digest form: {'key_message':'', 'context':'', 'title':'', 'url':'', 'website':''}
    """

    prompt = """
    Reformat the ' newsletter article' below to match the following output format:
                    
                    {{
                        "url": "link to the full article"
                        "title": "title of the article",
                        "abstract": "article abstract. leave blank if not included in the original new item."
                        "website": "source website"
                        "gen_key_message": "one or two sentence summary of the article's key message",
                        "gen_context": "additional context or description",
                        "published_date": "date the article was published. leave blank if not included in the original news item."
                    }}
    
    Additional instructions on generating the gen_context field:
    * 'gen_context' should explain why the story is important, what broader industry trend it reflects, and why it is meaningful given other ongoing trends.
    * Keep the statement short and to the point. 
    * Do not include phrases such as "This news is significant for our company because...". 
    * Do not restate what is already said in the key message.

    The output format should be a well formatted JSON object. Do not place the complete output text in brackets ("[]").
     
    Newsletter article:
    {}
    """

    generation_config = {"temperature": 0,
                         "response_mime_type": "application/json"}
    model = GenerativeModel(model_name=MODEL_FLASH,
                            generation_config=generation_config)

    prompt = prompt.format(nl_article)

    responses = model.generate_content(
        [prompt],
    )

    digest_article = responses.text.strip()
    digest_article = digest_article.replace(
        "```json", "").replace("```", "").strip()
    digest_article = json_repair.loads(digest_article)

    return digest_article


def highlights_cleanup(highlights_markdown):
    """Cleans up the markdown text of the 'Highlights of the Week' section.
    This function ensures that the markdown text is properly formatted,
    with two newline characters before each new item, and that the
    references are in sequential order.

    Args:
        highlights_markdown: The markdown text of the 'Highlights of the Week' section.

    Returns:
        The cleaned up markdown text.
    """

    prompt = """
    For the following markdown text, perform the following revisions:
    1. ensure there are two newline characters before each new item. Items are demarcated by two asterix and an emoji character. 
    If there is already one newline character, add another. If there are none, add two.
    2. Make sure the references are in sequential order. Renumber them if necessary.

    Ouput the new markdown text.

    Below are example input and outputs with correct changes applied. They are only meant to demonstrate correct revisions; do not use these example contents in the output.
    Example Input: '**\\ud83c\\udf0f  Consolidation:** Lufthansa secures approval for its acquisition of ITA Airways. **[12](https://skift.com/2024/07/03/lufthansa-secures-approval-for-ita-airways-deal/)**\n**\\u2708\\ufe0f Strong Passenger Demand:** IATA reports a 10.7% year-on-year increase in passenger demand in May. **[4](/en/pressroom/2024-releases/2024-07-03-02/)**'
    Example Output: '**\\ud83c\\udf0f Consolidation:** Lufthansa secures approval for its acquisition of ITA Airways. **[1](https://skift.com/2024/07/03/lufthansa-secures-approval-for-ita-airways-deal/)**\n\n**\\u2708\\ufe0f Strong Passenger Demand:** IATA reports a 10.7% year-on-year increase in passenger demand in May. **[2](/en/pressroom/2024-releases/2024-07-03-02/)**'

    Markdown text:
    {}
    """

    prompt = prompt.format(highlights_markdown)

    model = GenerativeModel(model_name=MODEL_FLASH)
    responses = model.generate_content(
        [prompt],)

    modified_markdown = responses.text

    return modified_markdown


def parse_newsletters(newsletter_list: List[Newsletter]) -> Dict[str, List[News]]:
    """Parses a list of newsletters and returns a dictionary of their articles categorized by website.

    Args:
        article_list: A list of newsletters.

    Returns:
        A dictionary where keys are websites and values are lists of news articles.
    """

    all_articles = []
    for newsletter in newsletter_list:
        all_articles.extend(newsletter.get_news())

    # Deduplicate articles based on URL
    unique_articles = {}
    for article in all_articles:
        unique_articles[article.get("url")] = article

    # Categorize articles by website
    articles_by_website = {}
    for url, article in unique_articles.items():
        website = article.get("website")
        if website not in articles_by_website:
            articles_by_website[website] = []
        articles_by_website[website].append(article)

    return articles_by_website

    for newsletter in newsletter_list:
        json_data = json.loads(newsletter["json_data"])

        for category, articles in json_data["categories"].items():
            if not isinstance(articles, list):  # Handle "Regional News"
                articles = list(articles.values())
                articles = [item for sublist in articles for item in sublist]

            for article in articles:
                website = article["website"]
                # Format the publication date if available
                if "published_at" in article:
                    article["published_at"] = datetime.strptime(
                        article["published_at"], "%Y-%m-%d %H:%M:%S")
                parsed_articles.setdefault(website, []).append(article)

    # Remove duplicate articles
    unique_urls = []
    unique_articles = {}
    for website in parsed_articles:
        for article in parsed_articles[website]:
            if article["url"] not in unique_urls:
                unique_urls.append(article["url"])
                unique_articles.setdefault(website, []).append(article)
            else:
                logging.info(f"Duplicate article found: {article['url']}")

    return unique_articles


def convert_to_digest(data):
    """
    Converts a dictionary to a Digest object.

    Args:
        data (dict): The dictionary to convert.

    Returns:
        Digest: The converted Digest object.
    """

    # Convert date strings to datetime objects
    start_date = datetime.strptime(data["start_date"], "%d-%m-%Y")
    end_date = datetime.strptime(data["end_date"], "%d-%m-%Y")

    # Extract highlight data
    highlight_data = data["categories"]["Highlights of the Week"]
    highlight_news = [
        DigestHighlightNews(
            url=news.get("url", ""),
            title=news.get("title", ""),
            ref=int(news.get("ref")),  # Convert ref to integer
            website=news.get("website", ""),
            abstract=news.get("abstract", "")
        )
        for news in highlight_data["news"]
    ]
    highlight = DigestHighlight(
        text=highlight_data["text"],
        markdown_text=highlight_data["markdown_text"],
        news=highlight_news
    )

    # Extract sections data
    sections = []
    for section_name, section_data in data["categories"]["Digest Sections"].items():
        if isinstance(section_data, dict):
            sub_sections = []
            for sub_section_name, sub_section_news in section_data.items():
                news_list = [
                    News(
                        url=news.get("url", ""),
                        title=news.get("title", ""),
                        abstract=news.get("abstract", ""),
                        website=news.get("website", ""),
                        key_message=news.get("key_message", ""),
                        context=news.get("context", ""),
                        publish_date=news.get("published_at", None)
                    )
                    for news in sub_section_news
                ]
                sub_sections.append(DigestSubSection(
                    name=sub_section_name, news=news_list))
            sections.append(DigestSection(
                name=section_name, subSections=sub_sections))
        elif isinstance(section_data, list):
            newslist = [
                News(
                    url=news.get("url", ""),
                    title=news.get("title", ""),
                    abstract=news.get("abstract", ""),
                    website=news.get("website", ""),
                    key_message=news.get("key_message", ""),
                    context=news.get("context", ""),
                    publish_date=news.get("published_at", None)
                )
                for news in section_data
            ]
            sections.append(DigestSection(name=section_name, news=newslist))
    # Create the Digest object
    digest = Digest(
        start_date=start_date,
        end_date=end_date,
        highlight=highlight,
        sections=sections
    )

    return digest


def generate_digest_contents(news_list_by_website):
    # Generate digest contents`
    digest_contents = generate_weekly_digest_text(news_list_by_website)
    if 'Digest Sections' not in digest_contents['categories']:
        categories = copy.deepcopy(digest_contents['categories'])
        digest_contents['categories']['Digest Sections'] = categories

    # Generate and format highlights
    digest_highlights = generate_highlights(digest_contents)
    highlights_markdown = digest_highlights['Highlights of the Week']['markdown_text']
    formatted_highlight_markdown = highlights_cleanup(highlights_markdown)
    digest_highlights['Highlights of the Week']['markdown_text'] = formatted_highlight_markdown
    digest_contents['categories']['Highlights of the Week'] = digest_highlights['Highlights of the Week']

    # Reorder categories and return digest
    digest_categories_order = ['Highlights of the Week', 'Digest Sections']
    categories = {key: digest_contents['categories'][key]
                  for key in digest_categories_order}
    digest_contents['categories'] = categories
    if 'Highlights of the week' in digest_contents['categories']['Digest Sections']:
        del digest_contents['categores']['Digest Sections']['Highlights of the week']

    return digest_contents


def generate_digest(start_date, end_date):
    newsletter_list = get_last_week_newsletters(
        start_date, end_date)
    if newsletter_list:
        news_list_by_website = parse_newsletters(newsletter_list)
        digest_contents = generate_digest_contents(news_list_by_website)
        digest = convert_to_digest(digest_contents)
        digest_dict = digest.model_dump(exclude_none=True)

        # Save digest to Firebase
        digest_id = save_digest(digest_dict)
        logging.info(f"Digest saved with ID: {digest_id}")
        return digest_dict
