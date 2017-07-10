

from cefpython3 import cefpython as cef
import ctypes
import os
import platform
import sys
from PyQt4.QtGui import *
from PyQt4.QtCore import *


# Fix for PyCharm hints warnings when using static methods
WindowUtils = cef.WindowUtils()

# Platforms
WINDOWS = (platform.system() == "Windows")
LINUX = (platform.system() == "Linux")
MAC = (platform.system() == "Darwin")

# Configuration
WIDTH = 800
HEIGHT = 600

# OS differences
CefWidgetParent = QWidget


def main():
    #check_versions()
    #sys.excepthook = cef.ExceptHook  # To shutdown all CEF processes on error
    cef.Initialize()
    app = CefApplication(sys.argv)
    main_window = MainWindow()
    main_window.show()
    main_window.activateWindow()
    main_window.raise_()
    app.exec_()
    app.stopTimer()
    del main_window  # Just to be safe, similarly to "del app"
    del app  # Must destroy app object before calling Shutdown
    #cef.Shutdown()



class MainWindow(QMainWindow):
    def __init__(self):
        # noinspection PyArgumentList
        super(MainWindow, self).__init__(None)
        self.cef_widget = None
        self.navigation_bar = None
        self.setWindowTitle("SpeKa Browser Created By Lusoma Joseph")
        self.setFocusPolicy(Qt.StrongFocus)
        self.setupLayout()
        name ='speka_logo'
        resources = os.path.join(os.path.abspath(os.path.dirname(__file__)),
                                 "resources")
        pixmap = QPixmap(os.path.join(resources, "{0}.png".format(name)))
        icon = QIcon(pixmap)
        self.setWindowIcon(icon)


    def setupLayout(self):
        self.resize(WIDTH, HEIGHT)
        self.cef_widget = CefWidget(self)
        self.navigation_bar = NavigationBar(self.cef_widget)
        layout = QGridLayout()
        # noinspection PyArgumentList
        layout.addWidget(self.navigation_bar, 0, 0)
        # noinspection PyArgumentList
        layout.addWidget(self.cef_widget, 1, 0)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        layout.setRowStretch(0, 0)
        layout.setRowStretch(1, 1)
        # noinspection PyArgumentList
        frame = QFrame()
        frame.setLayout(layout)
        self.setCentralWidget(frame)
        self.show()
        # Browser can be embedded only after layout was set up
        self.cef_widget.embedBrowser()


    def closeEvent(self, event):
        # Close browser (force=True) and free CEF reference
        if self.cef_widget.browser:
            self.cef_widget.browser.CloseBrowser(True)
            self.clear_browser_references()

    def clear_browser_references(self):
        # Clear browser references that you keep anywhere in your
        # code. All references must be cleared for CEF to shutdown cleanly.
        self.cef_widget.browser = None


class CefWidget(CefWidgetParent):
    def __init__(self, parent=None):
        # noinspection PyArgumentList
        super(CefWidget, self).__init__(parent)
        self.parent = parent
        self.browser = None
        self.hidden_window = None  # Required for PyQt5 on Linux
        self.show()

    def focusInEvent(self, event):
        # This event seems to never get called on Linux, as CEF is
        # stealing all focus due to Issue #284.
        if self.browser:
            if WINDOWS:
                WindowUtils.OnSetFocus(self.getHandle(), 0, 0, 0)
            self.browser.SetFocus(True)

    def focusOutEvent(self, event):
        # This event seems to never get called on Linux, as CEF is
        # stealing all focus due to Issue #284.
        if self.browser:
            self.browser.SetFocus(False)

    def embedBrowser(self):
        window_info = cef.WindowInfo()
        rect = [0, 0, self.width(), self.height()]

        #iniatial page display
        resources = os.path.join(os.path.abspath(os.path.dirname(__file__)), "resources/index_page")
        index_page = os.path.join(resources, "index_page.html")
        window_info.SetAsChild(self.getHandle(), rect)
        self.browser = cef.CreateBrowserSync(window_info,
                                             url=index_page)
        self.browser.SetClientHandler(LoadHandler(self.parent.navigation_bar))
        self.browser.SetClientHandler(FocusHandler(self))

    def getHandle(self):
        if self.hidden_window:
            # PyQt5 on Linux
            return int(self.hidden_window.winId())
        try:
            # PyQt4 and PyQt5
            return int(self.winId())
        except:
            # PySide:
            # | QWidget.winId() returns <PyCObject object at 0x02FD8788>
            # | Converting it to int using ctypes.
            if sys.version_info[0] == 2:
                # Python 2
                ctypes.pythonapi.PyCObject_AsVoidPtr.restype = (
                        ctypes.c_void_p)
                ctypes.pythonapi.PyCObject_AsVoidPtr.argtypes = (
                        [ctypes.py_object])
                return ctypes.pythonapi.PyCObject_AsVoidPtr(self.winId())
            else:
                # Python 3
                ctypes.pythonapi.PyCapsule_GetPointer.restype = (
                        ctypes.c_void_p)
                ctypes.pythonapi.PyCapsule_GetPointer.argtypes = (
                        [ctypes.py_object])
                return ctypes.pythonapi.PyCapsule_GetPointer(
                        self.winId(), None)

    def moveEvent(self, _):
        self.x = 0
        self.y = 0
        if self.browser:
            if WINDOWS:
                WindowUtils.OnSize(self.getHandle(), 0, 0, 0)
            elif LINUX:
                self.browser.SetBounds(self.x, self.y,
                                       self.width(), self.height())
            self.browser.NotifyMoveOrResizeStarted()

    def resizeEvent(self, event):
        size = event.size()
        if self.browser:
            if WINDOWS:
                WindowUtils.OnSize(self.getHandle(), 0, 0, 0)
            elif LINUX:
                self.browser.SetBounds(self.x, self.y,
                                       size.width(), size.height())
            self.browser.NotifyMoveOrResizeStarted()


class CefApplication(QApplication):
    def __init__(self, args):
        super(CefApplication, self).__init__(args)
        self.timer = self.createTimer()
        self.setupIcon()

    def createTimer(self):
        timer = QTimer()
        # noinspection PyUnresolvedReferences
        timer.timeout.connect(self.onTimer)
        timer.start(10)
        return timer

    def onTimer(self):
        cef.MessageLoopWork()

    def stopTimer(self):
        # Stop the timer after Qt's message loop has ended
        self.timer.stop()

    def setupIcon(self):
        icon_file = os.path.join(os.path.abspath(os.path.dirname(__file__)),
                                 "resources", "{0}.png".format(sys.argv[0]))
        if os.path.exists(icon_file):
            self.setWindowIcon(QIcon(icon_file))


class LoadHandler(object):
    def __init__(self, navigation_bar):
        self.initial_app_loading = True
        self.navigation_bar = navigation_bar

    def OnLoadingStateChange(self, **_):
        self.navigation_bar.updateState()

    def OnLoadStart(self, browser, **_):
        self.navigation_bar.url.setText(browser.GetUrl())
        if self.initial_app_loading:
            self.navigation_bar.cef_widget.setFocus()
            # Temporary fix no. 2 for focus issue on Linux (Issue #284)
            if LINUX:
                print("[qt.py] LoadHandler.OnLoadStart:"
                      " keyboard focus fix no. 2 (Issue #284)")
                browser.SetFocus(True)
            self.initial_app_loading = False


class FocusHandler(object):
    def __init__(self, cef_widget):
        self.cef_widget = cef_widget

    def OnSetFocus(self, **_):
        pass

    def OnGotFocus(self, browser, **_):
        # Temporary fix no. 1 for focus issues on Linux (Issue #284)
        if LINUX:
            print("[qt.py] FocusHandler.OnGotFocus:"
                  " keyboard focus fix no. 1 (Issue #284)")
            browser.SetFocus(True)


class NavigationBar(QFrame):
    def __init__(self, cef_widget):
        # noinspection PyArgumentList
        super(NavigationBar, self).__init__()
        self.cef_widget = cef_widget

        # Init layout
        layout = QGridLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Back button
        self.back = self.createButton("back")
        self.back.setToolTip("back")
        # noinspection PyUnresolvedReferences
        self.back.clicked.connect(self.onBack)
        # noinspection PyArgumentList
        layout.addWidget(self.back, 0, 0)

        # Forward button
        self.forward = self.createButton("forward")
        self.forward.setToolTip("forward")
        # noinspection PyUnresolvedReferences
        self.forward.clicked.connect(self.onForward)
        # noinspection PyArgumentList
        layout.addWidget(self.forward, 0, 1)

        # Reload button
        self.reload = self.createButton("reload")
        self.reload.setToolTip("reload")
        # noinspection PyUnresolvedReferences
        self.reload.clicked.connect(self.onReload)
        # noinspection PyArgumentList
        layout.addWidget(self.reload, 0, 2)

        # Url input
        self.url = QLineEdit("")
        # noinspection PyUnresolvedReferences
        self.url.returnPressed.connect(self.onGoUrl)
        # noinspection PyArgumentList
        layout.addWidget(self.url, 0, 3)

        # Reload button
        self.services = self.createButton("services")
        self.services.setToolTip("services")
        # noinspection PyUnresolvedReferences
        self.services.clicked.connect(self.onServices)
        # noinspection PyArgumentList
        layout.addWidget(self.services, 0, 4)


        # Layout
        self.setLayout(layout)
        self.updateState()
    def onServices(self):
        #accessing Logos from the Resources
        resources = os.path.join(os.path.abspath(os.path.dirname(__file__)),"resources")

        serv_layout = QGridLayout()
        serv_layout.setContentsMargins(0, 0, 0, 0)
        serv_layout.setSpacing(0)
        self.facebook = QPushButton("FaceBook")
        self.facebook.setToolTip("www.facebook.com")
        self.facebook.clicked.connect(self.onFacebook)

        facebook_icon = QPixmap(os.path.join(resources, "facebook_logo.png"))
        fb_icon = QIcon(facebook_icon)
        self.facebook.setIcon(fb_icon)

        google = QPushButton("Google")

        google_icon= QPixmap(os.path.join(resources,"google_logo.png"))
        gg_icon = QIcon(google_icon)
        google.setIcon(gg_icon)
        github = QPushButton("GithHub")

        youtube = QPushButton("YouTube")

        you_icon =QPixmap(os.path.join(resources,'youtube.png'))
        tube_icon =QIcon(you_icon)
        youtube.setIcon(tube_icon)
        personal_project= QPushButton("My Project")
        personal_project.clicked.connect(self.onMyProject)

        admin_personal_project =QPushButton()
        serv_layout.addWidget(google, 0, 0)
        serv_layout.addWidget(self.facebook,1,0)
        serv_layout.addWidget(youtube, 2, 0)
        serv_layout.addWidget(github, 3, 0)
        serv_layout.addWidget(personal_project,4,0)
        dialog = QDialog()
        dialog.resize(400,100)
        name ='speka_logo'

        pixmap = QPixmap(os.path.join(resources, "{0}.png".format(name)))
        icon = QIcon(pixmap)
        dialog.setWindowIcon(icon)

        dialog.setWindowTitle("SpeKa-Service -Enjoy some of the world's Platform Services")
        dialog.setLayout(serv_layout)
        dialog.exec_()
    def onFacebook(self):
        if self.cef_widget.browser:
            self.cef_widget.browser.LoadUrl("https://www.facebook.com")
    def onMyProject(self):
        if self.cef_widget.browser:
            self.cef_widget.browser.LoadUrl("http://127.0.0.1:8000")
    def onBack(self):
        if self.cef_widget.browser:
            self.cef_widget.browser.GoBack()

    def onForward(self):
        if self.cef_widget.browser:
            self.cef_widget.browser.GoForward()

    def onReload(self):
        if self.cef_widget.browser:
            self.cef_widget.browser.Reload()

    def onGoUrl(self):
        if self.cef_widget.browser:
            self.cef_widget.browser.LoadUrl(self.url.text())

    def updateState(self):
        browser = self.cef_widget.browser
        if not browser:
            self.back.setEnabled(False)
            self.forward.setEnabled(False)
            self.reload.setEnabled(False)
            self.url.setEnabled(False)
            return
        self.back.setEnabled(browser.CanGoBack())
        self.forward.setEnabled(browser.CanGoForward())
        self.reload.setEnabled(True)
        self.url.setEnabled(True)
        self.url.setText(browser.GetUrl())

    def createButton(self, name):
        resources = os.path.join(os.path.abspath(os.path.dirname(__file__)),
                                 "resources")
        pixmap = QPixmap(os.path.join(resources, "{0}.png".format(name)))
        icon = QIcon(pixmap)
        button = QPushButton()
        button.setIcon(icon)
        button.setIconSize(pixmap.rect().size())
        return button

if __name__ == '__main__':
    main()
