import json,os

class Bookmarks:
    def __init__(self,path = None):
        self.path = path or '.'
        self.data = self.load()

    def load(self):
        fp = os.path.join(self.path,'bookmarks.json')
        if not os.path.exists(fp):
            return {}

        f = open(fp,'r',encoding = 'utf-8')
        data = {}
        try:
            data = json.load(f)
        except:
            pass

        f.close()
        return data


    def save(self):
        fp = os.path.join(self.path,'bookmarks.json')
        f = open(fp,'w',encoding = 'utf-8')
        json.dump(self.data,f)
        f.close()

    def add(self,title,src,url):
        self.data.update({title:[src,url] })
        self.save()

    def clear(self):
        self.data = {}
        self.save()

    def getUrl(self,bookmark_title):
        return self.data.get(bookmark_title)      

    def __contains__(self,item):
        title,src,url = item
        return [src,url] == self.data.get(title,[])

    def remove(self,k):
        if k in self.data:
            self.data.pop(k)
            self.save()


if __name__ == '__main__':
    from functools import partial
    def openBookmark(arg):
        print(arg)

    bm = Bookmarks('.').load()
    res = []
    for k,v in bm.items():
        src,url = v
        cb = partial(openBookmark,(k,url))
        res.append((f'{k} - ({src})',cb))
        print(k,url,cb)

    res[0][1]()
    res[1][1]()


      
      
      