import base64
import json
import os
import sys
import urllib.parse
import urllib.request
import requests
from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo
import html

from mmm_bot.google import get_row_data, download_banner
from mmm_bot.koala import retrieve_poster

CAMPAIGN_TAG = "mmm"
LISTMONK_URL = "https://listmonk." + os.environ["CANONICAL_HOSTNAME"]

class Listmonk:
    def __init__(self):
        user = os.environ["LISTMONK_USER"]
        token = os.environ["LISTMONK_TOKEN"]
        self.auth = f"token {user}:{token}"

    def call(self, method, path, body=None):
        data = json.dumps(body).encode() if body is not None else None
        req = urllib.request.Request(
            LISTMONK_URL + path, data=data, method=method,
            headers={"Authorization": self.auth, "Content-Type": "application/json"},
        )
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                return json.load(resp)["data"]
        except urllib.error.HTTPError as e:
            sys.exit(f"Listmonk error ({e.code}): {method} {path}: {e.read().decode()}")

    def latest_concept(self):
        params = urllib.parse.urlencode([
            ("tag", CAMPAIGN_TAG), ("status", "draft"), ("status", "scheduled"),
            ("order_by", "created_at"), ("order", "DESC"),
            ("per_page", "1"), ("no_body", "true"),
        ])
        results = self.call("GET", f"/api/campaigns?{params}")["results"]
        if not results:
            sys.exit(f"No campaign found with tag {CAMPAIGN_TAG}")
        return results[0]["id"]

    def upload_image(self, filename, content, content_type):
        resp = requests.post(
            LISTMONK_URL + "/api/media",
            headers={"Authorization": self.auth},  # no Content-Type: requests sets the multipart boundary
            files={"file": (filename, content, content_type)},
            timeout=30,
        )
        if not resp.ok:
            sys.exit(f"Listmonk error ({resp.status_code}): POST /api/media: {resp.text}")
        return resp.json()["data"]["url"]

    def get_body(self, camp, activity_ids, dry_run):
        body = {}
        body["lists"] = [l["id"] for l in camp["lists"]]
        
        row_data = get_row_data()
        subject = row_data[2]
        author = row_data[3]

        # Banner
        filename, content = download_banner(row_data[4])
        banner_listmonk_link = self.upload_image(filename, content, "image/png")

        # Story
        text = row_data[5].replace("\r\n", "\n")
        paragraphs = html.escape(text).split("\n\n")
        story = "".join(f"<p>{p.replace(chr(10), '<br>')}</p>" for p in paragraphs)

        dilemma_1 = row_data[6]
        dilemma_2 = row_data[7]

        body["subject"] = subject

        attribs = dict(camp.get("attribs") or {}) # other attributes will remain
        attribs["Author"] = author
        attribs["Banner"] = banner_listmonk_link
        attribs["Story"] = story
        attribs["Dilemma_1"] = dilemma_1
        attribs["Dilemma_2"] = dilemma_2
        attribs["activities"] = activity_ids

        # Activities
        for activity_id in activity_ids:
            poster = retrieve_poster(activity_id)
            if dry_run:
                print(f"Dry run, would upload poster for {activity_id}")
            else:
                filename = f"poster-{activity_id}.webp"
                self.upload_image(filename, *poster)

        body["attribs"] = attribs
        return body

    def update_email_content(self, campaign_id, activity_ids, dry_run=False):
        camp = self.call("GET", f"/api/campaigns/{campaign_id}")
        
        body = self.get_body(camp, activity_ids, dry_run)
        
        print(f"Campaign {campaign_id}: '{camp['name']}' ({camp['status']})", file=sys.stderr)
        if dry_run:
            print("Dry run, nothing updated. Would send:", json.dumps(body), file=sys.stderr)
            return
        self.call("PUT", f"/api/campaigns/{campaign_id}", body)
        print("Updated.", file=sys.stderr)
