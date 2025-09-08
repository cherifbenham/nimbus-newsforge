from google.cloud import firestore
from datetime import (datetime, time)
import json
import hashlib
from src.core.utils.logger import get_logger


logger = get_logger()


def get_firestore_client():
    """Returns a Firestore client."""
    db = firestore.Client()
    return db


def save_news(news_list):

    # store all the news into firestore, in the news collection
    db = get_firestore_client()
    for news_item in news_list:
        website = news_item['website']
        news_data = news_item['news']
        for news in news_data:
            try:
                url = news.get('url')
                if not url:
                    logger.info(f"Storage - Skipping news with no URL: {news}")
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
                logger.info(f"Storage - Skipping news with error: {e}")
                continue


def update_newsletter(newsletter_id, newsletter_data):
    # update the newsletter in firestore, in the newsletters collection
    db = get_firestore_client()
    newsletter_doc_ref = db.collection('newsletters').document(newsletter_id)
    newsletter_doc_ref.update({
        'json_data': json.dumps(newsletter_data, default=str)
    })


def update_digest(digest_id, digest_data):
    # update the digest in firestore, in the digests collection
    db = get_firestore_client()
    digest_doc_ref = db.collection('digests').document(digest_id)
    digest_doc_ref.update({
        'json_data': json.dumps(digest_data, default=str)
    })


def update_article(article_url, data):
    # update the article in firestore, in the news collection
    db = get_firestore_client()
    article_id = hashlib.sha256(article_url.encode()).hexdigest()
    newsletter_doc_ref = db.collection('news').document(article_id)
    newsletter_doc_ref.update(data)
    logger.info(f"Article updated: {article_url} - id:{article_id}")


def save_newsletter(newsletter, start_date, end_date):

    # store the newsletter into firestore, in the newsletter collection
    db = get_firestore_client()
    # start_date_datetime = datetime.combine(
    #     start_date, time.min)
    # end_date_datetime = datetime.combine(
    #     end_date, time.min)
    newsletter_doc_ref = db.collection('newsletters').document()
    newsletter_doc_ref.set({
        'start_date': start_date,
        'end_date': end_date,
        'json_data': json.dumps(newsletter, default=str),
    })
    # returns the document ID of the saved newsletter
    return newsletter_doc_ref.id


def get_newsletter_history():
    # query firestore to retrieve the last 5 newsletters
    db = get_firestore_client()
    newsletters = db.collection('newsletters').order_by(
        'start_date', direction=firestore.Query.DESCENDING).limit(5).stream()
    return newsletters


def save_digest(digest, start_date):
    # store the digest into firestore, in the digest collection
    db = get_firestore_client()
    digest_doc_ref = db.collection('digests').document()
    digest_doc_ref.set({
        'start_date': start_date,
        'json_data': json.dumps(digest, default=str),
    })
    return digest_doc_ref.id


def get_digest_history():
    # query firestore to retrieve the last 5 digests
    db = get_firestore_client()
    digests = db.collection('digests').order_by(
        'start_date', direction=firestore.Query.DESCENDING).limit(5).stream()
    return digests


def delete_daily_newsletter_from_firestore(id):
    db = get_firestore_client()
    newsletter_doc_ref = db.collection('newsletters').document(id)
    newsletter_doc_ref.delete()


def delete_digest_from_firestore(digest_id):
    db = get_firestore_client()
    digest_doc_ref = db.collection('digests').document(digest_id)
    digest_doc_ref.delete()


def get_news_by_date_range(start_datetime, end_datetime, website=None):
    """Retrieves news articles from Firestore within a date range."""
    db = get_firestore_client()

    news_ref = db.collection('news')

    # print("Query start date and time:", start_datetime)
    # print("Query end date and time", end_datetime)
    # print("Query website:", website)
    # print("")

    query = news_ref.where(filter=firestore.FieldFilter('published_at', '>=', start_datetime)) \
        .where(filter=firestore.FieldFilter('published_at', '<=', end_datetime))

    if website:
        query = query.where(
            filter=firestore.FieldFilter('website', '==', website))
    docs = query.stream()

    existing_news = []
    for doc in docs:
        temp_doc = doc.to_dict()
        # Convert the published_at Datetime to date
        temp_doc['published_at'] = temp_doc['published_at'].replace(
            tzinfo=None)
        existing_news.append(temp_doc)
    # print(existing_news)
    return existing_news


def get_news_by_url(url):
    """Retrieves news article from Firestore by URL."""
    db = get_firestore_client()
    url_hash = hashlib.sha256(url.encode()).hexdigest()
    doc_ref = db.collection('news').document(url_hash)
    doc = doc_ref.get()
    if doc.exists:
        return doc.to_dict()
    else:
        return None


def get_news_by_website(website):
    """Retrieves news articles from Firestore by website."""
    db = get_firestore_client()
    docs = db.collection('news').where(
        filter=firestore.FieldFilter('website', '==', website)).stream()
    existing_news = []
    for doc in docs:

        existing_news.append(doc.to_dict())
    return existing_news


def get_last_week_newsletters(start_datetime, end_datetime):

    db = get_firestore_client()
    newsletter_ref = db.collection('newsletters')

    query = newsletter_ref.where(filter=firestore.FieldFilter('start_date', '>=', start_datetime)) \
        .where(filter=firestore.FieldFilter('end_date', '<=', end_datetime))

    docs = query.stream()
    # A list of newsletter dictionaries. Key values: 'end_date' , 'json_data', 'start_date'
    existing_newsletters = []
    for doc in docs:
        temp_doc = doc.to_dict()
        temp_doc['end_date'] = temp_doc['end_date'].replace(tzinfo=None)
        temp_doc['start_date'] = temp_doc['start_date'].replace(tzinfo=None)
        existing_newsletters.append(temp_doc)
    if existing_newsletters:
        return existing_newsletters
    else:
        return None
