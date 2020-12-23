#!/usr/bin/env python3

import argparse
import curses
import datetime
import os
import signal
import sys
import time

import dateutil.tz
import frontmatter
import pick

import books
import utilities


DIRECTORY = os.path.expanduser("~/Projects/jbmorley.co.uk/content/about/books")


def signal_handler(sig, frame):
    sys.exit(0)


def main():
    parser = argparse.ArgumentParser(description="Book tracker.")
    options = parser.parse_args()

    statuses = list(books.Status)

    def next_shelf(picker):
        selected, index = picker.get_selected()
        new_status_index = (statuses.index(selected.status) + 1)
        if new_status_index >= len(statuses):
            return
        selected.status = statuses[new_status_index]
        selected.save()

    def previous_shelf(picker):
        selected, index = picker.get_selected()
        new_status_index = (statuses.index(selected.status) - 1)
        if new_status_index < 0:
            return
        selected.status = statuses[new_status_index]
        selected.save()

    def cancel(picker):
        exit(0)

    signal.signal(signal.SIGINT, signal_handler)
    utilities.set_escdelay(25)
    picker = utilities.SearchablePicker(options=books.load(DIRECTORY),
                                        title="Books (all shelves)",
                                        options_map_func=lambda x: x.summary)
    picker.register_custom_handler(curses.KEY_LEFT, previous_shelf)
    picker.register_custom_handler(curses.KEY_RIGHT, next_shelf)
    picker.register_custom_handler(27, cancel)
    option, index = picker.start()


if __name__ == "__main__":
    main()
