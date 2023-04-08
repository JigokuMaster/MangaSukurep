import os,sys
from traceback import print_exc


def load() -> dict:
    pkg_path = __path__[0]
    sys.path.append(pkg_path)
    scrapers = {}

    for fn in os.listdir(pkg_path):
        if fn.startswith('__init__.py') or fn.startswith('scraper.py'):
            continue

        n,ext = os.path.splitext(fn)
        if ext == '.py':

            try:
                m = __import__(n)
                if hasattr(m,'ScraperImpl'):
                    scrapers.update({ n : m.ScraperImpl() })
            except:
                print_exc()

    return scrapers



