#!/usr/bin/env python3

import argparse
import curses
import datetime
import os
import signal
import string
import sys
import time

import frontmatter
import pick


DIRECTORY = os.path.expanduser("~/Projects/jbmorley.co.uk/content/about/books")


class SearchString(object):

    def __init__(self):
        self.timestamp = datetime.datetime.now()
        self.value = ""

    def add(self, character):
        now = datetime.datetime.now()
        if now - self.timestamp > datetime.timedelta(seconds=1):
            self.value = ""
        self.value += character
        self.timestamp = now


class Item(object):

    def __init__(self, path):
        self.path = path
        self.document = frontmatter.load(path)

    @property
    def title(self):
        return  ", ".join([self.document.metadata["title"]] + self.document.metadata["authors"])


def signal_handler(sig, frame):
    sys.exit(0)


def load_items(path):
    paths = [os.path.join(path, f) for f in os.listdir(path)
             if (f.lower().endswith(".markdown") and
                 not f.lower().endswith("index.markdown"))]
    items = [Item(path) for path in paths]
    items = sorted(items, key=lambda x: x.title)
    return items


class SearchablePicker(pick.Picker):

    def __init__(self, *args, **kwargs):
        super(SearchablePicker, self).__init__(*args, **kwargs)
        pick.KEYS_UP = [curses.KEY_UP]
        pick.KEYS_DOWN = [curses.KEY_DOWN]
        search = SearchString()

        def key_handler(character):
            def inner(picker):
                search.add(character)
                destination = -1
                for index, details in enumerate(picker.options):
                    title = picker.options_map_func(details)
                    if title.lower().startswith(search.value):
                        destination = index
                        break
                selected, index = picker.get_selected()
                if destination == -1 or destination == index:
                    return
                elif destination > index:
                    while index < destination:
                        picker.move_down()
                        selected, index = picker.get_selected()
                else:
                    while index > destination:
                        picker.move_up()
                        selected, index = picker.get_selected()
            return inner

        for letter in string.ascii_lowercase + " ":
            self.register_custom_handler(ord(letter), key_handler(letter))


def main():
    parser = argparse.ArgumentParser(description="Book tracker.")
    options = parser.parse_args()

    documents = load_items(DIRECTORY)

    signal.signal(signal.SIGINT, signal_handler)
    picker = SearchablePicker(options=documents,
                              title="Books",
                              options_map_func=lambda x: x.title)
    option, index = picker.start()
    print(book_title(option))


if __name__ == "__main__":
    main()
