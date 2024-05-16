#!/usr/bin/env python3

import argparse
import datetime
import json
import os
import re
import webbrowser
import collections

import dateutil.tz
import frontmatter
import pick
import pytz
import requests

import openlibrary


BOOKS_DIRECTORY = "~/Projects/jbmorley.co.uk/content/about/books/"


Document = collections.namedtuple("Document", ["content", "metadata"])


def safe_basename(title):
    title = re.sub(r"[^a-z0-9]+", " ", title.lower())
    title = re.sub(r"\W+", "-", title.strip())
    return title


def main():
    parser = argparse.ArgumentParser(description="Create a new book entry")
    options = parser.parse_args()

    query = input("Search: ")
    selected = openlibrary.interactive_search(query=query)
    metadata = selected.metadata

    status, _ = pick.pick(["read", "to-read", "abandoned", "currently-reading"], "Status")
    metadata["status"] = status

    # Determine where to put the date based on the status.
    date = datetime.datetime.now().replace(tzinfo=dateutil.tz.tzlocal()).isoformat()
    if status == "currently-reading":
        metadata["date"] = date
    elif status == "read":
        metadata["end_date"] = date

    destination = os.path.expanduser(BOOKS_DIRECTORY)
    with open(os.path.join(destination, f"{selected.basename}.md"), "w") as fh:
        fh.write(frontmatter.dumps(Document(content="", metadata=metadata)))
        fh.write("\n")


if __name__ == "__main__":
    main()
