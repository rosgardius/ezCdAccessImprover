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
  | **Convert** | **1** | **Rip CD** | **0** | **Burn Disc** | **10, 13, 14** |
  | Settings | 2 | Settings | 2 | Settings | 2 |
  | View | 15 | View | 15 | View | 15 |
  | Help | 19 | Help | 19 | Help | 19 |

- The main button of a tab is recognised by its image together with its caption, which must equal
  the string in one of the language files: Convert is image 1 with string `[232]` or `[406]`, Rip CD
  is image 0 with string `[176]`, Burn Disc is image 10, 13 or 14 with string `[239]`, `[391]` or `[392]`.
  No translation of these strings has a `▼`, so the menu buttons with the same images never match.
- Burn Disc changes with the page of the Disc Burner tab: on Audio CD it is image 13 captioned Burn CD
  (`[239]`), on MP3 Disc image 14 and on Data disc image 10, both captioned Burn disc (`[392]`). After
  the language is switched in the running application, the caption is `[392]` until the page changes.
  In Russian, `[239]` and `[392]` are the same. Burn DVD (`[391]`) was not seen without a DVD drive.
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
- Save metadata (converter image 7) has a `PopupMenu`, the only top-panel button with one: Save
  modified files (`[686]`) and Save all files (`[687]`); the click of the button does not show it. A
  posted `WM_CONTEXTMENU` at the button's centre, in screen coordinates, opens it; with the point -1, -1
  of the Applications key, nothing opens.
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

## Toolbars of the explorer

- The file explorer of the Audio Converter and Disc Burner tabs has a row above its tree and list: a
  `TPanel` holding the navigation toolbar on the left, the breadcrumb bar (`TJamShellBreadCrumbBar`),
  the toolbar of the list's view and the filter of file types (`TComboBox`). No other panel has a
  breadcrumb bar. Hiding the explorer hides the row.
- The toolbars are not tab stops; Tab goes from the explorer's list to the filter and on to the
  breadcrumb bar. Their `TabOrder` is the view, the filter, the navigation, the breadcrumb bar on the
  Audio Converter tab, but the view, the navigation, the filter, the breadcrumb bar on the Disc Burner
  tab. With a toolbar made the active control by `SetFocus`, Tab and Shift+Tab go on by `TabOrder`, not
  by the screen.
- The buttons show only an image and have no text. Images: 29 View Explorer, 33 Add files, 32 Add
  folder, 25 Go to Computer, 26 Go to Music, 30 and 31 back and forward in history, 3 Go up; the Disc
  Burner tab has no Add files and Add folder. Their hints are strings `[704]`, `[327]`, `[328]`, `[489]`,
  `[490]`, `[701]`, `[702]`, `[703]`. Separators have `TBSTYLE_SEP` and their width as `iBitmap`.
- View Explorer shows and hides the explorer; while it is shown, the button has `TBSTATE_PRESSED`, and
  the MSAA proxy reports it pressed. On the Disc Burner tab, once the explorer was shown again with View
  Explorer in its place, the button above it is no longer pressed (`fsState` 0x4); which of the two is
  shown tells the state.
- The view's toolbar has one button (image 4), without hint, with `TBSTYLE_DROPDOWN` on a toolbar with
  `TBSTYLE_EX_DRAWDDARROWS`. A click on its body does nothing; a posted click on the arrow, the right
  end of `TB_GETITEMRECT`, opens the menu List `[227]`, Details `[228]`, Icons `[339]`, Large icons
  `[735]`, the current one radio-checked. The MSAA proxy gives the button an object of its own (split
  button, child id 0); focus events for it carry child id 1.
- Posted clicks take the toolbar's client coordinates as `TB_GETITEMRECT` gives them only from a
  DPI-aware process, such as NVDA; Windows scales the coordinates posted by a DPI-unaware one.
- After a navigation button is pressed, focus stays on the toolbar.
- While the explorer is hidden, a `TPanel` of toolbars alone takes the place of the row above it, a
  sibling of that row's panel: View Explorer (image 29, without caption) on a toolbar of its own, and a
  toolbar with captions (`ShowCaptions`): Add files..., Add folder..., on the Audio Converter tab also
  Select all, Remove all and Create M3U playlist. The first control below it is the list of files on the
  Audio Converter tab and the page control of the Disc Burner tab, each its tab's first Tab stop.
  Shown, it has the same top as the hidden row above the explorer. On the Disc Burner tab both rows are
  children of the tab, as is the top panel, of toolbars alone too, which lies above them.
- View Explorer hides the button that has the focus: when it hides the explorer, focus goes to the main
  form; when it shows the explorer, to the navigation toolbar above it.

## Breadcrumb bar and lists of the explorer

- The breadcrumb bar (`TJamShellBreadCrumbBar`) is a tab stop without a name; NVDA calls it a pane.
  Its window text is the path of a file system folder (`C:\Windows`) and is empty for a virtual one
  (This PC); the crumbs are drawn, the last one the current folder. A drop-down arrow is at its right
  end. A narrow bar cuts the last crumb to its first letters. The node selected in the explorer's tree is the
  current folder, also while View hides the tree.
- A click on the empty space of the bar shows its hidden combo box (`TBreadCrumbComboBox` holding a
  `ComboBox` and its `Edit`) over it, with the path selected in the edit and focus in it; F4, Enter,
  Space and letters on the bar do nothing. Enter in the edit goes to the typed path; a path that does not
  exist leaves the edit with the path selected and fires no event but the caret's. The edit opens with
  the current path, This PC too. Enter and Escape hide the combo box: focus goes to the main form, after
  going to a folder first to the explorer's tree, whose node of the folder is selected. Tab from the
  edit goes on as from the bar, Shift+Tab goes back to the bar.
- Whenever the explorer goes to another folder, the bar fires a name change (`OBJID_WINDOW`), and the
  list of the folder is filled some 50 ms later: names of its items change, with no focused item. Enter
  on a folder and Backspace in the list keep focus in the list; the tree fires focus for its new node,
  which NVDA ignores, as the tree has no focus.
- The arrow keys on the bar move focus to another window of its parent, as VCL does (Down Arrow to the
  view's toolbar).
- A click on the arrow right of a crumb opens a popup form (`TForm`, made the active window, so the
  main window leaves the foreground) of two list views: `TJamShellPopupMenu` with the folders in the
  crumb, shown, and `TJamShellOverflowListView`, hidden, presumably the crumbs the bar has no room for
  (not seen). Focus goes to the list without a focused item; Down Arrow focuses the first folder. The
  first column of an item is empty and its header Name; the folder is in the second column, without a
  header, which MSAA gives as the item's description. Escape closes the form, and Enter after going to
  the folder: focus goes back to the bar, and NVDA gets a focus event for the main form first, as it
  comes back to the foreground. A click on a crumb itself goes to its folder.
- The list of the edit's combo box is the address history of Windows' File Explorer (`TypedPaths` in
  the registry); the arrow keys in the edit go through it.
- The tree of folders (`TJamShellTree`) and the list of the folder (`TJamShellList`, a list view with a
  column header) have no caption; the language files have Folders `[380]`. The filter of file types is a
  `TComboBox` whose items are All audio files `[491]` and extensions (`*.flac`).
- The MSAA proxy counts the column header of a list view among its children, so NVDA's position of an
  item ("1 of 3" for two items) is one too many in `TJamShellList` and `TListView`.

## Toolbar of the drive's tray

- The drive, its speed and the toolbar of the tray lie in one `TPanel`, the toolbar at the end of the
  row: right of the speed on both tabs, with the drive left of the speed on the Audio CD Ripper tab and
  above it on the Disc Burner tab. No other panel holds a toolbar and two combo boxes.
- Buttons, without text: Open tray (image 8, hint `[191]`) and Close tray (image 7, hint `[192]`,
  hidden); on the Audio CD Ripper tab also a hidden separator and a gear (image 9) without a hint,
  whose purpose is not known. Without a disc drive the combo boxes and the buttons are disabled.
- Open tray and Close tray are two buttons of the same toolbar window, one of them hidden; they
  presumably take turns as the tray moves (not tried: no disc drive).
- The toolbar is not a tab stop, and Tab skips the disabled combo boxes: Tab goes from the tab labels
  to the list of tracks on the Audio CD Ripper tab, and from the breadcrumb bar to Options on the Disc
  Burner tab.
- On the MP3 disc and Data disc pages of the Disc Burner tab, Options (`Опции (1) »`, the button right of
  the tray) and the filter of file types are hidden. The filter stays hidden on Audio CD afterwards, until
  the explorer is hidden and shown again. Tab then goes from the breadcrumb bar to the tab labels.

## Player of the Audio CD Ripper tab

- Below the metadata panel, a `TPanel` (the only one with a `TTrackBar` and a `TMyTrackBar`): from the
  left, an empty `TPanel` (the time, presumably), a `TPanel` with the toolbar, the volume (`TTrackBar`,
  0–65535) between a quiet and a loud loudspeaker (`TImage`s, one `OnClick` handler for both), and the
  position in the track (`TMyTrackBar`). It is there without a disc, the buttons disabled; MSAA gives
  the sliders their position as a percentage of the range.
- The toolbar's seven buttons have neither text nor a hint MSAA gives; by image: 1 Previous track
  `[185]`, 2 Rewind `[186]`, 0 Play `[184]`, 3 Forward `[187]`, 4 Next track `[188]`, 5 Stop `[189]`,
  6 Pause `[190]` (their design-time hints). The volume has `[109]` Volume Control; the position no string.
- Neither the toolbar nor the sliders are Tab stops. Tab goes from Filename preview, the last control
  of the output panel above, to Options right of the player, which lie on its row. So it is with the
  metadata panel at the bottom; for Left and Right, see Layouts of the metadata panel.
- A click on the quiet loudspeaker without a disc changed nothing on the screen.

## Themes

- View on the top panel has Theme (`[813]`) ▸: Auto (`[836]`, the default, after the mode of Windows),
  Light (`[837]`), Dark (`[838]`), a separator, Light ▸ (Blue `[814]`, Titanium `[967]`, Windows) and
  Dark ▸ (Black `[976]`, Dark gray `[977]`). The tabs have their own View with other command IDs, but
  one setting. Choosing a variant changes the theme only while its mode is shown.
- Switching between light and dark makes all windows of the main form anew, with new handles: focus
  goes to the form, and the explorer forgets its history (Back is disabled).
- The dark themes are VCL styles. They add, over each scroll bar of a list, a tree or a scroll box, a
  window of class `TScrollingStyleHook.TScrollWindow` or `TVclStyleScrollBarsHook.TScrollWindow` that
  draws the bar; NVDA's simple review would stop at it as an unknown object. Names, states, captions,
  toolbars, menus and the dialogs read the same in every theme.

## Tabs of the main window

- The main window's `TPageControl` is a direct child of `TMainform`; each tab is a `TTabSheet` child of
  it, the active one visible. The Disc Burner tab holds another `TPageControl`. The order of the
  `TTabSheet` windows changes as the tabs are switched.
- The main window's `TPageControl` (the tab labels) is a Tab stop between the top panel and the tab's
  first control. MSAA gives it the tab control role without children; the arrow keys do nothing on it.
- MSAA gives `TTabSheet` the property page role. NVDA treats it as a dialog and, on every focus entry
  into the tab, collects dialog text from all its panels: about 250 ms in the main window, with an
  empty result.

## Pages of the Disc Burner tab

- The Disc Burner tab holds a `TPageControl` of three pages, Audio CD, MP3 disc and Data disc (strings
  `[470]`–`[472]`), with their tab labels hidden: the page control has no tab items, is a Tab stop
  without a name (NVDA says "tab"), and the arrow keys do nothing on it. Each page is a
  `TTabSheet` captioned with its string; the window of a page is made the first time it is shown.
- The pages are switched only by three `TPngSpeedButton`s without windows, captioned with the same
  strings, in the `TPanel` right above the page control (its bottom one pixel above the page control's
  top; it has no child windows): 100 × 24 design units, at left 3, 108 and 213, top 0, scaled by the
  window's DPI / 96, in the DFM; at runtime each is as wide as its caption (in Russian at 120 DPI 127,
  150 and 197 pixels, 5 apart, from 4). A posted click at a button's centre shows its page.
- ezcd handles the click in 0.2–0.55 s, sent messages and MSAA calls waiting meanwhile; the new page
  may be visible after the first 50 ms of it. With focus on the page control, focus stays there; with
  focus on a control of the old page, it goes to the first control of the new one (its list).

## Lists of files

- The lists of files and tracks are `TVirtualStringTree` windows (VirtualTrees) with their own MSAA
  implementation: the tree and its focused node, nothing else. Without a focused node the item has no
  name, also while the list has files, or, in some lists with nodes, VirtualTrees' default text Node
  (the MP3 disc and Data disc pages, Replace text on the Filename generation page of Settings).
- The name of the item is the text of the visible columns that have text, `value; header: value; …` in
  column order; its description repeats the name without the first column, the file name. An empty
  first column leaves `; ` in front, as in the result of Search for CD metadata without a match.
- When the focused node changes, the tree fires name change, value change, state change, selection and
  focus, all on (tree window, `OBJID_CLIENT`, 0). The focus event comes last. A change of the focused
  node's text alone, such as the progress in the conversion window, fires nothing.
- The tree's own name is not translated: List of files on the converter tab, List of tracks on the CD
  Ripper tab, its class name CDW_VirtualStringTree on the Audio CD page of the Disc Burner tab, Files to
  burn on the MP3 disc and Data disc pages, Format in the conversion window. The language files have
  Files `[494]`, Tracklist `[137]` and Filelist `[141]` (in Russian in small letters). The tabs are
  `TTabSheet`s captioned with strings `[172]` (Audio Converter) and `[171]` (Audio CD Ripper), in Russian
  the same as `[9]` and `[8]` (Convert audio files, Rip audio CDs), in English not; the lists
  of the burner's pages are children of the pages, those of the tabs lie in panels. The captions repeat
  across languages: Audio CD `[470]` is the same in Russian and Bulgarian.
- The lists of the MP3 disc and Data disc pages hold the disc as their only top-level node, captioned
  with its label (the date by default, `20261023`), also when empty. `accSelect` with
  `SELFLAG_TAKEFOCUS` on it opens the cell editor of the label; Down Arrow does not.
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
  Control+A selects all nodes. Space and Control+Space do nothing. Numpad Plus and Minus, also sent
  with `SendMessageTimeout`, expand and collapse the focused folder; `TVM_EXPAND` does nothing.
  `TVGN_CHILD` gives the first file of a collapsed folder too; `TVGN_PARENT` of a top-level node is 0.
- `TVM_GETITEMW` with `TVIF_TEXT` gives an empty text.

### Cell editing in the main window's list

- The cell editor is a `TVTEdit` child window of the tree (`ES_MULTILINE`), created anew for each
  cell and spanning it. Its text is read with `WM_GETTEXT`; when it opens, the whole text is selected.
  While it is open, the tree still fires focus for its focused node.
- The tree keeps a focused column and does not tell which one it is. Left and Right Arrow on a file,
  and on a folder too instead of collapsing and expanding it, move it to the neighbouring column, only while no editor is open, and open the editor in it if the
  column can be edited. A key press sent with `SendMessageTimeout` returns once the editor exists and
  has the focus (25–35 ms); without an editor, in 1–5 ms. At the end of the row the key does nothing.
  Once a column other than the file name has been focused, the tree also opens the editor in it when
  its focus moves with Shift and the arrow keys, Home, End, Page Up and Page Down, or by `accSelect`,
  and when it gets the keyboard focus after files were added (Tab from the tab labels).
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
- A folder's row has only its name; the tree opens an empty editor in its other cells too. When that
  editor is left with Down Arrow, ezcd's focus stays on the main form and no next editor opens.
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
- The `TDropPanel`'s window text is the localized Cover Art (string `[349]`); MSAA gives it no name
  (see Cover art and rating). Under it, a label without a window shows the format, size and file size of
  the cover (`JPEG | 250x250 | 49.95 kB`), and nothing without a cover.
- The CD-Text fields of the Disc Burner tab are two `TEdit`s in a `TPanel` under the list of tracks,
  on the Audio CD page of the tab's own page control, captioned by labels without windows left of them.
- With the fields disabled (no file selected, no disc in the ripper), the captions are still drawn.

### Layouts of the metadata panel

- View on the top panel (string `[346]`) has Metadata panel (`[682]`) ▸: Standard (`[939]`), Extended
  (`[940]`), a separator, Left (`[683]`), Right (`[684]`), Bottom (`[685]`, the default). The Audio
  Converter and Audio CD Ripper tabs each have their own View and their own setting. ezcd draws its menu items itself: with
  the submenu closed, its items have command IDs and check marks, but no texts.
- Extended adds Lyrics (a `TMemo`), Language, Producer, Engineer, Mixer, BPM, ISRC, Catalog number and
  UPC/EAN. The rating with its caption then stands between two columns of fields, on the line of Language,
  with no window between Language and the field left of the rating.
- Left and Right make the panel anew, with new windows: a `TPanel` holding a `TScrollBox` holding the
  `TPanel` of the fields, beside the list of files for the whole height of the tab (the explorer and the
  drive's row stay above the list). The fields are in one column under the cover art; the text with the
  size and format of the cover is left of it, word-wrapped. The panel of the fields is taller than the
  scroll box: the display model has no captions of the fields scrolled out of view, and after a scroll
  it may keep pieces of captions at their old places. Tab to a field scrolls it into view. The captions
  of the fields are `TLabel`s, readable from ezcd's memory with their positions (see Cover art and
  rating).
- The output panel then is under the list, its controls in another arrangement, and the player of the
  Audio CD Ripper tab under the output panel: outside the metadata panel, no Tab stop is right of the
  player or below it. Tab goes from DSP, the last control of the output panel, to the tab labels. A
  one-pixel `TPanel` (a splitter, without MSAA role) stands between the list and the metadata panel.
- The status line under the list of files (1 file selected | format | … | size) is a `TLabel` in a
  `TPanel` without child windows. After the panel was made anew, the display model may have no text for
  it for a while, also after a repaint.

## Cover art and rating

- The cover art of the metadata panel (`TDropPanel`) is not a tab stop, but takes focus. VCL's Tab
  from it goes to the panel's first field in the Tab order, Shift+Tab to the control before the panel.
  Its menu (View, Load, Download, Save as, Resize ▸, Cut, Copy, Paste, Clear; View is not translated)
  opens on `WM_CONTEXTMENU` posted to it; with the point -1, -1 of the keyboard the menu shows at the
  mouse pointer. A posted Applications key does not open it.
- View (`TCoverArtWnd2`) has no focusable control: focus stays on the form. Its menu (as the cover's,
  without View) belongs to the larger of its two `TPanel`s, the picture; the other is the line of text
  under it. Escape does not close it.
- The panel over the cover art (`TCoverArtWnd`, caption Cover Art, not translated) shows while the
  mouse pointer rests on the cover art; a posted `WM_MOUSEMOVE` does not bring it up. Focus is on its
  `TPanel` captioned Cover Art. It closes on `WM_CLOSE` and shows again while the pointer stays there.
- Download Cover Art (`TAmazon`) opens with focus on the form; its list of results has no name. Escape
  closes it.
- The rating (`TRating`, caption Rating `[592]` left of it) has no window: five stars drawn in the
  metadata panel, 16 × 16 design units each from its left edge. A click sets the stars up to the one
  clicked; a click in the first few pixels of the rating (5 at 120 DPI) sets none, a click right of
  the stars all five. ezcd marks the file as changed (its name in italics) even when the stars are set
  back. ezcd hides it with the Rating field and disables it without a file.
- VCL objects in ezcd's memory: a window's object is in its property `ControlOfs` followed by the
  module instance and the thread id, 8 hexadecimal digits each. In the object, at 0x398 is
  `FControls`, the `TList` of the controls without windows (at 8 the pointer to the items, at 16 their
  count). A class name is a short string pointed to from 136 bytes before the virtual method table the
  object points to. A control has `FLeft`, `FTop`, `FWidth`, `FHeight` at 0x90 (parent's client
  pixels), `FVisible` at 0xA9 and `FEnabled` at 0xAA, the code pointer of `FOnClick` at 0x1F8,
  nil without a handler, and `FText` at 0x2D0: the caption, a null-terminated string made by
  `StrAlloc`, the size of its block in bytes (these 4 included) right before it, nil without a
  caption. `TRating` has its number of stars at 0x340. `FVisible` stays set inside a
  hidden window, as on a hidden tab.
- Controls without windows that take clicks: `TSpeedButton`s and `TPngSpeedButton`s (counters, pages
  of the Disc Burner tab, metadata services, Encoder information, the gear of Filename preview), the
  links of About (`TLabel`s with `OnClick`: the home page and Fraunhofer's page, opened in the
  browser), the captions of the CD Ripper's metadata fields (`TLabel`s with `OnClick`), the icons of its
  player and the picture of the panel over the cover art (`TImage`s with `OnClick`). The pictures of
  the cover art in the metadata panel (`TImage`s of the `TDropPanel`) take clicks too. Other labels,
  rating and bevels have no handler. MSAA shows a window's child windows in z-order, not by place.

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
- MSAA gives a slider (`TMyTrackBar`, a `msctls_trackbar32`) the position as a percentage of its range,
  rounded. The field right of it shows the value and follows every key at once; a value typed in the
  field moves the slider when the field loses focus. DSP sliders: silence 0–500 and fades 0–1000
  (0.01 s, arrows and pages 1 s), gain 0–240 (−12…+12 dB), peak 0–200 (−20…0 dB FS) and loudness
  770–1010 (−30…−6 LUFS), all three 0.1 a step and 1 a page; on these three the percentage repeats on
  half of the arrow keys or more.
- The Filename preview dialog has a one-line explanation of the template syntax above its list of
  templates, longer than any caption.
- The fields replacing characters on the File name settings page are captioned only by the character
  (`/ : * ? " < > |`), which NVDA does not say at its default punctuation level for most of them.

## Controls without captions

- Buttons that show only an image are `TButton` windows without text, right next to the control they
  serve: Browse after the output folder (`TEdit`) and Filename preview after the file name template
  (`TComboBox`) on the output panels of the Audio Converter and Audio CD Ripper tabs; Browse after the
  sound file (`TEdit`) on the General page of Settings; Move up and Move down (strings `[241]`,
  `[242]`) one above the other right of the list in Edit profiles. They have no hint; the language
  files have Filename preview (`[266]`) but no Browse.
- The tag buttons of Filename preview are 27 `TButton`s in three rows between the template field
  (`TEdit`) and the template history (`TListBox`), three of them children of the form, the others of
  the panel holding the field; all but Number and Sequence are outside the tab order. The one inserting
  a space has a space as its caption. A tag inserts its text into the field at the caret, replacing the
  selection (the field keeps it while unfocused), and moves focus to the field. Six are split buttons
  (Year, Disc Number, Total Discs, Total Tracks, Number, Sequence): Down on one, also posted, opens its
  menu of variants; a variant is inserted the same way, but focus stays on the button. The template
  changes the output panel's template at once, so closing the window by its close box keeps it.
- Right of Add in Filename preview, a gear without a window (`TPngSpeedButton` of the panel holding the
  template field) opens Settings at the Filename generation page (string `[576]`); it has no hint.
- The check box of DSP that switches the effect on has no caption; it lies left of the combo box
  choosing the effect (Gain, Loudness normalization, …), overlapping it by a few pixels. The
  effect's settings are on cards of a `TCardPanel` right below that combo box, one card shown
  (`TCard`): gain, peak (a slider and a field), loudness (a slider and three fields one above the
  other at its right edge: LUFS, dB Δ, dB SPL; its scales are those of LUFS above and dB SPL below).
  Both modes of loudness, "Loudness normalization | Integrated" and "| Top of Loudness Range", share
  its card. The cards have only scales and units on screen. With Peak normalization, a combo box
  without caption (Sample peak, True peak) takes the place of the Peak limit check box below the cards.
  ezcd's Tab order in DSP jumps around: Close, the effect's check box, the card's controls (loudness:
  dB SPL, the slider, dB Δ, LUFS), the effect, Peak limit, then the silence panel from the bottom up.
- When a check box or radio button of DSP changes, ezcd fills the background of its whole parent and
  draws again only what changed, so the display model loses the other labels (units, scales) until the
  parent is painted again with `RedrawWindow`.
- No caption on screen at all: the tree of pages in Settings (`TTreeView`), the list of profiles in
  Edit profiles, the file name template (`TEdit`), the template history (`TListBox`) and the preview
  (`TListView`) in Filename preview, and in the metadata editor (`TTMetadata`) the list of files, the
  list of fields, the combo box naming a field to add, the value of a field (`TMemo`), the combo box
  of picture types and the list of pictures (`TListView`). In the metadata editor the list of files is
  in a panel of the form, the list of fields in a panel inside a panel; the combo box of field names
  can be typed in (it has an `Edit` child), that of picture types cannot. So can the file name
  template on the output panels and the file name of the cover art in Options: focus is in the
  `Edit`, and NVDA leaves an edit in a named combo box without a name. The language files have
  Profile `[582]`, Filenames `[180]`, Filename preview `[266]`, Files `[494]`, Metadata `[101]`, Name
  `[834]`, Value `[835]`, Cover Art `[349]`, Tracklist `[137]`.
- The output panels of the Audio Converter and Audio CD Ripper tabs have no caption for the profile,
  the format, its extension and the codec's parameters. The profile is a `TComboBoxEx`, whose child
  `ComboBox` gets focus. The format and the extension are combo boxes right next to each other below
  it. The codec's parameters (up to six combo boxes, hidden as the format needs) lie in a panel of
  their own inside the output panel; which parameter is in which box depends on the format. Their items
  are the codec's, the same in every language: sample rates (`44100 Hz`, `Auto`, for DSD `DSD64` …),
  bit rates (`~128 kbit/s | V 5`), channels (`Stereo`, `Mono`, `5.1`), bit depths (`16-bit`), bit rate
  modes (`VBR`, `CBR`, `ABR`, `CVBR`), and levels: compression of FLAC, Monkey's Audio and WavPack,
  `q 0 (Best)` of LAME, `Music`/`Voice` of Opus, `Standard`/`Lossless` of WMA. ezcd keeps the
  parameters of each format, so switching the format and back keeps them.
- The drive and its speed have only icons before them: side by side on the Audio CD Ripper tab
  (Source drive `[462]`, Read speed `[463]`), one above the other on the Disc Burner tab (only hints
  Device and Speed; the language files have Disc writer `[235]` and Write speed `[236]`, ending in
  ` :` in some languages). Each pair lies in a panel with the toolbar of the tray. The drive at the top
  of the Drive settings page of Settings (`TSettings2AudioCDRipperDriveForm`) has no caption either.
  The language files have Profile `[582]`, Format `[619]`, Bit rate `[478]`, Bit depth `[479]`, Sample
  rate `[480]` and Channels `[481]`, but nothing for the extension, the bit rate mode or the levels.
- The manual search of metadata (`TMBManual`, one window for GD3, MusicBrainz, Discogs and Deezer) has
  no caption for its list of results. Its panel is too short at higher DPI: the last row (Release
  Code, a `TEdit` and a Search button) lies below the panel's edge, over the list, and its caption is
  not drawn. For GD3 the Barcode row and the last Search are hidden, but the Release Code field stays
  visible and in the tab order.
- The results of Search for CD metadata (`TFC_GetMetadata`) are a tree of tracks without a caption;
  Escape does not close the window, only Cancel or its close box.

### Repeated captions

- Several buttons or check boxes of one window share a caption: three Search in the manual search of
  metadata (`TMBManual`), Add and Delete for fields and for pictures in the metadata editor, Keep
  aspect ratio for embedded and external cover art in Options, and Cancel for the whole download and
  for each service in Download metadata (`TGetMetadataForm`). What tells them apart is on their row:
  the caption of the field before them (Artist, Barcode), the check box starting the row (Resize
  embedded Cover Art), the count left of them (6 metadata fields), or the status of the service
  (Querying MusicBrainz) while it is queried; the name of the service has no label of its own.
- The cover art size buttons of Options are split buttons captioned with the size (`500x500`); the
  check box at the start of their row tells which size it is.
- The hidden tab pages of the main window keep their windows with the visible style: their buttons
  repeat the captions of the active tab's (Options », DSP »), and only `IsWindowVisible` tells them
  apart.
- A language switched while ezcd runs is not in the registry until later (see Language files below);
  the language of a window shows in its captions, which are strings of one language file.

## Dialogs

- Each dialog is a top-level window of its own form class (`TAboutForm`, `TConverterOptions`,
  `TDSPForm`, …), owned by the main window. MSAA gives the form the client role (a pane for NVDA), not
  the dialog role, so NVDA collects no dialog text for it.
- The text of a dialog is in `TLabel`s without windows, in the display model of their parent: the form,
  a `TPanel`, `TCard` or `TGroupBox`. They are drawn before the dialog's first focus event: the display
  model has them when NVDA announces the dialog.
- The pages of Settings are forms (`TSettings2GeneralForm`, …) embedded as child windows in a `TPanel`
  of `TSettings2Form`.
- The section headings of Options of the Audio Converter and Audio CD Ripper tabs (`TConverterOptions`,
  `TRipperOptions`: Files, Metadata, Cover Art, and in the converter's one for tracks as separate
  files) are labels above the first check box of the section, with a `TBevel` line under them across
  the form; they are the only texts the form itself draws. A section runs down to the next heading;
  OK, alone on the bottom row, is in none. ezcd's Tab order there jumps between the sections
  (Overwrite, OK, Cue Sheets, …), and the forms open with focus on the first check box (converter) or
  on OK (ripper). Options of the Disc Burner tab (`TAudioCDOptions`) has no sections.
- In Encoder information, version and date values have the form of scale numbers (`13.2.1.1`,
  `24.09.2026`); the scales of sliders lie over or under the slider, within its height.
- The window shown while file names are checked before a conversion (Checking filenames...) has a label
  repeating its caption, with a space before the dots.
- The page forms of Settings are made anew each time their page is chosen. Their settings take effect
  at once; the dialog has only Close.
- Counters in Settings: the numbers of parallel converters and of scanners (`TEdit`s in their own
  `TPanel`s of `TSettings2AudioConverterForm`, captioned above) and the limit of metadata results per
  service (a read-only `TEdit` under the list of services of
  `TSettings2GeneralInternetDiscDatabaseForm`, captioned left). Each is a `TEdit` between "-" and "+"
  `TSpeedButton`s without windows, 23 × 23 design units, 1 unit (converter page) or 2 units (the limit)
  from the edit, as in the conversion window (see Number of converters). The number of scanners also
  takes typing. ezcd handles a click at once; the numbers go down to 1.
- The list of metadata services (`TCheckListBox`) has two `TPngSpeedButton`s without windows right of it,
  Move up and Move down: 23 × 22 design units, 4 units right of the list, the first level with its top,
  the second right under it. A click at the centre moves the selected service, and the list fires focus
  and selection on it at its new place; on the first service Move up does nothing.
- About is the last item of the Help menu (on every top panel); Escape closes it.
- When a dialog closes, VCL gives focus back to the control that had it before. After Options, DSP and
  Edit profiles, ezcd moves it on to the main form 10–110 ms later; Tab from the main form goes to the
  tab labels. After the conversion window and after a window opened by the mouse, focus goes to the tab
  labels. Settings and About (opened from the Help menu) leave it on their button.
- While a modal window is open, the main form is disabled: a state change for it comes when the window
  opens with focus on the form.
- A menu item that opens a dialog (Manual search) gives focus to the main window's list before the
  dialog gets it. Escape from a top panel menu returns focus to its button.
- The manual search (`TMBManual`) and Download Cover Art (`TAmazon`) give focus to their first field and
  some 10 ms later to the form.
- The status window shown while files are added (`TTStatusWindow`, Adding files... `[397]`) disables its
  Cancel at the end, and focus goes to its form before the window closes.
- Encoder information opens with a `TPngSpeedButton` without a window right of the format and extension
  combo boxes of the Audio Converter tab's output panel, at 292, 46 (24 × 24) in the panel as in the
  form's DFM; a posted click at its centre opens it. It has only an OK button and does not close on Escape.

## List boxes and list views

- When a `TListBox`, `TCheckListBox` or `TListView` gets focus, it fires focus on the list (child 0)
  and 1–10 ms later on its focused item. NVDA takes the first event for the focused item already, so
  without the add-on the item is said twice.
- Without a selection, the first arrow key in a `TCheckListBox` (metadata services in the settings)
  selects the focused item and fires focus on it again.
- MSAA gives the items of a `TCheckListBox` no check state. VCL keeps the state of an item in an
  object whose address is the item's data (`LB_GETITEMDATA`): after the pointer to its class and the
  item's own data (8 bytes each in the 64-bit ezcd) comes the state, a byte, 0 unchecked, 1 checked,
  2 grayed. Every item of the list of metadata services has such an object; its own data is the
  service's number, which moves with the item.
- Space toggles the item's check box without any event; Space on an item that is not selected also
  selects it and fires focus on it.
- A `TCheckListBox` with automatic dragging (the list of metadata services) starts a drag on a mouse
  press: after a posted press and release, VCL's drag window keeps the mouse capture and keys to the
  list do nothing until a release is posted to that window.

## Menus

- ezcd's menus are popup menus (`#32768`) of `TPopupMenu`s. Opened by a click (the menu buttons of the
  top panels and View of the explorer, a split button on Down, `WM_CONTEXTMENU`), a menu has no item
  selected, and NVDA gets focus on the menu itself. Down posted to the menu window selects the first
  item, as a real key does.
- MSAA numbers the separators among the items (child IDs), and gives an item with a submenu as an
  object of its own, with child ID 0; its place is found by its location among the menu's children.
- The menus of the top panels have their items drawn by ezcd (`MFT_OWNERDRAW`, no text in the menu;
  MSAA has the names) and no mnemonics. Other menus have plain text without `&`: an item is then
  chosen by its first character, which MSAA gives as its keyboard shortcut ("с" for List in the view
  menu of the explorer, "<" for every variant of a tag in Filename preview).
- Escape from a submenu fires focus on the parent menu from the submenu's window, which is destroyed by
  then.

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
  text line. Some entries are empty (`[580]` in Croatian): an empty string matches any window
  without text, so it tells nothing about the language.
- The active language is `HKCU\Software\Poikosoft\EZ CD Audio Converter`, value `k82`, equal to
  string `[0]` of the active file (unique among the files, as `Russian (ру́сский)`). When the language
  is switched in the running application, the captions change at once but `k82` keeps the old value.
- The language is switched in View > Language: its items are named by string `[0]` of each file, after
  a first item English that has no file. With that built-in English, `k82` keeps the previous language
  also after a restart; its captions are those of `english.uni`. Within about 10 ms of the switch ezcd fires name changes on
  the three tabs of the main window (`TTabSheet`), then on buttons and check boxes, and makes its
  toolbars anew; nothing else tells of it.
  A window shows few strings of its language (the main window 4 of 12 texts, About 2 of 3), and
  languages share many (Audio CD in Russian and Bulgarian), so a count of them alone can pick another
  language.
