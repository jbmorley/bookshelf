import argparse
import os

import lxml.html
import requests

import utilities


def main():
    parser = argparse.ArgumentParser(description="Download the cover for a Goodreads book")
    parser.add_argument("url", help="Goodreads URL")
    options = parser.parse_args()
    utilities.download_goodreads_cover(url=options.url, basename="cover")


if __name__ == "__main__":
    main()