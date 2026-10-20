# EZ CD Audio Converter Access Improver

Improves accessibility of EZ CD Audio Converter with NVDA.

* Author: Rosgardius
* NVDA compatibility: 2026.1 to 2026.2

## Features

### Top buttons of the main window's tabs

The large buttons at the top of the Audio Converter, Audio CD Ripper and Disc Burner tabs (Convert,
Rip CD, Burn Disc, Settings, View and the others) are read as buttons of a toolbar, including whether
they are unavailable. Convert and Rip CD report their shortcut, F8.

* The panel is one stop in the Tab order: Tab from the last control of the tab, or Shift+Tab from
  the tab labels, moves to it. Focus comes to the button that had it last, or to the first button
  (Audio Converter, CD Ripper, Disc Burner) the first time after the application starts.
* Left and Right Arrow move between the buttons, Home and End to the first and the last one.
* Enter, Numpad Enter and Space press the focused button.
* The buttons that open a menu (Audio Converter, CD Ripper, Disc Burner, Disc, Metadata, View and
  Help) are reported as menu buttons. Enter, Space or Down Arrow opens the menu; Escape closes it and
  returns to the button.
* The menu of the first button switches the tab. After choosing a tab there, focus goes to the first
  button of that tab.
* To press a button without focusing it, move the navigator object to it and press NVDA+Numpad Enter.

### Conversion window

Only the total progress of the conversion is reported, as NVDA's progress bar settings say; the
progress bars of the individual converters are silent. The total progress bar is named "Total
progress".

NVDA+End (NVDA+Shift+End in the laptop layout), NVDA's command that reads the status bar, reports the
state of the conversion: the total percentage, the number of converted files, the remaining time and
the speed, averaged over the last 5 seconds while the window is in the foreground. Errors and skipped
files are reported when there are any. A paused conversion starts with "Paused" and has no speed; a
finished one starts with "Finished" and gives the elapsed time instead of the remaining one. As
elsewhere, pressing the command twice spells the text and three times copies it to the clipboard.

The number of converters is a spin box, named by the caption next to it. Up and Down Arrow add and
remove a converter and report the new number, also while the conversion runs; at the limit the number
is reported unchanged. While converting, the application may take a moment to answer. In object
navigation, the "-" and "+" buttons of the application are the Decrease and Increase buttons on either
side of the spin box; NVDA+Numpad Enter presses them.

### Lists of files

In the lists of files of the main window and of the conversion window, each file is read once, with
all its columns, and the first arrow key after entering a list reports the file it moves to. When no
file of a list has focus, focus stays on the list itself. The list of the conversion window is named
Files, in the language of the application.

In the list of files of the main window, files are selected as in other Windows lists, and a file
that is not selected is reported as "not selected":

* Up and Down Arrow, Home, End, Page Up and Page Down move to a file and select only it; with Shift
  they extend the selection.
* Control with Up or Down Arrow, Home or End moves to a file without changing the selection.
* Control+Space selects or unselects the file, Space selects only it. On the row of a folder, both act
  on the folder together with all its files.
* Control+A selects all files, Escape unselects all.

These commands report the new state of the file and are silent when they change nothing.

## Commands

Commands of this add-on are listed in NVDA's Input Gestures dialog, under the
"EZ CD Audio Converter" category, and can be reassigned there.

## Licence

GPL v2. See COPYING.txt for the full text.
