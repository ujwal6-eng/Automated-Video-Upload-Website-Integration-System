import os
import json
import io
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload, MediaFileUpload

# ENV VARIABLES
PENDING_FOLDER_ID = os.getenv("PENDING_FOLDER_ID")
PROCESSING_FOLDER_ID = os.getenv("PROCESSING_FOLDER_ID")
UPLOADED_FOLDER_ID = os.getenv("UPLOADED_FOLDER_ID")
FAILED_FOLDER_ID = os.getenv("FAILED_FOLDER_ID")

GOOGLE_TOKEN_JSON = os.getenv("GOOGLE_TOKEN_JSON")


def get_services():
    creds_data = json.loads(GOOGLE_TOKEN_JSON)
    creds = Credentials.from_authorized_user_info(creds_data)

    drive = build("drive", "v3", credentials=creds)
    youtube = build("youtube", "v3", credentials=creds)

    return drive, youtube


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


def main():
    print("🚀 Automation started")

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

        print("✅ Uploaded to YouTube:", video_id)
        print("🔗 URL:", f"https://www.youtube.com/watch?v={video_id}")

        # Move to uploaded
        move_file(drive, file_id, UPLOADED_FOLDER_ID)

    except Exception as e:
        print("❌ ERROR:", str(e))
        move_file(drive, file_id, FAILED_FOLDER_ID)


if __name__ == "__main__":
    main()
