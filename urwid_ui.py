import urwid
from urwid.util import is_mouse_press
from urwid.command_map import ACTIVATE
from urwid.signals import connect_signal
import threading, os, io, fcntl
from collections import OrderedDict




screen,mainLoop = None,None


# Custom Widgets

class CCheckBox(urwid.CheckBox):
    def __init__(self, label,**kw):
        self.keypress_handler = None
        super().__init__(label,**kw)

    def keypress(self, size, key):
        _key = super().keypress(size, key)
        if _key and callable(self.keypress_handler):
            return self.keypress_handler(_key)


class CListBoxItem(urwid.Text):
    _selectable = True
    signals = ['click']

    def __init__(self, label, on_click = None,
        user_args = None,keypress_handler = None):
        self.handle_keypress = keypress_handler
        if on_click:
            connect_signal(self, 'click', on_click, user_args = user_args)

        super().__init__(label)

    def keypress(self, size, key):
        if self._command_map[key] != ACTIVATE:

            if callable(self.handle_keypress):
                return self.handle_keypress(key)
            return key

        self._emit('click')



    def mouse_event(self, size, event, button, x, y, focus):
        if button != 1 or not is_mouse_press(event):
            return False

        self._emit('click')
        return True

    def __str__(self):
        return self.text


class CListBox(urwid.ListBox):
    def __init__(self,items=[], item_click_cb=None):
        self.item_click = item_click_cb
        self.walker = urwid.SimpleListWalker([])
        for item in items:
            self.addItem(item)

        super().__init__(self.walker)


    def clear(self):
        self.walker.clear()

    def addWidget(self,w):
        w = urwid.AttrWrap(w,'listbox_item','focused_listbox_item')
        self.walker.append(w)
        return w

    def addItem(self,text, align='left'):
        item = CListBoxItem(text,self.item_click)
        item.set_align_mode(align)
        return self.addWidget(item)

    def getItem(self,pos):
        return self.walker[pos]

    def setItemClickCB(self,cb):
        self.item_click = cb

    def selectable(self):
        return True


    def mouse_event(self,size,event,btn,x,y,focus):
        # Scroll wheel up
        if btn == 5:
            self.keypress(size,'down')

        # Scroll wheel down
        elif btn == 4:
            self.keypress(size,'up')

        return super().mouse_event(size, event,btn,x,y,focus)




class CButton(urwid.SelectableIcon):

    signals = ['click']

    def __init__(self, label, on_press = None, user_args = None,align = 'center'):

        if on_press:
            connect_signal(self, 'click', on_press, user_args = user_args)

        super().__init__(label)

        self.set_align_mode(align)

    def keypress(self, size, key):

        if self._command_map[key] != ACTIVATE:
            return key

        self._emit('click')

    def mouse_event(self, size, event, button, x, y, focus):
        if button != 1 or not is_mouse_press(event):
            return False

        self._emit('click')
        return True

    def setOnClick(self,cb,user_args = None):
        if cb:
            connect_signal(self, 'click', cb,user_args = user_args)




class Window:
    def __init__(self,parent = None):
        self.parent = parent
        self._close_called = False

    def show(self,*args):
        self._close_called = False
        self.showWidget(self)

    def close(self,*args):
        if self.parent:
            self._close_called = True
            self.showWidget(self.parent)


    def showWidget(self,w = None):
        if hasattr(w,'widget'):
            w = w.widget
        if w:
            mainLoop.widget = w

        self._updateScreen()

    def _updateScreen(self):
        if not self._close_called:
            mainLoop.draw_screen()


    def createDialog(self,**kwargs):
        return Dialog(self,**kwargs)

    def mouse_event(self,*args):
        if hasattr(self,'widget'):
            w = w.widget
            return w.mouse_event(*args)

    def unhandled_input(self,key):
        pass




class LineWalker(urwid.ListWalker):

    """
    copied from urwid/examples/real_edit.py and 
    modified to work with StringIO instead of file object

    """

    def __init__(self, text,align='center'):
        self.text = text
        self.text_align = align
        self.io = io.StringIO(text)
        self.lines = []
        self.focus = 0
        self.lines_counter = 0
        self.lines_count = 0


    def count(self):
        if self.lines_count > 0:
            return self.lines_count

        else:
            _io = io.StringIO(self.text)
            return len(_io.readlines())

    def clear(self):
        self.io = None
        self.lines = []
        self.focus = 0
        self.lines_counter = 0
        self.lines_count = 0

    def setText(self,text):
        self.clear()
        self.io = io.StringIO(text)
        self._modified()

    def handleKeypress(self,size,key):
        return key


    def get_focus(self):
        return self._get_at_pos(self.focus)

    def set_focus(self, focus):
        self.focus = focus
        self._modified()

    def get_next(self, start_from):
        return self._get_at_pos(start_from + 1)

    def get_prev(self, start_from):
        return self._get_at_pos(start_from - 1)

    def read_next_line(self):
        """Read another line from the file."""

        next_line = self.io.readline()
        self.lines_counter += 1

        if not next_line or next_line[-1:] != '\n':
            # no newline on last line of file
            self.io = None
            self.lines_count = self.lines_counter

        else:
            # trim newline characters
            next_line = next_line[:-1]

        expanded = next_line.expandtabs()

        edit = urwid.Edit("", expanded,align=self.text_align, allow_tab=True)
        # replacing Edit.keypress with a dummy method to disable editing
        edit.keypress = self.handleKeypress
 
        edit.set_edit_pos(0)
        edit.original_text = next_line
        self.lines.append(edit)

        return next_line


    def _get_at_pos(self, pos):
        """Return a widget for the line number passed."""

        if pos < 0:
            # line 0 is the start of the file, no more above
            return None, None

        if len(self.lines) > pos:
            # we have that line so return it
            return self.lines[pos], pos

        if self.io is None:
            # file is closed, so there are no more lines
            return None, None

        assert pos == len(self.lines), "out of order request?"

        self.read_next_line()

        return self.lines[-1], pos

    def split_focus(self):
        """Divide the focus edit widget at the cursor location."""

        focus = self.lines[self.focus]
        pos = focus.edit_pos
        edit = urwid.Edit("",focus.edit_text[pos:], allow_tab=True)
        edit.original_text = ""
        focus.set_edit_text(focus.edit_text[:pos])
        edit.set_edit_pos(0)
        self.lines.insert(self.focus+1, edit)

    def combine_focus_with_prev(self):
        """Combine the focus edit widget with the one above."""

        above, ignore = self.get_prev(self.focus)
        if above is None:
            # already at the top
            return

        focus = self.lines[self.focus]
        above.set_edit_pos(len(above.edit_text))
        above.set_edit_text(above.edit_text + focus.edit_text)
        del self.lines[self.focus]
        self.focus -= 1

    def combine_focus_with_next(self):
        """Combine the focus edit widget with the one below."""

        below, ignore = self.get_next(self.focus)
        if below is None:
            # already at bottom
            return

        focus = self.lines[self.focus]
        focus.set_edit_text(focus.edit_text + below.edit_text)
        del self.lines[self.focus+1]



class Dialog(urwid.Overlay,Window):
    def __init__(self,parent,title = None,msg = None,buttons = []):
        top_widget = parent
        self.msg = None
        self.title = None
        self.content = []
        self.keybinding_map = {}

        if hasattr(parent,'widget'):
            top_widget = parent.widget

        if title:
            self.title = self._createTitleWidget(title)
            self.content.append(self.title)

        if msg:
            self.msg = self._createMsgWidget(msg)
            self.content.append(self.msg)


        self._setupBody()
        self._setupFooter(buttons)
        buttom_widget = self._setupButtomWidget()
        urwid.Overlay.__init__(self,
            buttom_widget,top_widget, align='center',width = ('relative', 80),
            valign='middle', height=('relative', 80))
        Window.__init__(self,parent)

    def _setupButtomWidget(self):
        self.frame = urwid.Frame(self.body,self.title,self.footer)
        return urwid.LineBox(self.frame)

    def _setupBody(self):
        self._container = urwid.Pile(self.content)
        self.body = urwid.Filler(self._container,'middle')

    def _setupFooter(self,buttons):
        self.footer = urwid.Columns([],5)
        div = urwid.Text(' '*15)
        params = ('pack',None,False)
        self.footer.contents.append((div,params))
        for title,cb in buttons:
            self.addButton(title,cb)

    def _createTitleWidget(self,title,align='center'):
        return urwid.Text(title,align,'space')

    def _createMsgWidget(self,msg, align='center'):
        walker = LineWalker(msg,align)
        w = urwid.BoxAdapter(urwid.ListBox(walker),8)
        return w

    def setTitle(self,title,align='center'):
        if self.title is None:
            self.title = self._createTitleWidget(title,align)
            self.frame.set_header(self.title)

        else:
            self.title.set_text(title)


        self.refreshIfNeeded()

    def setMessage(self,msg):
        if self.msg is None:
            self.msg = self._createMsgWidget(msg)
            self.content.append(self.msg)
            return

        else:
            self.msg.body.setText(msg)

        self.refreshIfNeeded()

    def addButton(self,title = '',cb = None):
        def _cb(*args):
            if cb:
                cb(*args)

            self.hide(*args)

        w = CButton(title,_cb)
        btn = urwid.AttrWrap(w,'dialog_btn')
        params = ('pack',None,False)
        self.footer.contents.append((btn,params))
        k = title[0].lower()
        self.keybinding_map.update({k : _cb})
        self.refreshIfNeeded()

    def setButton(self,title,cb):
        btn = CButton(title,cb)
        self.frame.set_footer(btn)
        self.refreshIfNeeded()

    def addWidget(self,w,params):
        self._container.contents.append((w,params))
        self.refreshIfNeeded()

    def hide(self,*args):
        self.close()

    def refreshIfNeeded(self):
        if threading.current_thread() != threading.main_thread():
            self._updateScreen()

    def keypress(self, size, key):
        if len(key) > 1:
            """
            allows scrolling using arrow keys

            when the msg widget contains a large text

            """
            return super().keypress(size, key)

        if key in ('c','C'):
            self.hide()

        k = key.lower()

        if k in self.keybinding_map:
            self.keybinding_map.get(k)()

        else:
            return key


class PopupMenu(urwid.Overlay,Window):
    def __init__(self,parent):
        self.actions = {}
        self.listBox = CListBox(item_click_cb = self.onClick)
        top_w = parent
        if hasattr(parent,'widget'):
            top_w = parent.widget

        bottom_w = urwid.LineBox(self.listBox)
        urwid.Overlay.__init__(self,bottom_w,top_w,
            align='left',width = ('relative', 80),
            valign='top', height = ('relative', 80),top=1 )

        Window.__init__(self,parent)
        self._got_mouse_event = False


    def mouse_event(self,size, event, button, col, row, focus):
        left, right, top, bottom = self.calculate_padding_filler(size,
            focus)
        maxcol, maxrow = size
        if self._got_mouse_event and (
            (col < left) or (col >= maxcol - right) or
            (row < top) or (row >= maxrow - bottom) ):
            self.hide()
            return False


        self._got_mouse_event = True
        return super().mouse_event(size, event, button, col, row, focus)

    def hide(self,*args):
        self._got_mouse_event = False
        self.close()


    def onClick(self,item):
        cb = self.actions.get(item.text)
        if cb:
            if cb(item.text):
                self.close()
            
    def addAction(self,label,cb = None):
        self.actions.update({label:cb})
        self.listBox.addItem(label)





class ActionBar(urwid.AttrWrap):
    def __init__(self,items = [],colors = None):
        self.def_colors = ('light gray','black')
        if colors is None:
            colors = self.def_colors
        spec = urwid.AttrSpec(*colors)
        self.items = items
        self.widget = urwid.Columns(self.items,5)
        super().__init__(self.widget,spec)

    def addAction(self,label,cb,colors = None):
        if colors is None:
            colors = self.def_colors
        spec = urwid.AttrSpec(*colors)
        btn = urwid.AttrWrap(CButton(label,cb),spec)
        params = ('pack',None,False)
        self.widget.contents.append((btn,params))

    def updateAction(self,idx,label = None,cb = None,colors = None):
        btn = self.widget.contents[idx][0]
        if btn:
            btn.set_text(label)
            if cb:
                btn.setOnClick(cb)
            if colors:
                spec = urwid.AttrSpec(*colors)
                btn.set_attr(spec)


class DownloadsWindow(Window):
    def __init__(self,parent,actions_handler = None):
        super().__init__(parent)
        self.actions_handler = actions_handler
        self.actions = []

    def chapterDownloaded(self,arg):
        self.parent.unCheckItem(arg)

    def updateDownloadInfo(self,idx,info):
        item = self.listBox.getItem(idx)
        dl_info = item.contents[1][0]
        dl_info.set_text(info)
    
    def updateDownloadProg(self,idx,val):
        item = self.listBox.getItem(idx)
        pb = item.contents[2][0]
        pb._done = val*100
        nval = (val*101) / val
        cval = pb._current
        cval += nval
        pb.set_completion(cval)
        self._updateScreen()

    def addAction(self,action):
        self.actions.append(action)

    def createActionBar(self):
        colors = ('black' ,'light gray')
        ab = ActionBar(colors = colors)
        def addAction(action):
            ab.addAction(*action,colors = colors)

        for action in self.actions:
            addAction(action)

        addAction(('<<back',self.close))
        return ab

    def createDLItem(self,ch):
        ch_item = CListBoxItem(ch,keypress_handler = self.handleKeyPress)
        dl_info = urwid.Text('')
        dl_pb = urwid.ProgressBar('pb normal','pb complete')
        content = [ch_item,dl_info,dl_pb]
        item = urwid.Pile(content,focus_item = 0)
        #item.keypress = ch_item.keypress
        item.id = ch
        return item

    def createListBox(self,ch_list):
        lb = CListBox()
        for ch,url in ch_list:
            w = self.createDLItem(ch)
            lb.addWidget(w)

        return urwid.AttrWrap(lb,'listbox')
 

    def show(self,*args):
        self.widget.set_focus('body')
        super().show()

    def handleKeyPress(self,key):
        if key in ('1','c','C'):
            self.close()

        else:
            return key

    def close(self,*args):
        self.actions_handler.cancelDownloads()
        super().close()

    def setup(self,ch_list):
        self.title = urwid.Text('')
        self.listBox = self.createListBox(ch_list)
        self.actionBar = self.createActionBar()
        self.widget = urwid.Frame(
            self.listBox,self.title,self.actionBar
        )
        return self


class ChaptersListWindow(Window):
    def __init__(self,parent,actions_handler = None):
        super().__init__(parent)
        self.actions_handler = actions_handler
        self.actions = []
        self.manga_data = None

    def download(self,*args):
        cb = self.actions_handler.downloadChapters
        if cb:
            items = self.getCheckedItems()
            if len(items):
                m_title = self.manga_data[0]
                cb(self, m_title, items)

    def downloadAll(self,*args):
        cb = self.actions_handler.downloadChapters
        if cb:
            items = OrderedDict(self.manga_data[4])
            m_title = self.manga_data[0]
            cb(self, m_title, items)

    def addOrRmBookmark(self,*args):
        cb = self.actions_handler.manageBookmarks
        if cb:
            cb(self,self.manga_data)

    def bookmarkAdded(self):
        self.actionBar.updateAction(
            3,label = '-bookmark',
            colors = ('dark blue','light gray')
        )

    def bookmarkRemoved(self):
        self.actionBar.updateAction(
            3,label = '+bookmark',
            colors = ('black','light gray')
        )


    def getCheckedItems(self):
        items = OrderedDict()
        for item in self.listBox.walker:
            if item.state:
                ch_name = item.label
                ch_url = item.url
                items.update({ch_name : ch_url})

        return items

    def unCheckItem(self,arg):
        if type(arg) == int:
            item = self.listBox.walker[arg]
            item.set_state(False)
            return

        for item in self.listBox.walker:
            if item.state and arg == item.label:
                item.set_state(False)

    def addAction(self,action):
        self.actions.append(action)


    def createActionBar(self,bookmarked):
        def_colors = ('black' ,'light gray')
        ab = ActionBar(colors = def_colors)
        def addAction(action,colors = None):
            ab.addAction(*action,colors = colors or def_colors)

        for action in self.actions:
            addAction(action)

        addAction(('<<back',self.close))
        addAction(('download-all',self.downloadAll))
        addAction(('download',self.download))
        if bookmarked:
            colors = ('dark blue','light gray')
            addAction(('-bookmark',self.addOrRmBookmark),colors)

        else:
            addAction(('+bookmark',self.addOrRmBookmark))

        return ab

    def createListBox(self,ch_list):
        lb = CListBox()
        for ch,url in ch_list:
            w = CCheckBox(ch)
            w.keypress_handler = self.handleKeyPress
            w.url = url
            lb.addWidget(w)


        return urwid.AttrWrap(lb,'listbox')

    def handleKeyPress(self,key):
        if key in ('1','c','C'):
            self.close()

        elif key in ('2','d','D'):
            self.download()

        elif key in ('3', 'a', 'A'):
            self.downloadAll()

        elif key in ('4','b','B'):
            self.addOrRmBookmark()

        else:
            return key




    def setup(self,manga_data):
        self.manga_data = manga_data
        m_title,m_src,m_url,bookmarked,ch_list = self.manga_data
        self.title = urwid.Text(m_title)
        self.listBox = self.createListBox(ch_list)
        self.actionBar = self.createActionBar(bookmarked)
        div = urwid.AttrWrap(urwid.Divider('_'),'div')
        footer = self.actionBar#urwid.Pile([div,self.actionBar])
        self.widget = urwid.Frame(
            self.listBox,self.title,footer
        )
        return self


class EventDispatcher:
    def __init__(self, loop, cb):
        self.fd = loop.watch_pipe(cb)

    def dispatch(self, event):
        os.write(self.fd, event)

class MainWindow(Window):
    def __init__(self,actions_handler = None):
        #fg : bg
        self.palette = [
        ('header', 'black', 'dark cyan', 'standout'),
        ('body', 'white', 'dark blue'),
        ('footer', 'black', 'dark cyan', 'standout'),
        ('div', 'black', 'dark gray'),
        ('txtbox', 'black', 'white'),
        ('btn', 'white', 'black'),
        ('dialog_btn', 'black', 'white'),
        ('actionbar','black' ,'white'),
        ('actionbar_btn','black' ,'white'),
        ('listbox', 'black', 'dark gray'),
        ('listbox_item', 'white', 'black'),
        ('focused_listbox_item','black','white','bold'),
        ('pb normal',    'white',      'black', 'standout'),
        ('pb complete',  'white',      'dark green'),
        ('pb smooth',     'dark magenta','black')
        ]

        self.actions_handler = actions_handler
        self.menu_actions = {
            'main' : [('Exit',self.close)] ,
        }
        self.content = []

        super().__init__()

    def showChaptersList(self,manga_data):
        self.chaptersListWindow.setup(manga_data)
        self.chaptersListWindow.show()

    def showSearchResult(self,res):
        self.widget.set_focus('body')
        self.searchListBox.clear()
        for n in res:
            self.searchListBox.addItem(n)

        self._updateScreen()

    def _showMenu(self,arg):
        _id = arg if isinstance(arg,str) else arg.text
        res = []
        if _id == 'source':
            res = self.actions_handler.getSourceList()

        if _id == 'bookmarks':
            res = self.actions_handler.loadBookmarks()

        self.createMenu(res).show()

    def createMenu(self,actions):
        menu = PopupMenu(self)
        for action in actions:
            menu.addAction(*action)

        return menu

    def createMainMenu(self):
        actions = self.menu_actions['main']
        menu = self.createMenu(actions)
        return menu

    def setMenuActions(self,k,actions):
        if k in self.menu_actions:
            self.menu_actions[k] = actions

    def addMenuAction(self,k,action):
        if k in self.menu_actions:
            self.menu_actions[k].append(action)
            


    def createActionBar(self):
        ab = ActionBar()
        self.mainMenu = self.createMainMenu()
        ab.addAction('menu',self.mainMenu.show)
        ab.addAction('source',self._showMenu)
        ab.addAction('bookmarks',self._showMenu)
        self.content.append(ab)
        return ab


    def createSrcLabel(self,txt):
        label = urwid.Text(('text',txt))
        pad = urwid.Padding(label,'center','pack')
        self.content.append(pad)
        return label

    def sourceChanged(self,txt):
        self.sourceLabel.set_text(('text',txt))


    def createSearchInput(self):
        class CEdit(urwid.Edit):
            def keypress(_self, size, key):
                if key == 'enter':
                    self.searchButton._emit('click')

                return super().keypress(size, key)

        txtbox = CEdit()
        txtbox = urwid.AttrWrap(txtbox,'txtbox')
        pad = urwid.Padding(txtbox,'center',30)
        self.content.append(pad)
        return txtbox



    def createSearchButton(self):
        def search_cb(*args):
            q = self.searchInput.get_edit_text()
            self.actions_handler.doSearch(q)

        btn = CButton('search',search_cb)
        btn = urwid.AttrWrap(btn,'btn')
        pad = urwid.Padding(btn,'center','pack')
        self.content.append(pad)
        return btn

    
    def createSearchListBox(self):
        cb = self.actions_handler.fetchChaptersList
        lb = CListBox(item_click_cb = cb)
        w = urwid.AttrWrap(lb,'listbox')
        return w



    def close(self,*args):
        raise urwid.ExitMainLoop()

    def unhandled_input(self,key):
        if key in ('0','q','Q'):
            self.close()

        elif key in ('1','m','M'):
            self.mainMenu.show()

        elif key in ('2','s','S'):
            self._showMenu('source')

        elif key in ('3','b','B'):
            self._showMenu('bookmarks')

        else:
            return key


    def setup(self,label):
        #setup body content
        self.searchListBox = self.createSearchListBox()
        frame = urwid.Frame(self.searchListBox)
        self.widget = urwid.AttrWrap(frame,'body')

        #setup header content
        self.actionBar = self.createActionBar()
        self.sourceLabel = self.createSrcLabel(label)
        self.searchInput = self.createSearchInput()
        self.searchButton = self.createSearchButton()
        header = urwid.Pile(self.content)
        self.widget.set_header(header)

        #setup other windows
        self.chaptersListWindow = ChaptersListWindow(self,self.actions_handler)
        self.downloadsWindow = DownloadsWindow(self.chaptersListWindow,self.actions_handler)
        return self


    def createEventDispatcher(self,cb):
        return EventDispatcher(mainLoop, cb)

    def show(self):
        global screen,mainLoop
        screen = urwid.raw_display.Screen()
        mainLoop = urwid.MainLoop(self.widget,
            self.palette,screen ,
            unhandled_input = self.unhandled_input)
        mainLoop.run()




if __name__ == '__main__':
    pass
