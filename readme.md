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

### Toolbars of the file explorer

The two toolbars above the file explorer of the Audio Converter and Disc Burner tabs are stops in the
Tab order, each right before the control right of it on the screen: the navigation toolbar before the
path bar, the view toolbar before the filter of file types. Their buttons are named by the
application's own hints, in its language: View Explorer, Add files, Add folder, Go to Computer, Go to
Music, back and forward in history, Go up, and View. View, alone in its toolbar, is read as a menu button
without the toolbar. View Explorer is a toggle button, pressed while the explorer is shown. Where the
application hides the filter of file types, as on the MP3 disc and Data disc pages of the Disc Burner tab,
the view toolbar is a stop at the end of the tab instead, right before the top buttons.

While the explorer is hidden, its place is taken by one toolbar: View Explorer, Add files, Add folder and,
on the Audio Converter tab, Select all, Remove all and Create M3U playlist. It is a stop in the Tab order
right before the list of files of the Audio Converter tab and before the page tabs of the Disc Burner
tab. Pressing View Explorer moves focus to View Explorer in the other place, so pressing it again
undoes it; as with any toggle button, only the new state is reported: pressed or not pressed.

* Focus comes to the button that had it last in that toolbar, or to the first one.
* Left and Right Arrow move between the buttons, Home and End to the first and the last one.
* Enter, Numpad Enter and Space press the focused button. On View, they or Down Arrow open the menu of
  the list's view (List, Details, Icons, Large icons).

### File explorer

The tree of folders, the list of the folder and the filter of file types are named: Folders, Folder
contents and File types. On entering the list without a current item, the number of its items is
reported. When the list goes to another folder (Enter on a folder, Backspace), the folder and the number
of its items are reported. The breadcrumb bar is reported as the button Path, with the current folder:
Enter or Space shows a field in which a path can be typed. Enter goes to that folder, Escape cancels;
either way focus comes back to Path. For a path that does not exist, focus stays in the field and the
current folder is reported. Up and Down Arrow in the field go through the address history of Windows'
File Explorer, as in the application itself, replacing the typed path; Escape brings back the current
folder.

### Pages of the Disc Burner tab

The Disc Burner tab has three pages, Audio CD, MP3 disc and Data disc, which the application switches
only with buttons for the mouse. The stop in the Tab order right before the list of files is read as
the tab of the current page, such as "MP3 disc, tab, 2 of 3".

* On that tab, Left and Right Arrow show the previous and the next page, Home and End the first and the
  last one.
* Control+Tab and Control+Shift+Tab anywhere on the Disc Burner tab show the next and the previous
  page, going round. From the list of files or another control of a page, focus goes to the list of the
  new page; elsewhere it stays where it is and the new page is reported.

The application takes a moment to show a page. Tab or Shift+Tab pressed on the page tab meanwhile waits
until the new page is reported.

### Toolbar of the drive's tray

The toolbar at the end of the drive and speed row of the Audio CD Ripper and Disc Burner tabs is a
stop in the Tab order right after the speed: before the list of tracks of the Audio CD Ripper tab and
before Options of the Disc Burner tab. On the MP3 disc and Data disc pages, which have no Options, it is
a stop at the end of the tab, right before the top buttons (after the view toolbar if that is there too).
Its buttons are named by the application's own hints: Open tray,
Close tray and, on the Audio CD Ripper tab, Drive settings. On the Disc Burner tab, with Open tray
alone, it is read as a button without the toolbar. Without a disc drive the buttons are unavailable.
Arrows, Home, End, Enter and Space work as in the toolbars of the file explorer.

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
* Right Arrow expands a folder, and on an expanded folder moves to its first file. Left Arrow collapses
  a folder, and on a file in a folder moves to the folder.
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
* In the list, Left and Right Arrow do not open the field of another column, as the application would.
  F2 on a folder does nothing: a folder has no fields.
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

### Metadata fields

The metadata fields below the list of files (Album artist, Title, Compilation and the others), the same
fields of the Audio CD Ripper tab, and the CD-Text fields of the Disc Burner tab are named by their
captions on the screen, in the language of the application. The fields right of the track and disc
numbers are named by the application's own words for the totals, such as Total Tracks. The cover art,
reached with object navigation, is named Cover Art and has its size and format as the description.

### Names of fields in all windows

Fields, lists, combo boxes and sliders that the application leaves without a name, in the main window
and in its dialogs (Settings, Options, DSP and the others), are named by their captions on the screen,
in the language of the application: the text left of the field, or the check box left of or above it,
or the text above it. A field next to a slider has the slider's name. A unit right of the field is
added after a comma, as in "Threshold, dB FS [ -80 ... -20 ]". A caption that is a single character,
as in the replacements of characters not allowed in file names, is read by NVDA's name for it, such as
"colon".

A field or list without any caption on the screen is named by the application's own word for it, in
its language, where it has one: Profile on the output panels of the Audio Converter and Audio CD
Ripper tabs and in Edit profiles; Source drive and Read speed on the Audio CD Ripper tab and in Drive
settings, Disc writer and Write speed on the Disc Burner tab; Files, Metadata, Name, Value and Cover Art
in the metadata editor; the file name template and the preview in Filename preview; Tracklist in the
results of Search for CD metadata. Otherwise it gets a name of this add-on: Categories for the pages of
Settings, Templates for the template history, Picture type in the metadata editor, Release code and
Results in the manual search of metadata. Fields not named in either way stay without a name.

The format and the codec's parameters on the output panels get short names of this add-on, all of
them, whichever format is chosen: Format, Extension, and for each parameter by what it offers, Rate
(sample rate), Bitrate, Channels, Bits (bit depth), Mode (VBR, CBR) and Level for any other, such as
the compression level of FLAC.

### Buttons

Buttons that show only an image are named: Browse next to the output folder and next to the sound file
in Settings, Filename preview next to the file name template, Move up and Move down in Edit profiles.
The tag button in Filename preview that inserts a space is named by NVDA's word for the space. The
check box without a caption in DSP is named by the mode chosen right of it, such as Gain.

Buttons and check boxes whose caption repeats in the window get the caption of their row after a
comma: "Search, Barcode" in the manual search of metadata, "Keep aspect ratio, Resize embedded Cover
Art" in Options, "Add, Name" and "Delete, 6 metadata fields" in the metadata editor, and the Cancel
button of each service with what the service is doing while metadata is downloaded. The buttons of
Options that show the size of the cover art are named the same way: "500x500, Resize embedded Cover
Art".

### Lists in dialogs

When a list such as the template history in Filename preview, the metadata services in Settings or the
cover art in the metadata editor gets focus, its item is read once, not twice.

### Text of dialogs

The windows of the application other than the main window and the conversion window are reported as
dialogs. When one opens, NVDA reads its text from the screen, as in other Windows dialogs: in About,
the version, the home page and the copyright; in Encoder information, the encoder and its module.
NVDA+B reads it again. Captions of fields, headings of sections, the numbers of slider scales and a
line repeating the title are not part of the text, so Settings, Options, DSP and Edit profiles open with their name alone.

## Commands

Commands of this add-on are listed in NVDA's Input Gestures dialog, under the
"EZ CD Audio Converter" category, and can be reassigned there.

## Licence

GPL v2. See COPYING.txt for the full text.
