## mailnoty
* Periodically checks your Gmail inbox via feed API
* Shows a system tray icon, which turns red when new mail gets detected
* Click on the indicator to show a menu with the latest message titles. Click a message to open it in Gmail in your browser.
* Run multiple `mailnoty` instances for multiple accounts.

### Install
#### Windows
1. Install Python 2.7 https://www.python.org/downloads/
2. Install PyQt4 for Py2.7 x32 binary package http://www.riverbankcomputing.co.uk/software/pyqt/download
3. Download and unpack `mailnoty` https://github.com/fillest/mailnoty/archive/master.zip

Create C:/Users/youruser/mailnoty.ini
```ini
[name1]
url = https://mail.google.com/mail/u/0/feed/atom
login = name1@gmail.com
password = yourpassword1

[name2]
url = https://mail.google.com/mail/u/1/feed/atom
login = name2@gmail.com
password = yourpassword2
```

### Run
Create a shortcut link for gmnoty.pyw and in its properties add your "name" from the config as a parameter, e.g. `C:\proj\mailnoty\gmnoty.pyw name1`