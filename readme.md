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
file of a list has focus, focus stays on the list itself. The lists of files of the main window and of
the conversion window are named Files, in the language of the application. The lists of tracks of the
CD Ripper and Disc Burner tabs are named by their tab page alone, instead of by internal English names.

In the list of files of the main window, files are selected as in other Windows lists, and a file
that is not selected is reported as "not selected":

* Up and Down Arrow, Home, End, Page Up and Page Down move to a file and select only it; with Shift
  they extend the selection.
* Control with Up or Down Arrow, Home or End moves to a file without changing the selection.
* Control+Space selects or unselects the file, Space selects only it. On the row of a folder, both act
  on the folder together with all its files.
* Control+A selects all files, Escape unselects all.

These commands report the new state of the file and are silent when they change nothing.

The metadata of the files can be edited right in the list of files of the main window, as in a table
whose columns are Track artist, Title, Album and the others:

* F2 opens the field of the focused file in the column it was last open in and reports the column and
  the value. The whole value is selected, so typing replaces it.
* Tab and Shift+Tab move to the next and the previous column that can be edited, keeping what was
  typed, and report the column and the value. Columns that cannot be edited in the list, such as the
  file name, Rating or the file's properties, are skipped. At the first and the last column, the column
  and the value are reported again. Held down, they report only the column they stop at.
* Alt+Home and Alt+End move to the first and the last column that can be edited, the last being the
  one before Lyrics, and report it. With many columns this takes about a second; any key stops it.
* Up and Down Arrow move to the same column of the previous and the next file and report the file name
  and the value. As in the application, they wrap around at the first and the last file. Held down,
  they report only the file they stop at.
* Tab or Shift+Tab to the Lyrics column opens the application's Lyrics dialog. When the dialog closes,
  focus returns to the field of the column it was opened from.
* Enter keeps the change and returns to the list, Escape discards it. F2 then opens the same column
  again.
* On a file, Left and Right Arrow do nothing; the application would open the field of another column.
* NVDA+Tab, NVDA's command that reports the focus, says which column the field is in, the file name
  (if NVDA reports object descriptions) and the value.

The application has its own keys for the field, which are reported the same way: Alt+Left and
Alt+Right Arrow move to the previous and the next column that can be edited, and Alt+Up and Alt+Down
Arrow to the previous and the next file. Unlike Tab, Alt+Left and Alt+Right go round within the file:
from the last column to the first one and back, so you do not hear where the row ends. They also pass
the Lyrics column by without opening its dialog. Use Tab and Shift+Tab to go through the columns of
a file one by one and know when you have reached its first or last column, or to open the lyrics; use
Alt+Left from the first column to get to the last one at once, or Alt+Home and Alt+End to get to either
end from anywhere in the row.

Moving the field takes the application a moment, and this cannot be made faster: for every move it
closes the field, keeping what was typed, and opens a new one in the next cell. You may notice it:

* Up and Down Arrow, and Alt with the arrow keys, take about a fifth of a second for each file. Held
  down, Up and Down Arrow move fewer files than the key repeats, as the application skips the repeats
  that come while it is still moving; Alt+Up and Alt+Down keep moving for a moment after the key is
  released.
* Tab and Shift+Tab take a little longer when they pass columns that cannot be edited or when the list
  has to scroll sideways.
* Alt+Home and Alt+End take up to about a second with many columns shown. The application has no
  command to go to the first or the last column, so the field is moved there column by column.
* The Lyrics dialog takes a moment to open, and NVDA is silent meanwhile.

## Commands

Commands of this add-on are listed in NVDA's Input Gestures dialog, under the
"EZ CD Audio Converter" category, and can be reassigned there.

## Licence

GPL v2. See COPYING.txt for the full text.
