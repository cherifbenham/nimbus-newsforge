import concurrent.futures
from src.core.utils.firebase_helpers import (
    get_firestore_client)
from src.core.process import (
    get_html_content,
    format_and_extract, get_urls
)
from src.core.utils.logger import get_logger
from datetime import datetime, timezone, date, timedelta

logger = get_logger()

# Function that incrementally fetches news from a list of given websites
# and saves them to a Firestore database.


def fetch_news():
    urls_to_retrieve = get_urls()
    logger.info("---------------------------------------")
    logger.info("URLs to retrieve:")
    logger.info(urls_to_retrieve)
    logger.info("---------------------------------------")

    if len(urls_to_retrieve) > 0:
        html_results = get_html_content(urls=urls_to_retrieve)

    # Get the last successfull batch run datetime from the database
    db = get_firestore_client()
    # Query the batches collection and retrieve the last batch run based on run_datetime
    last_batch_run = db.collection("batches").order_by(
        "run_datetime", direction="DESCENDING").limit(1).get()
    last_batch_run_datetime = None
    if last_batch_run:
        last_batch_run_datetime = last_batch_run[0].get("run_datetime")
    else:
        logger.info("No last batch run found in the database.")
        # defaulting the last_batch_run_datetime to now-3 days
        last_batch_run_datetime = datetime.now(
            timezone.utc) - timedelta(days=3)

    last_batch_run_datetime = last_batch_run_datetime.date()

    logger.info("Last batch run datetime: " + str(last_batch_run_datetime))

    news_list = []

    with concurrent.futures.ThreadPoolExecutor() as executor:
        futures = [
            executor.submit(format_and_extract, html,
                            [], last_batch_run_datetime)
            for html in html_results
            if html
        ]

        for i, future in enumerate(concurrent.futures.as_completed(futures)):
            if future.result():
                for website_result in future.result():
                    news_dict = website_result["news"]
                    website = website_result["website"]

                    news_list.append({"website": website, "news": news_dict})
        # if the retrieval was successfull, writing the batch object to the database:
        if len(news_list) > 0:
            # create a new batch document in Firestore
            batch_id = db.collection("batches").document().id
            batch_data = {
                "batch_id": batch_id,
                "run_datetime": datetime.now(timezone.utc),
                "news_count": sum([len(news["news"]) for news in news_list]),
                "websites": [{news["website"]: len(news["news"])} for news in news_list],
            }
            db.collection("batches").document(batch_id).set(batch_data)
            logger.info(
                f"Batch {batch_id} created with {len(news_list)} news articles.")
        else:
            logger.info("No new news articles found since the last batch run.")


if __name__ == "__main__":

    fetch_news()
