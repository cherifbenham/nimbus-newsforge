from flask import Flask, request, jsonify
from google.cloud import firestore
from google.cloud import bigquery
from vertexai.generative_models import GenerativeModel, GenerationConfig
from utils import MODEL_FLASH
import os
from datetime import datetime
from firebase_helpers import *
from newsletter_generation import *
from digest_generation import *
from classes.Newsletter import *
from news_search import *
from urllib.parse import urlparse
from flask_cors import CORS
from compose_weekly import generate_compose_weekly_insights

import concurrent.futures
import json

port = int(os.environ.get('PORT', 5000))
app = Flask(__name__)
# Allow CORS origins from env (comma-separated) or default to localhost for dev
cors_origins = os.getenv("CORS_ORIGINS", "http://localhost:*")
if "," in cors_origins:
    cors_origins = [o.strip() for o in cors_origins.split(",") if o.strip()]
CORS(app, resources={
    "/api/*": {
        "origins": cors_origins,
        "methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS"],
        "allow_headers": ["Content-Type", "Authorization"],
        "max_age": 600,
    }
})


# Initialize Firestore client honoring PROJECT_ID and FIRESTORE_DATABASE_ID
db = firestore.Client(
    project=os.getenv('PROJECT_ID') or None,
    database=os.getenv('FIRESTORE_DATABASE_ID', '(default)')
)

# Basic status/index endpoints

@app.route('/', methods=['GET'])
def root_index():
    return jsonify({
        "service": "competitive-intel-api",
        "status": "ok",
        "api_root": "/api",
        "example_endpoints": [
            "/api/newsletters",
            "/api/digests",
            "/api/news",
            "/api/news/search"
        ]
    }), 200


@app.route('/api', methods=['GET'])
def api_index():
    return jsonify({
        "message": "API root",
        "status": "ok",
        "endpoints": [
            "/api/newsletters",
            "/api/digests",
            "/api/news",
            "/api/news/search"
        ]
    }), 200


@app.route('/api/health', methods=['GET'])
def api_health():
    return jsonify({"status": "ok"}), 200

# Firestore Flask routes


@app.route('/api/health/deps', methods=['GET'])
def api_health_deps():
    """Checks connectivity to Firestore, BigQuery, and Vertex AI."""
    results = {
        "firestore": {"ok": False},
        "bigquery": {"ok": False},
        "vertex_ai": {"ok": False},
    }

    # Firestore: attempt a lightweight read
    try:
        _ = list(db.collection('config').limit(1).get())
        results["firestore"]["ok"] = True
    except Exception as e:
        results["firestore"]["error"] = str(e)

    # BigQuery: simple SELECT 1
    try:
        bq_client = bigquery.Client()
        bq_client.query("SELECT 1").result()
        results["bigquery"]["ok"] = True
    except Exception as e:
        results["bigquery"]["error"] = str(e)

    # Vertex AI: minimal generation
    try:
        region = os.getenv("REGION", "us-central1")
        model = GenerativeModel(
            model_name=MODEL_FLASH,
            generation_config=GenerationConfig(temperature=0, max_output_tokens=1),
        )
        _ = model.generate_content(["ping"])  # minimal request
        results["vertex_ai"].update({"ok": True, "model": MODEL_FLASH, "region": region})
    except Exception as e:
        results["vertex_ai"]["error"] = str(e)

    status = "ok" if all(v.get("ok") for v in results.values()) else "degraded"
    return jsonify({"status": status, **results}), (200 if status == "ok" else 503)


@app.route('/api/newsletters/email/compose', methods=['POST'])
def compose_email_route():
    try:
        data = request.get_json() or {}
        subject_hint = data.get('subject_hint')

        # Accept either a flat list of news items or a newsletter with sections
        news = data.get('news')
        if not news:
            newsletter = data.get('newsletter') or {}
            sections = (newsletter or {}).get('sections') or {}
            news = []
            # Flatten sections
            for item in sections.get('topNews', []) + sections.get('moreStories', []):
                news.append(item)
            for region in sections.get('regionalNews', []):
                for item in region.get('news', []):
                    news.append(item)
            for item in sections.get('podcasts', []):
                news.append(item)

        if not news:
            return jsonify({"error": "No news items provided"}), 400

        composed = compose_compact_email(news, subject_hint=subject_hint)
        return jsonify(composed), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/api/newsletters/email/compose/curated', methods=['POST'])
def compose_email_curated_route():
    try:
        data = request.get_json() or {}
        newsletter = data.get('newsletter') or {}
        subject_hint = data.get('subject_hint')
        max_items = int(data.get('max_items', 5))
        result = compose_curated_email(newsletter, max_items=max_items, subject_hint=subject_hint)
        return jsonify(result), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/api/newsletters', methods=['GET'])
def get_newsletter_history_route():
    """Retrieves newsletter history.

    Query Parameters:
        - limit (optional): Number of newsletters to retrieve (default: 5)

    Returns:
        Array of NewsHeader objects for the past 5 newsletters.
    """
    try:
        limit = request.args.get('limit', default=5, type=int)
        newsletters = get_newsletter_history(limit)

        formatted_newsletter_headers = []
        for newsletter in newsletters:
            header = {
                "id": newsletter.id,
                "start_date": newsletter.get('start_date').strftime('%Y-%m-%d'),
                "end_date": newsletter.get('end_date').strftime('%Y-%m-%d')}
            formatted_newsletter_headers.append(header)

        return jsonify(formatted_newsletter_headers)

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/api/digests', methods=['GET'])
def get_digest_history_route():
    """Retrieves digest history."""
    try:
        digests = db.collection('digests').order_by(
            'start_date', direction=firestore.Query.DESCENDING).limit(5).stream()
        formatted_digest_headers = []
        for digest in digests:
            header = {
                "id": digest.id,
                "start_date": digest.get('start_date').strftime('%Y-%m-%d')}
            formatted_digest_headers.append(header)
        return jsonify(formatted_digest_headers)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/api/news', methods=['GET'])
def get_news_by_date_range_route():
    """
    Retrieves news articles within a date range.

    Query parameters:
        - start_date (YYYY-MM-DD)
        - end_date (YYYY-MM-DD)
        - website (optional)
        - ranked (optional)


    Returns:
        JSON response with the following structure:
        {
            "news": [
                {
                    "id": "article_id",
                    "website": "https://www.example.com",
                    "published_at": "YYYY-MM-DD HH:MM:SS",
                    "title": "Article Title",
                    "abstract": "Article abstract",
                    "url": "https://www.example.com/article"
                },
                # ... more news articles
            ],
            "count": <number of articles>
        }
    """
    try:

        start_date_str = request.args.get('start_date')
        end_date_str = request.args.get('end_date')
        website = request.args.get('website')
        ranked = (request.args.get('ranked') == 'true')

        start_datetime = parse_iso_date(start_date_str)
        end_datetime = parse_iso_date(end_date_str)

        existing_news = get_news_by_date_range(
            start_datetime, end_datetime, website)

        formatted_news = []
        for news_item in existing_news:
            formatted_news.append({
                "id": news_item.id,
                "website": news_item.get('website'),
                "published_at": news_item.get('published_at').strftime('%Y-%m-%d %H:%M:%S') if news_item.get('published_at') else None,
                "title": news_item.get('title'),
                "abstract": news_item.get('abstract'),
                "url": news_item.get('url')
            })

        if ranked:
            formatted_news = rank_news(formatted_news)

        return jsonify({
            "news": formatted_news,
            "count": len(formatted_news)
        })
    except Exception as e:
        return jsonify(str(e)), 500


@app.route('/api/news/analyze', methods=['POST'])
def analyze_news_route():
    """
    Analyzes the news article with Gemini

    Query parameters:
        - News Object


    Returns:
        String with content analysis
    """
    try:
        data = request.get_json()  # Get JSON data from the request
        news = data.get('news')
        analysis = analyze_news(news)

        return analysis
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/api/news/url/<url_hash>', methods=['GET'])
def get_news_by_url_route(url_hash):
    """Retrieves a news article by its URL hash.

    Args:
        url_hash (str): The SHA256 hash of the article URL.

    Returns:
        JSON response with the following structure:
        {
            "news": {
                "id": "article_id",
                "website": "https://www.example.com",
                "published_at": "YYYY-MM-DD HH:MM:SS",
                "title": "Article Title",
                "abstract": "Article abstract",
                "full_text": "Article full text",
                "url": "https://www.example.com/article"
            }
        }
        Or a 404 error if the article is not found.
    """
    try:
        news_item = get_news_by_url(url_hash)
        if news_item:
            return jsonify({
                "news": {
                    "id": news_item.id,
                    "website": news_item.get('website'),
                    "published_at": news_item.get('published_at').strftime('%Y-%m-%d %H:%M:%S') if news_item.get('published_at') else None,
                    "title": news_item.get('title'),
                    "abstract": news_item.get('abstract'),
                    "full_text": news_item.get('full_text'),
                    "url": news_item.get('url')
                }
            })
        else:
            return jsonify({"message": "News article not found."}), 404
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/api/digest/news', methods=['GET'])
def get_news_for_digest():
    try:
        start_date_str = request.args.get('start_date')

        start_datetime = parse_iso_date(start_date_str)
        end_datetime = start_datetime + timedelta(days=7)

        existing_newsletters = get_last_week_newsletters(
            start_datetime, end_datetime)
        if existing_newsletters:
            newslist = []
            for newsletter in existing_newsletters:
                # nl = Newsletter.from_serialized(newsletter)
                newslist.extend(newsletter.get_news())

            return jsonify(newslist)
        else:
            return jsonify({"message": "No newsletters found for the given date range."}), 404
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/api/newsletter/id', methods=['GET'])
def get_newsletter_by_id_route():
    try:
        id = request.args.get('id')
        newsletter = get_newsletter_by_id(id)
        newsletter = newsletter.to_dict()
        newsletter = Newsletter.from_serialized(newsletter)
        # nlobject = transform_newsletter(newsletter)
        # print(nlobject)
        return jsonify(newsletter.to_dict())
    except (Exception) as e:
        print(e)
        return jsonify({"message": "Newsletter not found."}), 404


@app.route('/api/digests/id', methods=['GET'])
def get_digest_by_id_route():
    try:
        id = request.args.get('id')
        digest_snapshot = get_digest_by_id(id)
        if digest_snapshot.exists:
            digest = digest_snapshot.to_dict()
        if "digest" in digest:
            digest = digest['digest']
        return jsonify(digest)
    except (Exception) as e:
        return jsonify({"message": "An error occured while retrieving the Digest", "error": str(e)}), 500


@app.route('/api/newsletters/<newsletter_id>', methods=['PUT'])
def update_newsletter_route(newsletter_id):
    """Updates a newsletter in Firestore."""
    try:
        data = request.get_json()
        newsletter = data.get('newsletter')
        start_date = datetime.fromisoformat(newsletter['start_date'])
        end_date = datetime.fromisoformat(newsletter['end_date'])
        newsletter = Newsletter(
            start_date=start_date, end_date=end_date, sections=newsletter['sections'])
        serialized_newsletter = newsletter.serialize()
        update_newsletter(newsletter_id, serialized_newsletter)
        return jsonify({"message": f"Newsletter {newsletter_id} updated successfully!"}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/api/digests/<digest_id>', methods=['PUT'])
def update_digest_route(digest_id):
    """Updates a digest in Firestore."""
    try:
        digest_data = request.get_json()
        update_digest(digest_id, digest_data)
        return jsonify({"message": f"Digest {digest_id} updated successfully!"}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/api/articles/<article_url>', methods=['PUT'])
def update_article_route(article_url):
    """Updates an article in Firestore."""
    try:
        data = request.get_json()
        update_article(article_url, data)
        return jsonify({"message": f"Article {article_url} updated successfully!"}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/api/newsletters', methods=['POST'])
def save_newsletter_route():
    """Saves a newsletter to Firestore."""
    try:
        data = request.get_json()
        newsletter = data.get('newsletter')
        start_date = datetime.fromisoformat(newsletter['start_date'])
        end_date = datetime.fromisoformat(newsletter['end_date'])
        newsletter = Newsletter(
            start_date=start_date, end_date=end_date, sections=newsletter['sections'])
        serialized_newsletter = newsletter.serialize()

        newsletter_id = save_newsletter(
            serialized_newsletter, start_date, end_date)
        return jsonify({"id": newsletter_id}), 201
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/api/digests', methods=['POST'])
def save_digest_route():
    """Saves a digest to Firestore."""
    try:
        data = request.get_json()
        digest = data.get('digest')
        start_date = datetime.strptime(data['start_date'], '%Y-%m-%d').date()
        end_date = datetime.strptime(data['end_date'], '%Y-%m-%d').date()
        digest = Digest(
            start_date=start_date, end_date=end_date, sections=digest['sections'])
        serialized_digest = digest.serialize()

        digest_id = save_digest(serialized_digest, start_date)
        return jsonify({"message": "Digest saved successfully!", "id": digest_id}), 201

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/api/newsletters/<newsletter_id>', methods=['DELETE'])
def delete_daily_newsletter_route(newsletter_id):
    """Deletes a daily newsletter from Firestore."""
    try:
        newsletter_doc_ref = db.collection(
            'newsletters').document(newsletter_id)
        newsletter_doc_ref.delete()
        return jsonify({"message": f"Newsletter {newsletter_id} deleted successfully!"}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/api/digests/<digest_id>', methods=['DELETE'])
def delete_digest_route(digest_id):
    """Deletes a digest from Firestore."""
    try:
        digest_doc_ref = db.collection('digests').document(digest_id)
        digest_doc_ref.delete()
        return jsonify({"message": f"Digest {digest_id} deleted successfully!"}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# Newsletter generation flask routes


@app.route('/api/newsletters/generate', methods=['POST'])
def generate_newsletter_route():
    """Fetches website content, extracts news, and generates newsletter data."""
    try:
        news_list = []
        news_list_by_website = {}
        media_list = []

        # argument
        data = request.get_json()  # Get JSON data from the request
        start_date_string = data.get("start_date")
        end_date_string = data.get("end_date")

        video_links = request.form.get("video_links", None)
        article_links = request.form.get("article_links", None)

        start_date = datetime.fromisoformat(start_date_string)
        end_date = datetime.fromisoformat(end_date_string)

        # --- Process Added Content ---
        if video_links:
            video_links = video_links.split(',')
            with concurrent.futures.ThreadPoolExecutor() as executor:
                # 1. Process YouTube Videos
                video_futures = {
                    executor.submit(fetch_and_analyze_media, video_link): video_link
                    for video_link in video_links
                }
                for future in concurrent.futures.as_completed(video_futures):
                    video_link = video_futures[future]
                    try:
                        video_data = future.result()
                        media_list.append(video_data)
                    except Exception as e:
                        return jsonify({
                            f"Error processing YouTube link {video_link}": str(e)}), 500

        if article_links:
            article_links = article_links.split(',')
            article_html_list = get_html_content(
                urls=article_links)
            with concurrent.futures.ThreadPoolExecutor() as executor:
                article_futures = [
                    executor.submit(extract_news_with_gemini, html)
                    for html in article_html_list
                    if html
                ]
                for future in concurrent.futures.as_completed(article_futures):
                    article = future.result()
                    if article:
                        news_list.append(article)

        # keep the date of start_date but set its time to the min time of the day
        # to ensure we get all the news articles, including those without a proper time
        start_date = datetime.combine(
            start_date, datetime.min.time())
        raw_news_list = get_news_by_date_range(start_date, end_date)
        raw_news_dict = {}

        for news in raw_news_list:
            # simplify the news object. Only keep the title, the abstract and the url
            light_news = {}
            light_news['title'] = news.get('title')
            light_news['abstract'] = news.get('abstract')
            light_news['url'] = news.get('url')
            raw_news_dict[light_news['url']] = light_news
        simplified_published_newslist = get_published_raw_news(start_date)

        top_source_sites = get_top_sources(5, 10)
        top_news_dict = {}
        for raw_key in raw_news_dict.keys():
            if urlparse(raw_key).netloc in top_source_sites:
                top_news_dict[raw_key] = raw_news_dict[raw_key]

        remaining_news_dict = raw_news_dict.copy()
        for key in top_news_dict.keys():
            remaining_news_dict.pop(key, None)

        url_list = select_important_news(
            list(remaining_news_dict.values()))

        for url in url_list:
            news = remaining_news_dict.get(url)
            if news:
                top_news_dict[url] = news

        # Use Gemini to remove news related to themes already published previously
        duplicate_news = find_duplicate_news(
            list(top_news_dict.values()), simplified_published_newslist)

        # print stats
        print(f"Number of news articles: {len(top_news_dict)}")
        print(f"Number of duplicate news articles: {len(duplicate_news)}")

        print(duplicate_news)

        # removing duplicates from the Top_news_list
        for duplicate in duplicate_news:
            if duplicate['url'] in top_news_dict:
                top_news_dict.pop(duplicate['url'], None)

        # print stats
        print(
            f"Number of news articles after removing duplicates: {len(raw_news_dict)}")
        # News are raw. Group the news by the "website" field.
        news_list_by_website = group_news_by_website(raw_news_list)

        try:
            if news_list_by_website:
                for website in news_list_by_website.keys():
                    news_dict = news_list_by_website[website]

                    news_dict = filter_news_by_date_range(
                        news_dict, start_date, end_date)

                    news_list.append(
                        {"website": website, "news": news_dict})
        except Exception as e:
            logging.error(f"Error during extraction: {e}")
            raise e

        newsletter = generate_newsletter_text(
            list(top_news_dict.values()), past_newsletters=simplified_published_newslist)
        # if newsletter:
        #     newsletter_id = save_newsletter(
        #         newsletter, start_date, end_date)
        # newsletter = newsletter.to_dict()
        nlobject = transform_newsletter(newsletter)

        return jsonify({
            "start_date": start_date.isoformat(),
            "end_date": end_date.isoformat(),
            "sections": nlobject
        })

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/api/digests/generate', methods=['POST'])
def generate_digest_content_route():

    try:
        data = request.get_json()
        start_date_string = data.get("start_date")  # string
        end_date_string = data.get("end_date")  # string
        start_date_datetime = parse_iso_date(start_date_string)
        end_date_datetime = parse_iso_date(end_date_string)

        digest_dict = generate_digest(start_date_datetime, end_date_datetime)
        return jsonify(digest_dict), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/api/digests/highlight/generate', methods=['POST'])
def generate_digest_highlight_route():

    try:
        data = request.get_json()
        digest = data.get('digest')
        digest_dict = regenerate_digest_highlights(digest=digest)
        return jsonify(digest_dict), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/api/news/search', methods=['GET'])
def search_news_route():
    try:
        query = request.args.get('input')
        search_results = search(query)
        return jsonify(search_results), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/api/compose-weekly/analyze', methods=['POST'])
def compose_weekly_analyze_route():
    try:
        data = request.get_json() or {}
        items = data.get('items', [])
        if not isinstance(items, list) or not items:
            return jsonify({"error": "No news items provided"}), 400

        sanitized = []
        for idx, item in enumerate(items):
            if not isinstance(item, dict):
                continue
            title = str(item.get("title", "") or "").strip()
            abstract = str(item.get("abstract", "") or "").strip()
            if not title and not abstract:
                continue
            sanitized.append(
                {
                    "id": str(item.get("id", idx)),
                    "title": title,
                    "abstract": abstract,
                    "url": str(item.get("url", "") or "").strip(),
                    "date": str(item.get("date", "") or "").strip(),
                    "class_daily": str(item.get("class_daily", "") or "").strip(),
                }
            )

        if not sanitized:
            return jsonify({"error": "No valid items to analyze"}), 400

        insights_out = generate_compose_weekly_insights(sanitized)
        if isinstance(insights_out, tuple):
            insights, source = insights_out
        else:
            insights, source = insights_out, "unknown"
        return jsonify({"results": insights, "source": source}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/api/compose-weekly/prompt', methods=['GET'])
def get_compose_weekly_prompt():
    """Read prompt from Firestore config/dev.prompt_weekly_compose."""
    try:
        text = ''
        # Allow dev mode to bypass Firestore
        local_only = os.getenv('COMPOSE_WEEKLY_PROMPT_LOCAL_ONLY', '').strip().lower() in {'1','true','yes'}
        if not local_only:
            try:
                doc = db.collection('config').document('dev').get()
                if doc.exists:
                    text = str(doc.to_dict().get('prompt_weekly_compose', '') or '')
            except Exception:
                pass
        return jsonify({"prompt": text}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/api/compose-weekly/prompt', methods=['PUT'])
def set_compose_weekly_prompt():
    """Persist prompt in Firestore config/dev.prompt_weekly_compose."""
    try:
        data = request.get_json() or {}
        prompt = str(data.get('prompt', '') or '')
        # Save to Firestore unless disabled via env
        local_only = os.getenv('COMPOSE_WEEKLY_PROMPT_LOCAL_ONLY', '').strip().lower() in {'1','true','yes'}
        if not local_only:
            try:
                db.collection('config').document('dev').set({'prompt_weekly_compose': prompt}, merge=True)
            except Exception:
                # In dev, ignore Firestore errors
                pass
        return jsonify({"status": "ok"}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/digests/metadata', methods=['POST'])
def generate_digest_metadata_route():
    try:
        data = request.get_json()
        news_item = get_news_by_url(data.get("url_hash"))
        news_item = news_item.to_dict()
        if news_item:
            digest_news_item = generate_digest_metadata(news_item)
            return jsonify({
                "news": {
                    "website": digest_news_item.get('website'),
                    "published_at": digest_news_item.get('published_at', ""),
                    "title": digest_news_item.get('title'),
                    "abstract": digest_news_item.get('abstract', ""),
                    "url": digest_news_item.get('url'),
                    "key_message": digest_news_item.get('key_message'),
                    "context": digest_news_item.get('context')
                }
            })
        else:
            return jsonify({"message": "News article not found."}), 404
    except Exception as e:
        return jsonify({"error": str(e)}), 500


if __name__ == '__main__':

    app.run(debug=False, host="0.0.0.0",
            port=int(os.environ.get("PORT", 5000)))
