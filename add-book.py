#!/usr/bin/env python3

import argparse
import collections
import json
import os
import re
import sys
import webbrowser

import frontmatter
import pick
import requests

import utilities


BOOKS_DIRECTORY = "~/Projects/jbmorley.co.uk/content/about/books/"


Document = collections.namedtuple("Document", ["content", "metadata"])

class GoogleBook(object):

    def __init__(self, data):
        self._data = data

    @property
    def id(self):
        return self._data["id"]

    @property
    def language(self):
        return self._data["volumeInfo"]["language"]

    @property
    def title(self):
        return self._data["volumeInfo"]["title"]

    @property
    def authors(self):
        try:
            return self._data["volumeInfo"]["authors"]
        except KeyError:
            return []

    @property
    def url(self):
        return self._data["volumeInfo"]["canonicalVolumeLink"]

    @property
    def thumbnail(self):
        if "imageLinks" not in self._data["volumeInfo"]:
            return None
        return self._data["volumeInfo"]["imageLinks"]["thumbnail"] + "&fife=w400-h600"

    @property
    def isbn(self):
        for identifier in self._data["volumeInfo"]["industryIdentifiers"]:
            if identifier["type"] == "ISBN_10":
                return identifier["identifier"]
        raise KeyError("isbn")

    @property
    def isbn_13(self):
        for identifier in self._data["volumeInfo"]["industryIdentifiers"]:
            if identifier["type"] == "ISBN_13":
                return identifier["identifier"]
        raise KeyError("isbn_13")

    @property
    def metadata(self):
        metadata = {
            "title": self.title,
            "authors": self.authors,
            "category": "books",
            "link": self.url,
            "ids": {
                "google_books": self.id,
            }
        }
        try:
            metadata["ids"]["isbn_10"] = self.isbn
        except KeyError:
            pass
        try:
            metadata["ids"]["isbn_13"] = self.isbn_13
        except KeyError:
            pass
        return metadata

    @property
    def basename(self):
        title = f"{self.title} {' '.join(self.authors)}"
        title = re.sub(r"[^a-z0-9]+", " ", title.lower())
        title = re.sub(r"\W+", "-", title.strip())
        return title


class BookNotFound(Exception):
    pass


def google_books(query, index=0):
    response = requests.get("https://www.googleapis.com/books/v1/volumes", params={"q": query, "startIndex": index})
    response_data = response.json()
    if response_data["totalItems"] < 1:
        raise BookNotFound()
    return [GoogleBook(data) for data in response_data['items']]


def google_interactive(query, details, accept_single_result=False):

    page = 0
    default_index = 0
    selected = None
    while True:
        books = google_books(query=query, index=page)
        if len(books) == 1 and accept_single_result:
            selected = books[0]
            break

        def summary(book):
            isbn = ""
            try:
                isbn = book.isbn
            except KeyError:
                pass
            try:
                isbn = book.isbn_13
            except KeyError:
                pass
            return f"{book.title[:30]:34}{', '.join(book.authors)[:20]:24}{book.language[:3]:5}{isbn}"

        def show_webpage(picker):
            selection, index = picker.get_selected()
            webbrowser.open(selection.url)

        def skip(picker):
            return None, -1

        def next(picker):
            return None, -2

        def previous(picker):
            return None, -5

        def refine(picker):
            return None, -3

        def inspect(picker):
            selection, index = picker.get_selected()
            return (selection, index), -4

        def thumbnail(picker):
            selection, index = picker.get_selected()
            webbrowser.open(selection.thumbnail)

        picker = pick.Picker(books,
                             f"[Page {page}]\n\nDetails: {details}\nQuery: {query}\n\nv - view\nt - view thumbnail\ns - skip\nn - next page\np - previous page\nr - refine",
                             indicator='*',
                             options_map_func=summary,
                             default_index=default_index)
        picker.register_custom_handler(ord('v'),  show_webpage)
        picker.register_custom_handler(ord('s'),  skip)
        picker.register_custom_handler(ord('n'),  next)
        picker.register_custom_handler(ord('p'),  previous)
        picker.register_custom_handler(ord('r'),  refine)
        picker.register_custom_handler(ord('i'),  inspect)
        picker.register_custom_handler(ord('t'),  thumbnail)
        selected, index = picker.start()
        if index >= 0:
            break
        if index == -1:
            break
        elif index == -2:
            page = page + 1
            default_index = 0
        elif index == -3:
            query = input("Refine query: ")
            page = 0
            default_index = 0
        elif index == -4:
            selected, default_index = selected
            print(json.dumps(selected._data, indent=4))
            print(selected.metadata)
            input("Press any key to continue...")
        elif index == -5:
            page = page - 1
            default_index = 0

    return selected


def main():
    parser = argparse.ArgumentParser(description="Add a new book")
    options = parser.parse_args()

    directory = os.path.expanduser(BOOKS_DIRECTORY)
    query = input("Query: ")
    new_book = google_interactive(query=query, details=f"query")
    cover_basename = f"{new_book.basename}.jpg"
    utilities.download_image(new_book.thumbnail, os.path.join(directory, cover_basename))
    metadata = dict(new_book.metadata)
    metadata["cover"] = cover_basename
    metadata["status"] = "to-read"
    contents = frontmatter.dumps(Document(content="", metadata=metadata))
    with open(os.path.join(directory, f"{new_book.basename}.markdown"), "w") as fh:
        fh.write(contents)
        fh.write("\n")


if __name__ == "__main__":
    main()
