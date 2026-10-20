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
  | **Convert** | **1** | **Rip CD** | **0** | **Burn Disc** | **13** |
  | Settings | 2 | Settings | 2 | Settings | 2 |
  | View | 15 | View | 15 | View | 15 |
  | Help | 19 | Help | 19 | Help | 19 |

- The main button of a tab is recognised by its image together with its caption, which must equal
  the string in one of the language files: Convert is image 1 with string `[232]` or `[406]`, Rip CD
  is image 0 with string `[176]`, Burn Disc is image 13 with string `[392]`. No translation of these
  strings has a `▼`, so the menu buttons with the same images never match.
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

## Conversion window

- A top-level `TConvertWnd` window, shown while files are converted and kept open after the end.
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
