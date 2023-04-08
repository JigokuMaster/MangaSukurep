import os
from bs4 import BeautifulSoup
from requests_cache import CachedSession

def _setup_data_dir():
	cwd = os.path.dirname(__file__) or './'
	main_dir = os.path.abspath(cwd)
	_data_dir = os.path.join(main_dir,'../data')
	data_dir = os.path.abspath(_data_dir)

	if not os.path.exists(data_dir):
		try:
			os.mkdir(data_dir)
		except:
			data_dir = None

	return data_dir


DATA_DIR = _setup_data_dir()
class Util:
    def strip(raw_text):
        return raw_text.rstrip().lstrip()




class Scraper:
    def __init__(self,name, session=None):
        """
        this class acts just like a helper 
        and it doesn't parser or scrap any data

        """
        self.name = name
        self.cache_db = os.path.join(DATA_DIR,f'{self.name}_cache')
        self.session = session
        if self.session is None:
            self.session = CachedSession(self.cache_db, backend='sqlite')
            self.session.headers.update({'User-Agent':'Mozila/5.0'})

        self.util = Util

    def fetchDoc(self,url = None,req_timeout = 60,cache_exp = -1):
        self.session.expire_after = cache_exp
        doc = self.session.get(url,timeout = req_timeout).content
        return doc

    def getSoup(self,
            url = None,req_timeout = 60,
            cache_exp = -1,bs_parser = 'html.parser'
         ):

        doc = self.fetchDoc(url,req_timeout,cache_exp)
        return BeautifulSoup(doc,features = bs_parser)

    def getSession(self,no_cache = False):
        if no_cache:
           self.disableSessionCache()

        return self.session

    def disableSessionCache(self):
        self.session.expire_after = 0


    def search(self,name):
        pass

    def getChapters(self,url):
        pass

    def getChapterPages(self, url):
        pass
    

 