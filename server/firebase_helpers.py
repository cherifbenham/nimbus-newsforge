from flask import Flask, request, jsonify
from google.cloud import firestore
from datetime import (datetime, timedelta)
from google.cloud.firestore import DocumentSnapshot
from urllib.parse import urlparse
from utils import *
import json
import hashlib
import logging
# from google.cloud.logging import *

from classes.Newsletter import *

app = Flask(__name__)
# logging = get_logging()

# Initialize Firestore client
db = firestore.Client()


def save_news(news_list):

    # store all the news into firestore, in the news collection
    for news_item in news_list:
        website = news_item['website']
        news_data = news_item['news']
        for news in news_data:
            try:
                url = news.get('url')
                if not url:
                    logging.info(
                        f"Storage - Skipping news with no URL: {news}")
                    continue
                # Using the URL as the unique ID. To prevent too long document ID, we use SHA256 hash of the URL
                url_hash = hashlib.sha256(url.encode()).hexdigest()
                news_doc_ref = db.collection('news').document(url_hash)
                news_doc_ref.set({
                    'website': website,
                    'published_at': (datetime.strptime(
                        news.get('datetime'), '%Y-%m-%d %H:%M') if news.get('datetime') else None),
                    'title': news.get('title'),
                    'abstract': news.get('abstract'),
                    'full_text': "",
                    'url': url
                })
            except Exception as e:
                logging.info(f"Storage - Skipping news with error: {e}")
                continue


def get_last_week_newsletters(start_datetime, end_datetime):
    """Retrieves newsletters from Firestore within a date range.

    Args:
        start_datetime (datetime): The start date and time of the range.
        end_datetime (datetime): The end date and time of the range.

    Returns:
        A generator of DocumentSnapshots representing the newsletters, or None if no newsletters are found.
    """
    newsletter_ref = db.collection('newsletters')

    query = newsletter_ref.where(filter=firestore.FieldFilter('start_date', '>=', start_datetime)) \
        .where(filter=firestore.FieldFilter('end_date', '<=', end_datetime))

    docs = query.stream()
    # A list of newsletter dictionaries. Key values: 'end_date' , 'json_data', 'start_date'
    existing_newsletters = []
    for doc in docs:
        existing_newsletters.append(Newsletter.from_serialized(doc.to_dict()))
    if existing_newsletters:
        return existing_newsletters


def get_past_digests(n):
    try:
        digests_ref = db.collection('digests')
        digests = digests_ref.order_by(
            'start_date', direction=firestore.Query.DESCENDING).limit(n).get()
        # Convert Firestore documents to dictionaries
        digests_list = [digest.to_dict() for digest in digests]

        if digests_list:
            return digests_list
        else:
            return None
    except Exception as e:
        logging.error(f"Error retrieving past digests: {e}")
        return None


def get_newsletter_by_id(newsletter_id):
    """Retrieves a newsletter from Firestore by its ID.

    Args:
        id (str): The ID of the newsletter.

    Returns:
        A DocumentSnapshot representing the newsletter, or None if not found.
    """
    newsletter_doc_ref = db.collection('newsletters').document(newsletter_id)
    newsletter_doc = newsletter_doc_ref.get()

    if newsletter_doc.exists:
        return newsletter_doc
    else:
        return None


def get_digest_by_id(digest_id):
    """Retrieves a digest from Firestore by its ID.

    Args:
        id (str): The ID of the digest.

    Returns:
        A DocumentSnapshot representing the digest, or None if not found.
    """
    digest_dic_ref = db.collection('digests').document(digest_id)
    digest_doc = digest_dic_ref.get()
    if digest_doc.exists:
        return digest_doc
    else:
        return None


def update_newsletter(newsletter_id, newsletter_data):
    try:
        # update the newsletter in firestore, in the newsletters collection
        newsletter_doc_ref = db.collection(
            'newsletters').document(newsletter_id)
        newsletter_doc_ref.update({
            'json_data': json.dumps(newsletter_data, default=str)
        })
    except Exception as e:
        logging.error(f"Error updating article: {e}")
        raise e


def update_digest(digest_id, digest_dict):
    try:
        # update the digest in firestore, in the digests collection
        digest_doc_ref = db.collection('digests').document(digest_id)
        digest_doc_ref.update({
            'digest': digest_dict
        })
    except Exception as e:
        logging.error(f"Error updating article: {e}")
        raise e


def update_article(article_url, data):
    try:
        # update the article in firestore, in the articles collection
        article_id = hashlib.sha256(article_url.encode()).hexdigest()
        newsletter_doc_ref = db.collection('news').document(article_id)
        newsletter_doc_ref.update(data)
    except Exception as e:
        logging.error(f"Error updating article: {e}")
        raise e


def save_newsletter(newsletter, start_date, end_date):
    newsletter_doc_ref = db.collection('newsletters').document()
    newsletter_doc_ref.set({
        'start_date': start_date,
        'end_date': end_date,
        'json_data': json.dumps(newsletter, default=str),
    })
    # returns the document ID of the saved newsletter
    return newsletter_doc_ref.id


def save_digest(digest_dict):
    # store the digest into firestore, in the digest collection
    digest_doc_ref = db.collection('digests').document()
    digest_doc_ref.set(digest_dict)
    return digest_doc_ref.id


def get_newsletter_history(limit=5):
    """Queries Firestore to retrieve newsletter history.

    Args:
        limit (int): The maximum number of newsletters to retrieve.

    Returns:
        A generator of DocumentSnapshots representing the newsletters.
    """
    newsletters_ref = db.collection('newsletters')
    query = newsletters_ref.order_by(
        'start_date', direction=firestore.Query.DESCENDING).limit(limit)
    return query.stream()


def get_news_by_date_range(start_datetime, end_datetime, website=None):
    """Retrieves news articles from Firestore within a date range."""
    news_ref = db.collection('news')

    query = news_ref.where(filter=firestore.FieldFilter('published_at', '>=', start_datetime)) \
        .where(filter=firestore.FieldFilter('published_at', '<=', end_datetime))

    if website:
        query = query.where(
            filter=firestore.FieldFilter('website', '==', website))

    return query.stream()  # Returns a generator of DocumentSnapshots


def get_news_by_url(url_hash):
    """Retrieves news article from Firestore by URL hash.

    Args:
        url_hash (str): The SHA256 hash of the article URL.

    Returns:
        A DocumentSnapshot representing the news article, or None if not found.
    """
    doc_ref = db.collection('news').document(url_hash)
    doc = doc_ref.get()
    if doc.exists:
        return doc
    else:
        return None


def get_published_raw_news(start_date):
    """
    Retrieve past newsletters from firestore

    Args:
        start_date (str)
    """

    # remove one day to news_start_datetime
    news_start_datetime = start_date - \
        timedelta(days=1)
    past_newsletters_collection = db.collection('newsletters').where('start_date', '<', news_start_datetime).order_by(
        'end_date', direction='DESCENDING').limit(14)
    past_newsletters = past_newsletters_collection.get()
    # check if there are any documents in the collection
    if not past_newsletters:
        return
    # extract the json_data field from each document
    past_newsletters_json = [doc.to_dict()['json_data']
                             for doc in past_newsletters]

    simplified_published_newslist = []
    for newsletter in past_newsletters_json:
        newsletter = json.loads(newsletter)
        for category_items in newsletter["categories"].items():
            if isinstance(category_items, list):
                for item in category_items:
                    if "url" in item:
                        simplified_published_newslist.append(
                            {
                                "url": item["url"],
                                "title": item.get("title", ""),
                                "abstract": item.get("abstract", "")
                            }
                        )
            elif isinstance(category_items, dict):
                for region_items in category_items.items():
                    for item in region_items:
                        if "url" in item:
                            simplified_published_newslist.append(
                                {
                                    "url": item["url"],
                                    "title": item.get("title", ""),
                                    "abstract": item.get("abstract", "")
                                }
                            )

    # Get articles with empty abstracts from simplified_published_newslist
    urls_to_fetch = [article['url']
                     for article in simplified_published_newslist if not article.get('abstract')]
    retrieved_articles = []
    for url in urls_to_fetch:
        news_item = get_news_by_url(url)
        retrieved_articles.append(news_item)

    # Update simplified_published_newslist with retrieved abstracts
    for article in simplified_published_newslist:
        for retrieved_article in retrieved_articles:
            if article['url'] == retrieved_article['url']:
                article['abstract'] = retrieved_article.get('abstract', '')
                break

    return simplified_published_newslist


def get_top_sources(top_n, corpus_size=10):
    """
    Retrieves the last n newsletters from Firestore and analyzes the source 
    websites of the articles. Prints a breakdown of the articles by source.

    Args:
        n (int): The number of newsletters to retrieve.
    """

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


def get_valid_top_stories(n):
    """
    Fetches and structures the 'n' most recent validated "Top News of the Day" articles from a database.

    The function fetches the 'n' most recent articles validated as "Top News", 
    extracting only the title, abstract, and website for each. 
    Args:
        n (int): The number of "Top News" articles to retrieve from the database.

    Returns:
        str: A JSON string containing a list of dictionaries, each representing a validated "Top News
            of the Day" article with 'title', 'abstract', and 'website' fields.
    """
    valid_top_stories_collection = db.collection('news').where(
        'validated_section', 'in', ['Top News of the Day']).order_by(
        'published_at', direction='DESCENDING').limit(n)

    valid_top_stories = valid_top_stories_collection.get()
    valid_top_stories_json = [doc.to_dict() for doc in valid_top_stories]
    valid_top_stories_json = [{
        'title': doc['title'],
        'abstract': doc['abstract'],
        'website': doc['website']
    } for doc in valid_top_stories_json]
    valid_top_stories = json.dumps(valid_top_stories_json, default=str)

    return valid_top_stories


def get_valid_regional_stories(n):
    """
    Retrieves and formats a specified number of validated "Regional News" articles from a database.

    The function fetches the 'n' most recent articles validated as "Regional News," 
    extracting only the title, abstract, and website for each. 

    Args:
        n (int): The number of "Regional News" articles to retrieve from the database.

    Returns:
        str: A JSON string containing a list of dictionaries, each representing a validated "Regional News" 
            article with 'title', 'abstract', and 'website' fields. 
    """

    valid_regional_stories_collection = db.collection('news').where(
        'validated_section', 'in', ['Regional News']).order_by(
        'published_at', direction='DESCENDING').limit(n)

    valid_regional_stories = valid_regional_stories_collection.get()
    valid_regional_stories_json = [doc.to_dict()
                                   for doc in valid_regional_stories]
    # keep only the title, abstract and website field
    valid_regional_stories_json = [{
        'title': doc['title'],
        'abstract': doc['abstract'],
        'website': doc['website']
    } for doc in valid_regional_stories_json]
    valid_regional_stories = json.dumps(
        valid_regional_stories_json, default=str)

    return valid_regional_stories


def get_valid_more_stories(n):
    """
    Retrieves a specified number of validated "More Stories" articles from a database.

    The function fetches the 'n' most recent articles validated as "More Stories," 
    extracting only the title and website for each. 

    Args:
        n (int): The number of articles to retrieve.

    Returns:
        str: A JSON string containing a list of dictionaries, each representing an article 
            with 'title' and 'website' fields.
    """
    valid_more_stories_collection = db.collection('news').where(
        'validated_section', 'in', ['More Stories']).order_by(
        'published_at', direction='DESCENDING').limit(n)

    valid_more_stories = valid_more_stories_collection.get()
    valid_more_stories_json = [doc.to_dict() for doc in valid_more_stories]
    # keep only the title, abstract and website field
    valid_more_stories_json = [{
        'title': doc['title'],
        'website': doc['website']
    } for doc in valid_more_stories_json]
    valid_more_stories = json.dumps(valid_more_stories_json, default=str)

    return valid_more_stories


def get_rejected_stories(n):

    rejected_stories_collection = db.collection('news').where(
        'removed_reason', '!=', '').order_by(
        'published_at', direction='DESCENDING').limit(40)

    rejected_stories = rejected_stories_collection.get()

    rejected_stories_json = [doc.to_dict() for doc in rejected_stories]

    rejected_stories = json.dumps(rejected_stories_json, default=str)

    return rejected_stories


def get_config():
    # retrive the prompts from the Firestore db
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
        logging.error("Config document not found in Firestore.")
        return {}


def save_config(config_data):
    config_collection = db.collection('config')

    if is_prod():
        config_doc = config_collection.document('prod')
    else:
        config_doc = config_collection.document('dev')

    try:
        config_doc.update(config_data)
    except Exception as e:
        logging.error(f"Error updating config document: {e}")


def get_urls():
    # load the urls from the Firestore db
    config_data = get_config()
    if config_data:
        urls = config_data.get('urls', [])
        return urls
    else:
        logging.error("Config document not found in Firestore.")
        return []


def save_media(media_obj):
    try:
        media_collection = db.collection('media')
        media_collection.document(media_obj['hash']).set(media_obj)
        logging.info(f"Media object saved to Firestore: {media_obj['hash']}")
    except Exception as e:
        logging.error(f"Error saving media object to Firestore: {e}")


if __name__ == '__main__':
    app.run(debug=True)
