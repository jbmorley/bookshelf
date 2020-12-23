#!/usr/bin/env python3

import argparse
import os

import frontmatter

import googlebooks
import utilities


BOOKS_DIRECTORY = "~/Projects/jbmorley.co.uk/content/about/books/"


def main():
    try:
        directory = os.path.expanduser(os.environ["BOOKSHELF_LIBRARY_PATH"])
    except KeyError:
        exit("Use the BOOKSHELF_LIBRARY_PATH environment variable to specify the location of your library.")
    parser = argparse.ArgumentParser(description="Add a new book")
    options = parser.parse_args()
    utilities.add_book(directory=directory, search_callback=googlebooks.search)


if __name__ == "__main__":
    main()
