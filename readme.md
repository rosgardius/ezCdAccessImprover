# EZ CD Audio Converter Access Improver

Improves accessibility of EZ CD Audio Converter with NVDA.

* Author: Rosgardius
* NVDA compatibility: 2026.1 to 2026.2

## Features

### Top buttons of the converter and ripper tabs

The large buttons at the top of the Audio Converter and Audio CD Ripper tabs (Convert, Rip CD,
Settings, View and the others) are read as buttons of a toolbar, including whether they are
unavailable. Convert and Rip CD report their shortcut, F8.

* The panel is one stop in the Tab order: Tab from the last control of the tab, or Shift+Tab from
  the tab labels, moves to it. Focus comes to the button that had it last, or to Convert or Rip CD
  after the application starts.
* Left and Right Arrow move between the buttons, Home and End to the first and the last one.
* Enter, Numpad Enter and Space press the focused button.
* The buttons that open a menu (Audio Converter, CD Ripper, Disc, Metadata, View and Help) are
  reported as menu buttons. Enter, Space or Down Arrow opens the menu; Escape closes it and returns
  to the button.
* To press a button without focusing it, move the navigator object to it and press NVDA+Numpad Enter.

## Commands

Commands of this add-on are listed in NVDA's Input Gestures dialog, under the
"EZ CD Audio Converter" category, and can be reassigned there.

## Licence

GPL v2. See COPYING.txt for the full text.
