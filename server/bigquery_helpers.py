import hashlib
import datetime
from google.cloud import bigquery
from utils import get_logger

BQ_NEWS_TABLE_ID = "fsa-amadeus.competitive_intel.news_v2"
BQ_BATCH_TABLE_ID = "fsa-amadeus.competitive_intel.batches_v2"
BQ_URL_HASH_TABLE_ID = "fsa-amadeus.competitive_intel.url_hashes"

bq_client = bigquery.Client()
logger = get_logger()

def save_news_to_bigquery(news_dict):
    """
    Adds new rows to a BigQuery table for articles from a given website.
    Skips fields that are not present in the data dictionary.

    Args:
        news_dict: A dictionary containing the data to insert. Keys should match the field names in the BigQuery schema.
    
    Returns:
        Updated news_dict with list[str] of url_hashes per website
    """

    # Get table schema
    table = bq_client.get_table(BQ_NEWS_TABLE_ID)
    schema_fields = [field.name for field in table.schema]
    news_items = news_dict["news"]
    
    rows_to_insert = []
    # Iterate over news_list
    for news_item in news_items:
        if not isinstance(news_item, dict):
            logger.info(f"Skipping invalid news item: {news_item}")
            continue
        # Prepare input data
        url = news_item.get('url')
        if not url:
            logger.info(f"Skipping news item without URL: {news_item}")
            continue
        news_item['url_hash'] = hashlib.sha256(url.encode()).hexdigest() if url else None
        news_item["Synced to Datastore"] = False


        # Prepare row data, skipping missing fields
        row_to_insert = {}
        for key in schema_fields:
            row_to_insert["website"] = news_dict["website"]
            if key in news_item:
                if isinstance(news_item[key], datetime.datetime):  # Check for other datetime objects
                    news_item[key] = news_item[key].isoformat()
                row_to_insert[key] = news_item[key]
        if 'datetime' in news_item:
            row_to_insert['published_at'] = news_item['datetime']
        
        rows_to_insert.append(row_to_insert)
    
    # Remove duplicates and non-dictionaries 
    cleaned_rows = []
    url_hashes = set()

    for row in rows_to_insert:
        if isinstance(row, dict) and 'url_hash' in row:
            url_hash = row['url_hash']
            if url_hash not in url_hashes:
                url_hashes.add(url_hash)
                cleaned_rows.append(row)
    

    # Only add new articles
    prev_day_ids = get_latest_website_hashes(news_dict["website"])
    todays_news = cleaned_rows
    if prev_day_ids:
        todays_news = [row for row in cleaned_rows if row['url_hash'] not in prev_day_ids]
        rows_removed = len(cleaned_rows) - len(todays_news)
        logger.info(f"Removed {rows_removed} articles from site {news_dict['website']}")

    # Insert row
    if todays_news:
        row_ids = [row['url_hash'] for row in todays_news]
        errors = bq_client.insert_rows_json(BQ_NEWS_TABLE_ID, todays_news, row_ids=row_ids, skip_invalid_rows=True)
        if errors == []:
           logger.info(f"{len(todays_news)} new articles added from {todays_news[0]['website']}")
        else:
           logger.info(f"Encountered errors while inserting row: {errors}")
    
    news_dict["news"] = todays_news

    # Return all hashes attempted, not just added, so later runs can catch and 
    # prevent from adding the same articles
    news_dict["url_hashes"] = list(url_hashes)
    return news_dict

def update_url_hash_rows(row_data: list):

    rows_to_insert = []
    for row in row_data:
        website = row["website"]
        delete_query = f"""
        DELETE FROM `{BQ_URL_HASH_TABLE_ID}`
        WHERE website = '{website}'
        """
        try:
            delete_job = bq_client.query(delete_query)
            delete_job.result()
        except Exception as e:
            logger.error(f"Error deleting rows from url_hashes table: {e}")
            continue

        if delete_job.num_dml_affected_rows > 0:
            logger.info(f"Deleted {delete_job.num_dml_affected_rows} row(s) with website = '{website}'")
        
        rows_to_insert.append(row)
    
    result = insert_bq_rows(BQ_URL_HASH_TABLE_ID, rows_to_insert)

    return result

def insert_bq_rows(bq_table: str, row_data: list):

    table = bq_client.get_table(bq_table)  # Get the table object

    errors = bq_client.insert_rows_json(table, row_data)

    if errors == []:
        logger.info(f"New row inserted to table {bq_table}.")
        return True
    else:
        logger.error(f"Encountered errors while inserting row: {errors}")
        return False

def get_latest_website_hashes(website):
    """
    Fetches the list of article_ids (hashes) for a given website from the most 
    recent entry in the BigQuery table.

    Args:
        client: A BigQuery client object.
        table_id: The ID of the BigQuery table (e.g., "your-project.your_dataset.batches_v2").
        website: The website for which to retrieve the hashes.

    Returns:
        A list of strings representing the article_ids (hashes), or None if no data is found.
    """
    query = f"""
        SELECT url_hashes
        FROM `{BQ_URL_HASH_TABLE_ID}` AS hashes
        WHERE website = '{website}'
    """
    
    query_job = bq_client.query(query)
    results = query_job.result()  # Waits for job to complete

    for row in results:
        return row.url_hashes  # Extract the list of hashes
    return None  # No data found