import requests

import utilities


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
    def volume_info(self):
        return self._data["volumeInfo"]

    @property
    def title(self):
        if "subtitle" in self.volume_info:
            return f"{self.volume_info['title']}: {self.volume_info['subtitle']}"
        return self.volume_info["title"]

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
        return utilities.basename(f"{self.title} {' '.join(self.authors)}")


def search(query, index=0):
    response = requests.get("https://www.googleapis.com/books/v1/volumes",
                            params={"q": query, "startIndex": index})
    response_data = response.json()
    if response_data["totalItems"] < 1:
        raise utilities.BookNotFound()
    return [GoogleBook(data) for data in response_data['items']]
