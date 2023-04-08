import sys,os
from threading import Thread
from traceback import print_exc,format_exc
from collections import OrderedDict
from functools import partial
from hurry import filesize

# import internal modules

import scrapers
import urwid_ui
from configs import Bookmarks
from downloadutils import *

class ChapterDownloader:
    def __init__(self,ui, m_title, scraper):
        self.ui = ui
        self.ui.actions_handler = self
        self.dl_path = self._getDownloadPath(m_title)
        self.dlr = None
        self.thread = None
        self.scraper = scraper


    def _getDownloadPath(self,chapters_dir):
        # check for user defined path
        dl_path = os.getenv('MDL_PATH')
        if dl_path:
            dl_path = os.path.expanduser(dl_path)

        else:
            # default path
            dl_path = '/sdcard/manga/'

        return os.path.join(dl_path,chapters_dir)

    def updateDLInfo(self, idx, files_count, dlr_args):
        info = ''
        if len(dlr_args) == 3:
            f_name,f_size,dl_bytes = dlr_args
            str_fsize = filesize.size(f_size)
            str_dlbytes = filesize.size(dl_bytes)
            info = f'{f_name}/{files_count} , {str_dlbytes}/{str_fsize}'

        if len(dlr_args) == 2:
            f_name,f_size = dlr_args
            str_fsize = filesize.size(f_size)
            info = f'downloaded-pages:{files_count} - chapter-size:{str_fsize}'
            self.ui.unCheckChapter(f_name)

        self.ui.updateDownloadInfo(idx, info)
        self.ui.updateDownloadProg(idx, files_count)

    def handleDownloaderState(self, *dlr_args, extra_args = ()):
        args = list(dlr_args)
        state = args.pop(0)
        ch_list , idx, files_count = extra_args
        if state == DOWNLOADING:
            f_name,f_size,dl_bytes = args
            str_fsize = filesize.size(f_size)
            str_dlbytes = filesize.size(dl_bytes)
            info = f'{f_name}/{files_count} , {str_dlbytes}/{str_fsize}'
            self.ui.updateDownloadInfo(idx, info)
            self.ui.updateDownloadProg(idx, files_count)

        elif state == FILE_DOWNLOADED:
            f_name,f_size = args
            str_fsize = filesize.size(f_size)
            info = f'downloaded-pages:{files_count} - chapter-size:{str_fsize}'
            self.ui.updateDownloadInfo(idx,info)
            self.ui.updateDownloadProg(idx,files_count)
            self.ui.chapterDownloaded(f_name)

        elif state == DOWNLOAD_FAILED:
            self.handleDLError(args, ch_list)

    def handleDLError(self, dlr_args, ch_list):
        ch,err = dlr_args
        d_msg = f'failed to download {ch}\n\n{err}'
        d = self.ui.createDialog(msg=d_msg)
        def retry(*args):
            d.hide()
            self.downloadList(ch_list)


        def skip(*args):
            d.hide()
            ch_list.update({ch:None})
            self.downloadList(ch_list)


        d.addButton('retry', retry)
        d.addButton('skip', skip)
        d.addButton('cancel')
        d.show()

    def download(self, ch_list):
        # reverse chapters list
        r_items = reversed(ch_list.items())
        r_ch_list = OrderedDict(r_items)
        r_keys = list(r_ch_list.keys())
        d = None

        def downloadOrderedList(*args):
            if d:
                d.hide()

            self.ui.setup(ch_list.items()).show()
            self.downloadList(ch_list)


        def downloadReversedList(*args):
            if d:
                d.hide()

            self.ui.setup(r_ch_list.items()).show()
            self.downloadList(r_ch_list)

        if len(r_keys) < 2:
            downloadOrderedList()

        else:
            first_ch = r_keys[0]
            last_ch = r_keys[-1]
            order = f"from '{first_ch}' to '{last_ch}'"
            d_msg = f'download in reverse order \n\n {order} ?'
            d = self.ui.parent.createDialog(msg=d_msg)
            d.addButton('no', downloadOrderedList)
            d.addButton('yes', downloadReversedList)
            d.addButton('cancel')
            d.show()

    def downloadList(self,ch_list):
        session = self.scraper.session
        self.dlr = DownloaderV1(self.dl_path, session)

        def run():
            _ch_list = ch_list.copy()
            items = ch_list.items()
            for idx,item in enumerate(items):
                ch,url = item
                if url is None:
                    continue
                try:
                    ch_pages = self.scraper.getChapterPages(url)
                    prog_args = (_ch_list, idx, len(ch_pages))
                    cb = partial(self.handleDownloaderState, extra_args=prog_args)
                    self.dlr.reportState = cb
                    self.session_holder.disableSessionCache()
                    if self.dlr.downloadFiles(ch_pages.items(), ch):
                         _ch_list.pop(ch)

                except:
                    err = format_exc()
                    self.handleDLError((ch,err), _ch_list)
                    break


        if self.thread and self.thread.isAlive():
            return

        else:
            self.thread = Thread(target=run)
            self.thread.start()

    def cancelDownloads(self):
        if self.dlr:
            self.dlr.cancelDownload()

        self.scraper.session.close()

class Main:
    def __init__(self,ui):
        self.ui = ui(actions_handler=self)
        self.searchResult = {}
        self.currentScraper = None
        self.sources_list = []
        self.scrapers_dict = self.loadScrapers()
        self.bookmarks = Bookmarks()


    def manageBookmarks(self,ui,manga_data):
        title,src,url,bookmarked,ch_list = manga_data
        def rm(*args):
            self.bookmarks.remove(title)
            ui.bookmarkRemoved()

        if (title,src,url) in self.bookmarks:
            d = ui.createDialog(msg = 'remove from bookmarks ?')
            d.addButton('yes',rm)
            d.addButton('cancel')
            d.show()

        else:
            self.bookmarks.add(title,src,url)
            ui.bookmarkAdded()


    def openBookmark(self,*args, i=None):
        if i:
            manga_title = i[0]
            src , url = i[1]
            self.changeSource(src)
            self.fetchChaptersList((manga_title,url))

    def loadBookmarks(self,*args):
        bm_dict = self.bookmarks.load()
        res = []
        for item in bm_dict.items():
            manga_title = item[0]
            src , url = item[1]
            cb = partial(self.openBookmark, i=item)
            res.append((f'{manga_title} - ({src})',cb))

        return res
 


    def changeSource(self , k):
        self.currentScraper = self.scrapers_dict[k]
        self.ui.sourceChanged(k)
        return True
   
    def loadScrapers(self):
        scrapers_dict = scrapers.load()
        scraper = None
        for scraper in scrapers_dict.keys():
            self.sources_list.append((scraper, self.changeSource))

        self.currentScraper = scrapers_dict[scraper]
        return scrapers_dict

    def getSourceList(self):
        return self.sources_list


    def downloadChapters(self,m_title, ch_list):
        ui = self.ui.downloadsWindow
        dlr = ChapterDownloader(ui, m_title , self.currentScraper)
        dlr.download(ch_list)

    def fetchChaptersList(self,arg):
        req_canceled = False
        m_title = str(arg)
        if type(arg) == tuple:
            m_title = arg[0]

        d_msg = f'fetching {m_title} chapters list ...'
        d = self.ui.createDialog(msg=d_msg)

        def retry(*args):
            self.fetchChaptersList(arg)

        def cancel(*args):
            nonlocal req_canceled
            req_canceled = True
            self.currentScraper.session.close()

        def get(url):
            try:
                res = self.currentScraper.getChapters(url)
                d.hide()
                if not req_canceled:
                    src = self.currentScraper.name
                    bookmarked = (m_title, src, url) in self.bookmarks
                    manga_data = m_title, src, url, bookmarked, res.items()
                    self.ui.showChaptersList(manga_data)

            except:
                msg = format_exc()
                d.setTitle('failed to fetch chapters list')
                d.setMessage(msg)
                d.addButton('retry',retry)


        ch_url = None
        if type(arg) == tuple:
            ch_url = arg[1]
        else:
            ch_url = self.searchResult.get(m_title)

        if ch_url:
            d.addButton('cancel',cancel)
            d.show()
            t = Thread(target=get, args=(ch_url,) )
            t.start()



    def doSearch(self,q):
        req_canceled = False
        d = self.ui.createDialog(msg=f'searching for {q}...')
        def retry(*args):
            self.doSearch(q)

        def cancel(*args):
            nonlocal req_canceled
            req_canceled = True
            self.currentScraper.session.close()


        def get(q):

            try:

                self.searchResult = self.currentScraper.search(q)
                d.hide()
                if req_canceled:
                    return

                if self.searchResult:
                    self.ui.showSearchResult(self.searchResult)



            except:
                msg = format_exc()
                d.setTitle('Search Failed')
                d.setMessage(msg)
                d.addButton('retry',retry)

        d.addButton('cancel',cancel)
        if q:
            d.show()
            t = Thread(target=get, args=(q,) )
            t.start()


    def showUIWindow(self):
        self.ui.setup(self.currentScraper.name)
        self.ui.show()



if __name__ == '__main__':
    # args = sys.argv[1:]
    Main(urwid_ui.MainWindow).showUIWindow()


