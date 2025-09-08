from pytube import YouTube
from google.cloud import storage
import io
import hashlib


def get_video_info(url):
    yt = YouTube(url)

    return {
        "title": yt.title,
        "description": yt.description,
        "thumbnail": yt.thumbnail_url,
        "url": url
    }


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
