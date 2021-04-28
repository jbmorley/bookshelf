#!/usr/bin/env python3

import argparse
import curses
import datetime
import os
import signal
import subprocess
import sys
import time

import dateutil.tz
import frontmatter
import pick

import books
import googlebooks
import utilities


class AddBookInterrupt(Exception):
    pass


class ExitInterrupt(Exception):
    pass


def signal_handler(sig, frame):
    sys.exit(0)


def interactive_books(directory, selected_path=None):
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

    def add_book(picker):
        return None, -2

    def cancel(picker):
        return None, -3

    signal.signal(signal.SIGINT, signal_handler)
    utilities.set_escdelay(25)
    options = books.load(directory)
    default_index = [book.path for book in options].index(selected_path) if selected_path is not None else 0
    picker = utilities.SearchablePicker(options=options,
                                        title="Bookshelf\n\ntab - add book\nleft/right - change status\nesc - exit",
                                        options_map_func=lambda x: x.summary,
                                        default_index=default_index)
    picker.register_custom_handler(curses.KEY_LEFT, previous_shelf)
    picker.register_custom_handler(curses.KEY_RIGHT, next_shelf)
    picker.register_custom_handler(ord('\t'), add_book)
    picker.register_custom_handler(27, cancel)

    book, index = picker.start()
    if index == -2:
        raise AddBookInterrupt()
    elif index == -3:
        raise ExitInterrupt()
    return book


class Bookshelf(object):

    def __init__(self):
        self.directory = books.library_path()

    def run(self):
        new_book_path = None
        while True:
            try:
                interactive_books(directory=self.directory, selected_path=new_book_path)
                new_book_path = None
            except AddBookInterrupt:
                new_book_path = books.add_book(directory=self.directory, search_callback=googlebooks.search)
            except ExitInterrupt:
                answer = input("Save? [y/N] ")
                if answer == "y":
                    print("Saving...")
                    os.chdir(self.directory)
                    subprocess.check_call(["git", "add", "."])
                    subprocess.check_call(["git", "commit", "-m", "Updating reading list"])
                    subprocess.check_call(["git", "push"])
                exit(0)



def main():
    parser = argparse.ArgumentParser(description="Book tracker.")
    options = parser.parse_args()

    bookshelf = Bookshelf()
    bookshelf.run()


if __name__ == "__main__":
    main()
