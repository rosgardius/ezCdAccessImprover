# EZ CD Audio Converter Access Improver

**The code of this add-on was written entirely by AI**, and tested by the author with NVDA. If you don't
trust software made by AI or don't want to use it, please don't install this add-on, or remove it.

Improves accessibility of EZ CD Audio Converter with NVDA.

* Author: Rosgardius
* NVDA compatibility: 2026.1 to 2026.2
* EZ CD Audio Converter compatibility: 13.2.1 or later

## Features

* [Top buttons](#top-buttons): the large buttons of every tab are one toolbar, with arrows between the
  buttons and menus opened from the keyboard.
* [Toolbars and the CD player](#toolbars-and-the-cd-player): the small toolbars of the file explorer and
  the drive tray, and the player of the CD Ripper, are reachable with Tab.
* [File explorer](#file-explorer): a path can be typed into the path bar; going to a folder reports it
  and the number of its items.
* [Disc Burner pages](#disc-burner-pages): Audio CD, MP3 disc and Data disc switch from the keyboard.
* [Lists of files](#lists-of-files): files are selected with the keys of other Windows lists.
* [Editing metadata in the list](#editing-metadata-in-the-list): metadata are edited cell by cell right in
  the list of files.
* [Cover art and rating](#cover-art-and-rating): the cover art has a menu, and the rating is a slider.
* [Names of controls](#names-of-controls): fields and buttons without names get them, in the language of
  EZ CD.
* [Buttons without windows](#buttons-without-windows): buttons and links that EZ CD only draws can be
  pressed through object navigation.
* [Filename preview](#filename-preview): tags are inserted into the template from the keyboard.
* [Settings](#settings): metadata services are reordered with Alt+Up and Alt+Down Arrow.
* [Conversion window](#conversion-window): NVDA+End reports the state of the conversion; the number of
  converters changes with the arrows.
* [Dialogs and menus](#dialogs-and-menus): Tab follows the screen in Options and DSP, and menus open with
  the first item selected.

### Top buttons

The large buttons at the top of the Audio Converter, Audio CD Ripper and Disc Burner tabs (Convert, Rip
CD, Burn Disc, Settings, View and the others) are a toolbar.

* It is one Tab stop: Tab from the last control of the tab, or Shift+Tab from the tab labels. Focus comes
  back to the button that had it last.
* Left and Right Arrow move between the buttons, Home and End to the first and the last one.
* Enter or Space presses the button. On a menu button, such as Disc, Metadata, View or Help, Enter, Space
  or Down Arrow opens the menu.
* The tab labels do not switch the tab. Use the menu of the first button (Audio Converter, CD Ripper or
  Disc Burner); after it, focus is on the first button of the new tab.
* On Save metadata, Applications or Shift+F10 opens its menu: Save modified files and Save all files.
* Convert and Rip CD report their shortcut, F8.

### Toolbars and the CD player

These toolbars are Tab stops, and their buttons are named by EZ CD's own hints:

* The navigation toolbar of the file explorer (View Explorer, Add files, Add folder, Go to Computer, Go to
  Music, Back, Forward, Go up), right before the path bar.
* View of the file explorer, right before the filter of file types, or at the end of the tab on the MP3
  disc and Data disc pages. Enter, Space or Down Arrow opens its menu: List, Details, Icons, Large icons.
* With the explorer hidden, the toolbar in its place (View Explorer, Add files, Add folder and, on the
  Audio Converter tab, Select all, Remove all, Create M3U playlist), right before the list of files.
* The drive tray of the Audio CD Ripper and Disc Burner tabs (Open tray, Close tray, Drive settings),
  right after the speed.
* The player of the Audio CD Ripper tab (Previous track, Rewind, Play, Forward, Next track, Stop, Pause),
  right before Options, followed by Volume and Position, read in percent.

The keys are those of the top buttons. View Explorer is a toggle: it moves focus to View Explorer in the
other toolbar, so pressing it again brings the explorer back. After Open tray, focus moves to Close tray
once EZ CD shows it, and the other way round.

### File explorer

* Going to another folder (Enter on a folder, Backspace) reports the folder and the number of its items.
* The path bar is the button Path, read with the current folder. Enter or Space opens a field for typing
  a path; Enter goes there, Escape cancels. Up and Down Arrow in the field go through the address history
  of Windows' File Explorer. For a path that does not exist, focus stays in the field.
* The list of folders that a click on the arrow after a folder of the path opens is an ordinary list:
  Enter goes to the folder, Escape closes the list.

### Disc Burner pages

EZ CD switches the pages of the Disc Burner tab (Audio CD, MP3 disc, Data disc) only with the mouse.

* The Tab stop right before the list of files is a page tab, such as "MP3 disc, tab, 2 of 3". Left and
  Right Arrow, Home and End switch the page.
* Control+Tab and Control+Shift+Tab switch the page from anywhere on the tab. From the list of files,
  focus moves to the list of the new page.

### Lists of files

In the list of files of the main window, a file that is not selected is reported as "not selected".

* Arrows, Home, End, Page Up and Page Down select only the file they move to; with Shift they extend the
  selection. Control with Up Arrow, Down Arrow, Home or End moves without changing it.
* Right Arrow expands a folder or moves to its first file; Left Arrow collapses a folder or moves from
  a file to its folder.
* Space selects only the focused file, Control+Space adds it to the selection or removes it. On a folder,
  both act on all its files.
* Control+A selects all files, Escape none. With no file selected, the metadata fields below the list
  are unavailable.

On the Disc Burner tab, the first item of the list is the disc itself, read as "Disc" and its label.

### Editing metadata in the list

The list of files of the main window is a table whose columns (Track artist, Title, Album, …) can be
edited in place.

* F2 opens the field of the focused file in the column last used and reports the column and the value.
  The value is selected, so typing replaces it.
* Tab and Shift+Tab move to the next and the previous column, keeping what was typed. Columns that
  cannot be edited are skipped; at the first and the last one, the same column is reported again.
* Alt+Home and Alt+End move to the first and the last column; the last is the one before Lyrics.
* Up and Down Arrow move to the same column of the previous and the next file, going round at the ends.
* Tab to the Lyrics column opens the Lyrics dialog; when it closes, focus is back in the field.
* Enter keeps the change, Escape discards it.
* NVDA+Tab reports the column, the file name and the value.

EZ CD's own keys work too: Alt+Up and Alt+Down Arrow as Up and Down Arrow; Alt+Left and Alt+Right Arrow
as Shift+Tab and Tab, but going round within the file and passing Lyrics without opening it. So Alt+Left
from the first column goes straight to the last one.

### Cover art and rating

* The cover art left of the metadata fields is a Tab stop right before the first field, read with the
  format and size of the picture, such as "Cover Art, JPEG | 250x250 | 49.95 kB". Applications or
  Shift+F10 opens its menu: View, Load, Download, Save as, Resize, Cut, Copy, Paste, Clear. The same keys
  work in the window that View opens; Escape closes it.
* When the mouse pointer rests on the cover art, EZ CD shows a panel of buttons over it, which keeps
  coming back. Escape closes it and moves the pointer away.
* The rating is a slider right before the field below it, such as "Rating, slider, 3 of 5". Right and Up
  Arrow add a star, Left and Down Arrow take one away, Home sets none and End all five.

### Names of controls

Fields, lists, sliders and buttons that EZ CD leaves without a name get one, in all its windows. The
names are in the language of EZ CD where this add-on has a translation for it, otherwise in English.

* Most are named by their captions on the screen, with the unit after a comma: "Threshold, dB FS [ -80
  ... -20 ]". The rest get EZ CD's own word for them, or a name of this add-on.
* A slider and the field next to it showing its value are one control, and the slider says the value as
  the field shows it: "Fade In, s, slider, 3.00".
* Buttons with only an image are named: Browse, Filename preview, Move up, Move down.
* Buttons whose caption repeats in the window get the caption of their row: "Search, Barcode".
* The format and the codec's settings on the output panels have short names: Format, Extension, Rate,
  Bitrate, Channels, Bits, Mode, Level.
* A caption of one sign is read by name, such as "colon" or "backslash".

### Buttons without windows

Some buttons and links EZ CD only draws, so NVDA would not find them. In object navigation they are among
the other controls of their panel, in screen order, and NVDA+Numpad Enter presses them. They are not Tab
stops; most of them have keys of their own, described above.

* Encoder information, right of the format on the output panels.
* The links of About: the home pages of EZ CD and of Fraunhofer.
* Move up and Move down of the metadata services in Settings.
* The Decrease and Increase buttons of the number fields.
* The page buttons of the Disc Burner tab and the Filename generation gear of Filename preview.
* On the Audio CD Ripper tab, the captions of the metadata fields that can be clicked, and Quiet and Loud
  of the player's volume.

### Filename preview

* Tab goes round in screen order: template, Add, Filename generation, the tags, template history,
  preview, Close.
* Filename generation, the gear right of Add, opens Settings at the Filename generation page.
* All 27 tags are one Tab stop. Left and Right Arrow move along a row, Up and Down Arrow between rows,
  Home and End to the ends of the row.
* Enter or Space inserts the tag at the cursor of the template and reads the new template. Focus stays
  on the tag, so a template can be put together tag by tag.
* Alt+Down Arrow on Year, Disc Number, Total Discs, Total Tracks, Number or Sequence opens its variants,
  such as Number ## for two digits.
* EZ CD keeps a changed template even when the window is closed with Escape.

### Settings

* The numbers of parallel converters and scanners and the limit of metadata results per service are
  spin boxes: Up and Down Arrow change the number and report it.
* In the list of metadata services, Space checks or unchecks a service, and Alt+Up and Alt+Down Arrow
  move it up and down, reporting its new position.

### Conversion window

* Only the total progress is reported, as NVDA's progress bar settings say.
* NVDA+End (NVDA+Shift+End in the laptop layout) reports the state: the total percentage, the converted
  files, the remaining time and the speed, and errors and skipped files if any. A paused or finished
  conversion starts with "Paused" or "Finished".
* The number of converters is a spin box: Up and Down Arrow add and remove a converter, also while
  converting.

### Dialogs and menus

* In Options of the Audio Converter and Audio CD Ripper tabs and in DSP, Tab and Shift+Tab go in screen
  order, row by row from left to right, instead of jumping between sections. In Options, the section
  (Files, Metadata, Cover Art, …) is reported on entering it.
* Encoder information and the results of Search for CD metadata close with Escape.
* Menus opened by a button, by Applications or by Alt+Down Arrow open with the first item selected, so
  Enter chooses it at once.

## Known limitations

* The tray buttons and the player have not been tried with a disc drive; please report what does not
  work.
* Moving the field of the list takes EZ CD about a fifth of a second per file, and up to a second for
  Alt+Home and Alt+End with many columns. Held Up or Down Arrow move fewer files than the key repeats.
  NVDA is silent while the Lyrics dialog opens.

## Keys

| Where | Keys | Does |
|---|---|---|
| Top buttons and toolbars | Left and Right Arrow, Home, End | Move between the buttons |
| Menu button, View | Enter, Space, Down Arrow | Open the menu |
| Save metadata, cover art | Applications, Shift+F10 | Open its menu |
| Panel over the cover art | Escape | Close it |
| Path | Enter, Space | Open the field for a path |
| Field of Path | Up and Down Arrow | Go through the address history |
| Disc Burner tab | Control+Tab, Control+Shift+Tab | Next and previous page |
| Page tab of Disc Burner | Left and Right Arrow, Home, End | Switch the page |
| List of files | Space; Control+Space | Select only this file; add it to the selection or remove it |
| List of files | Control with Up Arrow, Down Arrow, Home, End | Move without changing the selection |
| List of files | F2 | Edit the file's metadata |
| Field of the list | Tab, Shift+Tab | Next and previous column |
| Field of the list | Alt+Home, Alt+End | First and last column |
| Field of the list | Up and Down Arrow | Same column of the previous and the next file |
| Field of the list | Alt+Left and Alt+Right Arrow | Previous and next column, going round |
| Rating | Arrows, Home, End | Add or take away stars |
| Tags of Filename preview | Enter, Space | Insert the tag |
| Tags of Filename preview | Alt+Down Arrow | Open the tag's variants |
| Metadata services in Settings | Alt+Up and Alt+Down Arrow | Move the service |
| Number fields | Up and Down Arrow | Change the number |
| Conversion window | NVDA+End | Report the state of the conversion |
| Encoder information, results of Search for CD metadata | Escape | Close the window |

## Licence

GPL v2. See COPYING.txt for the full text.
