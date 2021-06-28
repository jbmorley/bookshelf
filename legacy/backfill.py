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

import openlibrary


BOOKS_DIRECTORY = "~/Projects/jbmorley.co.uk/content/about/books/"


Document = collections.namedtuple("Document", ["content", "metadata"])

class Book(object):

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
            metadata["isbn"] = self.isbn
        except KeyError:
            pass
        try:
            metadata["isbn_13"] = self.isbn_13,
        except KeyError:
            pass
        return metadata


class BookNotFound(Exception):
    pass


def google_books(query, index=0):
    response = requests.get("https://www.googleapis.com/books/v1/volumes", params={"q": query, "startIndex": index})
    response_data = response.json()
    if response_data["totalItems"] < 1:
        raise BookNotFound()
    return [Book(data) for data in response_data['items']]


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
            query = input("New query: ")
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


def google_books_by_isbn(isbn):
    books = google_books(query=isbn)
    book = books[0]
    try:
        if book.isbn == isbn:
            return book
    except KeyError:
        pass
    try:
        if book.isbn_13 == isbn:
            return book
    except KeyError:
        pass
    raise BookNotFound


def main():
    parser = argparse.ArgumentParser(description="Complete the book files")
    parser.add_argument("--skip-interactive", action="store_true", default=False, help="skip interactive lookup for books without ISBNs")
    options = parser.parse_args()

    directory = os.path.expanduser(BOOKS_DIRECTORY)

    files = [os.path.join(directory, f) for f in os.listdir(os.path.expanduser(BOOKS_DIRECTORY))
             if re.match(r"^[0-9]+\.markdown$", f)]

    for f in files:
        book = frontmatter.load(f)
        title = book.metadata['title']
        author = book.metadata['authors'][0] if book.metadata["authors"] else ""

        sys.stdout.write(f"{title}, {author}... ")
        sys.stdout.flush()
        new_book = None
        if "google_books" in book.metadata["ids"]:
            sys.stdout.write(f"skipping\n")
            sys.stdout.flush()
            continue
        if "isbn" not in book.metadata and "isbn_13" not in book.metadata:
            sys.stdout.write(f"interactive search\n")
            sys.stdout.flush()
            query = f"{title} {author}"
            try:
                new_book = google_interactive(query=query, details=f"{title}, {author}")
            except BookNotFound:
                pass
        else:
            isbn = book.metadata["isbn_13"] if "isbn_13" in book.metadata else book.metadata["isbn"]
            sys.stdout.write(f"ISBN {isbn}\n")
            sys.stdout.flush()
            if new_book is None:
                try:
                    new_book = google_books_by_isbn(isbn=book.metadata["isbn_13"])
                except (KeyError, BookNotFound):
                    pass
            if new_book is None:
                try:
                    new_book = google_books_by_isbn(isbn=book.metadata["isbn"])
                except (KeyError, BookNotFound):
                    pass
            if new_book is None:
                new_book = google_interactive(query=f"{title} {author}", details=f"{title}, {author} (ISBN {isbn})")

        if new_book is None:
            print(f"Unable to find '{title}'")
            continue

        metadata = new_book.metadata
        metadata['ids']['goodreads'] = book.metadata['ids']['goodreads']
        metadata['status'] = book.metadata['status']

        # Preserve the dates.
        if "date" in book.metadata:
            metadata["date"] = book.metadata["date"]
        if "end_date" in book.metadata:
            metadata["end_date"] = book.metadata["end_date"]

        # Preserve ISBNs if they're somehow missing in the OpenLibrary.
        if "isbn" not in metadata and "isbn" in book.metadata:
            metadata["isbn"] = book.metadata["isbn"]
        if "isbn_13" not in metadata and "isbn_13" in book.metadata:
            metadata["isbn_13"] = book.metadata["isbn_13"]

        # Download the image.
        if new_book.thumbnail is not None:
            r = requests.get(new_book.thumbnail, stream=True)
            if r.status_code == 200:
                with open(os.path.join(directory, new_book.id + ".jpeg"), 'wb') as fh:
                    for chunk in r:
                        fh.write(chunk)

        # Write the markdown file.
        contents = frontmatter.dumps(Document(content="", metadata=metadata))
        with open(f, "w") as fh:
            fh.write(contents)
            fh.write("\n")


if __name__ == "__main__":
    main()
