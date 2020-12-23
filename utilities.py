import collections
import json
import re
import webbrowser

import pick
import requests


Document = collections.namedtuple("Document", ["content", "metadata"])


class BookNotFound(Exception):
    pass


def download_image(url, destination):
    r = requests.get(url, stream=True)
    if r.status_code == 200:
        with open(destination, 'wb') as fh:
            for chunk in r:
                fh.write(chunk)


def basename(name):
    name = re.sub(r"[^a-z0-9]+", " ", name.lower())
    name = re.sub(r"\W+", "-", name.strip())
    return name


def interactive_search(search_callback):
    page = 0
    default_index = 0
    selected = None

    query = input("Query: ")
    while True:
        books = search_callback(query=query, index=page)

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
                             f"[Page {page}]\n\nQuery: {query}\n\nv - view\nt - view thumbnail\nn - next page\np - previous page\nr - refine query",
                             indicator='*',
                             options_map_func=summary,
                             default_index=default_index)
        picker.register_custom_handler(ord('v'),  show_webpage)
        picker.register_custom_handler(ord('n'),  next)
        picker.register_custom_handler(ord('p'),  previous)
        picker.register_custom_handler(ord('r'),  refine)
        picker.register_custom_handler(ord('i'),  inspect)
        picker.register_custom_handler(ord('t'),  thumbnail)
        selected, index = picker.start()
        if index >= 0:
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
