import curses
import enum
import json
import os
import subprocess
import tempfile
import webbrowser

import dateutil
import frontmatter
import pick

import utilities


class Status(enum.Enum):
    TO_READ = "to-read"
    CURRENTLY_READING = "currently-reading"
    READ = "read"
    ABANDONED = "abandoned"


class Book(object):

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


def interactive_search(search_callback):
    with tempfile.TemporaryDirectory() as temporary_directory:
        page = 0
        default_index = 0
        selected = None

        query = input("Search: ")
        if not query:
            return
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

            def cancel(picker):
                return None, -1

            def next(picker):
                return None, -2

            def previous(picker):
                if page == 0:
                    return
                return None, -5

            def refine(picker):
                return None, -3

            def inspect(picker):
                selection, index = picker.get_selected()
                return (selection, index), -4

            def thumbnail(picker):
                selection, index = picker.get_selected()
                return (selection, index), -6

            utilities.set_escdelay(25)
            picker = pick.Picker(books,
                                 f"Add Book ({page + 1})\n\nv - view\nt - view thumbnail\ntab - refine search\nleft/right - change page\ni - inspect\nesc - back",
                                 indicator='*',
                                 options_map_func=summary,
                                 default_index=default_index)
            picker.register_custom_handler(27,  cancel)
            picker.register_custom_handler(ord('v'),  show_webpage)
            picker.register_custom_handler(ord('n'),  next)
            picker.register_custom_handler(curses.KEY_RIGHT,  next)
            picker.register_custom_handler(ord('p'),  previous)
            picker.register_custom_handler(curses.KEY_LEFT,  previous)
            picker.register_custom_handler(ord('\t'),  refine)
            picker.register_custom_handler(ord('i'),  inspect)
            picker.register_custom_handler(ord('t'),  thumbnail)
            selected, index = picker.start()
            if index >= 0:
                break
            elif index == -1:
                break
            elif index == -2:
                page = page + 1
                default_index = 0
            elif index == -3:
                query = input("Search: ")
                page = 0
                default_index = 0
            elif index == -4:
                selected, default_index = selected
                thumbnail_path = os.path.join(temporary_directory, "thumbnail.jpg")
                utilities.download_image(selected.thumbnail, thumbnail_path)
                utilities.preview_image(thumbnail_path)
                print(json.dumps(selected._data, indent=4))
                print(selected.metadata)
                input("Press any key to continue...")
            elif index == -5:
                page = max(page - 1, 0)
                default_index = 0
            elif index == -6:
                selected, default_index = selected
                thumbnail_path = os.path.join(temporary_directory, "thumbnail.jpg")
                utilities.download_image(selected.thumbnail, thumbnail_path)
                utilities.preview_image(thumbnail_path)

        return selected


def library_path():
    try:
        return os.path.expanduser(os.environ["BOOKSHELF_LIBRARY_PATH"])
    except KeyError:
        exit("Use the BOOKSHELF_LIBRARY_PATH environment variable to specify the location of your library.")


def load(path):
    paths = [os.path.join(path, f) for f in os.listdir(path)
             if (f.lower().endswith(".markdown") and
                 not f.lower().endswith("index.markdown"))]
    books = [Book(path) for path in paths]
    books = sorted(books, key=lambda x: x.title)
    return books


def add_book(directory, search_callback):
    new_book = interactive_search(search_callback=search_callback)
    if new_book is None:
        return
    cover_basename = f"{new_book.basename}.jpg"
    utilities.download_image(new_book.thumbnail, os.path.join(directory, cover_basename))
    metadata = dict(new_book.metadata)
    metadata["cover"] = cover_basename
    metadata["status"] = "to-read"
    contents = frontmatter.dumps(utilities.Document(content="", metadata=metadata))
    path = os.path.join(directory, f"{new_book.basename}.markdown")
    with open(path, "w") as fh:
        fh.write(contents)
        fh.write("\n")
    return path
