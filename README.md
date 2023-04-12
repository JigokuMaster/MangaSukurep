# MangaSukurep

Manga Downloader written in Python , with a default UI built using urwid tui library.


## background

i originally wrote this simple tool for personal use only ,
under android **TerminalEmulator** using **mcedit** (midnight commander) :) , so it's pretty hackish with just a very basic **features** like : 

- quick search for a favorite manga.

- simple bookmarks manager.

- download manager supports resuming failed or incomplete chapters.

- select one/multiple/all chapters to download.

- download each chapter in zip format.

- basic keybindings.

## limitations 

- no themes or keybindings customizations for now.

- no multithreading , it can download only one chapter at a time and one image/page at a time.

- no fast html parser like lxml.

 - for now it can download manga in english translations only , and there are just 2 scrapers see the [scrapers directory](scrapers/)


## requirements & installation 

should work on python 3.6 , but also it needs the following libraries :

- urwid 
- beautifulsoup4
- requests
- requests-cache , sqlite3
- hurry.filesize

just install them manually using pip .

then download the [latest source-code release](https://github.com/JigokuMaster/MangaSukurep/releases/latest)

1 )  - running it in termux 

by default termux supports mouse events in tui based tools , and it's good for interacting with this tool using  the touchscreen, but the keyboard is also important and in case you pressed the back key and the keyboard refuse to show again ,
you can press the keyboard toggle in
extra keys or left drawer to show it.

anyway after downloading just
extract  it , then

$ cd MangaSukurep

$ python main.py

2 )  - running it in qpython : 

tested in QPython OS v3.2.3  , but the issue after enabling "sending mouse event" in terminal preference , there is no option to force-show the soft-keyboard , so it's kinda unusable,  anyway if you want to try it , download and extract it to /sdcard/qpython/projects3/

from qpython go to the place you usually run your projects , then click on MangaSukurep folder to start it.



3 )  - using it in a linux distro :

though i didn't tested , i think it should work, 
like termux , download > extract > python main.py

## downloads directory

the default path is /sdcard/manga , to change the /sdcard path 
do for e.g : 

$ MDL_PATH=~/downloads python main.py


## keybindings

- pressing ( q ) key from any window will  exit/close the program.


1 ) main window :

- pressing ( ENTER ) key , search for the inputted manga title.

- pressing (1 | m  | M ) keys , will show exit menu.

- pressing ( 2 | s | S ) keys , will show source menu.

- pressing (3 | b | B) keys , will show bookmarks menu.

2 ) chapters list window :

- pressing ( c | C  ) keys , will close the current window and return to the main window.

- pressing (  d | D ) keys , download selected chapters.

- pressing ( a | A ) keys , download all manga chapters.

- pressing ( b | B ) keys , add / remove  manga bookmark.

3 ) dialog windows :

- pressing ( c ) key , hide / close the dialog or cancel https requests ,though it's unstable.

-  pressing ( r ) key , retry failed action.

- pressing ( y ) key , yes perform action.

- pressing ( n ) key , no don't perform action.

- pressing ( UP | DOWN | PAGE-UP | PAGE-DOWN ) keys , scroll long error message content


## some screenshots taken from termux

![Main Window](https://github.com/JigokuMaster/MangaSukurep/raw/main/Screenshots/Termux_4.jpg)


![Chapters List Window](https://github.com/JigokuMaster/MangaSukurep/raw/main/Screenshots/Termux_5.jpg)


![Downloader Window](https://github.com/JigokuMaster/MangaSukurep/raw/main/Screenshots/Termux_1.jpg)


































