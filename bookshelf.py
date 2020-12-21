#!/usr/bin/env python3

import argparse
import os
import string

import frontmatter
import pick


DIRECTORY = os.path.expanduser("~/Projects/jbmorley.co.uk/content/about/books")


def main():
    parser = argparse.ArgumentParser(description="Book tracker.")
    options = parser.parse_args()

    files = [os.path.join(DIRECTORY, f) for f in os.listdir(DIRECTORY)
             if (f.lower().endswith(".markdown") and
                 not f.lower().endswith("index.markdown"))]
    documents = [(f, frontmatter.load(f)) for f in files]
    
    def book_title(details):
        path, document = details
        return document.metadata["title"]

    documents = sorted(documents, key=book_title)
    sections = [book_title(document).lower()[0] for document in documents]
    
    def key_handler(character):
        def inner(picker):
            destination = sections.index(character)
            selected, index = picker.get_selected()
            if destination > index:
                while index < destination:
                    picker.move_down()
                    selected, index = picker.get_selected()
            else:
                while index > destination:
                    picker.move_up()
                    selected, index = picker.get_selected()
        return inner

    picker = pick.Picker(options=sorted(documents, key=book_title),
                         title="Books",
                         options_map_func=book_title)

    for letter in string.ascii_lowercase:
        picker.register_custom_handler(ord(letter), key_handler(letter))
    option, index = picker.start()

    print(book_title(option))


if __name__ == "__main__":
    main()
