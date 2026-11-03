#!/usr/bin/env python3
# {{ ansible_managed }}

"""
This script retrieves the public activities starting coming Monday from
Koala and puts their IDs in the attributes of the latest MMM campaign in
Listmonk (max 6 activities, sorted on time).  The MMM template uses these
IDs to build the links to the activities and their posters.
Furthermore, it grabs data (story, image, dilemma, etc.) from a spreadsheet to fill in the rest of the MMM. 

Usage:
    python3 mmm_automation.py
    Update latest compaign with the mmm tag (either concept or planned)

    python3 mmm_automation.py --dry-run
    Show the updates to Listmonk without sending requests to Listmonk

    python3 mmm_automation.py --print
    Print the JSON that can be pasted into the Listmonk campaign (doesn't require Listmonk to run)

    python3 mmm_automation.py --campaign 42
    python3 mmm_automation.py --week 2026-10-05
    Update specific campaign
"""
import argparse
import sys
import mmm_bot.google
import mmm_bot.listmonk
import mmm_bot.koala

def main() -> None:
    p = argparse.ArgumentParser(description="Update the latest MMM campaign with next weeks' activities & spreadsheet data")
    p.add_argument("--week", help="Monday from when activities should be included (YYYY-MM-DD)")
    p.add_argument("--campaign", type=int, help="Campaign ID, default: the latest campaign")
    p.add_argument("--dry-run", action="store_true", help="Do not send the update request to Listmonk")
    p.add_argument("--print", action="store_true", help="Just print the attributes JSON")
    args = p.parse_args()

    start = koala.week_start(args.week)
    ids = koala.select(koala.retrieve_activities(), start)
    print(f"{len(ids)} activiteit(en) vanaf {start:%d-%m-%Y}: {ids}", file=sys.stderr)

    if args.print:
        print(json.dumps({"activities": ids}))
        return

    lm = listmonk.Listmonk()
    lm.update_email_content(args.campaign or lm.latest_concept(), ids, args.dry_run)