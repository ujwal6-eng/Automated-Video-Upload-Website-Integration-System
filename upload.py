import os
import json
import io
import requests
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload, MediaFileUpload


# ========= ENV VARIABLES =========

GOOGLE_TOKEN_JSON = os.getenv("GOOGLE_TOKEN_JSON")
PENDING_FOLDER_ID = os.getenv("PENDING_FOLDER_ID")
PROCESSING_FOLDER_ID = os.getenv("PROCESSING_FOLDER_ID")
UPLOADED_FOLDER_ID = os.getenv("UPLOADED_FOLDER_ID")
FAILED_FOLDER_ID = os.getenv("FAILED_FOLDER_ID")
VIDEO_WEBHOOK_SECRET = os.getenv("VIDEO_WEBHOOK_SECRET")
WEBHOOK_URL = os.getenv("WEBHOOK_URL")


# ========= GOOGLE SERVICES =========

def get_services():
    creds_data = json.loads(GOOGLE_TOKEN_JSON)
    creds = Credentials.from_authorized_user_info(creds_data)

    drive = build("drive", "v3", credentials=creds)
    youtube = build("youtube", "v3", credentials=creds)

    return drive, youtube


# ========= DRIVE HELPERS =========

def list_pending_files(drive):
    query = f"'{PENDING_FOLDER_ID}' in parents and trashed=false"
    res = drive.files().list(q=query, fields="files(id,name)").execute()
    return res.get("files", [])


def move_file(drive, file_id, target_folder):
    file = drive.files().get(fileId=file_id, fields="parents").execute()
    previous_parents = ",".join(file.get("parents"))

    drive.files().update(
        fileId=file_id,
        addParents=target_folder,
        removeParents=previous_parents
    ).execute()


def download_file(drive, file_id, filename):
    request = drive.files().get_media(fileId=file_id)
    fh = io.FileIO(filename, "wb")
    downloader = MediaIoBaseDownload(fh, request)

    done = False
    while not done:
        _, done = downloader.next_chunk()

    return filename


# ========= YOUTUBE =========

def upload_to_youtube(youtube, file_path, title):
    body = {
        "snippet": {"title": title},
        "status": {"privacyStatus": "unlisted"}
    }

    media = MediaFileUpload(file_path, resumable=True)

    request = youtube.videos().insert(
        part="snippet,status",
        body=body,
        media_body=media
    )

    response = None
    while response is None:
        status, response = request.next_chunk()

    return response["id"]


# ========= REVIEW ID EXTRACTION =========

def extract_review_id(filename):
    """
    Expected format:
    wada_review_<video_review_id>_something.mp4
    """
    parts = filename.split("_")
    if len(parts) >= 3:
        return parts[2]
    return None


# ========= WEBHOOK =========

def notify_website(video_review_id, video_id, youtube_url):
    payload = {
        "video_review_id": video_review_id,
        "youtube_video_id": video_id,
        "youtube_url": youtube_url
    }

    headers = {
        "x-api-key": VIDEO_WEBHOOK_SECRET,
        "Content-Type": "application/json"
    }

    response = requests.post(WEBHOOK_URL, json=payload, headers=headers)
    print("🔔 Webhook response:", response.status_code, response.text)


# ========= MAIN =========

def main():
    print("🚀 Automation started")

    if not GOOGLE_TOKEN_JSON:
        print("❌ GOOGLE_TOKEN_JSON not set")
        return

    drive, youtube = get_services()

    files = list_pending_files(drive)

    if not files:
        print("✅ No pending videos found")
        return

    file = files[0]
    file_id = file["id"]
    filename = file["name"]

    print("🎬 Processing:", filename)

    try:
        # Move to processing
        move_file(drive, file_id, PROCESSING_FOLDER_ID)

        # Download locally
        local_path = download_file(drive, file_id, filename)

        # Upload to YouTube
        video_id = upload_to_youtube(youtube, local_path, filename)
        youtube_url = f"https://www.youtube.com/watch?v={video_id}"

        print("✅ Uploaded to YouTube:", video_id)

        # Extract review ID
        review_id = extract_review_id(filename)

        if not review_id:
            print("❌ Could not extract review ID from filename")
            move_file(drive, file_id, FAILED_FOLDER_ID)
            return

        # Notify website
        notify_website(review_id, video_id, youtube_url)

        # Move to uploaded
        move_file(drive, file_id, UPLOADED_FOLDER_ID)

        print("🎉 Process complete")

    except Exception as e:
        print("❌ ERROR:", str(e))
        move_file(drive, file_id, FAILED_FOLDER_ID)


if __name__ == "__main__":
    main()
