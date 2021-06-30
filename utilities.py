import collections
import curses
import datetime
import json
import os
import re
import string
import webbrowser

import dateutil.tz
import pick
import requests


Document = collections.namedtuple("Document", ["content", "metadata"])


class Chdir(object):

    def __init__(self, path):
        self.path = os.path.abspath(path)

    def __enter__(self):
        self.pwd = os.getcwd()
        os.chdir(self.path)
        return self.path

    def __exit__(self, exc_type, exc_value, traceback):
        os.chdir(self.pwd)


class BookNotFound(Exception):
    pass


class SearchString(object):

    def __init__(self):
        self.timestamp = datetime.datetime.now()
        self.value = ""

    def add(self, character):
        now = datetime.datetime.now()
        if now - self.timestamp > datetime.timedelta(seconds=1):
            self.value = ""
        self.value += character
        self.timestamp = now


class SearchablePicker(pick.Picker):

    def __init__(self, *args, **kwargs):
        super(SearchablePicker, self).__init__(*args, **kwargs)
        pick.KEYS_UP = [curses.KEY_UP]
        pick.KEYS_DOWN = [curses.KEY_DOWN]
        search = SearchString()

        def key_handler(character):
            def inner(picker):
                search.add(character)
                destination = -1
                for index, details in enumerate(picker.options):
                    title = picker.options_map_func(details)
                    if title.lower().startswith(search.value):
                        destination = index
                        break
                selected, index = picker.get_selected()
                if destination == -1 or destination == index:
                    return
                elif destination > index:
                    while index < destination:
                        picker.move_down()
                        selected, index = picker.get_selected()
                else:
                    while index > destination:
                        picker.move_up()
                        selected, index = picker.get_selected()
            return inner

        for letter in string.ascii_lowercase + " ":
            self.register_custom_handler(ord(letter), key_handler(letter))


def set_escdelay(delay):
    os.environ.setdefault('ESCDELAY', str(delay))


def tznow():
    return datetime.datetime.now().replace(tzinfo=dateutil.tz.tzlocal())


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


def which(program):
    import os
    def is_exe(fpath):
        return os.path.isfile(fpath) and os.access(fpath, os.X_OK)

    fpath, fname = os.path.split(program)
    if fpath:
        if is_exe(program):
            return program
    else:
        for path in os.environ["PATH"].split(os.pathsep):
            exe_file = os.path.join(path, program)
            if is_exe(exe_file):
                return exe_file

    return None
