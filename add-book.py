#!/usr/bin/env python3

import argparse
import os

import frontmatter

import googlebooks
import utilities


BOOKS_DIRECTORY = "~/Projects/jbmorley.co.uk/content/about/books/"


def add_book(directory):
    new_book = utilities.interactive_search(search_callback=googlebooks.search)
    cover_basename = f"{new_book.basename}.jpg"
    utilities.download_image(new_book.thumbnail, os.path.join(directory, cover_basename))
    metadata = dict(new_book.metadata)
    metadata["cover"] = cover_basename
    metadata["status"] = "to-read"
    contents = frontmatter.dumps(utilities.Document(content="", metadata=metadata))
    with open(os.path.join(directory, f"{new_book.basename}.markdown"), "w") as fh:
        fh.write(contents)
        fh.write("\n")


def main():
    parser = argparse.ArgumentParser(description="Add a new book")
    options = parser.parse_args()
    add_book(directory=os.path.expanduser(BOOKS_DIRECTORY))


if __name__ == "__main__":
    main()
