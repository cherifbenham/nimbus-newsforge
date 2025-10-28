import requests
from bs4 import BeautifulSoup
import vertexai
import json
from vertexai.generative_models import GenerativeModel, Part, GenerationConfig
from google.cloud.firestore import DocumentSnapshot
import os
import logging
import concurrent.futures
from src.core.utils.logger import get_logger
from datetime import datetime, date
import traceback
import json_repair
from src.core.utils.firebase_helpers import save_news, get_news_by_date_range, get_firestore_client
from src.core.utils.media_retriever import fetch_and_store
import concurrent.futures
from urllib.parse import urlparse
from proto.marshal.collections import repeated
from proto.marshal.collections import maps
from google.api_core.client_options import ClientOptions
from google.cloud import storage
from google.cloud import discoveryengine as discoveryengine
from typing import List


PROJECT_ID = os.getenv("PROJECT_ID", "fsa-amadeus")
LOCATION = os.getenv("REGION", "us-central1")
MAX_PAGES = 5

logger = get_logger()

vertexai.init(project=PROJECT_ID, location=LOCATION)


def is_prod():
    if os.environ.get('K_SERVICE') or os.environ.get('CLOUD_RUN_JOB'):
        return True
    else:
        return False


def get_urls():
    # load the urls from the Firestore db
    config_data = get_config()
    if config_data:
        urls = config_data.get('urls', [])
        return urls
    else:
        logger.error("Config document not found in Firestore.")
        return []


def get_config():
    # retrive the prompts from the Firestore db
    db = get_firestore_client()
    config_collection = db.collection('config')

    if is_prod():
        config_doc = config_collection.document('prod')
    else:
        config_doc = config_collection.document('dev')
    config_doc = config_doc.get()
    if config_doc.exists:
        config_data = config_doc.to_dict()
        return config_data
    else:
        logger.error("Config document not found in Firestore.")
        return {}


def save_config(config_data):
    db = get_firestore_client()
    config_collection = db.collection('config')

    if is_prod():
        config_doc = config_collection.document('prod')
    else:
        config_doc = config_collection.document('dev')

    try:
        config_doc.update(config_data)
    except Exception as e:
        logger.error(f"Error updating config document: {e}")


def get_news_for_period(start_datetime, end_datetime):
    cached_news = get_news_by_date_range(start_datetime, end_datetime)
    return cached_news


def get_cached_news_for_period(start_datetime, end_datetime):
    valid_cached_news = []
    urls = get_urls()
    cached_news = get_news_by_date_range(
        start_datetime, end_datetime)
    # Group the news by website
    cached_site_news = {}
    for news in cached_news:
        website = news['website']
        if website not in cached_site_news:
            cached_site_news[website] = []
        cached_site_news[website].append(news)
        # Iterate over the websites
    for website in urls:
        if website not in cached_site_news:
            continue
        # Order the news by date
        cached_site_news = sorted(
            cached_site_news[website], key=lambda x: x['published_at'], reverse=True)
        if cached_site_news and cached_site_news[0]['published_at'] >= end_datetime:
            logger.info(f'Cached news for {website}: {len(cached_site_news)}')
            valid_cached_news.append(
                {'website': website, 'news': cached_site_news})
    return valid_cached_news


def fix_json_formatting(json_string, error_message):
    """Corrects invalid JSON strings using the Gemini model.

  This function takes an invalid JSON string and the error message
  generated during parsing. It then leverages the Gemini model to
  interpret the error and generate a corrected JSON object.

  Args:
    json_string: The invalid JSON string to be corrected.
    error: The error message generated when attempting to parse
           the json_string.

  Returns:
    A dictionary representing the corrected JSON object, or a
    dictionary containing an "error" key with a descriptive
    error message if correction fails.
  """

    model = GenerativeModel(model_name="gemini-2.0-flash-001")
    prompt = f"""
    You are a JSON correction tool. Your goal is to help users fix invalid JSON strings.
You will receive an input JSON string and an error message describing the problem with the JSON.
Output a corrected JSON string based on the error provided. Ensure the entire JSON output is valid, well-formatted, and addresses any issues mentioned in the error.
Do not include any explanations or markdown in your output. Only return the raw corrected JSON.

Here's an example:
Input JSON:
{{"name": "John, "age": 30, "city": "New York"}}

Error:
Invalid JSON: Expecting ',' delimiter: line 1 column 16 (char 15)

Output JSON:
{{"name": "John", "age": 30, "city": "New York"}}

Now, please correct the following JSON:
Input JSON:
{json_string}

Error:
{error_message}
    """

    logger.info("Trying to fix json....")

    generation_config = {
        "temparature": 0,
        "top_p": 0.95,
    }

    responses = model.generate_content(
        [prompt],

    )

    data = responses.text.strip()
    data = data.replace("```json", "").replace("```", "").strip()

    try:
        valid_json = json_repair.loads(data)
    except json.JSONDecodeError as e:
        logger.error(f"Error fixing JSON: {e}, skipping this item.")
        logger.error(f"Problematic JSON String:{data}")
        return {"error": str(e)}

    return valid_json


def fetch_from_url(url):
    user_agent = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36"

    headers = {
        'User-Agent': user_agent
    }
    try:
        result = dict()
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        # store the website domain in the result
        parsed_url = urlparse(url)
        result['website'] = f"{parsed_url.scheme}://{parsed_url.netloc}"
        # result['website'] = url
        result['html'] = response.text
        logger.info(f"Successfully retrieved HTML from {url}")
    except requests.exceptions.RequestException as e:
        logger.warning(f"Error fetching {url}: {e}")

    return result


def get_html_content(urls=None):
    """
    Fetches and returns the HTML content of multiple web pages.

    Args:
      urls: A list of URLs to scrape.

    Returns:
      A list of strings, where each string contains the HTML content 
      of the corresponding URL.
    """
    if not urls:
        urls = get_urls()

    user_agent = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36"

    html_results = []  # Use a dictionary to store results
    headers = {
        'User-Agent': user_agent
    }
    for url in urls:
        try:
            result = fetch_from_url(url)
            html_results.append(result)
        except requests.exceptions.RequestException as e:
            logger.warning(f"Error fetching {url}: {e}")
    return html_results


def next_page_url(html):
    """Extracts the URL of the next page of articles from a webpage.

    Args:
        html: The HTML content of a webpage.

    Returns:
        The URL of the next page of articles.
    """
    model = GenerativeModel(model_name="gemini-2.0-flash-001")

    prompt = """
    ```html
    {}
    ```
    The HTML above contains a list of articles. At the bottom of the page, there is a
    a link navigate to the next page of articles. Return the URL for this next page of articles. Do not return any other context or metadata.
    The URL should be a string in the following format:  "https://www.example.com/page/2"
    If there is no button to navigate to the next page,
    or you are unsure whether there is a next page, or if you are uncertain about the url you are providing, return an empty string.
    """

    if html:
        responses = model.generate_content([prompt.format(html)])
        next_page_url = responses.text.strip()
    else:
        next_page_url = ""

    if next_page_url == "":
        logger.error(
            "Unable to extract next page URL. No additional content to fetch.")
        return None

    return next_page_url


def extract_datetime_with_gemini(html):
    """Extracts datetime of article publication from article HTML.

    Args:
        html: The HTML content of an article.

    Returns:
        The datetime of the article publication. If the datetime is not found, an empty string is returned. 
        The datetime is returned as a string in the following format: "YYYY-MM-DD HH:MM."
    """

    try:
        generation_config = {"temperature": 0}
        model = GenerativeModel(
            model_name="gemini-1.5-flash-002", generation_config=generation_config)
        prompt = """
        ```html
        {}
        ```
        Extract the date and time of the article publication from the HTML.
        The date and time should be in the following format: "YYYY-MM-DD HH:MM."
        Do not return any other context or metadata. 
        If the date is found but the time is not, return the "HH:MM" section as "12:01".
        If the time is found to be "00:00" or "12:00:00 AM", return the "HH:MM" section as "12:01".
        If the date and time are not found, output an empty string.
        """
        responses = model.generate_content([prompt.format(html)])
        datetime_string = responses.text.strip()
    except Exception as e:
        logger.error(f"Error extracting date from HTML: {e}")
        datetime_string = ""

    return datetime_string


def extract_date_from_news_item(news_item):
    """Retrieves missing dates from a news_item dictionary

    Args:
        news_item: A dictionary with 'title, 'abstract', 'datetime' and 'url' keys.

    Returns:
        The updated news_item with populated datetime key
    """

    datetime_string = news_item.get("datetime", None)
    if not datetime_string:
        url = news_item.get("url", None)
        if url:
            html = fetch_from_url(url)
            if html:
                datetime_string = extract_datetime_with_gemini(html)
                if datetime_string:
                    news_item["datetime"] = datetime_string
                    logger.info(
                        f"Extracted date from HTML for {url}: {datetime_string}")
                else:
                    logger.warning(
                        f"Unable to extract date from HTML for {url}")

    return news_item


def find_oldest_date(news_dict):
    """Finds the oldest date from a list of article dictionaries.

    Args:
        news_dict: A dictionary with two keys:,'news' and 'website'. 'news' is a list of article dictionaries, each with a datetime key.

    Returns:
        The oldest date in the list as a datetime object or None if the list is empty.
    """
    if not news_dict:
        return
    news_list = news_dict.get('news')
    website = news_dict.get('website')
    datetimes = []
    for news_item in news_list:
        # get date string
        # logger.debug(news_item)
        datetime_string = news_item.get("datetime", None)
        if datetime_string:
            try:
                datetime_obj = datetime.strptime(
                    datetime_string, '%Y-%m-%d %H:%M')
                datetimes.append(datetime_obj)
            except ValueError:
                continue
    oldest_datetime = None  # Initialize to track the oldest date

    for date_obj in datetimes:
        if oldest_datetime is None or date_obj < oldest_datetime:
            oldest_datetime = date_obj
    logger.info(f"datetimes for {website}: {datetimes}")
    logger.info(f"oldest datetime for {website}: {oldest_datetime}")
    return oldest_datetime if oldest_datetime else None


def filter_news_by_date_range(news_list, low_datetime, high_datetime):

    if low_datetime > high_datetime:
        raise ValueError("low_datetime cannot be greater than high_datetime")

    filtered_news = []

    for news_item in news_list:
        try:
            # Convert string to datetime object, then extract date
            item_datetime = datetime.strptime(
                news_item['datetime'], '%Y-%m-%d %H:%M')

            if low_datetime <= item_datetime <= high_datetime or item_datetime == "":
                filtered_news.append(news_item)
            # if datetime outside of desired range, don't keep article
        except (KeyError, ValueError):
            # Datetime extractions unsuccessful, keep article anyways
            filtered_news.append(news_item)
            continue

    return filtered_news


def extract_article_with_gemini(html_content):
    """Extracts the article content from HTML content using Gemini and structures it into JSON.

    Args:
        html_content: The HTML content of a webpage (as a string).

    Returns:
        A JSON object containing the extracted article content or an error message.
    """

    try:
        generation_config = {"temperature": 0}
        model = GenerativeModel(
            model_name="gemini-1.5-flash-002", generation_config=generation_config)
        prompt = """
        ```html
        {}
        ```
        Extract the main article present on this page.
        Identify and extract the following information for the article, if available:

        1. **title**: The headline of the article.
        2. **abstract**: A short summary or description of the article.
        3. **datetime**: **datetime**: The date and time the article was published. Format should be: YYYY-MM-DD HH:MM. If the date and/or time is not found, leave the "datetime" field empty. If the HH:MM is "00:00", replace it with "12:01".
        4. **url**: The complete URL of the full article, including the domain.

        **Output Format:**
        Output the extracted information in JSON format, following the structure below:
                {{
                    "title": "News Article Title",
                    "abstract": "Short abstract of the news article...",
                    "datetime": "Publishing date time of the article format should be:YYYY-MM-DD HH:MM",
                    "url": "The complete URL of the full article, including the domain."
                }}
        *Escaping:**

        Escape every double quote (") with \\" and every single quote (') with \\' in the title and abstract fields.
        """

        logger.info('Processing content for {}'.format(
            html_content['website']))

        responses = model.generate_content(
            [prompt.format(html_content['html'])]),

        if responses:
            extracted_data = responses[0].text.strip()
        else:
            raise Exception("No response from Gemini")

        logger.info(f"extracted data: {extracted_data}")
        extracted_data = extracted_data.replace(
            "```json", "").replace("```", "").strip()

        try:
            article = json_repair.loads(extracted_data)
            # adding a flagindicating that this article was manually added
            article['forced'] = True

        except json.JSONDecodeError as e:
            error_message = ''.join(traceback.format_exception(
                type(e), e, e.__traceback__))
            article = fix_json_formatting(extracted_data, error_message)
        except Exception as e:
            logger.error(f"Extract with Gemini error:{e}")

        return {"website": html_content["website"], "news": [article]}

    except Exception as e:
        logger.error(f"Error extracting news from HTML: {e}")
        logger.error(f"Full error stack: {traceback.format_exc()}")
        logger.error(f"Problematic Content: {extracted_data}")
        return {"error": str(e)}


def extract_news_with_gemini(html_content):
    """Extracts news information from HTML content using Gemini and structures it into JSON.

    Args:
        html_content: The HTML content of a webpage (as a string).

    Returns:
        A JSON object containing the extracted news data or an error message.
    """
    try:
        generation_config = {"temperature": 0}
        model = GenerativeModel(
            model_name="gemini-1.5-flash-002", generation_config=generation_config)
        prompt = """
        ```html
        {}
        ```
        Extract the news articles present in the main News section.
        Identify and extract the following information for each article, if available:

        1. **title**: The headline of the news article.
        2. **abstract**: A short summary or description of the article.
        3. **datetime**: **datetime**: The date and time the article was published. Format should be: YYYY-MM-DD HH:MM. If the date and/or time is not found, leave the "datetime" field empty. If the HH:MM is "00:00", replace it with "12:01".
        4. **url**: The complete URL of the full article, including the domain. 

        **Filtering Criteria:**
 
        - Only extract articles from the main News section.
        - Only extract articles that have an abstract.

        **Output Format:**
        Output the extracted information in JSON format, following the structure below:
                {{
                "news": [
                    {{
                    "title": "News Article Title 1",
                    "abstract": "Short abstract of the news article...",
                    "datetime": "Publishing date time of the article format should be:YYYY-MM-DD HH:MM",
                    "url": "The complete URL of the full article, including the domain."
                    }},
                    {{
                    "title": "News Article Title 2",
                    "abstract": "Short abstract of the news article...",
                    "datetime": "Publishing date time of the article format should be:YYYY-MM-DD HH:MM" ,
                    "url": "The complete URL of the full article, including the domain." 
                    }},
                    // ... more news articles
                ]
                }}
        *Escaping:**

        Escape every double quote (") with \\" and every single quote (') with \\' in the title and abstract fields.
        """

        logger.info('Processing content for {}'.format(
            html_content['website']))

        responses = model.generate_content(
            [prompt.format(html_content['html'])]),

        extracted_data = responses[0].text.strip()

        logger.info(f"extracted data: {extracted_data}")
        extracted_data = extracted_data.replace(
            "```json", "").replace("```", "").strip()

        try:
            news = json_repair.loads(extracted_data)
        except json.JSONDecodeError as e:
            error_message = ''.join(traceback.format_exception(
                type(e), e, e.__traceback__))
            news = fix_json_formatting(extracted_data, error_message)
        except Exception as e:
            logger.error(f"Extract with Gemini error:{e}")

        return {"website": html_content["website"], "news": news["news"]}

    except Exception as e:
        logger.error(f"Error extracting news from HTML: {e}")
        logger.error(f"Full error stack: {traceback.format_exc()}")
        logger.error(f"Problematic Content: {extracted_data}")
        return {"error": str(e)}

# helper funtion to extract news, filter by specified range


def format_and_extract(html, news_list, low_datetime, max_pages=MAX_PAGES):
    """
    Extracts news articles from a given HTML page and filters by date range.
    Checks if the oldest article on that page is older than the low_date.
    If it is, method returns news_list. If it is not, it calls itself with the next page HTMl contents.

    Args:
        html: The HTML to extract news from.
        news_list: A list of dictionaries containing news articles.
        low_datetime: bottom threshold for article extraction (no articles extracted from before this datetime)
        max_pages: The maximum number of pages to extract from. Limits the method recurssion.

    Returns:
        news_list: A list of dictionaries containing news articles for a certain website.
        news_counts: A dictionary containing the number of articles per website.
    """

    if max_pages == 0:  # Stop recursion
        return news_list

    # Extract dict with 'website' and 'news' key for input HTML. 'News' value pair
    # is a list of dictionaries of articl info.
    try:
        news_data = extract_news_with_gemini(html)
    except Exception as e:
        logging.warning(
            'Failed to extract news for {}'.format(html.get("website")))
        return

    try:
        # Check the news_data for articles without dates, fetch dates from article htmls
        news_articles = news_data.get("news", [])
        updated_news_articles = []
        with concurrent.futures.ThreadPoolExecutor() as executor:
            futures = [executor.submit(extract_date_from_news_item, news_item)
                       for news_item in news_articles]

            for i, future in enumerate(concurrent.futures.as_completed(futures)):
                if future.result():
                    news_item = future.result()
                    updated_news_articles.append(news_item)
                else:
                    logging.warning(
                        'Failed to extract date for {}'.format(news_articles[i]))

        news_data["news"] = updated_news_articles

        # Get the oldest article date before filtering.
        oldest_datetime = find_oldest_date(news_data)

        # Add articles to news_list and store in Firestore
        news_list.append(news_data)
        save_news(news_list)

        # Add counts to news_counts
        website = news_data.get("website", "Unknown Website")

        if oldest_datetime == None or oldest_datetime < low_datetime:
            # don't check the next page, return list and counts
            return news_list
        else:
            # Get next page URL
            next_url = next_page_url(html)
            # Fetch next page HTML
            next_html = fetch_from_url(next_url)
            max_pages = max_pages - 1
            # Recursive call to get the following page of articles
            next_page_news = format_and_extract(next_html,
                                                [], low_datetime, max_pages)
            temp_news = news_list[0].get("news", [])
            if next_page_news:
                for page_news in next_page_news:
                    temp_news.extend(page_news.get('news', []))
            news_list[0]["news"] = temp_news
            logger.info("Finished multipage retrieval for {}".format(website))
            return news_list

    except json.JSONDecodeError as e:
        logger.error(f"Error decoding JSON: {e}")
        logger.error(f"Full error trace: {traceback.format_exc()}")

        return news_list


def fetch_and_analyze_media(url):

    media_obj = fetch_and_store(url, "fsa_amadeus")

    prompt = """
You are an industry specialist working at Amadeus. Summarize and give structured highlights about this podcast. Those highlights should be focused on:
* **Areas:** Travel distribution, Travel IT Solutions, Airlines, Hospitality, Airport IT.
* **Players:** Amadeus' competitors (Sabre, Travelport), major tech companies (Google, Amazon, Microsoft), OTAs, Metasearch engines, TMCs, Aggregators, Airlines, Hotel chains, Short-term rentals, and key players in each area.
* **Key Topics:** Industry updates on capacity, traffic, forecasts, NDC, biometrics, consolidation, funding, regulations, financial results, sustainability, loyalty, business travel, and changes in strategies.

Finally, make a summary of the content and explain if this has an interest for Amadeus and why.

return a JSON object structured like this:
{
    "summary": "The summary of the podcast.",
    "pov"  :   "Point of view on the podcast from the perspective of Amadeus",
    "highlights": [
        "Highlight 1",
        "Highlight 2",
        "Highlight 3"
    ]
}
    """
    gcs_file = media_obj.get('gcs_file')
    logger.info('Processing content for {}'.format(gcs_file))
    media = Part.from_uri(
        mime_type="video/mp4",
        uri=gcs_file)

    model = GenerativeModel(model_name="gemini-2.0-flash-001")
    responses = model.generate_content(
        [prompt, media],

    )

    extracted_data = responses.text.strip()
    logger.info(f"extracted data: {extracted_data}")
    extracted_data = extracted_data.replace(
        "```json", "").replace("```", "").strip()

    try:
        media_content = json_repair.loads(extracted_data)

        # build a media object and store it in the media collection
        media_obj["summary"] = media_content.get("summary", "")
        media_obj["pov"] = media_content.get("pov", "")
        media_obj["highlights"] = media_content.get("highlights", [])
        media_obj["retrieved_at"] = datetime.now()

        # add into the firestore media collection. The id of the document is the hashed url
        db = get_firestore_client()
        media_collection = db.collection('media')
        media_collection.document(media_obj['hash']).set(media_obj)
        logger.info(f"Media object saved to Firestore: {media_obj['hash']}")
        return media_obj

    except json.JSONDecodeError as e:
        error_message = ''.join(traceback.format_exception(
            type(e), e, e.__traceback__))
        news = fix_json_formatting(extracted_data, error_message)
    except Exception as e:
        logger.error(f"Extract with Gemini error:{e}")


def generate_newsletter_text(news_list, past_newsletters=None, media_list=None):
    """
    Generates a structured newsletter text from a list of news articles
    using Gemini Pro for content creation.

    Args:
        news_list (list): A list of dictionaries, with each dictionary containing 
                          news from a specific website.

    Returns:
        str: The formatted newsletter text.
    """

    # # Retrieve past newsletters from firestore
    db = get_firestore_client()

    valid_top_stories_collection = db.collection('news').where(
        'validated_section', 'in', ['Top News of the Day']).order_by(
        'published_at', direction='DESCENDING').limit(40)

    valid_regional_stories_collection = db.collection('news').where(
        'validated_section', 'in', ['Regional News']).order_by(
        'published_at', direction='DESCENDING').limit(40)

    valid_more_stories_collection = db.collection('news').where(
        'validated_section', 'in', ['More Stories']).order_by(
        'published_at', direction='DESCENDING').limit(40)

    rejected_stories_collection = db.collection('news').where(
        'removed_reason', '!=', '').order_by(
        'published_at', direction='DESCENDING').limit(40)

    valid_top_stories = valid_top_stories_collection.get()
    valid_regional_stories = valid_regional_stories_collection.get()
    valid_more_stories = valid_more_stories_collection.get()
    rejected_stories = rejected_stories_collection.get()

    valid_top_stories_json = [doc.to_dict() for doc in valid_top_stories]
    # keep only the title, abstract and website field
    valid_top_stories_json = [{
        'title': doc['title'],
        'abstract': doc['abstract'],
        'website': doc['website']
    } for doc in valid_top_stories_json]

    valid_regional_stories_json = [doc.to_dict()
                                   for doc in valid_regional_stories]
    # keep only the title, abstract and website field
    valid_regional_stories_json = [{
        'title': doc['title'],
        'abstract': doc['abstract'],
        'website': doc['website']
    } for doc in valid_regional_stories_json]

    valid_more_stories_json = [doc.to_dict() for doc in valid_more_stories]
    # keep only the title, abstract and website field
    valid_more_stories_json = [{
        'title': doc['title'],
        'website': doc['website']
    } for doc in valid_more_stories_json]

    rejected_stories_json = [doc.to_dict() for doc in rejected_stories]
    valid_top_stories = json.dumps(valid_top_stories_json, default=str)
    valid_regional_stories = json.dumps(
        valid_regional_stories_json, default=str)
    valid_more_stories = json.dumps(valid_more_stories_json, default=str)
    rejected_stories = json.dumps(rejected_stories_json, default=str)

    formatted_news_data = json.dumps(news_list, default=str)
    if media_list:
        formatted_media_data = json.dumps(media_list, default=str)
    else:
        formatted_media_data = ""

    config = get_config()
    if not config or not config['prompt_daily']:
        raise Exception('Invalid configuration or prompt_daily is not set')

    prompt = f"""
    {config['prompt_daily']}

        **Prioritization:**

* **Relevance:** Prioritize news that directly impacts Amadeus's business, its competitors, or its key customer segments.
* **Quantitative Metrics:**  Prioritize news that involves significant funding rounds (above $5M), mergers, acquisitions, or changes in market share. 

**Rejected News Examples:**

 {rejected_stories}

    The output format should be a well formatted JSON object, formatted as:
    {{
      date: "DD-MM-YYYY",
      "categories": {{
      "Top News of the Day": [
        {{
          "website": "source website",
          "title": "title of the news”,
          "abstract": "abstract of the news",
          "url":"link to the full article",
          "reason":"explanation on why this news is important for Amadeus",
          "duplicate_candidates": [optional - full url of the artcle pointing to the duplicate news]
        }}
      ],"Podcasts of the Day": [
        {{
          "website": "source website",
          "title": "title of the podcast”,
          "abstract": "summary of the podcast",
          "url":"link to the podcast",
          "reason":"explanation on why this news is important for Amadeus",
          "duplicate_candidates": [optional - full url of the artcle pointing to the duplicate news]
        }}
      ],
      "Regional News": {{
        "Region name (i.e North America)": [
          {{
            "website": "source website",
            "title": "title of the news”",
            "abstract": "abstract of the news",
            "url":"link to the full article",
            "reason":"explanation on why this news is important for Amadeus",
            "duplicate_candidates": [optional - full url of the artcle pointing to the duplicate news]
            }}
          ]
        }},
        "More Stories": [
          {{
            "website": "source website",
            "title": "title of the news",
            "url":"link to the full article",
            "reason":"explanation on why this news is important for Amadeus",
            "duplicate_candidates": [optional - full url of the artcle pointing to the duplicate news]
          }}
        ]
    }}

Input News:
        {json.dumps(news_list,ensure_ascii=False, default=str)}

Newsletter:
              
      
    """

    config = GenerationConfig(
        response_mime_type="application/json", temperature=0.6)
    model = GenerativeModel(
        model_name="gemini-1.5-pro-002", generation_config=config)
    responses = model.generate_content(
        [prompt],

    )

    newsletter = responses.text.strip()
    newsletter = newsletter.replace("```json", "").replace("```", "").strip()
    try:
        newsletter_json = json_repair.loads(newsletter)
    except Exception as e:
        newsletter_json = fix_json_formatting(newsletter, e)

    return newsletter_json


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
    db = get_firestore_client()
    past_digests_collection = db.collection('digests').order_by(
        'end_date', direction='DESCENDING').limit(7)
    past_digests = past_digests_collection.get()
    # check if there are any documents in the collection
    if not past_digests:
        past_digests = ""
    # extract the json_data field from each document
    past_digests_json = [doc.to_dict()['json_data']
                         for doc in past_digests]
    past_digests = json.dumps(past_digests_json, default=str)

    generation_config = {"temperature": 0,
                         "response_mime_type": "application/json"}
    model = GenerativeModel(model_name="gemini-1.5-pro-002",
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
    db = get_firestore_client()

    past_digests_collection = db.collection('digests').order_by(
        'end_date', direction='DESCENDING').limit(7)
    past_digests = past_digests_collection.get()
    # check if there are any documents in the collection
    if not past_digests:
        past_digests = ""
    # extract the json_data field from each document
    past_digests_json = [doc.to_dict()['json_data']
                         for doc in past_digests]
    past_digests = json.dumps(past_digests_json, default=str)

    generation_config = {"temperature": 0,
                         "response_mime_type": "application/json"}
    model = GenerativeModel(model_name="gemini-1.5-pro-002",
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


def regenerate_digest_highlights(digest, highlights_news_list):
    """Regenerates the 'Highlights of the Week' section of the digest using only articles included in the 'Highlights News Items' section.

    Args:
        digest: The digest JSON object.
        highlights_news_list: A list of dictionaries containing the news items to be included in the highlights section.

    Returns:
        A JSON object containing the regenerated 'Highlights of the Week' section.
    """

    prompt = """
    Rewrite the 'Highlights of the Week' section of the digest below using only articles included in the 'Highlights News Items' section below.
    Remove all highlights that do not reference items in the news list, and add new highlights for items in the news list not yet referenced.
    
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
                    "website": "source website"
                }}
                // ... more news articles
            ]
        }}
    }}

    ** Digest **:
    {}

    ** Highlights News Items**
    {}
    """

    formatted_digest = json.dumps(digest, default=str)

    generation_config = {"temperature": 0,
                         "response_mime_type": "application/json"}
    model = GenerativeModel(model_name="gemini-1.5-pro-002",
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

def reformat_article_for_digest(nl_article):
    """
    Reformats article from newsletter format to digest format. Generates key_message and context fields.

    Args:
        nl_article: Article dictionary in newsletter form: {'abstract':'', 'title':'', 'website':'', 'full_text':'', 'published_at':''}
    
    Returns:
        digest_article: Article dictionary in digest form: {'key_message':'', 'context':'', 'title':'', 'url':'', 'website':''}
    """

    prompt=    """
    Reformat the ' newsletter article' below to match the following output format:
                    
                    {{
                        "key_message": "one or two sentence summary of the article's key message",
                        "context": "additional context or description",
                        "title": "title of the article",
                        "url": "link to the full article"
                        "website": "source website"
                    }}
    
    Additional instructions on generating the context field:
    * 'context' should explain why the story is important, what broader industry trend it reflects, and why it is meaningful given other ongoing trends.
    * Keep the statement short and to the point. 
    * Do not include phrases such as "This news is significant for Amadeus because...". 
    * Do not restate what is already said in the key message.

    The output format should be a well formatted JSON object. Do not place the complete output text in brackets ("[]").
     
    Newsletter article:
    {}
    """

    generation_config = {"temperature": 0,
                         "response_mime_type": "application/json"}
    model = GenerativeModel(model_name="gemini-1.5-pro-002",
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

def find_duplicate_news(news_list, simplified_published_newslist):
    """
    Removes news articles from the news_list that are talking about news
    already published in a previous newsletter using Gemini Pro.

    Args:
        news_list (list): A list of dictionaries, with each dictionary containing
                          news from a specific website.

    Returns:
        list: The updated news_list with duplicate news articles removed.
    """

    prompt = """
You are an experienced travel industry editor, tasked with identifying duplicate articles

Your goal is to identify articles that discuss the **EXACT SAME** news as already covered in the provided past newsletters.  
**Carefully look for strong indicators of duplication:**
* **Identical company names:** The articles should mention the same company in the same context (e.g., a product launch by the same company).
* **Identical facts:** The articles should report the same specific facts or figures (e.g., the same amount of investment, the same number of flights).
* **Identical events:** The articles should focus on the same event or announcement.

**Avoid identifying duplicates based on:**
* **General themes or trends:** The articles should not be marked as duplicates just because they discuss similar topics or industry trends.
* **Similar language:** The articles should not be marked as duplicates just because they use similar language or phrases.

If unsure, do not identify the article as a duplicate.

you are given a list of articles to qualify as input. Compare it with the existing corpus and flag it as a duplicate using the above rules.
Output the url of the input articles that are duplicates in the following JSON format:
[
  {{
    "url":"link to the full article that is a duplicate",
    "published_url":"link of the article that was already published",
  }}
]

input articles:
{}

existing articles:
{}

Duplicates(url):
    """

    model = GenerativeModel(model_name="gemini-1.5-pro-002", generation_config=GenerationConfig(
        response_mime_type="application/json", temperature=0.6))

    prompt = prompt.format(
        json.dumps(news_list, default=str), json.dumps(simplified_published_newslist, default=str))

    responses = model.generate_content(
        [prompt],

    )

    filtered_news = responses.text.strip()
    filtered_news = filtered_news.replace(
        "```json", "").replace("```", "").strip()
    filtered_news = json_repair.loads(filtered_news)

    return filtered_news


def transform_newsletter(newsletter_json):
    """
    Transforms a newsletter JSON into a dictionary with article URLs as keys and
    relevant information as values.

    Args:
        newsletter_json (dict): The newsletter JSON.

    Returns:
        dict: A dictionary with article URLs as keys and a dictionary of section,
              region (if applicable), and title as values.
    """

    article_dict = {}
    # if this is a DocumentSnnapshot document, get the dict
    if isinstance(newsletter_json, DocumentSnapshot):
        newsletter_json = newsletter_json.to_dict()

    if 'json_data' in newsletter_json:
        newsletter_json = json.loads(newsletter_json['json_data'])

    if not isinstance(newsletter_json, dict):
        newsletter_json = json.loads(newsletter_json)
        print(newsletter_json)
    for category_name, category_items in newsletter_json["categories"].items():
        if isinstance(category_items, list):
            for item in category_items:
                if "url" in item:
                    article_dict[item["url"]] = {
                        "section": category_name,
                        "region": None,
                        "title": item.get("title")
                    }
        elif isinstance(category_items, dict):
            for region_name, region_items in category_items.items():
                for item in region_items:
                    if "url" in item:
                        article_dict[item["url"]] = {
                            "section": category_name,
                            "region": region_name,
                            "title": item.get("title")
                        }

    return article_dict


def get_top_sources(top_n, corpus_size=10):
    """
    Retrieves the last n newsletters from Firestore and analyzes the source 
    websites of the articles. Prints a breakdown of the articles by source.

    Args:
        n (int): The number of newsletters to retrieve.
    """

    db = get_firestore_client()
    newsletters_collection = db.collection('newsletters').order_by(
        'end_date', direction='DESCENDING').limit(corpus_size)
    newsletters = newsletters_collection.get()

    article_sources = {}

    for newsletter_doc in newsletters:
        newsletter_data = json.loads(newsletter_doc.to_dict()['json_data'])
        # Transform the newsletter using your existing function
        transformed_newsletter = transform_newsletter(newsletter_data)
        for url, article_info in transformed_newsletter.items():
            # Extract domain name from URL
            domain_name = urlparse(url).netloc
            # Increment count for the domain
            article_sources[domain_name] = article_sources.get(
                domain_name, 0) + 1

    total_articles = sum(article_sources.values())

    # Sort the article sources by percentage in descending order
    sorted_sources = sorted(article_sources.items(
    ), key=lambda item: item[1] / total_articles, reverse=True)

    return [website for website, count in sorted_sources[:top_n]]


def select_important_news(remaining_news_list):
    """
    Adds remaining important news from the news list to the generated newsletter in parallel.

    Args:
        generated_newsletter (dict): The generated newsletter.
        remaining_news_list (list): The list of remaining news articles.
        past_newsletters (list): The list of past newsletters.

    Returns:
        dict: The updated generated newsletter with additional important news.
    """

    chunk_size = 10  # Adjust this based on your needs
    chunked_news = [remaining_news_list[i:i + chunk_size]
                    for i in range(0, len(remaining_news_list), chunk_size)]
    filtered_urls = []

    with concurrent.futures.ThreadPoolExecutor() as executor:
        futures = [executor.submit(
            process_news_chunk, chunk) for chunk in chunked_news]

        for future in concurrent.futures.as_completed(futures):
            result = future.result()
            # Add selected news to the generated newsletter
            filtered_urls.extend(result)

    return filtered_urls


def process_news_chunk(news_chunk):
    """
    Processes a chunk of news articles to select the most important ones.

    Args:
        generated_newsletter (dict): The generated newsletter.
        news_chunk (list): The chunk of news articles.
        past_newsletters (list): The list of past newsletters.

    Returns:
        list: A list of selected important news articles.
    """

    prompt = f"""
    You are an experienced travel industry editor, tasked with selecting the most important news articles from a list.
    This must be a strict process. It is OK if you don't find any important news. Quality over quantity!


    The following news articles are from sources that were not included in the initial newsletter.
    Please carefully consider these articles and select only the most important ones for Amadeus, based on the criteria provided below:
    When selecting news, consider:

* **Areas:** Travel distribution, Travel IT Solutions, Airlines, Hospitality, Airport IT.
* **Key Players and Competitors:**
    * **Aggregator:** Travelfusion, Duffel, Kyte, Atriis, Aeronology, TPConnects
    * **Airline IT:** PROS, Datalex, ATPCO
    * **Airport IT:** SITA, NEC, Thales, Collins Aerospace
    * **Consolidator:** Aerticket
    * **Corporate Travel:** Concur, Amex GBT, Travelperk, Spotnana, CWT, CTM, Navan, Deem, Serko, Chase Travel, BCD
    * **Data:** STR, OAG
    * **Distribution IT:** Accelya 
    * **GDS:** Sabre, Travelport, Travelsky
    * **Hospitality:** Oracle, Hyatt, Marriott, Accor, Hilton, Hotelbeds, Cendyn, Siteminder, Shiji, Cloudbeds, Mews, Rategain, D-Edge, IDS
    * **Metasearch:** Kayak, trivago, Google, Skyscanner
    * **OTA:** Expedia, Booking, Tripadvisor, edreams, Trip.com, Despegar, MakemyTrip, Priceline, Hopper, Kiwi.com, FlightCenter, etravel, Fliggy
    * **Payments:** Wex, Revolut, Stripe
    * **Rail:** Trainline
    * **STR:** Airbnb
    * **Super app:** Uber, Grab
    * **T&A:** GetYourguide, Klook
    * **Short term rental:** Vrbo
* **Key Topics:** Industry updates on capacity, traffic, forecasts, NDC, AI, biometrics, consolidation, funding, regulations, financial results, mergers and acquisitions, sustainability, loyalty, business travel, and changes in strategies.

Prioritize news based on:

* **Quantitative criteria:** Size of players, funding amounts (above $5M), impact on market share.
* **Qualitative criteria:** Involvement of key players, impact on the travel industry, potential impact on Amadeus's business, relevance to Amadeus's customer segments, avoiding repetitive topics, and focusing on global rather than local news.
* **User control: articles having the flag {{forced: True}} must be added in the newsletter, either in the Top News of the Day or Regional News section.**
* **Source website:** priority websites are skift, theBeat, sabre,Phocuswire and businesstravelnews

Do not include stories covering the following topics:

* News focused on Amadeus itself, unless in connection to additional major players (eg. Google, Mariot, United Airlines)
* News included in previous newsletters, including from separate sources – list of previous newsletter provided below
* Industries to avoid: Cargo, Cruises or cruise lines, Entertainment, Amusement parks, Events
* Overly local news that lacks broader industry implications
* Airlines opening new destinations or new routes
* Awards given or received by industry players
* New appointments or hires, unless by the biggest industry players
* New airline cabin designs
* Purchase of new aircrafts
* Codeshare agreements
* Interviews of industry professionals

Format the output as a JSON list article urls.
example:
[
"article_url1",
"article_url2",
"article_url3"
]

    Input News:
    {json.dumps(news_chunk, indent=4, ensure_ascii=False,default=str)}


    Selected Important News:
    """
    options = GenerationConfig(
        response_mime_type="application/json", temperature=0.6)
    model = GenerativeModel(
        model_name="gemini-1.5-pro-002", generation_config=options)
    responses = model.generate_content([prompt])

    selected_news = responses.text.strip()
    selected_news = selected_news.replace(
        "```json", "").replace("```", "").strip()

    try:
        selected_news_json = json_repair.loads(selected_news)
    except Exception as e:
        selected_news_json = fix_json_formatting(selected_news, e)

    return selected_news_json


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

    model = GenerativeModel(model_name="gemini-2.0-flash-001")
    responses = model.generate_content(
        [prompt],)

    modified_markdown = responses.text

    return modified_markdown

def search_news(
    project_id: str,
    location: str,
    engine_id: str,
    search_query: str,
) -> List[discoveryengine.SearchResponse]:
    client_options = (
        ClientOptions(api_endpoint=f"{location}-discoveryengine.googleapis.com")
        if location != "global"
        else None
    )

    client = discoveryengine.SearchServiceClient(client_options=client_options)

    serving_config = f"projects/{project_id}/locations/{location}/collections/default_collection/engines/{engine_id}/servingConfigs/default_config"

    content_search_spec = discoveryengine.SearchRequest.ContentSearchSpec(
        snippet_spec=discoveryengine.SearchRequest.ContentSearchSpec.SnippetSpec(
            return_snippet=True
        ),
        summary_spec=discoveryengine.SearchRequest.ContentSearchSpec.SummarySpec(
            summary_result_count=5,
            include_citations=True,
            ignore_adversarial_query=True,
            ignore_non_summary_seeking_query=True,
            model_prompt_spec=discoveryengine.SearchRequest.ContentSearchSpec.SummarySpec.ModelPromptSpec(
                preamble="YOUR_CUSTOM_PROMPT"
            ),
            model_spec=discoveryengine.SearchRequest.ContentSearchSpec.SummarySpec.ModelSpec(
                version="stable",
            ),
        ),
    )

    request = discoveryengine.SearchRequest(
        serving_config=serving_config,
        query=search_query,
        page_size=5,
        content_search_spec=content_search_spec,
        query_expansion_spec=discoveryengine.SearchRequest.QueryExpansionSpec(
            condition=discoveryengine.SearchRequest.QueryExpansionSpec.Condition.AUTO,
        ),
        spell_correction_spec=discoveryengine.SearchRequest.SpellCorrectionSpec(
            mode=discoveryengine.SearchRequest.SpellCorrectionSpec.Mode.AUTO
        ),
    )

    response = client.search(request)

    return response

def extract_results(response):
    formatted_response = {}
    articles = []

    results = response.results
    for idx, result in enumerate(results):
        article = {}
        for key, value in result.document.struct_data.items():
            article[key] = value
        derived_struct_data = recurse_proto_marshal_to_dict(result.document.derived_struct_data)
        if derived_struct_data['snippets']['snippet_status'] == 'SUCCESS':
            article['snippet'] = derived_struct_data['snippets']['snippet']
        articles.append(article)

    formatted_response['articles'] = articles

    if response.summary.summary_with_metadata.summary:
        formatted_response['summary'] = response.summary.summary_with_metadata.summary

    return formatted_response

def recurse_proto_marshal_to_dict(object):
    new_dict = {}
    for k, v in object.items():
      if not v:
        continue
      elif isinstance(v[0], maps.MapComposite):
          v = recurse_proto_marshal_to_dict(v[0])
      new_dict[k] = v

    return new_dict 
