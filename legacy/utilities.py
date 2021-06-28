import os

import lxml.html
import requests

def download_image(url, destination):
    r = requests.get(url, stream=True)
    if r.status_code == 200:
        with open(destination, 'wb') as fh:
            for chunk in r:
                fh.write(chunk)


def download_goodreads_cover(url, basename):
    response = requests.get(url)
    document = lxml.html.fromstring(response.text)
    cover_url = document.xpath('//div[@class="editionCover"]/img/@src')[0]
    _, ext = os.path.splitext(cover_url)
    download_image(url=cover_url, destination=f"{basename}{ext}")
