import re,json
from scraper import Scraper
from datetime import timedelta

test = False

class ScraperImpl(Scraper):

    def __init__(self,session = None):
        self.base_url = 'https://funmanga.com'
        self.search_url = self.base_url + '/manga-list/{0}'
        super().__init__(name = 'funmanga')

    def search(self,name):
        res = {}
        c = ''
        if name:
            fc = name.lower()[0]
            if fc.isalpha():
                c = fc

            url = self.search_url.format(c)
            if test:
                soup = self.getSoup(url = url)

            else:
                # 5 minutes
                soup  = self.getSoup(url = url,cache_exp = 300)

            ul = soup.find('ul',{'class':'manga-list circle-list'})

            if ul:
                a_tags = ul.findAll('a',{'class':'manga-info-qtip'})

                for a in a_tags:
                    title = self.util.strip(a.text)
                    link = a.get('href')

                    if title and link:
                        if name.lower() in title.lower():
                            res.update({ title : link})

        return res


    def getChapters(self,url):
        res = {}
        soup = None
        if test:
           soup = self.getSoup(url = url)

        else:
           # 5 minutes
           soup = self.getSoup(url = url,cache_exp = 300)


        div = soup.find('div',{'id':'chapter_list'})
        if div:
            a_tags = div.findAll('a')
            for a in a_tags:
                val = a.find('span',{'class':'val'}).text
                ch_title = self.util.strip(val)
                ch_link = a.get('href')

                if ch_title and ch_link:
                    res.update({ch_title : ch_link })

        return res


    def getChapterPages(self, url):
        res = {}
        doc = ''
        if test:
            doc = self.fetchDoc(url = url)


        else:

            page_num = '/1'
            if url.endswith(page_num):
                # no we want the html-page that contains all images
                url = url.rstrip(page_num)

            doc = self.fetchDoc(url = url,cache_exp = timedelta(days = 1))

        match = re.search(rb'(var images\s*=\s*)(.+)(?=;)', doc)

        if match and ( len(match.groups()) >= 2) :
            json_payload = match.group(2)
            imgs = json.loads(json_payload)

            for i in imgs:
                n = int(i['id']) + 1
                name = '{0}.jpg'.format(n)
                link = i['url']

                if link.startswith('//'):
                    link = 'https:{0}'.format(link)

                res.update({name : link})


        return res


def test_scraper():
    global test
    test = True
    ms = ScraperImpl()
    print(f'#tesing {ms.name} scraper\n')
    print('#fetching search result')
    res = ms.search('one')
    m_link = ''
    for i,n in enumerate(res['names']):
        m_link = res['links'][i]
        print(n,f'link : {m_link}',sep = '\n\n',end = '\n\n')

    print('#fetching chapters list',end = '\n\n')
    res = ms.getChapters(m_link)
    ch_link = ''
    for i,ch in enumerate(res['names']):
        ch_link = res['links'][i]
        print(ch,f'link : {ch_link}',sep = '\n\n',end = '\n\n')

    print('\n\n#fetching chapter images')
    for img_fn,link in ms.getChapterPages(ch_link):
        print(img_fn,link,sep = '\n\n',end = '\n\n')

if __name__ == '__main__':
   test_scraper()



      
    
    