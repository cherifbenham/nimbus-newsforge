import requests
import vertexai
import json
from vertexai.generative_models import GenerativeModel, Part, GenerationConfig
import os
import logging
import concurrent.futures
from datetime import datetime
import traceback
import json_repair
from firebase_helpers import get_rejected_stories, get_config, get_urls, save_media
from utils import fetch_and_store
import concurrent.futures
from urllib.parse import urlparse
import pandas as pd


PROJECT_ID = os.getenv("PROJECT_ID", "fsa-amadeus")
LOCATION = os.getenv("REGION", "us-central1")
MAX_PAGES = 5

vertexai.init(project=PROJECT_ID, location=LOCATION)


def serialize_newsletter(newsletter):
    """Serializes a newsletter object into a dictionary suitable for storage."""

    serialized = {
        "date": datetime.fromisoformat(newsletter["start_date"]).strftime("%d-%m-%Y"),
        "categories": {}
    }

    convertion_table = {'topNews': 'Top News of the Day',
                        'podcasts': 'Podcasts of the Day',
                        'moreStories': 'More Stories',
                        'regionalNews': 'Regional News'}

    for section, items in newsletter["sections"].items():
        if items:
            section_name = convertion_table.get(
                section)  # Use the convertion table
            if section_name is None:
                continue  # Skip unknown sections
            serialized["categories"][section_name] = []
            if section == "regionalNews":
                for region_section in items:  # Handle nested structure for regional news
                    region = region_section["region"]
                    region_items = region_section["news"]

                    serialized["categories"][section_name].append(
                        {
                            region: region_items
                        })

            else:
                for item in items:
                    serialized_item = {
                        "website": item.get("website", ""),
                        "title": item.get("title", ""),
                        "abstract": item.get("abstract", ""),
                        "url": item.get("url", ""),
                        "reason": "",
                        "duplicate_candidates": []
                    }
                    if "publishDate" in item and item["publishDate"]:
                        serialized_item["publishDate"] = item["publishDate"].strftime(
                            "%Y-%m-%d")
                    serialized["categories"][section_name].append(
                        serialized_item)

    return serialized


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
    output = {"topNews": [], "podcasts": [],
              "regionalNews": [], "moreStories": []}

    convertion_table = {'Top News of the Day': 'topNews',
                        'Podcasts of the Day': 'podcasts',
                        'Regional News': 'regionalNews',
                        'More Stories': 'moreStories'}

    if 'json_data' in newsletter_json:
        newsletter_json = json.loads(newsletter_json['json_data'])

    if not isinstance(newsletter_json, dict):
        newsletter_json = json.loads(newsletter_json)
    for category_name, category_items in newsletter_json["categories"].items():
        category_name = convertion_table[category_name]
        if isinstance(category_items, list):
            for item in category_items:
                if "url" in item:
                    output[category_name].append(item)

        elif isinstance(category_items, dict):
            for region_name, region_items in category_items.items():
                region_output = {
                    "region": region_name,
                    "news": []
                }
                for item in region_items:
                    if "url" in item:
                        region_output['news'].append(item)

                output[category_name].append(region_output)

    return output


def group_news_by_website(news_list):

    news_list_by_website = {}
    for news_dict in news_list:
        website = news_dict["website"]
        if website not in news_list_by_website:
            news_list_by_website[website] = []
        news_list_by_website[website].append(news_dict)
    return news_list_by_website


def analyze_news(news_item):

    prompt = """
You are an industry specialist working at Amadeus. Analyze the news article below and give a summary of why this news is important (or not) to Amadeus.
Use markdown for formatting. Do not exceed 100 words. Format the response using all the possible markdown elements (like bullet points) to make it clear and readable to the user

News:
{}
    
Analyzis:
    
    """.format(news_item)

    model = GenerativeModel(model_name="gemini-1.5-flash-002", generation_config=GenerationConfig(
        temperature=0.3, max_output_tokens=500))
    responses = model.generate_content(
        [prompt],

    )

    extracted_data = responses.text.strip()
    return extracted_data


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
    logging.info('Processing content for {}'.format(gcs_file))
    media = Part.from_uri(
        mime_type="video/mp4",
        uri=gcs_file)

    model = GenerativeModel(model_name="gemini-1.5-flash-001")
    responses = model.generate_content(
        [prompt, media],

    )

    extracted_data = responses.text.strip()
    logging.info(f"extracted data: {extracted_data}")
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
        save_media(media_obj)
        return media_obj

    except json.JSONDecodeError as e:
        error_message = ''.join(traceback.format_exception(
            type(e), e, e.__traceback__))
        news = fix_json_formatting(extracted_data, error_message)
    except Exception as e:
        logging.error(f"Extract with Gemini error:{e}")


def tournament_rank(news_items, article_data):
    """
    Ranks news items using a tournament-style algorithm with parallel Gemini calls.

    Args:
        news_items: A list of news item IDs (or other unique identifiers).

    Returns:
        A list of news item IDs sorted by rank (highest to lowest).  Returns an empty list if input is empty.
    """

    n = len(news_items)
    if n == 0:
        return []
    if n == 1:
        return news_items

    # Simulate pairwise comparisons (replace this with your Gemini API call)
    def compare_news(item1, item2):

        if not item1 in article_data:
            return item2
        if not item2 in article_data:
            return item1

        article1 = article_data[item1]
        article2 = article_data[item2]

        ranking_prompt = """TASK:
As an experienced travel industry editor working for Amadeus, look carrefully at the 2 given input news and output the most important one for Amadeus


INSTRUCTIONS
- CAREFULLY analyze the text before choosing the most important news for Amadeus
- you MUST choose between the 2 input news and return only one.
- return the URL of the chosen news

When ranking news, consider:

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

Classify news based on:

* **Quantitative criteria:** Size of players, funding amounts (above $5M), impact on market share.
* **Qualitative criteria:** Involvement of key players, impact on the travel industry, potential impact on Amadeus's business, relevance to Amadeus's customer segments, avoiding repetitive topics, and focusing on global rather than local news.

Output is a JSON object with the following format:
{{'url':'url of the highhest importantce news'}}

Input news:
{}

{}
"""

        model = GenerativeModel(model_name="gemini-1.5-flash-002", generation_config=GenerationConfig(
            response_mime_type="application/json", temperature=0.3, max_output_tokens=200))

        comparison_prompt = ranking_prompt.format(
            json.dumps(article1, default=str),  json.dumps(article2, default=str))

        responses = model.generate_content(
            [comparison_prompt],
        )
        try:
            result = json.loads(responses.text.strip())
        except json.JSONDecodeError as e:
            print('Error decoding the comparison JSON')
            print(responses)
            print(responses.text.strip())
        except Exception:
            print("An error occured while parsing the comparison JSON")
        return result['url']

    winners = news_items.copy()
    round_results = {}  # Keep track of wins/losses for complete ranking

    round_number = 1  # Initialize round number
    while len(winners) > 1:
        new_winners = []
        # Use a ThreadPoolExecutor for parallel processing
        with concurrent.futures.ThreadPoolExecutor() as executor:
            # Ensure i+1 is within the bounds of the list
            futures = [executor.submit(
                compare_news, winners[i], winners[i+1]) for i in range(0, len(winners)-1, 2)]
            for i, future in enumerate(concurrent.futures.as_completed(futures)):
                winner = future.result()

                loser = winners[i] if winner == winners[i +
                                                        1] else winners[i+1]

                # Update round_results with round_number for tie-breaking
                round_results[winner] = round_results.get(
                    winner, 0) + (10 ** round_number)
                round_results[loser] = round_results.get(loser, 0)

                new_winners.append(winner)
        winners = new_winners
        round_number += 1  # Increment round number

    # Include all items in the final ranking
    all_items = news_items.copy()
    for item in round_results:
        if item in all_items:
            all_items.remove(item)

    # Combine ranked winners with remaining items
    ranked_news = sorted(
        round_results, key=round_results.get, reverse=True) + all_items

    return ranked_news


def rank_news(news_list):
    df = pd.DataFrame(news_list)

    df['url_key'] = df['url']  # Create a copy of the url field to use as a key
    article_data = df.set_index('url_key').to_dict(orient='index')
    urls_to_rank = df['url'].tolist()

    ranking = tournament_rank(urls_to_rank, article_data)
    ranked_news_items = [article_data.get(
        url) for url in ranking if article_data.get(url)]

    return ranked_news_items

def fetch_from_url(url):
    """
    Get HTML content from a single URL
    """
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
        logging.info(f"Successfully retrieved HTML from {url}")
    except requests.exceptions.RequestException as e:
        logging.warning(f"Error fetching {url}: {e}")

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
            logging.warning(f"Error fetching {url}: {e}")
    return html_results


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
            model_name="gemini-1.5-flash-001", generation_config=generation_config)
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

        logging.info('Processing content for {}'.format(
            html_content['website']))

        responses = model.generate_content(
            [prompt.format(html_content['html'])]),

        extracted_data = responses[0].text.strip()

        logging.info(f"extracted data: {extracted_data}")
        extracted_data = extracted_data.replace(
            "```json", "").replace("```", "").strip()

        try:
            news = json_repair.loads(extracted_data)
        except json.JSONDecodeError as e:
            error_message = ''.join(traceback.format_exception(
                type(e), e, e.__traceback__))
            news = fix_json_formatting(extracted_data, error_message)
        except Exception as e:
            logging.error(f"Extract with Gemini error:{e}")

        return {"website": html_content["website"], "news": news["news"]}

    except Exception as e:
        logging.error(f"Error extracting news from HTML: {e}")
        logging.error(f"Full error stack: {traceback.format_exc()}")
        logging.error(f"Problematic Content: {extracted_data}")
        return {"error": str(e)}


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

    model = GenerativeModel(model_name="gemini-1.5-flash-001")
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

    logging.info("Trying to fix json....")

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
        logging.error(f"Error fixing JSON: {e}, skipping this item.")
        logging.error(f"Problematic JSON String:{data}")
        return {"error": str(e)}

    return valid_json

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
        logging.error(f"Error extracting date from HTML: {e}")
        datetime_string = ""

    return datetime_string


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

# helper funtion to extract news, filter by specified range

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

    rejected_stories = get_rejected_stories(40)

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
            "abstract": "abstract of the news",
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
        model_name="gemini-1.5-pro-001", generation_config=config)
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

    model = GenerativeModel(model_name="gemini-1.5-pro-001", generation_config=GenerationConfig(
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
        model_name="gemini-1.5-pro-001", generation_config=options)
    responses = model.generate_content([prompt])

    selected_news = responses.text.strip()
    selected_news = selected_news.replace(
        "```json", "").replace("```", "").strip()

    try:
        selected_news_json = json_repair.loads(selected_news)
    except Exception as e:
        selected_news_json = fix_json_formatting(selected_news, e)

    return selected_news_json
