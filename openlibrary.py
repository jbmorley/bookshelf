import collections
import json
import re
import webbrowser

import pick
import requests
import titlecase


NewAuthor = collections.namedtuple("NewAuthor", ["name"])


class Book(object):

    def __init__(self, isbn):
        try:
            # response = requests.get(f"https://openlibrary.org/isbn/{isbn}.json")
            # self._dictionary = response.json()

            # https://openlibrary.org/api/books?bibkeys=ISBN:9780380788620&jscmd=data&format=json
            key = f"ISBN:{isbn}"
            response = requests.get("https://openlibrary.org/api/books", params={"bibkeys": key, "jscmd": "data", "format": "json"})
            self._dictionary = response.json()[key]
        except json.decoder.JSONDecodeError:
            raise KeyError(isbn)

    def get(self, key, default):
        try:
            return self._dictionary[key]
        except KeyError:
            return default

    @property
    def url(self):
        return "https://openlibrary.org" + self.key

    @property
    def title(self):
        return self._dictionary["title"]

    @property
    def subtitle(self):
        try:
            return self._dictionary["subtitle"]
        except KeyError:
            return None

    @property
    def full_title(self):
        components = [self.title]
        if self.subtitle is not None:
            components.append(self.subtitle)
        return titlecase.titlecase(": ".join(components))

    @property
    def key(self):
        return self._dictionary["key"]

    @property
    def cover(self):
        try:
            covers = self._dictionary["covers"][0]
            return covers
        except KeyError:
            return None

    @property
    def authors(self):
        if "authors" not in self._dictionary:
            return []
        # return [Author(author["key"]) for author in self._dictionary["authors"]]
        return [NewAuthor(name=author["name"]) for author in self._dictionary["authors"]]

    @property
    def isbn(self):
        try:
            return self._dictionary["isbn_10"][0]
        except KeyError:
            return None

    @property
    def isbn_13(self):
        try:
            return self._dictionary["isbn_13"][0]
        except KeyError:
            return None

    @property
    def format(self):
        try:
            return self._dictionary["physical_format"]
        except KeyError:
            return None

    @property
    def basename(self):
        title = f"{self.title} {self.authors[0]}"
        title = re.sub(r"[^a-z0-9]+", " ", title.lower())
        title = re.sub(r"\W+", "-", title.strip())
        return title

    @property
    def metadata(self):
        metadata = {
            "title": self.full_title,
            "authors": [author.name for author in self.authors],
            "category": "books",
            "link": self.url,
            "ids": {
                "openlibrary": self.key,
            }
        }

        if self.isbn is not None:
            metadata["isbn"] = self.isbn
        if self.isbn_13 is not None:
            metadata["isbn_13"] = self.isbn_13

        return metadata


class Cache(object):

    def __init__(self):
        self._results = {}

    def get(self, url):
        if url not in self._results:
            response = requests.get(url)
            self._results[url] = response.json()
        return self._results[url]


cache = Cache()


class Author(object):

    def __init__(self, key):
        url = f"https://openlibrary.org{key}.json"
        self._data = cache.get(url)

    @property
    def name(self):
        return self._data["name"]


def search(query=None, title=None, author=None):
    # TODO: Check if it's better to search by ISBN 13

    params = {}
    if query is not None:
        params["q"] = query
    if title is not None:
        params["title"] = title
    if author is not None:
        params["author"] = author

    response = requests.get("http://openlibrary.org/search.json", params=params)
    results = []
    for doc in response.json()["docs"][:3]:
        try:
            isbns = doc["isbn"]
            results.extend(isbns)
        except KeyError:
            pass
    return [Book(isbn) for isbn in results]


def interactive_search(query=None, title=None, author=None):
    books = search(query=query, title=title, author=author)
    if not books:
        raise KeyError(query)

    def summary(book):
        details = ", ".join([book.full_title] + [author.name for author in book.authors])
        summary = [details]
        if book.format is not None:
            summary.append(book.format)
        if book.cover is not None:
            summary.append("📗")
        return " -- ".join(summary)

    def show_webpage(picker):
        selection, index = picker.get_selected()
        webbrowser.open(selection.url)

    def skip(picker):
        return None, -1

    picker = pick.Picker(books, "Select edition ('v' to view, 's' to skip):", indicator='*', options_map_func=summary)
    picker.register_custom_handler(ord('v'),  show_webpage)
    picker.register_custom_handler(ord('s'),  skip)
    selected, index = picker.start()
    return selected
