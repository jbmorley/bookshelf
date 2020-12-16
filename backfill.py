#!/usr/bin/env python3

import argparse
import collections
import json
import os
import re
import sys

import frontmatter

import openlibrary


BOOKS_DIRECTORY = "~/Projects/jbmorley.co.uk/content/about/books/"


Document = collections.namedtuple("Document", ["content", "metadata"])


def google_interactive(search=search):
    response = requests.get("https://www.googleapis.com/books/v1/volumes", params={q: search})
    print(response.json())
    exit()


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
        print(f"{title}, {author}")
        new_book = None
        if "isbn" not in book.metadata and "isbn_13" not in book.metadata:
            if options.skip_interactive:
                print("   skipping interactive lookup")
            else:
                print(f"  interactive...")
                while True:
                    try:
                        default_query = f"{title} {author}"
                        query = input(f"Search ['enter' to accept default ('{default_query}'), 's' to skip]:\n")
                        if query == "s":
                            break
                        if query == "":
                            query = default_query
                        new_book = openlibrary.interactive_search(query=query)
                        if new_book is not None:
                            break
                    except KeyError:
                        print("  no books found")
        else:
            isbn = book.metadata["isbn_13"] if "isbn_13" in book.metadata else book.metadata["isbn"]
            print(f"  ISBN {isbn}...")
            try:
                new_book = openlibrary.Book(isbn=isbn)
            except KeyError:
                print("  skipping...")

        if new_book is None:
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

        with open(f, "w") as fh:
            fh.write(frontmatter.dumps(Document(content="", metadata=metadata)))
            fh.write("\n")


if __name__ == "__main__":
    main()
