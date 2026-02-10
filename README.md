# 🎥 Automated Video Upload & Website Integration System

## Overview

This repository documents and implements a **fully automated video pipeline** that connects a website, Google Drive, GitHub Actions, and YouTube to create a private/unlisted video hosting system with automatic website integration.

The system is designed to:

* Handle large video uploads efficiently
* Avoid server bandwidth costs
* Use YouTube as a backend streaming CDN
* Automatically embed uploaded videos on a website

---

## 🧠 System Architecture

```
Website Upload
   ↓
Google Drive (pending folder)
   ↓
GitHub Actions Automation
   ↓
YouTube (Private / Unlisted)
   ↓
Metadata Store (DB / JSON / API)
   ↓
Website Auto Embed
```

Each component is loosely coupled to ensure reliability and scalability.

---

## 📁 Google Drive Folder Structure

```
/video-system
 ├── pending/        # New uploads from website
 ├── processing/     # Video currently being uploaded
 ├── uploaded/       # Successfully uploaded videos
 └── failed/         # Failed uploads (retry/debug)
```

Drive folders act as a **queue + visual status tracker**.

---

## 🔹 Step 1: Website → Google Drive Upload

### What happens

* User uploads a video on the website
* Website uses Google OAuth 2.0 (`drive.file` scope)
* Video uploads **directly from browser to Google Drive**
* File is placed in the `pending/` folder

### Why this works

* No server load
* Supports large files
* Upload resume supported

---

## 🔹 Step 2: Pending Folder = Queue

The `pending/` folder represents videos waiting for processing.

Rule:

> Automation only reads from `pending/`

---

## 🔹 Step 3: GitHub Actions Automation

GitHub Actions acts as a **serverless worker**.

### Automation responsibilities

1. Scan `pending/` folder
2. Move file to `processing/`
3. Upload video to YouTube
4. Generate metadata
5. Notify website backend
6. Move file to `uploaded/` or `failed/`

---

## 🔹 Step 4: YouTube Upload

### Upload configuration

* Privacy: `private` or `unlisted`
* OAuth 2.0 with refresh token

### YouTube API response

* `videoId`
* Upload timestamp
* Privacy status

Generated link:

```
https://www.youtube.com/watch?v=VIDEO_ID
```

---

## 🔹 Step 5: Metadata Generation (Single Source of Truth)

After upload, automation generates a metadata record.

### Metadata fields

* video_id
* youtube_url
* original_filename
* drive_file_id
* upload_time
* status

This metadata is the **brain of the system**.

---

## 🔹 Step 6: Automatic Website Integration

### Recommended approach

Automation sends metadata to website backend via API (POST request).

Website:

* Saves metadata in DB
* Automatically renders video player

### Embed example

```html
<iframe src="https://www.youtube.com/embed/VIDEO_ID" allowfullscreen></iframe>
```

User sees video on website, YouTube handles streaming.

---

## 🔹 Step 7: Drive Folder Finalization

* On success → move to `uploaded/`
* On failure → move to `failed/`

Folders = logs
Metadata = truth

---

## 🔐 Security Practices

* No API keys in frontend
* OAuth tokens stored as GitHub Secrets
* Limited Drive scope (`drive.file`)
* Videos not public by default

---

## 🧩 Tech Stack

* Website: Any (React / HTML / PHP / etc.)
* Storage Queue: Google Drive
* Automation: GitHub Actions
* Video CDN: YouTube
* Backend Metadata: API / DB / JSON

---

## 🚀 Future Enhancements

* Role-based access
* Paid video locking
* Analytics sync
* AI tagging & thumbnails
* Retry & rate-limit handling

---

## ✅ Final Notes

This project is not just automation — it is the foundation of a **private video distribution platform**.

Simple components. Strong architecture. Zero unnecessary complexity.
