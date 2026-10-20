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

## Commands

Commands of this add-on are listed in NVDA's Input Gestures dialog, under the
"EZ CD Audio Converter" category, and can be reassigned there.

## Licence

GPL v2. See COPYING.txt for the full text.
