import hashlib
import json
import logging
import multiprocessing as mp
import re
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import List, Set

# noinspection PyUnresolvedReferences
import cchardet  # https://beautiful-soup-4.readthedocs.io/en/latest/#improving-performance
# noinspection PyUnresolvedReferences
import lxml  # https://beautiful-soup-4.readthedocs.io/en/latest/#improving-performance
from bs4 import BeautifulSoup, NavigableString
from selenium import webdriver

options = webdriver.FirefoxOptions()
options.add_argument("--headless")
options.add_argument("--disable-gpu")
options.add_argument("--disable-dev-shm-usage")
logger = mp.log_to_stderr(logging.WARNING)


class MenuItem:
    def __init__(self, title, link, parent=None):
        self.title = title
        self.link = link
        if parent is not None and not isinstance(parent, type(self)):
            raise ValueError("Parent should be instance of MenuItem")
        self.parent = parent
        self.children = []

    def add_child(self, child):
        if child is not None and not isinstance(child, type(self)):
            raise ValueError("Child should be instance of MenuItem")
        self.children.append(child)

    def get_level(self):
        level = 0
        parent: MenuItem | None = self
        while True:
            if parent.parent is None:
                return level
            level += 1
            parent = parent.parent

    def item_hash(self):
        parentsStr = ''
        parent: MenuItem | None = self
        while parent is not None:
            parentsStr += parent.link  # make sure item hash is equal with parent hash
            parent = parent.parent
        return hashlib.sha256(parentsStr.encode('utf-8')).hexdigest()

    def __hash__(self):
        return hash(self.item_hash())

    def __ne__(self, other):
        return self.item_hash() != other.item_hash()

    def __eq__(self, other):
        if not isinstance(other, type(self)):
            return NotImplemented

        return self.item_hash() == other.item_hash()

    def __dict__(self):
        return {'title': self.title,
                'link': self.link,
                'children': self.children,
                'level': self.get_level(),
                'hash': self.item_hash(),
                'parent': self.parent.item_hash() if self.parent is not None else None}


class SetEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, set):
            return list(obj)
        if isinstance(obj, MenuItem):
            return obj.__dict__()
        return json.JSONEncoder.default(self, obj)


class Main:
    def __init__(self):
        self.visitedHistory = mp.Manager().list([])
        self.lockFileWrite = mp.Manager().Lock()
        self.items = set()
        self.url_pattern = re.compile("(^https?://.+)?(?P<addr>/hire/[\\w|-]+/)")
        self.mainCat: List[MenuItem] = []
        self.subCat: List[MenuItem] = []
        self.subSubCat: List[MenuItem] = []

    def run(self):
        links = self.load_home_page_links()
        items = set()
        iterateNumber = 0
        try:
            print("Total Links: %d" % len(links))
            while True:
                print("%d Iteration" % iterateNumber)
                previousLen = len(self.visitedHistory)
                with ThreadPoolExecutor(max_workers=mp.cpu_count()) as executor:
                    futures = [executor.submit(self.load_sub_pages, url, items) for url in links]
                    links.clear()
                    for future in as_completed(futures):
                        links.extend(future.result())

                if len(self.visitedHistory) == previousLen:
                    break
                with open('iteration_result%d.json' % iterateNumber, 'w') as f:
                    f.write(json.dumps(items, cls=SetEncoder, indent=2))
                print("Total Links: %d" % len(links))
                iterateNumber += 1
        finally:
            with open('upwork_categories.json', 'w') as f:
                f.write(json.dumps(items, cls=SetEncoder, indent=2))

    def load_sub_pages(self, url, items: Set) -> (Set[MenuItem], Set[str]):

        if url in self.visitedHistory:
            return set()
        self.visitedHistory.append(url)
        content = None
        try:
            content = Main.get_url_source('https://www.upwork.com' + url)
        except Exception:
            time.sleep(10)
            try:
                content = Main.get_url_source('https://www.upwork.com' + url)
            except Exception:
                time.sleep(10)
                content = Main.get_url_source('https://www.upwork.com' + url)
        finally:
            if content is None:
                return set()
            soap = BeautifulSoup(content, "lxml")
            breadcrumb = soap.find('ol', attrs={'class': 'breadcrumb'})
            parent = None
            if breadcrumb:
                for cat in breadcrumb.findAll('li', attrs={"data-qa": "breadcrumb"}):
                    a = cat.find('a')
                    if a:
                        it = MenuItem(a.text, a['href'], parent)
                        items.add(it)
                        parent = it

                sub_cat = breadcrumb.find('li', attrs={"data-qa": "breadcrumb-active"})
                text = "".join([t for t in sub_cat.contents if type(t) == NavigableString]).strip()
                items.add(MenuItem(text, url, parent))

            else:
                items.add(MenuItem(soap.find('title').text, url, None))

            links = set()
            for item in soap.findAll('div', attrs={"class": "related-skills__column-classes"}):
                a = item.find('a', href=self.url_pattern)
                if a:
                    match = self.url_pattern.match(a['href'])
                    addr = match.groupdict()['addr']
                    if addr not in links and addr not in self.visitedHistory:
                        links.add(addr)

            for a in soap.findAll('a', href=self.url_pattern, attrs={'class': 'related-link'}):
                if a:
                    match = self.url_pattern.match(a['href'])
                    addr = match.groupdict()['addr']
                    if addr not in links and addr not in self.visitedHistory:
                        links.add(addr)
            self.lockFileWrite.acquire()
            with open('visited_links.json', 'w') as f:
                f.write(json.dumps(list(self.visitedHistory), indent=2))
            self.lockFileWrite.release()
            print("Total processed urls: %d" % len(self.visitedHistory))
            return links

    def load_home_page_links(self):
        content = Main.get_url_source('https://www.upwork.com/')
        soup = BeautifulSoup(content, "lxml")
        links = set()
        nav = soup.find('nav', attrs={'class': 'nav-secondary-menu'})
        for a in nav.findAll('a', href=True):
            links.add(a['href'])
        return list(links)

    @staticmethod
    def get_url_source(url):
        driver = webdriver.Firefox(options=options)  # Optional argument, if not specified will search path.

        driver.get(url)

        source = driver.page_source

        driver.quit()

        return source


# Press the green button in the gutter to run the script.
if __name__ == '__main__':
    m = Main()
    m.run()
# See PyCharm help at https://www.jetbrains.com/help/pycharm/
