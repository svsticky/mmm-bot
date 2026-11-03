import gspread
from google.oauth2.service_account import Credentials
import html
import gdown
from time import strftime
from PIL import Image
import io
import re
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload
import os

google_scopes = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive.readonly",
]
google_creds = Credentials.from_service_account_file("credentials.json", scopes=google_scopes)
client = gspread.authorize(google_creds)
drive = build("drive", "v3", credentials=google_creds)

def extract_drive_id(url):
    m = re.search(r"/d/([A-Za-z0-9_-]+)", url) or re.search(r"[?&]id=([A-Za-z0-9_-]+)", url)
    if not m:
        sys.exit(f"Cannot find Drive file ID in: {url}")
    return m.group(1)

def download_banner(url):
    file_id = extract_drive_id(url)

    # Check metadata
    meta = drive.files().get(fileId=file_id, fields="mimeType").execute()
    if not meta["mimeType"].startswith("image/"):
        sys.exit(f"No image, but {meta['mimeType']}")

    # Download to memory
    buf = io.BytesIO()
    downloader = MediaIoBaseDownload(buf, drive.files().get_media(fileId=file_id))
    done = False
    while not done:
        _, done = downloader.next_chunk()
    buf.seek(0)

    # Validate and convert to PNG
    with Image.open(buf) as img:
        img.verify()
    buf.seek(0)
    with Image.open(buf) as img:
        if img.format not in {"JPEG", "JPG", "PNG", "WEBP"}:
            raise ValueError(f"Unsupported format: {img.format}")
        out = io.BytesIO()
        img.convert("RGBA").save(out, "PNG")

    timestamp = strftime("%Y%m%d%H%M%S")
    filename = f"mmm_banner_{timestamp}.png"
    return filename, out.getvalue()

# Open MMM Google Sheet
sheet_id = os.environ["SHEET_ID"] # "{{ secret_listmonk.google_sheet_id }}"
workbook = client.open_by_key(sheet_id)

def get_row_data():
    MAX_ROW_AMOUNT = 100
    previous_row_data = workbook.sheet1.row_values(1)
    for row_idx in range(2, MAX_ROW_AMOUNT):
        next_row_data = workbook.sheet1.row_values(row_idx)
        if not next_row_data:
            return previous_row_data
        else:
            previous_row_data = next_row_data