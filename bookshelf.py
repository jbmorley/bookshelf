#!/usr/bin/env python3

import argparse
import curses
import datetime
import enum
import os
import signal
import sys
import time

import dateutil.tz
import frontmatter
import pick

import utilities


DIRECTORY = os.path.expanduser("~/Projects/jbmorley.co.uk/content/about/books")


class Item(object):

    def __init__(self, path):
        self.path = path
        self.document = frontmatter.load(path)

    @property
    def title(self):
        return  self.document.metadata["title"]

    @property
    def status(self):
        return Status(self.document.metadata["status"])

    @status.setter
    def status(self, status):
        self.document.metadata["status"] = status.value
        if status == Status.TO_READ:
            self.date = None
            self.end_date = None
        elif status == Status.CURRENTLY_READING:
            self.date = utilities.tznow()
            self.end_date = None
        elif status == Status.READ or status == Status.ABANDONED:
            self.end_date = utilities.tznow()

    @property
    def summary(self):
        return f"{self.title} [{self.status.value}]"

    @property
    def date(self):
        return dateutil.parser.parse(self.document.metadata["date"])

    @date.setter
    def date(self, date):
        if date is None:
            try:
                del self.document.metadata["date"]
            except KeyError:
                pass
            return
        self.document.metadata["date"] = date.isoformat()

    @property
    def end_date(self):
        return dateutil.parser.parse(self.document.metadata["end_date"])

    @end_date.setter
    def end_date(self, end_date):
        if end_date is None:
            try:
                del self.document.metadata["end_date"]
            except KeyError:
                pass
            return
        self.document.metadata["end_date"] = end_date.isoformat()

    def save(self):
        with open(self.path, "w") as fh:
            fh.write(frontmatter.dumps(self.document))
            fh.write("\n")


def signal_handler(sig, frame):
    sys.exit(0)


def load_items(path):
    paths = [os.path.join(path, f) for f in os.listdir(path)
             if (f.lower().endswith(".markdown") and
                 not f.lower().endswith("index.markdown"))]
    items = [Item(path) for path in paths]
    items = sorted(items, key=lambda x: x.title)
    return items


class Status(enum.Enum):
    TO_READ = "to-read"
    CURRENTLY_READING = "currently-reading"
    READ = "read"
    ABANDONED = "abandoned"

STATUSES = [
    Status.TO_READ,
    Status.CURRENTLY_READING,
    Status.READ,
    Status.ABANDONED,
]


def main():
    parser = argparse.ArgumentParser(description="Book tracker.")
    options = parser.parse_args()

    def next_shelf(picker):
        selected, index = picker.get_selected()
        new_status_index = (STATUSES.index(selected.status) + 1)
        if new_status_index >= len(STATUSES):
            return
        selected.status = STATUSES[new_status_index]
        selected.save()

    def previous_shelf(picker):
        selected, index = picker.get_selected()
        new_status_index = (STATUSES.index(selected.status) - 1)
        if new_status_index < 0:
            return
        selected.status = STATUSES[new_status_index]
        selected.save()

    def cancel(picker):
        exit(0)

    signal.signal(signal.SIGINT, signal_handler)
    documents = load_items(DIRECTORY)
    utilities.set_escdelay(25)
    picker = utilities.SearchablePicker(options=documents,
                                        title="Books (all shelves)",
                                        options_map_func=lambda x: x.summary)
    picker.register_custom_handler(curses.KEY_LEFT, previous_shelf)
    picker.register_custom_handler(curses.KEY_RIGHT, next_shelf)
    picker.register_custom_handler(27, cancel)
    option, index = picker.start()


if __name__ == "__main__":
    main()
