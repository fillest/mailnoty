#coding: utf-8
import urllib2
import contextlib
import base64
import argparse
import traceback
import webbrowser
import logging
import threading
import time
import ConfigParser
import os
import sys
import time
from functools import partial
import xml.etree.ElementTree as ET
import gzip
import cStringIO
from itertools import takewhile
from PyQt4 import QtGui, QtCore


logging.basicConfig(level = logging.INFO, format = '%(asctime)s %(levelname)-5.5s %(name)s:%(lineno)d:%(funcName)s  %(message)s')
log = logging.getLogger(__name__)


class FetchError (Exception):
    pass

class AuthError (Exception):
    pass

def raise_fetch_error ():
    log.warning("Exception while fetching feed:\n%s" % traceback.format_exc())
    raise FetchError()

def fetch_feed (url, user, password):
    #https://developers.google.com/google-apps/gmail/gmail_inbox_feed
    # GMAIL_FEED_URL = 'https://mail.google.com/mail/feed/atom/'
    # GMAIL_FEED_URL = 'https://mail.google.com/mail/u/0/feed/atom/'
    # GMAIL_FEED_URL = 'https://mail.google.com/mail/u/1/feed/atom/'

    # h=urllib2.HTTPSHandler(debuglevel=1)
    # opener = urllib2.build_opener(h)
    # urllib2.install_opener(opener)
    req = urllib2.Request(url)

    #looks like the feed returns gzip only on some combination of headers and values (copied them from broser)
    req.add_header('Accept-Encoding', 'gzip')
    req.add_header('User-Agent', 'Mozilla/5.0 (Windows NT 6.1; WOW64; rv:39.0) Gecko/20100101 Firefox/39.0')
    req.add_header('Cache-Control:', "max-age=0")

    req.add_header('Authorization', "Basic " + base64.encodestring("%s:%s" % (user, password)))
    try:
        with contextlib.closing(urllib2.urlopen(req, timeout = 10)) as resp:
            raw = resp.read()
            if resp.info().get('Content-Encoding') == 'gzip':
                s = cStringIO.StringIO(raw)
                try:
                    with gzip.GzipFile(mode = 'rb', fileobj = s) as gz:
                        data = gz.read()
                finally:
                    s.close()
                return data
            else:
                log.warning("not gzipped")
                return raw
    except urllib2.HTTPError as e:
        if e.code == 401:
            raise AuthError()
        else:
            raise_fetch_error()
    except:
        raise_fetch_error()

def fetch_recent_unread_entries (url, user, password):
    data = fetch_feed(url, user, password)

    data = data.replace('xmlns', 'dummy')
    feed = ET.fromstring(data)
    
    total_unread_num = int(feed.find('fullcount').text)
    entries = []
    if total_unread_num:
        for e in feed.findall('entry'):
            entries.append((
                e.find('author/name').text,
                e.find('title').text,
                e.find('link').get('href'),
            ))
    return total_unread_num, entries

def fetch_mail_loop (state, url, user, password, interval):
    while True:
        entries = []
        is_error = False
        try:
            # t = time.time()
            _total_unread_num, entries = fetch_recent_unread_entries(url, user, password)
            # print time.time() - t
        except FetchError:
            is_error = True
        with state.lock:
            state.entries = entries
            state.is_error = is_error
        
        time.sleep(interval)

class SystemTrayIcon (QtGui.QSystemTrayIcon):
    def __init__ (self, parent = None):
        QtGui.QSystemTrayIcon.__init__(self, parent)

        #https://icons8.com/web-app/63/message
        self.icon_has_new = QtGui.QIcon("icons/mail_red.png")
        self.icon_nothing_new = QtGui.QIcon("icons/mail_gray.png")
        self.icon_error = QtGui.QIcon("icons/mail_error.png")
        self.icon_new = QtGui.QIcon("icons/mail_new.png")
        self.icon_null = QtGui.QIcon()

        self.setIcon(self.icon_nothing_new)

        self.menu = QtGui.QMenu(parent)
        self.menu.aboutToHide.connect(self._clear_entry_icons)
        self.setContextMenu(self.menu)
        self.finish_menu()

        self.activated.connect(self.onTrayIconActivated)

        self.last_entries = []
        self.was_error = False
        self.new_entries = set()

    def _clear_entry_icons (self):
        for action in self.menu.actions():
            action.setIcon(self.icon_null)

    def onTrayIconActivated(self, reason):
        if reason == QtGui.QSystemTrayIcon.Trigger:
            self.menu.exec_(QtGui.QCursor.pos())
        # elif reason == QtGui.QSystemTrayIcon.MiddleClick:
        #     self.setIcon(self.icon_has_new)
        if not self.was_error:
            self.setIcon(self.icon_nothing_new)
        self.new_entries = set()

    def update_menu (self, state):
        with state.lock:
            entries = state.entries[:]
            is_error = state.is_error

        if is_error:
            self.setIcon(self.icon_error)
            self.was_error = True
            return

        new = new_entries(self.last_entries, entries)
        if not new:
            if self.was_error:
                if self.new_entries:
                    self.setIcon(self.icon_has_new)
                else:
                    self.setIcon(self.icon_nothing_new)
            return

        for link in new:
            self.new_entries.add(link)
        self.last_entries = entries
        
        self.menu.clear()
        for name, title, link in entries:
            action = self.menu.addAction(u"%s — %s" % (title, name))
            action.triggered.connect(partial(webbrowser.open, link))
            if link in self.new_entries:
                action.setIcon(self.icon_new)
        self.menu.addSeparator()
        self.finish_menu()
        
        self.setIcon(self.icon_has_new)
        self.was_error = False

    def finish_menu (self):
        action = self.menu.addAction("Quit")
        action.triggered.connect(lambda: QtGui.QApplication.exit(0))

def new_items (old, new, m = lambda v: v):
    old = map(m, old)
    new = map(m, new)
    common = frozenset(old).intersection(frozenset(new))
    return list(takewhile(lambda x: x not in common, new))

new_entries = partial(new_items, m = lambda v: v[2])

def _test_diff ():
    df = new_items
    a = []
    b = []
    assert df(a, b) == [], df(a, b)
    a = [1]
    b = []
    assert df(a, b) == [], df(a, b)
    a = []
    b = [1]
    assert df(a, b) == [1], df(a, b)
    a = [1]
    b = [1]
    assert df(a, b) == [], df(a, b)
    a = [2,1]
    b = [2,1]
    assert df(a, b) == [], df(a, b)
    a = [1]
    b = [2,1]
    assert df(a, b) == [2], df(a, b)
    a = [3,2]
    b = [4,3]
    assert df(a, b) == [4], df(a, b)
    a = [3,2]
    b = [5,4]
    assert df(a, b) == [5,4], df(a, b)
    a = [4,3,2]
    b = [4,3,1]
    assert df(a, b) == [], df(a, b)
    a = [4,3,2]
    b = [5,3,1]
    assert df(a, b) == [5], df(a, b)

    a = [(0,0,2), (0,0,1)]
    b = [(0,0,2), (0,0,1)]
    assert new_entries(a, b) == [], new_entries(a, b)

def read_cfg (config_path, name):
    p = ConfigParser.SafeConfigParser()
    fpath = os.path.expanduser(config_path)
    # print fpath; sys.exit(1)
    if not p.read(fpath):
        log.error("failed to read config")
        sys.exit(1)
    return p.get(name, 'url'), p.get(name, 'login'), p.get(name, 'password')

def parse_args ():
    parser = argparse.ArgumentParser()
    parser.add_argument('-i', '--interval', default = 15, type = int, help = "Interval between checks (in seconds)")
    parser.add_argument('-c', '--config-path', default = '~/mailnoty.ini')
    parser.add_argument('name')
    return parser.parse_args()

class State (object):
    pass

def main():
    _test_diff()#; return

    args = parse_args()

    url, login, password = read_cfg(args.config_path, args.name)

    state = State()
    state.lock = threading.Lock()
    state.entries = []
    state.is_error = False
    thr = threading.Thread(target = fetch_mail_loop, args = [state, url, login, password, args.interval], name = 'fetcher')
    thr.daemon = True
    thr.start()

    app = QtGui.QApplication(sys.argv)

    w = QtGui.QWidget()
    trayIcon = SystemTrayIcon(w)
    # assert trayIcon.isSystemTrayAvailable()
    trayIcon.show()

    intv = 1000
    def periodic_update_menu ():
        trayIcon.update_menu(state)
        QtCore.QTimer.singleShot(intv, periodic_update_menu)
    periodic_update_menu()

    sys.exit(app.exec_())

if __name__ == '__main__':
    main()
