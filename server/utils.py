import os
import vertexai
import logging
import json_repair
import random
import string
from pytube import YouTube
from google.cloud import storage
from vertexai.generative_models import GenerativeModel
import io
import json
import hashlib
import datetime
import logging
from logging import getLogger
import os
import google.cloud.logging

PROJECT_ID = os.getenv("PROJECT_ID", "fsa-amadeus")
LOCATION = os.getenv("REGION", "us-central1")

vertexai.init(project=PROJECT_ID, location=LOCATION)


def is_prod():
    if os.environ.get('K_SERVICE') or os.environ.get('CLOUD_RUN_JOB'):
        return True
    else:
        return False


def upload_to_gcs(bucket_name, blob_name, buffer):
    """Uploads a buffer to Google Cloud Storage."""
    storage_client = storage.Client()
    bucket = storage_client.bucket(bucket_name)
    blob = bucket.blob(blob_name)
    blob.upload_from_string(buffer.getvalue())
    print(f"Uploaded {blob_name} to bucket {bucket_name}.")
    # return the full gcs path in the form of gs://bucket_name/blob_name
    return f"gs://{bucket_name}/{blob_name}"


def fetch_and_store(youtube_url, bucket_name):
    """Downloads a YouTube video and uploads it to Google Cloud Storage."""
    yt = YouTube(youtube_url)
    stream = yt.streams.filter(progressive=True)
    # get the lowest resolution stream
    stream = stream[0]

    buffer = io.BytesIO()

    stream.stream_to_buffer(buffer)
    buffer.seek(0)  # Reset buffer position to the beginning

    # url encode the title to avoid special characters
    url_hash = hashlib.sha256(youtube_url.encode()).hexdigest()
    output_filename = "media/{}.mp4".format(url_hash)
    print(output_filename)

    gcs_file = upload_to_gcs(bucket_name, output_filename, buffer)

    media_object = {
        "youtube_url": youtube_url,
        "gcs_file": gcs_file,
        'title': yt.title,
        'description': yt.description,
        'thumbnail': yt.thumbnail_url,
        'hash': url_hash
    }

    return media_object


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


def parse_iso_date(date_str: str) -> datetime.datetime:
    try:
        # Parse using UTC timezone to be consistent
        return datetime.datetime.strptime(date_str, "%Y-%m-%dT%H:%M:%S.%fZ")
    except ValueError as e:
        raise ValueError(f"Invalid ISO date string: {date_str}, error: {e}")

def generate_random_id(length=20):
  """Generates a random ID string with the specified format.

  Args:
    length: The desired length of the ID string (default: 20).

  Returns:
    A random ID string with the format "07<random_chars>".
  """

  # Generate random characters (alphanumeric + uppercase)
  characters = string.ascii_letters + string.digits 
  random_chars = ''.join(random.choice(characters) for i in range(length - 3))

  # Construct the ID string
  random_id = "07" + random_chars

  return random_id

def get_logger():
    """Returns a singleton logger instance."""

    logger = logging.getLogger('my_app')

    if logger.handlers:  # Logger already configured
        return logger

    logger.setLevel(logging.DEBUG)

    # Choose handler based on environment
    if os.environ.get('K_SERVICE'):
        handler = google.cloud.logging.Client().get_default_handler()
    else:
        handler = logging.StreamHandler()
        handler.setFormatter(logging.Formatter(
            '%(asctime)s - %(levelname)s - %(message)s'))

    logger.addHandler(handler)
    return logger
