import enum
import os

import dateutil
import frontmatter

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


def load(path):
    paths = [os.path.join(path, f) for f in os.listdir(path)
             if (f.lower().endswith(".markdown") and
                 not f.lower().endswith("index.markdown"))]
    books = [Book(path) for path in paths]
    books = sorted(books, key=lambda x: x.title)
    return books
