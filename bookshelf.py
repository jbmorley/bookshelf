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


class EmptyBook(object):

    @property
    def summary(self):
        return "Empty"


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

    def delete_book(picker):
        selected, index = picker.get_selected()
        return selected, -5

    def cancel(picker):
        return None, -3

    def thumbnail(picker):
        selected, index = picker.get_selected()
        return selected, -4

    def edit(picker):
        selected, index = picker.get_selected()
        return selected, -6

    signal.signal(signal.SIGINT, signal_handler)
    utilities.set_escdelay(25)
    options = books.load(directory)
    if not options:
        options = [EmptyBook()]
    default_index = [book.path for book in options].index(selected_path) if selected_path is not None else 0
    picker = utilities.SearchablePicker(options=options,
                                        title="Bookshelf\n\ntab - add book\nleft/right - change status\n\\ - view thumbnail\n+ - edit\ndel - delete\nesc - exit",
                                        options_map_func=lambda x: x.summary,
                                        default_index=default_index)
    picker.register_custom_handler(curses.KEY_LEFT, previous_shelf)
    picker.register_custom_handler(curses.KEY_RIGHT, next_shelf)
    picker.register_custom_handler(ord('\t'), add_book)
    picker.register_custom_handler(ord('\\'), thumbnail)
    picker.register_custom_handler(127, delete_book)
    picker.register_custom_handler(curses.KEY_BACKSPACE, delete_book)
    picker.register_custom_handler(27, cancel)
    picker.register_custom_handler(ord('+'), edit)

    book, index = picker.start()
    if index == -2:
        raise AddBookInterrupt()
    elif index == -3:
        raise ExitInterrupt()
    elif index == -4:
        cover_path = book.cover_path
        if cover_path is not None:
            utilities.preview_image(cover_path)
        else:
            input("Missing cover.")
    elif index == -5:
        answer = input("Delete book? [y/N] ")
        if answer.lower() == "y":
            if os.path.exists(book.cover_path):
                os.remove(book.cover_path)
            if os.path.exists(book.path):
                os.remove(book.path)
            return
    elif index == -6:
        subprocess.check_call([os.environ['EDITOR'], book.path])
    return book.path


class Bookshelf(object):

    def __init__(self):
        self.directory = books.library_path()

    def run(self):

        print("Updating library...")
        with utilities.Chdir(self.directory):
            subprocess.check_call(["git", "fetch", "origin"])
            subprocess.check_call(["git", "rebase", "--autostash", "origin/main"])

        new_book_path = None
        while True:
            try:
                new_book_path = interactive_books(directory=self.directory, selected_path=new_book_path)
            except AddBookInterrupt:
                new_book_path = books.add_book(directory=self.directory, search_callback=googlebooks.search)
            except ExitInterrupt:
                answer = input("Save? [Y/n] ")
                if answer.lower() == "y" or answer == "":
                    print("Saving...")
                    with utilities.Chdir(self.directory):
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
