import os
from pathlib import Path
try:
    # Load environment variables from a local .env file if present (dev convenience)
    # Use override=True so .env wins over stray shell settings
    from dotenv import load_dotenv
    load_dotenv(override=True)
except Exception:
    # Safe no-op if python-dotenv is not installed or not needed in prod
    pass

# Ensure local service-account credentials are picked up when running outside GCP
_repo_root = Path(__file__).resolve().parents[1]
_local_creds = _repo_root / "fsa-amadeus-471508-b1e0395dd912.json"
if _local_creds.exists():
    # Force the SDK to use repo-local credentials when running locally
    os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = str(_local_creds)
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
# Model names can be overridden via environment variables
# Default to Gemini 2.0 Flash for broader availability
MODEL_FLASH = os.getenv("MODEL_FLASH", "gemini-2.0-flash-001")
MODEL_PRO = os.getenv("MODEL_PRO", "gemini-1.5-pro-002")

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

    model = GenerativeModel(model_name=MODEL_FLASH)
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
    """Parse various ISO8601 formats into a timezone-naive UTC datetime.

    Accepts strings like:
    - YYYY-MM-DDTHH:MM:SSZ
    - YYYY-MM-DDTHH:MM:SS.sssZ (ms)
    - YYYY-MM-DDTHH:MM:SS.%fZ (us)
    - Or with timezone offset: replace trailing 'Z' with +00:00 and use fromisoformat.
    """
    if not isinstance(date_str, str):
        raise ValueError(f"Invalid ISO date: expected string, got {type(date_str)}")

    s = date_str.strip()
    # Fast paths
    fmts = [
        "%Y-%m-%dT%H:%M:%SZ",
        "%Y-%m-%dT%H:%M:%S.%fZ",
    ]
    for fmt in fmts:
        try:
            return datetime.datetime.strptime(s, fmt)
        except ValueError:
            pass

    # Try Python's fromisoformat with timezone offset
    try:
        if s.endswith("Z"):
            s2 = s[:-1] + "+00:00"
        else:
            s2 = s
        dt = datetime.datetime.fromisoformat(s2)
        # Normalize to naive UTC
        if dt.tzinfo:
            dt = dt.astimezone(datetime.timezone.utc).replace(tzinfo=None)
        return dt
    except Exception as e:
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


def generate_with_fallback(contents, generation_config=None, prefer_pro=True):
    """Generate content trying PRO first, then FLASH as fallback.

    Args:
        contents: list or str passed to model.generate_content
        generation_config: optional GenerationConfig
        prefer_pro: if True, try MODEL_PRO before MODEL_FLASH

    Returns:
        The responses object from model.generate_content

    Raises:
        Last exception if both attempts fail.
    """
    order = [MODEL_PRO, MODEL_FLASH] if prefer_pro else [MODEL_FLASH, MODEL_PRO]
    last_exc = None
    for name in order:
        try:
            model = GenerativeModel(model_name=name, generation_config=generation_config)
            return model.generate_content(contents)
        except Exception as e:
            last_exc = e
            continue
    if last_exc:
        raise last_exc
    raise RuntimeError("generate_with_fallback: unexpected state")
