import re,requests
from scraper import Scraper
from datetime import timedelta

test = False

class ScraperImpl(Scraper):

    def __init__(self,session = None):
        self.search_url = 'https://mangaread.org/?s={0}&post_type=wp-manga'
        super().__init__(name = 'mangaread')

    def search(self,name):
        res = {}
        if name:
            q = re.sub('\s+','+',name)
            url = self.search_url.format(q)
            soup = None
            if test:
                soup = self.getSoup(url = url)

            else:
                # 5 minutes
                soup  = self.getSoup(url = url,cache_exp = 300)


            divs = soup.findAll('div',{'class':'tab-thumb c-image-hover'})
            for div in divs:
                a = div.find('a')
                if a:
                    title = self.util.strip(a.get('title'))
                    link = a.get('href')
                    if title and link:
                        res.update( {title  : link} )

            return res


    def getChapters(self,url):
        res = {}
        soup = ''
        if test:
           soup = self.getSoup(url = url)

        else:
            # 5 minutes
           soup = self.getSoup(url = url,cache_exp = 300)

        li_tags = soup.findAll('li',{'class':'wp-manga-chapter'})
        for li in li_tags:
            a = li.find('a')
            if a:
                name = self.util.strip(a.text)
                link = a.get('href')
                if name and link:
                    res.update({ name  : link })
        return res


    def getChapterPages(self, url):
        res ={}
        soup = None
        if test:
           soup = self.getSoup(url = url)

        else:
            soup = self.getSoup(url = url,cache_exp = timedelta(days = 1))
        
        div = soup.find('div',{'class':'reading-content'})
        if div:
           img_list = div.findAll('img')
           for i,img in enumerate(img_list):
                i += 1
                src = img.get('data-src')
                if src:
                    link = src.strip()
                    fn = f'{i}.jpg'
                    res.update({ fn  : link })

        return res


def test_scraper():
    global test
    test = True
    ms = ScraperImpl()
    print(f'#tesing {ms.name} scraper\n')
    print('#fetching search result')
    res = ms.search('one punch')
    m_link = ''
    for n,link in res.items():
        m_link = link
        print(n,f'link : {m_link}',sep = '\n\n',end = '\n\n')

    print('#fetching chapters list',end = '\n\n')
    res = ms.getChapters(m_link)
    ch_link = ''
    for ch,link in res.items():
        ch_link = link
        print(ch,f'link : {ch_link}',sep = '\n\n',end = '\n\n')

    print('\n\n#fetching chapter images',ch_link)
    for img_fn,link in ms.getChapterPages(ch_link).items():
        print(img_fn,link,sep = '\n\n',end = '\n\n')

if __name__ == '__main__':
   test_scraper()



      
    
    