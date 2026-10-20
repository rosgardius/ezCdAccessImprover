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

## Top panel of the converter and ripper tabs

- The panel is a `TPanel` that is a direct child of the tab's `TTabSheet`. Each large button on it
  is a `TToolBar` window holding one `TToolButton`.
- `TToolBar` is a superclassed comctl32 toolbar: `TB_*` messages work, and the MSAA toolbar proxy
  exposes the button as child id 1 of the window (role button, name = caption, state always 0,
  not focusable). The MSAA location of the button is scaled wrongly at DPI above 100%.
- `TB_GETBUTTON` `iBitmap` equals `ImageIndex` of the `TToolButton`. Images on the top panels
  (unique within each panel, but not across panels):

  | Converter | Image | Ripper | Image |
  |---|---|---|---|
  | Audio Converter ▼ | 0 | CD Ripper ▼ | 1 |
  | **Convert** | **1** | **Rip CD** | **0** |
  | Metadata ▼ | 4 | Disc ▼ | 3 |
  | Rename files | 6 | Metadata ▼ | 4 |
  | Save metadata | 7 | AutoRip | 5 |
  | Settings | 2 | Settings | 2 |
  | View | 15 | View | 15 |
  | Help | 19 | Help | 19 |

- The main button of a tab is recognised by its image together with its caption, which must equal
  the string in one of the language files: Convert is image 1 with string `[232]` or `[406]`, Rip CD
  is image 0 with string `[176]`. No translation of these strings has a `▼`, so the menu buttons
  with the same images never match.
- The Disc Burner tab has no such main button; it has a three-button toolbar and repeated image numbers on its top panel.
- Disabled buttons lack `TBSTATE_ENABLED` in `fsState`.
- The buttons marked ▼ in the caption, and View and Help, open a menu (`DropdownMenu`): converter
  images 0, 4, 15, 19, ripper images 1, 3, 4, 15, 19. Nothing in the toolbar or MSAA tells them
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
- The MSAA proxy reports the button's position as 1 of 1 (within its own toolbar).
- Pressing Alt on a focused toolbar fires a focus event for the toolbar again before the system menu
  item gets focus.

## Tabs of the main window

- The main window's `TPageControl` is a direct child of `TMainform`; each tab is a `TTabSheet` child of
  it, the active one visible. The Disc Burner tab holds another `TPageControl`.
- MSAA gives `TTabSheet` the property page role. NVDA treats it as a dialog and, on every focus entry
  into the tab, collects dialog text from all its panels: about 250 ms in the main window, with an
  empty result.

## Keyboard

- F8 presses Convert or Rip CD, depending on the current tab. The hint text (`Convert [ F8 ]`) is not
  translated.
- Shift+F10 opens the registration key dialog.

## Language files

- `Language\*.uni` next to `ezcd.exe`: UTF-16 with BOM, each entry is a `[N]` line followed by the
  text line.
- The active language is `HKCU\Software\Poikosoft\EZ CD Audio Converter`, value `k82`, equal to
  string `[0]` of the active file. When the language is switched in the running application, the
  captions change at once but `k82` keeps the old value, so it cannot tell the current language.
