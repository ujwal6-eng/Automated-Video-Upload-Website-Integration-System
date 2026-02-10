import os
import io
import requests
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload, MediaFileUpload

# ENV
PENDING_FOLDER_ID = os.getenv("PENDING_FOLDER_ID")
PROCESSING_FOLDER_ID = os.getenv("PROCESSING_FOLDER_ID")
UPLOADED_FOLDER_ID = os.getenv("UPLOADED_FOLDER_ID")
FAILED_FOLDER_ID = os.getenv("FAILED_FOLDER_ID")


def get_drive_service():
    creds = Credentials(
        None,
        refresh_token=os.getenv("DRIVE_REFRESH_TOKEN"),
        token_uri="https://oauth2.googleapis.com/token",
        client_id=os.getenv("DRIVE_CLIENT_ID"),
        client_secret=os.getenv("DRIVE_CLIENT_SECRET"),
        scopes=["https://www.googleapis.com/auth/drive"]
    )
    return build("drive", "v3", credentials=creds)


def get_youtube_service():
    creds = Credentials(
        None,
        refresh_token=os.getenv("YT_REFRESH_TOKEN"),
        token_uri="https://oauth2.googleapis.com/token",
        client_id=os.getenv("YT_CLIENT_ID"),
        client_secret=os.getenv("YT_CLIENT_SECRET"),
        scopes=["https://www.googleapis.com/auth/youtube.upload"]
    )
    return build("youtube", "v3", credentials=creds)


def list_pending_files(drive):
    query = f"'{PENDING_FOLDER_ID}' in parents and trashed=false"
    res = drive.files().list(q=query, fields="files(id,name)").execute()
    return res.get("files", [])


def move_file(drive, file_id, target_folder):
    file = drive.files().get(fileId=file_id, fields="parents").execute()
    prev_parents = ",".join(file.get("parents"))
    drive.files().update(
        fileId=file_id,
        addParents=target_folder,
        removeParents=prev_parents
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

    media = MediaFileUpload(file_path, chunksize=-1, resumable=True)

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

    drive = get_drive_service()
    youtube = get_youtube_service()

    files = list_pending_files(drive)
    if not files:
        print("✅ No pending videos")
        return

    file = files[0]
    file_id = file["id"]
    filename = file["name"]

    print("🎬 Processing:", filename)

    try:
        move_file(drive, file_id, PROCESSING_FOLDER_ID)

        local_path = download_file(drive, file_id, filename)
        video_id = upload_to_youtube(youtube, local_path, filename)

        print("✅ Uploaded to YouTube:", video_id)

        move_file(drive, file_id, UPLOADED_FOLDER_ID)

        print("🔗 Video URL:", f"https://www.youtube.com/watch?v={video_id}")

    except Exception as e:
        print("❌ ERROR:", e)
        move_file(drive, file_id, FAILED_FOLDER_ID)


if __name__ == "__main__":
    main()
