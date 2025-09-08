import concurrent.futures
import json
import traceback
from vertexai.generative_models import GenerativeModel
from google.cloud import firestore
from firebase_helpers import (
    get_urls)
from newsletter_generation import (
    extract_news_with_gemini,
    fetch_from_url,
    get_html_content, 
)
from utils import generate_random_id, get_logger
from server.bigquery_helpers import (insert_bq_rows, save_news_to_bigquery, update_url_hash_rows)
from datetime import datetime, timezone, date, timedelta

MAX_PAGES = 5
BQ_BATCH_TABLE_ID = "fsa-amadeus.competitive_intel.batches_v2"
BQ_URL_HASH_TABLE_ID = "fsa-amadeus.competitive_intel.url_hashes"

db = firestore.Client()
logger = get_logger()
# Function that incrementally fetches news from a list of given websites
# and saves them to a Firestore database.
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
            model_name="gemini-1.5-flash-001", generation_config=generation_config)
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

def format_and_extract(html, news_dict, max_pages=MAX_PAGES):
    """
    Extracts news articles from a given HTML page and filters by date range.
    Checks if the oldest article on that page is older than the low_date.
    If it is, method returns news_list. If it is not, it calls itself with the next page HTMl contents.

    Args:
        html: The HTML to extract news from.
        news_dict: A dictionary containing two k/v paris: the website name and a list of articles.
        low_datetime: bottom threshold for article extraction (no articles extracted from before this datetime)
        max_pages: The maximum number of pages to extract from. Limits the method recurssion.

    Returns:
        news_list: A list of dictionaries containing news articles for a certain website.
        news_counts: A dictionary containing the number of articles per website.
    """

    if max_pages == 0:  # Stop recursion
        return news_dict

    # Extract dict with 'website' and 'news' key for input HTML. 'News' value pair
    # is a list of dictionaries of articl info.
    try:
        news_data = extract_news_with_gemini(html)
    except Exception as e:
        logger.warning(
            'Failed to extract news for {}'.format(html.get("website")))
        return

    try:
        # Check the news_data for articles without dates, fetch dates from article htmls
        news_articles = news_data.get("news", [])
        updated_news_articles = []
        # Extract article dates, add to article objects, and update the news_data["news"] list
        with concurrent.futures.ThreadPoolExecutor() as executor:
            futures = [executor.submit(extract_date_from_news_item, news_item)
                       for news_item in news_articles]

            for i, future in enumerate(concurrent.futures.as_completed(futures)):
                if future.result():
                    news_item = future.result()
                    updated_news_articles.append(news_item)
                else:
                    logger.warning(
                        'Failed to extract date for {}'.format(news_articles[i]))

        news_data["news"] = updated_news_articles # retrieved news
        # Add articles to news_list and store in Firestore
        if "news" in news_dict:
            news_dict["news"].append(news_data["news"])
        else:
            news_dict["news"] = news_data["news"]
        news_dict["website"] = news_data["website"]

        news_dict = save_news_to_bigquery(news_dict)
        return news_dict
        
    except json.JSONDecodeError as e:
        logger.error(f"Error decoding JSON: {e}")
        logger.error(f"Full error trace: {traceback.format_exc()}")

        return news_dict

def fetch_news():
    urls_to_retrieve = get_urls()
    logger.info("---------------------------------------")
    logger.info("URLs to retrieve:")
    logger.info(urls_to_retrieve)
    logger.info("---------------------------------------")

    if len(urls_to_retrieve) > 0:
        html_results = get_html_content(urls=urls_to_retrieve)

    news_list = []

    for html in html_results:
        if html:
            result = format_and_extract(html, {})  # Call format_and_extract directly
            if result:
                news_added = result["news"]
                website = result["website"]
                url_hashes = result["url_hashes"]
                news_list.append({"website": website, "news": news_added, "url_hashes": url_hashes})
    # if the retrieval was successfull, writing the batch object to the database:
    if len(news_list) > 0:
        # create a new batch document in Firestore
        batch_id = generate_random_id()
        run_datetime = datetime.now(timezone.utc).isoformat()
        batch_data = [{
            "batch_id": batch_id,
            "news_count": sum([len(news["news"]) for news in news_list]),
            "run_datetime": run_datetime,
            "websites": [{"website": news["website"], "count": len(news["news"])} for news in news_list],
        }]
        batch_result = insert_bq_rows(BQ_BATCH_TABLE_ID, batch_data)
        if batch_result:
            logger.info(
                f"Batch {batch_id} created with {batch_data[0]['news_count']} news articles.")
        # update url hash table
        url_hash_rows = [{"website": news["website"], "url_hashes": news["url_hashes"], "batch_id": batch_id, "run_datetime": run_datetime} for news in news_list]
        url_hash_result = update_url_hash_rows(url_hash_rows)
        if url_hash_result:
            logger.info(
                f"URL Hashes updated for batch {batch_id}"
            )
    else:
        logger.info("No new news articles found since the last batch run.")


if __name__ == "__main__":

    fetch_news()
