import sys,os,queue
from threading import Thread
from traceback import print_exc,format_exc
from collections import OrderedDict
from functools import partial
from importlib import import_module
from hurry import filesize

import scrapers
import urwid_ui
from configs import Bookmarks
from downloadutils import *


class ReqTask(Thread):
    def __init__(self,*args,**kwargs):
        super().__init__(*args,**kwargs)
        self.data_queue = queue.Queue(maxsize=1)
        self.event_dispatcher = None

    def setupEventDispatcher(self, dispatcher):
        self.event_dispatcher = dispatcher(self.handleEvent)

    def putData(self,**kwargs):
        self.data_queue.put(kwargs)

    def getData(self):
        if self.data_queue.empty():
            return {}
        else:
            return self.data_queue.get()

    def sendEvent(self,event,**data):
        self.putData(**data)
        if self.event_dispatcher:
           self.event_dispatcher.dispatch(event.encode())

    def handleEvent(self, event):
        target_id = event.decode()
        if hasattr(self, target_id):
            kwargs = self.getData()
            target = getattr(self, target_id)
            return target(**kwargs)



    def taskFinished(self):
        pass

    def taskStarted(self):
        pass

    def taskFailed(self):
        pass

class ChapterDownloaderTask(ReqTask):
    ACTION_RE_DOWNLOAD = 0
    ACTION_SKIP_CHAPTER = 1
    ACTION_CANCEL_DOWNLOAD = 2

    def __init__(self,executer, m_title, ch_list):
        super().__init__()
        self.setupEventDispatcher(executer.getEventDispatcher())
        self.executer = executer
        self.m_title = m_title
        self.ch_list = ch_list
        self.scraper = executer.currentScraper
        self.ui = executer.ui.downloadsWindow
        self.ui.actions_handler = self
        self.dl_path = self._getDownloadPath(m_title)
        self.dlr = None
        self.action_queue = queue.Queue(maxsize=1)
        self.task_canceled = False

    def _getDownloadPath(self,chapters_dir):
        # check for user defined path
        dl_path = os.getenv('MDL_PATH')
        if dl_path:
            dl_path = os.path.expanduser(dl_path)

        else:
            # default path
            dl_path = '/sdcard/manga/'

        return os.path.join(dl_path,chapters_dir)



    def handleDownloaderState(self,dlr_args=None, extra_args=None):
        state = dlr_args.pop(0)
        ch_list , idx, files_count = extra_args
        if state == DOWNLOADING:
            f_name,f_size,dl_bytes = dlr_args
            str_fsize = filesize.size(f_size)
            str_dlbytes = filesize.size(dl_bytes)
            info = f'{f_name}/{files_count} , {str_dlbytes}/{str_fsize}'
            self.ui.updateDownloadInfo(idx, info)
            self.ui.updateDownloadProg(idx, files_count)

        elif state == FILE_DOWNLOADED:
            f_name,f_size = dlr_args
            str_fsize = filesize.size(f_size)
            info = f'downloaded-pages:{files_count} - chapter-size:{str_fsize}'
            self.ui.updateDownloadInfo(idx,info)
            self.ui.updateDownloadProg(idx,files_count)
            self.ui.chapterDownloaded(f_name)

        elif state == DOWNLOAD_FAILED:
            self.handleDLError(*dlr_args, ch_list)

    def sendDownloaderState(self, *args, extra_args=()):
        e = 'handleDownloaderState'
        self.sendEvent(e, dlr_args=list(args) , extra_args=extra_args)


    def handleDLError(self, ch, err, ch_list):
        if not self.task_canceled:
            d_msg = f'failed to download {ch}\n\n{err}'
            d = self.ui.createDialog(msg=d_msg)
            d.addButton('retry', self.reDownload)
            d.addButton('skip', self.skipChapter)
            d.addButton('cancel',self.cancelDownload)
            d.show()


    def taskFinished(self):
        return False

    def taskStarted(self):
        self.ui.setup(self.ch_list.items()).show()

    def taskFailed(self, ch=None, msg=None, ch_list=None):
        self.handleDLError(ch, msg, ch_list)

    def cancelDownload(self, *args):
        self.task_canceled = True
        self.action_queue.put(self.ACTION_CANCEL_DOWNLOAD)

    def reDownload(self, *args):
        self.action_queue.put(self.ACTION_RE_DOWNLOAD)

    def skipChapter(self, *args):
        self.action_queue.put(self.ACTION_SKIP_CHAPTER)

    def getUserAction(self):
        return self.action_queue.get()


    def downloadChapter(self, idx, ch, url, ch_list):
        def _handleUserAction():
            user_action = self.getUserAction()
            if user_action == self.ACTION_RE_DOWNLOAD:
                return self.downloadChapter(idx, ch, url, self.ch_list)

            else:
                return user_action

        try:

            ch_pages = self.scraper.getChapterPages(url)
            prog_args = ch_list, idx, len(ch_pages)
            cb = partial(self.sendDownloaderState, extra_args=prog_args)
            self.dlr.reportState = cb
            self.scraper.disableSessionCache()
            if not self.dlr.downloadFiles(ch_pages.items(), ch):
                return _handleUserAction()

        except:
            err = format_exc()
            event = 'taskFailed'
            self.sendEvent(event, ch = ch , msg = err , ch_list = ch_list)
            return _handleUserAction()



    def run(self):
        self.sendEvent('taskStarted')
        session = self.scraper.session
        self.dlr = DownloaderV1(self.dl_path, session)
        items = self.ch_list.items()
        for idx,item in enumerate(items):

            ch,url = item
            if url is None:
                continue

            user_action = self.downloadChapter(idx, ch, url, self.ch_list)
            if user_action == self.ACTION_SKIP_CHAPTER:
                continue

            elif user_action == self.ACTION_CANCEL_DOWNLOAD:
                break

        self.sendEvent('taskFinished')


    def cancelDownloads(self):
        self.task_canceled = True
        if self.dlr:
            self.dlr.cancelDownload()

        self.scraper.session.close()


class ChaptersFetcherTask(ReqTask):
    ACTION_RE_FETCH = 0
    ACTION_CANCEL = 1

    def __init__(self, executer, m_title, m_url):
        super().__init__()
        self.setupEventDispatcher(executer.getEventDispatcher())
        self.executer = executer 
        self.scraper = executer.currentScraper
        self.ui = executer.ui
        self.dialog = None
        self.m_title = m_title
        self.m_url = m_url
        self.action_queue = queue.Queue(maxsize=1)
        self.task_canceled = False


    def cancel(self, *args):
        self.scraper.session.close()
        self.task_canceled = True
        self.action_queue.put(self.ACTION_CANCEL)

    def reFetch(self, *args):
        self.action_queue.put(self.ACTION_RE_FETCH)


    def getUserAction(self):
        return self.action_queue.get()


    def fetch(self):
        res = None
        try:
            self.sendEvent('taskStarted')
            res = self.scraper.getChapters(self.m_url)

        except:
            err = format_exc()
            self.sendEvent('taskFailed', msg=err)
            user_action = self.getUserAction()
            if user_action == self.ACTION_RE_FETCH:
                res = self.fetch()

        return res

    def run(self):
        res = self.fetch()
        self.sendEvent('taskFinished', ch_list=res)

    def taskFinished(self, ch_list=None):
        if self.task_canceled:
            return False

        else:
            self.dialog.hide()
            if  ch_list:
                src = self.scraper.name
                bookmarked = (self.m_title, src, self.m_url) in self.executer.bookmarks
                manga_data = self.m_title, src, self.m_url, bookmarked, ch_list.items()
                self.ui.showChaptersList(manga_data)

        return False

    def taskStarted(self):
        d_msg = f'fetching {self.m_title} chapters list ...'
        self.dialog = self.ui.createDialog(msg=d_msg)
        self.dialog.addButton('cancel', self.cancel)
        self.dialog.show()

    def taskFailed(self, msg=None):
        self.dialog.setTitle('failed to fetch chapters list')
        self.dialog.setMessage(msg)
        self.dialog.addButton('retry', self.reFetch)

class MangaSearchTask(ReqTask):
    ACTION_RE_SEARCH = 0
    ACTION_CANCEL = 1

    def __init__(self, executer, m_title):
        super().__init__()
        self.setupEventDispatcher(executer.getEventDispatcher())
        self.executer = executer
        self.scraper = executer.currentScraper
        self.ui = executer.ui
        self.m_title = m_title
        self.dialog = None
        self.action_queue = queue.Queue(maxsize=1)
        self.task_canceled = False

    def cancel(self, *args):
        self.scraper.session.close()
        self.task_canceled = True
        self.action_queue.put(self.ACTION_CANCEL)

    def reSearch(self, *args):
        self.action_queue.put(self.ACTION_RE_SEARCH)


    def getUserAction(self):
        return self.action_queue.get()

    def search(self):
        res = None
        try:

            self.sendEvent('taskStarted')
            res = self.scraper.search(self.m_title)

        except:
            err = format_exc()
            self.sendEvent('taskFailed' , msg=err)
            user_action = self.getUserAction()
            if user_action == self.ACTION_RE_SEARCH:
                res = self.search()

        return res

    def run(self):
        res = self.search()
        self.sendEvent('taskFinished' , search_res=res)

    def taskFinished(self, search_res=None):
        if self.task_canceled:
            return False

        else:
            self.dialog.hide()
            if search_res:
                self.executer.showSearchResult(search_res)

        return False

    def taskStarted(self):
        d_msg = f'searching for {self.m_title}...'
        self.dialog = self.ui.createDialog(msg=d_msg)
        self.dialog.addButton('cancel',self.cancel)
        self.dialog.show()

    def taskFailed(self,msg = None):
        self.dialog.setTitle('search failed')
        self.dialog.setMessage(msg)
        self.dialog.addButton('retry',self.reSearch)



class Main:
    def __init__(self,ui):
        self.ui = ui(actions_handler=self)
        self.searchResult = {}
        self.currentScraper = None
        self.sources_list = []
        self.scrapers_dict = self.loadScrapers()
        self.bookmarks = Bookmarks()

    def getEventDispatcher(self):
        return self.ui.createEventDispatcher

    def manageBookmarks(self, ui, manga_data):
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



    def downloadChapters(self, ui, m_title, ch_list):
        # reverse chapters list
        r_items = reversed(ch_list.items())
        r_ch_list = OrderedDict(r_items)
        r_keys = list(r_ch_list.keys())

        def downloadOrderedList(*args):
            ChapterDownloaderTask(self, m_title , ch_list).start()


        def downloadReversedList(*args):
            ChapterDownloaderTask(self, m_title , r_ch_list).start()

        if len(r_keys) < 2:
            downloadOrderedList()

        else:
            first_ch = r_keys[0]
            last_ch = r_keys[-1]
            order = f"from '{first_ch}' to '{last_ch}'"
            d_msg = f'download in reverse order \n\n {order} ?'
            d = ui.createDialog(msg=d_msg)
            d.addButton('no', downloadOrderedList)
            d.addButton('yes', downloadReversedList)
            d.addButton('cancel')
            d.show()




    def fetchChaptersList(self,arg):
        m_title = str(arg)
        m_url = None
        if type(arg) == tuple:
            m_title = arg[0]
            m_url = arg[1]

        else:
            m_url = self.searchResult.get(m_title)

        task = ChaptersFetcherTask(self, m_title, m_url)
        task.start()

    def doSearch(self, q):
        MangaSearchTask(self,q).start()

    def showSearchResult(self, res):
        self.searchResult = res
        self.ui.showSearchResult(res)

    def showUIWindow(self):
        self.ui.setup(self.currentScraper.name)
        self.ui.show()

def loadUIModule(name):
    try:
        m = import_module(name)
        return m.MainWindow
    except:
        print_exc()
        print(f'failed to load {name} module')

    print('loading default UI module ...')
    m = import_module('urwid_ui')
    return m.MainWindow



if __name__ == '__main__':
    args = sys.argv[1:]
    ui = None
    if args:
        name = f'{args[0]}_ui'
        ui = loadUIModule(name)
    else:
        ui = loadUIModule('urwid_ui')

    Main(ui).showUIWindow()

