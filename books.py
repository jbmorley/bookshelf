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
    TO_READ = ("to-read", "To Read", lambda x: x.date is None and x.end_date is None)
    CURRENTLY_READING = ("currently-reading", "Reading", lambda x: x.date is not None and x.end_date is None)
    READ = ("read", "Read", lambda x: x.end_date is not None)
    ABANDONED = ("abandoned", "Abandoned", lambda x: x.date is not None)
    READ_UNKNOWN = ("read", "Read, Unknown", lambda x: x.date is None and x.end_date is None)
    ABANDONED_UNKNOWN = ("abandoned", "Abandoned, Unknown", lambda x: x.date is None and x.end_date is None)


def clear_start_date(book):
    book.date = None


def clear_end_date(book):
    book.end_date = None


def set_start_date(book):
    book.date = utilities.tznow()


def set_end_date(book):
    book.end_date = utilities.tznow()


STATUS_TRANSFORMS = {
    Status.TO_READ: [clear_start_date, clear_end_date],
    Status.CURRENTLY_READING: [set_start_date, clear_end_date],
    Status.READ: [set_end_date],
    Status.ABANDONED: [set_end_date],
    Status.READ_UNKNOWN: [clear_start_date, clear_end_date],
    Status.ABANDONED_UNKNOWN: [clear_start_date, clear_end_date],
}


def get_status(book):
    for status in list(Status):
        if status.value[0] == book.raw_status and status.value[2](book):
            return status
    exit(f"Unable to determine status for '{book.title}'.")


class Book(object):

    def __init__(self, path):
        self.path = path
        self.document = frontmatter.load(path)

    @property
    def title(self):
        return self.document.metadata["title"]

    @property
    def cover_path(self):
        if "cover" in self.document.metadata:
            return os.path.join(os.path.dirname(self.path), self.document.metadata["thumbnail"])
        return None

    @property
    def raw_status(self):
        return self.document.metadata["status"]

    @property
    def status(self):
        return get_status(self)

    @status.setter
    def status(self, status):
        self.document.metadata["status"] = status.value[0]
        transforms = STATUS_TRANSFORMS[status]
        for transform in transforms:
            transform(self)

    @property
    def summary(self):
        return f"{self.title} [{self.status.value[1]}]"

    @property
    def date(self):
        if "date" in self.document.metadata:
            return self.document.metadata["date"]
        return None

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
        if "end_date" in self.document.metadata:
            return self.document.metadata["end_date"]
        return None

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

            def manual(picker):
                return None, -7

            utilities.set_escdelay(25)
            picker = pick.Picker(books,
                                 f"Add Book ({page + 1})\n\nv - view\n\\ - view thumbnail\ntab - refine search\nleft/right - change page\ni - inspect\nm - manual entry\nesc - back",
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
            picker.register_custom_handler(ord('\\'),  thumbnail)
            picker.register_custom_handler(ord('m'),  manual)
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
                preview_cover(temporary_directory, selected)
                print(json.dumps(selected._data, indent=4))
                print(selected.metadata)
                input("Press any key to continue...")
            elif index == -5:
                page = max(page - 1, 0)
                default_index = 0
            elif index == -6:
                selected, default_index = selected
                preview_cover(temporary_directory, selected)
            elif index == -7:
                return add_book_manual()

        return selected


def add_book_manual():
    title = input("Title: ")
    author = input("Author: ")
    thumbnail = input("Cover: ")
    return ManualBook(title, author, thumbnail if thumbnail else None)


class ManualBook(object):

    def __init__(self, title, author, thumbnail):
        self.title = title
        self.authors = [author]
        self.thumbnail = None
        self.thumbnail = thumbnail

    @property
    def metadata(self):
        metadata = {
            "title": self.title,
            "authors": self.authors,
            "category": "books",
        }
        return metadata

    @property
    def basename(self):
        return utilities.basename(f"{self.title} {' '.join(self.authors)}")


def preview_cover(temporary_directory, book):
    thumbnail = book.thumbnail
    if thumbnail is not None:
        thumbnail_path = os.path.join(temporary_directory, "thumbnail.jpg")
        utilities.download_image(thumbnail, thumbnail_path)
        utilities.preview_image(thumbnail_path)
    else:
        input("Missing cover.")


def load(path):
    paths = [os.path.join(path, f) for f in os.listdir(path)
             if (f.lower().endswith(".md") and
                 not f.lower().endswith("index.md"))]
    books = [Book(path) for path in paths]
    books = sorted(books, key=lambda x: x.title)
    return books


def import_book(directory, new_book):
    metadata = dict(new_book.metadata)
    metadata["status"] = "to-read"

    thumbnail = new_book.thumbnail
    if thumbnail is not None:
        cover_basename = f"{new_book.basename}-cover.jpg"
        utilities.download_image(thumbnail, os.path.join(directory, cover_basename))
        metadata["thumbnail"] = cover_basename

    contents = frontmatter.dumps(utilities.Document(content="", metadata=metadata))
    path = os.path.join(directory, f"{new_book.basename}.md")
    with open(path, "w") as fh:
        fh.write(contents)
        fh.write("\n")
    return path


def add_book(directory, search_callback):
    new_book = interactive_search(search_callback=search_callback)
    if new_book is None:
        return
    return import_book(directory, new_book)
