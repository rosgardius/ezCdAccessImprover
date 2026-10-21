# EZ CD Audio Converter: UI facts the add-on relies on

Checked with EZ CD Audio Converter 13.2.1.1 (x64). An update of the application may change image
numbers or layout; recheck this file then.

## Framework

The application is built with Embarcadero C++Builder (VCL). Controls are windows of VCL classes
(`TMainform`, `TPageControl`, `TTabSheet`, `TPanel`, `TToolBar`, …). The main window has three tabs:
Audio CD Ripper, Audio Converter and Disc Burner.

Not usable to recognise a control: window handles, `GWL_ID` (equal to the handle for VCL windows),
window text of toolbars (a copied design-time caption such as `ToolBar9`, repeated across toolbars),
absolute coordinates, captions in a particular language.

## Top panels of the main window's tabs

- The panel is a `TPanel` that is a direct child of the tab's `TTabSheet`. Each large button on it
  is a `TToolBar` window holding one `TToolButton`, except Erase Disc, Burn Disc Image and Save to ISO
  of the Disc Burner tab, which share one toolbar.
- `TToolBar` is a superclassed comctl32 toolbar: `TB_*` messages work, and the MSAA toolbar proxy
  exposes button *i* as child id *i* + 1 of the window (role button, name = caption, state always 0,
  not focusable). The MSAA location of the button is scaled wrongly at DPI above 100%.
- `TB_GETBUTTON` `iBitmap` equals `ImageIndex` of the `TToolButton`. Images on the top panels, from
  left to right (repeated across panels and, on the Disc Burner panel, within it: its Settings comes
  from another image list):

  | Converter | Image | Ripper | Image | Burner | Image |
  |---|---|---|---|---|---|
  | Audio Converter ▼ | 0 | CD Ripper ▼ | 1 | Disc Burner ▼ | 2 |
  | Metadata ▼ | 4 | Disc ▼ | 3 | Erase Disc | 8 |
  | Rename files | 6 | Metadata ▼ | 4 | Burn Disc Image | 9 |
  | Save metadata | 7 | AutoRip | 5 | Save to ISO | 11 |
  | **Convert** | **1** | **Rip CD** | **0** | **Burn Disc** | **13, 14** |
  | Settings | 2 | Settings | 2 | Settings | 2 |
  | View | 15 | View | 15 | View | 15 |
  | Help | 19 | Help | 19 | Help | 19 |

- The main button of a tab is recognised by its image together with its caption, which must equal
  the string in one of the language files: Convert is image 1 with string `[232]` or `[406]`, Rip CD
  is image 0 with string `[176]`, Burn Disc is image 13 or 14 with string `[239]`, `[391]` or `[392]`.
  No translation of these strings has a `▼`, so the menu buttons with the same images never match.
- Burn Disc changes with the page of the Disc Burner tab: on Audio CD it is image 13 captioned Burn CD
  (`[239]`), on MP3 Disc and Data disc image 14 captioned Burn disc (`[392]`). After the language is
  switched in the running application, the caption is `[392]` until the page changes. In Russian,
  `[239]` and `[392]` are the same. Burn DVD (`[391]`) was not seen without a DVD drive.
- The first button of each panel opens a menu of the three tabs. Choosing a tab there, the current one
  too, puts focus on the tab's first control (the list of files or tracks, the burner's inner tab labels).
  The ripper and burner tabs open without a disc drive.
- Hidden buttons have `TBSTATE_HIDDEN` in `fsState` (Save to ISO on the Disc Burner panel, without a disc).
- Disabled buttons lack `TBSTATE_ENABLED` in `fsState`.
- The buttons marked ▼ in the caption, and View and Help, open a menu (`DropdownMenu`): converter
  images 0, 4, 15, 19, ripper images 1, 3, 4, 15, 19, burner images 2 (the first of them), 15, 19. Nothing in the toolbar or MSAA tells them
  from other buttons: `fsStyle` is `TBSTYLE_AUTOSIZE` on all of them, without `TBSTYLE_DROPDOWN`.
  The menu opens on the mouse press, in a modal menu loop; the posted click opens it all the same,
  and Escape returns focus to the toolbar.
- Pressing: a posted `WM_LBUTTONDOWN`/`WM_LBUTTONUP` pair at the centre of `TB_GETITEMRECT`, in the
  toolbar's client coordinates, presses the button (no DPI conversion needed). The proxy's
  `accDoDefaultAction` and `WM_COMMAND` to the parent do nothing.
- `SetFocus` on the toolbar window (with the calling thread attached to ezcd's input) makes it VCL's
  active control. Tab then moves on to the tab labels (`TPageControl`), Shift+Tab to the last control
  of the tab. The toolbar does nothing on Enter or Space itself.
- The toolbars are not tab stops. The top panel is last in its tab's tab order, and the page control is
  first in the form's, so Tab from the last control of a tab goes to the tab labels, and Shift+Tab
  from the tab labels goes to the last control of the active tab.
- Up and Down Arrow on a toolbar move focus through the panel's toolbars in tab order, wrapping
  around (VCL's form dialog-key handling), not in visual order.
- The MSAA proxy reports the button's position within its own toolbar (1 of 1 for most of them).
- Pressing Alt on a focused toolbar fires a focus event for the toolbar again before the system menu
  item gets focus.
- When a toolbar window gets focus, the proxy fires focus for the window and then for its first
  button: VCL keeps no current button within a toolbar.

## Tabs of the main window

- The main window's `TPageControl` is a direct child of `TMainform`; each tab is a `TTabSheet` child of
  it, the active one visible. The Disc Burner tab holds another `TPageControl`.
- MSAA gives `TTabSheet` the property page role. NVDA treats it as a dialog and, on every focus entry
  into the tab, collects dialog text from all its panels: about 250 ms in the main window, with an
  empty result.

## Lists of files

- The lists of files and tracks are `TVirtualStringTree` windows (VirtualTrees) with their own MSAA
  implementation: the tree and its focused node, nothing else. Without a focused node the item has no
  name, also while the list has files.
- The name of the item is the text of the visible columns that have text, `value; header: value; …` in
  column order; its description repeats the name without the first column, the file name.
- When the focused node changes, the tree fires name change, value change, state change, selection and
  focus, all on (tree window, `OBJID_CLIENT`, 0). The focus event comes last. A change of the focused
  node's text alone, such as the progress in the conversion window, fires nothing.
- The tree's own name is not translated: List of files on the converter tab, List of tracks on the CD
  Ripper tab, its class name CDW_VirtualStringTree on the Audio CD page of the Disc Burner tab, Format in
  the conversion window. String `[494]` of the language files is Files. The converter's tab page is a
  `TTabSheet` captioned with string `[9]` (Convert audio files).
- Dialogs (metadata editor, Edit profiles, Settings, …) use the same tree for their lists. Unless ezcd
  gives it a name (Path in the overwrite prompt), its MSAA name is the component name, such as
  VirtualStringTree1.
- The tree may fire the name change of its focused node on another object than the one NVDA has as the
  focus, so NVDA says nothing for the first moves after the list gets focus.
- MSAA tells nothing about the selection: the focused node's state is the same whether it is selected or
  not, and no event comes when only the selection changes.
- The tree answers `TVM_GETNEXTITEM` (`TVGN_ROOT`, `NEXT`, `PARENT`, `CHILD`, `FIRSTVISIBLE`,
  `NEXTVISIBLE`, `PREVIOUSVISIBLE`, `LASTVISIBLE`, `CARET`) with node pointers, and `TVM_GETITEMW` with
  `TVIS_SELECTED` and `TVIS_FOCUSED` for a node pointer. It does not check the pointer: a stale one may
  crash ezcd.
- `accSelect` on the tree's client object works with the node's position among all nodes in the tree's
  order (each node followed by its children) as the child id, 0 being the first node:
  `SELFLAG_TAKEFOCUS` moves the focus without changing the selection, `SELFLAG_ADDSELECTION` and
  `SELFLAG_REMOVESELECTION` change one node, `SELFLAG_TAKESELECTION` selects only the node. The
  metadata fields follow these changes.
- In the main window's list a folder added to the list is a node with the files as its children.
  Selecting the folder's node alone selects no files: the metadata fields stay disabled.
- Keys of the main window's list: Up, Down, Home, End, Page Up and Page Down select only the node they
  move to, with Shift they extend the selection, with Control they scroll without moving the focus.
  Control+A selects all nodes. Space and Control+Space do nothing.
- `TVM_GETITEMW` with `TVIF_TEXT` gives an empty text.

### Cell editing in the main window's list

- The cell editor is a `TVTEdit` child window of the tree (`ES_MULTILINE`), created anew for each
  cell and spanning it. Its text is read with `WM_GETTEXT`; when it opens, the whole text is selected.
  While it is open, the tree still fires focus for its focused node.
- The tree keeps a focused column and does not tell which one it is. Left and Right Arrow on a file
  move it to the neighbouring column, only while no editor is open, and open the editor in it if the
  column can be edited. A key press sent with `SendMessageTimeout` returns once the editor exists and
  has the focus (25–35 ms); without an editor, in 1–5 ms. At the end of the row the key does nothing.
  Once a column other than the file name has been focused, the tree also opens the editor in it when
  its focus moves with Shift and the arrow keys, Home, End, Page Up and Page Down, or by `accSelect`.
- F2 opens the editor in the focused column; if that column cannot be edited, in the column edited
  last, leaving the focused one where it is.
- In the editor: Enter keeps the text and closes it; Escape discards the text and closes it, the
  focused column stays (Escape posted to the editor does the same); Up and Down Arrow keep the text and
  open the editor in the same column of the previous or next file, wrapping around at the ends; Tab and
  Shift+Tab do the same as Down and Up.
- Also in the editor (ezcd's own navigation, since 9.5.1): Alt+Left and Alt+Right keep the text and
  move the editor to the previous or next column that can be edited, passing Lyrics by and going round
  within the file (from the last column to the first one and back); Alt+Up and Alt+Down move to the
  previous or next file. Alt+Home and Alt+End do nothing. ezcd checks the real state of Alt: a
  `WM_SYSKEYDOWN` sent or posted to the editor or the tree does nothing. With Alt marked down in the
  shared key state the key works, but asynchronously: the editor closes, focus goes to the main form,
  and the next editor opens about 25 ms after the key returns.
- Not editable in the list: the file name, Rating, Compilation and the Info columns (Length, Format,
  Bit rate, …).
- The Lyrics column (caption `[474]`) opens the modal `TLyricsEditor` dialog in the tree's handling of
  the key that focuses the column, so a key sent to the tree does not return while the dialog is open.
  While the Lyrics column is focused, moving to another file opens the dialog too. After the dialog
  closes, the focused column is the one before it or still the Lyrics column, depending on how it was
  closed. With all columns shown, Lyrics is the last metadata column; the Info and EBU R 128 |
  ReplayGain columns follow.
- A key that moves the focused column while that column is scrolled partly out of view only scrolls
  it back into view and opens the editor in it again. `WM_HSCROLL` with `SB_LINELEFT`/`SB_LINERIGHT`
  scrolls by 20 pixels, taking up to 20 ms each.
- An editor's window is destroyed when it closes; its handle is soon given to a new editor.
- Moving the editor to another file takes ezcd about 130 ms. On keys held down, focus goes for a moment
  to the main form or to the tree, with the tree's object of any role, between one editor and the next;
  keys that come in between are lost on Up and Down Arrow. Alt+Up and Alt+Down are all handled, the
  editor arriving up to a few seconds after the last key.
- The column header is painted in the tree's non-client area and has no window. The display model has
  each caption a few pixels right of its column's left edge; a caption at the edge of the view is cut
  off. The tree has a standard horizontal scroll bar: `GetScrollInfo` works from another process, its
  position is in the same units as the display model's coordinates, and `WM_HSCROLL` with
  `SB_PAGELEFT`/`SB_PAGERIGHT` scrolls without moving the focus. After a scroll the header is in the
  display model once the frame is painted again (`RedrawWindow` with `RDW_FRAME`).

## Metadata fields

- The metadata panel below the list of files on the Audio Converter tab, and the same panel on the
  Audio CD Ripper tab, is a `TPanel` holding `TEdit` fields, a `TMemo` for the comment, a `TCheckBox`
  for Compilation and the cover art, a `TDropPanel`. No other form has a `TDropPanel`.
- The fields have no MSAA names. Their captions are `TLabel`s without windows, left of each field,
  visible only in the display model of the panel. The layout depends on which fields are chosen in the
  application's settings: the fields not shown stay in the panel as hidden windows, among the shown
  ones, and the design-time positions do not hold.
- The total right of the track number and of the disc number is captioned only by a "/" label between
  the two fields.
- The captions are strings `[588]`–`[603]`, `[608]`, `[609]`, `[900]`–`[906]` and `[934]`–`[936]`
  with a colon, Number being `[590]` and Disc number `[598]`. Short captions are the same in several
  languages: Number in Russian, Bulgarian and Ukrainian, in English and Estonian. Strings `[801]` and
  `[503]` are the totals as placeholders of the file name pattern (`<Total Tracks>`, `<Total Discs>`).
- The `TDropPanel`'s window text is the localized Cover Art (string `[349]`); MSAA gives it no name.
  It is not a tab stop. Under it, a label without a window shows the format, size and file size of
  the cover (`JPEG | 250x250 | 49.95 kB`), and nothing without a cover.
- The CD-Text fields of the Disc Burner tab are two `TEdit`s in a `TPanel` under the list of tracks,
  on the Audio CD page of the tab's own page control, captioned by labels without windows left of them.
- With the fields disabled (no file selected, no disc in the ripper), the captions are still drawn.

## Captions in all windows

- No `TLabel` of the application has `FocusControl`, so MSAA gives no field, list, combo box or
  slider a name from its caption. The labels have no windows; their text is in the display model of
  the control's parent, together with the captions of `TSpeedButton`s, such as the "-" and "+" of a
  counter.
- A setting is laid out on one line: a caption, a check box or a radio button, then the control,
  then a unit (`s`, `dB FS`, `seconds`). Text between two windows on a line lies next to the window
  it belongs to. A field showing a slider's value lies right next to the slider (3–4 pixels), and so
  does a second combo box of one setting; separate settings on a line are tens of pixels apart.
- Some controls are captioned only by a check box above them: the fade and silence sliders of the DSP
  dialog, the sound file in General settings, the file name pattern on the Audio Converter tab.
- The scales of sliders are numbers drawn as labels above and below them (`-30 … -6`, `0 … 10`).
- The Filename preview dialog has a one-line explanation of the template syntax above its list of
  templates, longer than any caption.
- The fields replacing characters on the File name settings page are captioned only by the character
  (`/ : * ? " < > |`), which NVDA does not say at its default punctuation level for most of them.

## List boxes and list views

- When a `TListBox`, `TCheckListBox` or `TListView` gets focus, it fires focus on the list (child 0)
  and 1–10 ms later on its focused item. NVDA takes the first event for the focused item already, so
  without the add-on the item is said twice.
- Without a selection, the first arrow key in a `TCheckListBox` (metadata services in the settings)
  selects the focused item and fires focus on it again.

## Conversion window

- A top-level `TConvertWnd` window, shown while files are converted and kept open after the end.
  Its caption is string `[476]` (Converting files).
  The application also has `TConvertWnd_Single`, of the same layout but with one converter bar in a
  `TPanel` right on the form. It did not appear with one converter, one file or a loudness scan, so
  when it is used is not known.
- Progress bars are `TProgressBar` windows with a range of 0 to 10000, each updated several times a
  second. One bar per converter, in a `TGridPanel` child of the form. The total bar is in the summary
  `TPanel`, inside the `TPanel` that also holds the file list.
- The labels of the summary panel (Total, Converted, Speed, …) are `TLabel`s without windows,
  visible only in the display model; the total bar has no MSAA name.
- The summary panel is a `TPanel` holding the total bar. Its labels keep their design-time positions
  scaled by the window's DPI / 96, while the bar and the percentage right of it stretch with the window.
  In design units, the bar is at top 16 with the percentage right of it; below are three rows (tops 37,
  53, 69) of label and value pairs, labels at left 0, 264, 528 and values at 128, 384, 648:
  Converted, Elapsed, Threads; Errors, Remaining, CPU; Skipped, Speed, Average CPU.
- When a value changes, ezcd fills the background of the whole panel and draws only the changed labels
  again. NVDA's display model clears the whole filled rectangle regardless of clipping, so it holds only
  the last changed values. `RedrawWindow` with `RDW_INVALIDATE | RDW_UPDATENOW` on the panel makes ezcd
  draw all of them; it took 4–80 ms during a conversion.
- While paused, the Pause button reads Resume (language string `[145]`). After the end, Pause is
  disabled and Cancel reads Close.

### Number of converters

- The only `TEdit` of `TConvertWnd` (none in `TConvertWnd_Single`), in a `TPanel` under the file list.
  It is read-only and in the tab order after the file list. Its text must be read with `WM_GETTEXT`: the
  window text Windows keeps for it is not updated. The edit has no MSAA name.
- The "-" and "+" buttons are `TSpeedButton`s without windows, 23 × 23 design units, 3 units left and
  right of the edit, level with its top, scaled by the window's DPI / 96. Their DFM `Left` does not hold
  at runtime: the localized caption left of them is longer. The caption is a `TLabel`, visible only
  in the display model.
- A `WM_LBUTTONDOWN`/`WM_LBUTTONUP` pair to the panel at the centre of a button presses it, posted or
  sent; a sent pair returns once the number has changed. The number goes down to 1 and up to at least 37.
- While converting, ezcd's window thread answers messages 5–360 ms late, and stops answering for up to
  seconds while it starts or stops converters. Paused or finished, it answers in a few milliseconds.

## Keyboard

- F8 presses Convert or Rip CD, depending on the current tab. The hint text (`Convert [ F8 ]`) is not
  translated. Burn Disc has no such hint; without a disc drive neither F8 nor Burn Disc does anything
  noticeable, so whether F8 presses it is not known.
- Shift+F10 opens the registration key dialog.

## Language files

- `Language\*.uni` next to `ezcd.exe`: UTF-16 with BOM, each entry is a `[N]` line followed by the
  text line.
- The active language is `HKCU\Software\Poikosoft\EZ CD Audio Converter`, value `k82`, equal to
  string `[0]` of the active file. When the language is switched in the running application, the
  captions change at once but `k82` keeps the old value, so it cannot tell the current language.
