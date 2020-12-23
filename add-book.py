#!/usr/bin/env python3

import argparse
import os

import frontmatter

import books
import googlebooks
import utilities


BOOKS_DIRECTORY = "~/Projects/jbmorley.co.uk/content/about/books/"


def main():
    directory = books.library_path()
    parser = argparse.ArgumentParser(description="Add a new book")
    options = parser.parse_args()
    utilities.add_book(directory=directory, search_callback=googlebooks.search)


if __name__ == "__main__":
    main()
