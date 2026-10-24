# Copyright (C) 2026 Rosgardius
# This file is covered by the GNU General Public License.
# See the file COPYING.txt for more details.

"""App module for EZ CD Audio Converter (ezcd.exe)."""

import ctypes
import time
from collections.abc import Hashable
from ctypes.wintypes import DWORD

import api
import appModuleHandler
import braille
import controlTypes
import eventHandler
import inputCore
import oleacc
import winKernel
import winUser
from keyboardHandler import KeyboardInputGesture
from logHandler import log
from NVDAObjects.IAccessible import ContentGenericClient, IAccessible, getNVDAObjectFromEvent
from scriptHandler import script
from speech.speech import speakMessage
from winBindings import kernel32

from . import (
    burner_pages,
    captions,
    cards,
    cells,
    convert_window,
    counters,
    cover_art,
    dialogs,
    explorer,
    file_lists,
    filename_preview,
    list_items,
    menus,
    metadata,
    names,
    options,
    panels,
    player,
    rating,
    sliders,
    styles,
    tab_end,
    tab_order,
    toolbar,
    toolbar_stops,
    top_panel,
    tray,
    version,
    window_focus,
    windowless,
)
from .language import LanguageFiles
from .windows import child_windows, parent, root, shown_texts, top_level_windows

_PROCESS_QUERY_LIMITED_INFORMATION = 0x1000
# Seconds from pressing View Explorer to the focus ezcd moves as it hides the button.
_TOGGLE_FOCUS_TIMEOUT = 1.5
# Seconds from a key to the focus ezcd moves as it hides the window with the focus and acts, as it goes to
# a folder.
_RETURN_FOCUS_TIMEOUT = 5
_MAX_PATH_LENGTH = 32767


class AppModule(appModuleHandler.AppModule):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        app_path = self._executable_path()
        version.choose(app_path)
        self.language = LanguageFiles(app_path, self._main_window_texts)
        self.remembered_buttons: dict[Hashable, tuple[int, int]] = {}
        """``StopButton.key`` of the last focused button of each toolbar stop, by ``ToolbarStop.key``."""
        self._focus_window = 0
        self._tab_menu_tab = 0
        self._tab_key = 0
        """1 after Tab, -1 after Shift+Tab, until the next focus or key."""
        self._passing = 0
        self._skipped_tree = 0
        """The hidden folder tree that Tab or Shift+Tab went on past, until the next key."""
        self._passed_toolbar: tuple[tuple[int, int, int] | None, int] = (None, 0)
        """The last answer of ``_toolbar_passed``, until the next key."""
        self._explorer_toggle = 0
        """The toolbar on which View Explorer was pressed, until the next focus."""
        self._toggle_pressed_at = 0.0
        self._quiet_toggle = 0
        """The toolbar of View Explorer that gets focus after the press: only its state is reported."""
        self._tab_kept = False
        self._focus_return = 0
        """The window that gets focus back when ezcd moves it elsewhere in the window, until the next key."""
        self._focus_return_at = 0.0
        self._folder_changed = False
        """The list in focus went to another folder, until the next key: the names of its items are not
        reported."""
        self._conversion_status = convert_window.ConversionStatus()
        self.counter_steps = counters.StepAnnouncer()
        self.page_switcher = burner_pages.PageSwitcher(self.language, self._note_gesture)
        self.closed_editor = file_lists.ClosedEditor()
        self.cells = cells.CellTable(self.language)
        self.tag_stop = filename_preview.TagStop()
        self.window_focus = window_focus.WindowFocus()
        self.tray_pair = tray.PairFocus()
        inputCore.decide_executeGesture.register(self._note_gesture)
        # Also while ezcd is in the background: a switch of its language captions the tabs anew.
        eventHandler.requestEvents("nameChange", self.processID, "TTabSheet")

    def terminate(self):
        inputCore.decide_executeGesture.unregister(self._note_gesture)
        self.counter_steps.terminate()
        self.page_switcher.terminate()
        self.tray_pair.terminate()
        super().terminate()

    def _executable_path(self) -> str | None:
        if self.appPath:
            return self.appPath
        # NVDA's handle to an elevated ezcd may lack query rights; the limited right is granted anyway.
        handle = winKernel.openProcess(_PROCESS_QUERY_LIMITED_INFORMATION, False, self.processID)
        if not handle:
            return None
        try:
            size = DWORD(_MAX_PATH_LENGTH)
            buffer = ctypes.create_unicode_buffer(size.value)
            if not kernel32.QueryFullProcessImageName(handle, 0, buffer, ctypes.byref(size)):
                return None
        finally:
            winKernel.closeHandle(handle)
        log.debugWarning(f"appPath unavailable, ezcd path from a limited process handle: {buffer.value}")
        return buffer.value

    def _main_window_texts(self) -> tuple[set[str], set[str]]:
        """The captions of the main window's tabs and the texts the window shows; empty if it has no tabs
        yet."""
        for form in top_level_windows(self.processID, "TMainform"):
            for labels in child_windows(form, "TPageControl"):
                captions = {winUser.getWindowText(t) for t in child_windows(labels, "TTabSheet")} - {""}
                if captions:
                    return captions, shown_texts(form)
        return set(), set()

    def tab_menu_opened(self, tab: int):
        """The menu that switches the main window's tab is opening on the tab's top panel."""
        self._tab_menu_tab = tab

    def pass_focus(self, hwnd: int):
        """Moves ezcd's focus to the window for the key that follows, without NVDA reporting it."""
        self._passing = hwnd
        if not toolbar.set_focus(hwnd):
            self._passing = 0

    def return_focus(self, hwnd: int):
        """ezcd is about to hide the focus: focus goes back to the window from wherever ezcd moves it in the
        same top-level window."""
        self._focus_return = hwnd
        self._focus_return_at = time.monotonic()

    def _returns_focus(self, hwnd: int) -> bool:
        """Whether focus on the window goes back to the window of ``return_focus``."""
        back = self._focus_return
        return (
            bool(back)
            and hwnd != back
            and root(hwnd) == root(back)
            and time.monotonic() - self._focus_return_at < _RETURN_FOCUS_TIMEOUT
        )

    def leave_tab_end(self, stop_hwnd: int, forward: bool, process_handle: int) -> bool:
        """Moves focus from a stop at the end of its tab to the next or previous stop there, and after the
        last one to the tab labels, on the way to the top panel; ``False`` if it did not move.

        Before the first stop, focus passes by the tab labels for the key that follows: VCL goes from there
        to the tab's last control.
        """
        target = tab_end.neighbour(stop_hwnd, forward)
        if not target:
            return False
        if not top_panel.is_main_tab_labels(target):
            return self._enter_end_stop(target, process_handle)
        if forward:
            return toolbar.set_focus(target)
        self.pass_focus(target)
        return False

    def _enter_end_stop(self, hwnd: int, process_handle: int) -> bool:
        """Moves focus to the stop of a window ``tab_end`` gives: a toolbar stop or a slider of the player;
        ``False`` if it did not move."""
        if winUser.getClassName(hwnd) != "TToolBar":
            return toolbar.set_focus(hwnd)
        return self._enter_stop(
            explorer.stop_of(hwnd, process_handle, self.language)
            or tray.stop_of(hwnd, process_handle, self.language)
            or player.stop_of(hwnd, process_handle, self.language)
        )

    def explorer_toggled(self, toolbar_hwnd: int):
        """View Explorer is being pressed on the toolbar: ezcd will hide it and show the other one."""
        self._explorer_toggle = toolbar_hwnd
        self._toggle_pressed_at = time.monotonic()

    def _toolbar_passed(self, window: int, previous: int, tab_key: int, process_handle: int) -> int:
        """The toolbar of the explorer or the tray, or the window of a stop at the end of the tab, that Tab
        or Shift+Tab passed by, once for the focus and its ancestors."""
        if not tab_key:
            return 0
        key = (window, previous, tab_key)
        if self._passed_toolbar[0] != key:
            forward = tab_key == 1
            passed = (
                explorer.toolbar_passed(window, previous, forward)
                or tray.toolbar_passed(window, previous, forward)
                or tab_end.toolbar_passed(window, previous, forward, process_handle, self.language)
            )
            self._passed_toolbar = (key, passed)
        return self._passed_toolbar[1]

    def _note_gesture(self, gesture) -> bool:
        # Called in NVDA's keyboard hook thread for every gesture, in any application.
        self._tab_key = 0
        self._passing = 0
        self._skipped_tree = 0
        self._passed_toolbar = (None, 0)
        self._focus_return = 0
        self._folder_changed = False
        if isinstance(gesture, KeyboardInputGesture):
            if gesture.vkCode == winUser.VK_TAB:
                modifiers = gesture.modifierNames
                self._tab_key = 1 if not modifiers else -1 if modifiers == ["shift"] else 0
            self.closed_editor.note_key(gesture)
            self.cells.note_key(gesture.vkCode)
        return True

    def event_gainFocus(self, obj, nextHandler):
        if isinstance(obj, cells.CellEditor) and obj.is_closed:
            return
        if self.window_focus.is_form_passed(obj):
            return
        previous, self._focus_window = self._focus_window, obj.windowHandle
        tab_key, self._tab_key = self._tab_key, 0
        passing, self._passing = self._passing, 0
        self._tab_kept = False
        window_return = self.window_focus.note_focus(obj, previous)
        if passing and obj.windowHandle == passing:
            return
        hwnd = obj.windowHandle
        if tab_key and (hwnd == self._skipped_tree or explorer.is_hidden_tree(hwnd)):
            # NVDA does not see the key it sends: the next focus comes from the same key, past the tree. The
            # tree and then its item get focus: the key is sent once.
            self._focus_window, self._tab_key = previous, tab_key
            if hwnd != self._skipped_tree:
                self._skipped_tree = hwnd
                KeyboardInputGesture.fromName("tab" if tab_key > 0 else "shift+tab").send()
            return
        # VCL moves focus to the form as the Cancel of a status window, such as Adding files, is disabled at
        # the end; the window was reported already.
        if obj.windowClassName == "TTStatusWindow" and root(previous) == obj.windowHandle:
            return
        back = self.tag_stop.focus_back(obj)
        if back and toolbar.set_focus(back):
            return
        if self._returns_focus(obj.windowHandle) and toolbar.set_focus(self._focus_return):
            self._tab_kept = True
            return
        quiet, self._quiet_toggle = self._quiet_toggle, 0
        if quiet and obj.windowHandle == quiet:
            # Only the new state, as for a toggle button that keeps the focus.
            braille.handler.handleGainFocus(obj)
            pressed = controlTypes.State.PRESSED
            speakMessage(pressed.displayString if pressed in obj.states else pressed.negativeDisplayString)
            return
        toggle, self._explorer_toggle = self._explorer_toggle, 0
        if toggle and time.monotonic() - self._toggle_pressed_at < _TOGGLE_FOCUS_TIMEOUT:
            found = explorer.toggle_button(toggle, obj.processHandle, self.language)
            if found is not None and toolbar_stops.focus_button(self, *found, obj.windowHandle):
                self._quiet_toggle = found[1].toolbar
                # Focus may have left the tab for the main form in between.
                self._tab_kept = True
                return
        # VCL skips the cover art, the rating and the player; stop at them.
        stop = (
            cover_art.stop_target(obj.windowHandle, previous, tab_key)
            or rating.stop_target(obj.windowHandle, previous, tab_key, obj.processHandle)
            or player.stop_target(obj.windowHandle, previous, tab_key)
        )
        if stop and toolbar.set_focus(stop):
            return
        if self.closed_editor.is_left_focus(obj):
            braille.handler.handleGainFocus(obj)
            return
        if self.closed_editor.is_unasked(obj):
            self.closed_editor.close(obj.windowHandle)
            return
        if self.cells.handle_focus(obj, self.helperLocalBindingHandle):
            return
        if window_return is not None and self._go_back(obj, window_return, nextHandler):
            return
        if self._tab_menu_tab and obj.windowClassName != "#32768":
            # Whichever tab was chosen, VCL puts focus on the tab's first control.
            panel = top_panel.panel_after_tab_menu(self._tab_menu_tab, obj.processHandle, self.language)
            self._tab_menu_tab = 0
            if (
                panel is not None
                and top_panel.is_beside_panel(panel, obj.windowHandle)
                and toolbar_stops.focus_button(self, panel, panel.buttons[0])
            ):
                return
        # VCL skips the toolbars of the explorer and the tray; stop at the one Tab or Shift+Tab passed by.
        # Those at the end of the tab come before its top panel, also the player's stops.
        passed = self._toolbar_passed(obj.windowHandle, previous, tab_key, obj.processHandle)
        if passed and self._enter_end_stop(passed, obj.processHandle):
            return
        # VCL skips the top panel on Tab; stop at it instead of the tab labels.
        if (
            tab_key == 1
            and previous
            and obj.windowClassName == "TPageControl"
            and self._enter_stop(
                top_panel.panel_left_by_tab(obj.windowHandle, previous, obj.processHandle, self.language)
            )
        ):
            return
        nextHandler()

    def _go_back(self, obj, back: window_focus.Return, nextHandler) -> bool:
        """Moves focus back from the form or the tab labels; ``False`` if it did not move and the focus was
        not reported."""
        if back.silent:
            self.pass_focus(back.target)
            return self._passing == back.target
        # The main form as the first focus in the main window, its title not reported yet.
        reported = obj.windowHandle == root(obj.windowHandle)
        if reported:
            nextHandler()
        if not toolbar.set_focus(back.target):
            return reported
        self.window_focus.going_back(back)
        return True

    def _enter_stop(self, stop: toolbar_stops.ToolbarStop | None) -> bool:
        """Moves focus to the stop's remembered button; ``False`` if it did not move.

        Focus stays in the tab, but may have passed by the tab labels, as Shift+Tab from its first control.
        """
        if stop is None or not toolbar_stops.focus_button(self, stop, stop.entry(self.remembered_buttons)):
            return False
        self._tab_kept = True
        return True

    def event_nameChange(self, obj, nextHandler):
        if obj.windowClassName == "TTabSheet" and top_panel.is_main_window_tab(obj.windowHandle):
            self.language.tabs_captioned()
        # The new path: the list in focus is going to another folder.
        if obj.windowClassName == "TJamShellBreadCrumbBar" and explorer.is_folder_list_focus(
            obj.windowHandle
        ):
            self._folder_changed = True
            explorer.announce_folder(obj.windowHandle, self.helperLocalBindingHandle, obj.processHandle)
        if obj.windowClassName == "TJamShellList" and self._folder_changed:
            return
        if obj.windowClassName == "TVirtualStringTree":
            focus = api.getFocusObject()
            if file_lists.is_list_focus_event(obj, focus):
                # The focus event that follows would be dropped as a duplicate of the item without a name.
                item = file_lists.focused_file(obj.windowHandle)
                if item is not None:
                    eventHandler.queueEvent("gainFocus", item)
                return
            if obj is not focus and file_lists.is_focused_file_event(obj, focus):
                eventHandler.executeEvent("nameChange", focus)
                return
        nextHandler()

    def event_valueChange(self, obj, nextHandler):
        if obj.windowClassName == "TProgressBar":
            kind = convert_window.bar_kind(obj.windowHandle)
            # Every converter bar changes several times a second; drop them before anything else.
            if kind == convert_window.Bar.CONVERTER:
                return
            if kind == convert_window.Bar.TOTAL:
                self._conversion_status.sample_speed(obj.windowHandle, self.helperLocalBindingHandle)
        else:
            self.tag_stop.note_change(obj)
        nextHandler()

    def event_selection(self, obj, nextHandler):
        # ezcd selects the folder it went to in the tree, which has focus on its way back.
        if self._returns_focus(obj.windowHandle):
            return
        nextHandler()

    def event_stateChange(self, obj, nextHandler):
        # The main form is disabled while a dialog is open; a status window disables its Cancel at the end.
        if (
            obj.windowClassName == "TMainform"
            or winUser.getClassName(root(obj.windowHandle)) == "TTStatusWindow"
        ):
            return
        # View Explorer changes its state as ezcd hides it; the state of the other one comes with the focus.
        if (
            obj.windowClassName == "TToolBar"
            and time.monotonic() - self._toggle_pressed_at < _TOGGLE_FOCUS_TIMEOUT
        ):
            return
        nextHandler()

    def _step_burner_page(self, gesture, step: int):
        """Shows the page of the Disc Burner tab next to the active one, going round, if focus is in that
        tab."""
        focus = api.getFocusObject()
        tab = top_panel.main_tab(focus.windowHandle)
        pages = burner_pages.pages_in_tab(tab) if tab else 0
        if not pages:
            gesture.send()
            return
        self.page_switcher.move(
            pages, focus.processHandle, lambda current: (current + step) % burner_pages.PAGE_COUNT
        )

    @script(gesture="kb:control+tab")
    def script_next_burner_page(self, gesture):
        self._step_burner_page(gesture, 1)

    @script(gesture="kb:control+shift+tab")
    def script_previous_burner_page(self, gesture):
        self._step_burner_page(gesture, -1)

    def _get_statusBar(self):
        panel = convert_window.summary_panel(root(api.getForegroundObject().windowHandle))
        if panel is None:
            raise NotImplementedError
        return getNVDAObjectFromEvent(panel, winUser.OBJID_CLIENT, 0)

    def getStatusBarText(self, obj):
        window = root(obj.windowHandle)
        if obj.windowHandle != convert_window.summary_panel(window):
            raise NotImplementedError
        return self._conversion_status.text(window, self.helperLocalBindingHandle, self.language)

    def event_appModule_loseFocus(self):
        self._tab_menu_tab = 0

    def event_foreground(self, obj, nextHandler):
        if self.cells.is_coming_back(obj):
            return
        self.window_focus.note_foreground(obj)
        nextHandler()

    def event_focusEntered(self, obj, nextHandler):
        if self.cells.is_coming_back(obj):
            return
        # Focus comes back to a tag from its menu: only the template is reported.
        if self.tag_stop.returned:
            return
        if self.window_focus.is_quiet_ancestor(obj):
            return
        # The tab labels, named after the tab, are left for a control of the tab.
        if top_panel.is_main_window_tab(obj.windowHandle) and parent(obj.windowHandle) == self._focus_window:
            return
        # Focus stayed in the tab: the tab labels or the main form in between were not announced.
        if self._tab_kept and obj.windowClassName in ("TTabSheet", "TPageControl"):
            return
        # Focus is passing by, about to go back, or about to go on to a toolbar Tab passed by: the control is
        # not announced.
        focus = api.getFocusObject().windowHandle
        if (
            (focus and focus in (self._passing, self._quiet_toggle))
            or self._returns_focus(focus)
            or self._toolbar_passed(focus, self._focus_window, self._tab_key, obj.processHandle)
        ):
            return
        # Focus is about to leave the tab's first control for its top panel: the control is not announced.
        if self._tab_menu_tab:
            panel = top_panel.panel_after_tab_menu(self._tab_menu_tab, obj.processHandle, self.language)
            if panel is not None and top_panel.is_beside_panel(panel, obj.windowHandle):
                return
        nextHandler()

    def chooseNVDAObjectOverlayClasses(self, obj, clsList):
        if not isinstance(obj, IAccessible):
            return
        hwnd, window_class, child_id = obj.windowHandle, obj.windowClassName, obj.IAccessibleChildID
        # The client object of the window, not its window object.
        client = child_id == 0 and obj.IAccessibleRole != oleacc.ROLE_SYSTEM_WINDOW
        if child_id == 0 and obj.IAccessibleRole == oleacc.ROLE_SYSTEM_CLIENT and dialogs.is_dialog(hwnd):
            if explorer.is_crumb_popup(hwnd):
                clsList.insert(0, explorer.CrumbPopup)
            else:
                clsList.insert(
                    0,
                    cover_art.DIALOG_CLASSES.get(window_class)
                    or dialogs.DIALOG_CLASSES.get(window_class, dialogs.EzcdDialog),
                )
        elif window_class == "TProgressBar":
            if convert_window.bar_kind(hwnd) == convert_window.Bar.TOTAL:
                clsList.insert(0, convert_window.TotalProgressBar)
        elif window_class == "TEdit" and client and counters.is_counter(hwnd):
            clsList.insert(0, counters.CounterSpinBox)
        elif window_class in metadata.FIELD_CLASSES and client and metadata.is_metadata_field(hwnd):
            clsList.insert(0, metadata.MetadataField)
        elif window_class in names.BUTTON_CLASSES:
            if client:
                clsList.insert(0, names.CaptionedButton)
                if filename_preview.is_tag(hwnd):
                    clsList.insert(0, filename_preview.TagButton)
        elif window_class == "ComboBox":
            if client and names.is_combo_box_ex_child(hwnd):
                clsList.insert(0, names.Captioned)
            elif client and explorer.is_path_field(hwnd):
                clsList.insert(0, explorer.PathComboBox)
        elif window_class in captions.CLASSES:
            if client:
                if window_class == "TJamShellList":
                    clsList.insert(0, explorer.FolderList)
                elif window_class in captions.SLIDER_CLASSES and sliders.value_field(hwnd):
                    clsList.insert(0, sliders.FieldSlider)
                else:
                    clsList.insert(0, names.Captioned)
                if player.is_player_slider(hwnd):
                    clsList.insert(0, player.PlayerSlider)
                if cards.card_panel_of(hwnd):
                    clsList.insert(0, cards.CardControl)
            elif child_id > 0 and window_class in list_items.CLASSES:
                clsList.insert(0, list_items.item_class(hwnd))
        elif window_class in explorer.CRUMB_LIST_CLASSES:
            if client:
                clsList.insert(0, explorer.CrumbList)
            elif child_id > 0:
                clsList.insert(0, explorer.CrumbItem)
        elif window_class == "TJamShellBreadCrumbBar":
            if client:
                clsList.insert(0, explorer.PathBar)
        elif window_class == "Edit":
            if client and explorer.is_path_field(hwnd):
                clsList.insert(0, explorer.PathEdit)
            elif client and names.is_combo_box_edit(hwnd):
                clsList.insert(0, names.ComboBoxEdit)
        elif window_class == cover_art.COVER_CLASS:
            if client:
                clsList.insert(0, cover_art.CoverArt)
        elif window_class == "TVTEdit":
            if file_lists.is_main_list_editor(hwnd):
                clsList.insert(0, cells.CellEditor)
        elif window_class == "TVirtualStringTree" and child_id == 0:
            self._choose_list_classes(obj, clsList)
        elif window_class == "TMainform":
            if child_id == 0:
                clsList.insert(0, cells.BetweenEditors)
        elif window_class == "TPageControl" and client:
            if burner_pages.is_pages(hwnd):
                clsList.insert(0, burner_pages.BurnerPages)
            elif top_panel.is_main_tab_labels(hwnd):
                clsList.insert(0, top_panel.TabLabels)
        elif window_class == "TTabSheet":
            if top_panel.is_main_window_tab(hwnd):
                clsList.insert(0, top_panel.MainWindowTab)
        elif window_class == "TPanel" and child_id == 0:
            if client and rating.is_stop(hwnd):
                clsList.insert(0, rating.RatingSlider)
            elif client and filename_preview.is_settings_stop(hwnd):
                clsList.insert(0, filename_preview.SettingsButton)
            elif top_panel.read_top_panel(hwnd, obj.processHandle, self.language) is not None:
                clsList.insert(0, top_panel.TopPanelWindow)
            elif explorer.is_hidden_explorer_row(hwnd):
                clsList.insert(0, explorer.HiddenExplorerRow)
            elif ContentGenericClient in clsList:
                clsList.insert(0, panels.TextPanel)
        elif window_class in styles.SCROLL_BAR_COVER_CLASSES:
            if child_id == 0:
                clsList.insert(0, styles.ScrollBarCover)
        elif window_class == "#32768":
            role = obj.IAccessibleRole
            if client and role == oleacc.ROLE_SYSTEM_MENUPOPUP:
                clsList.insert(0, menus.Menu)
            elif child_id > 0 or role == oleacc.ROLE_SYSTEM_MENUITEM:
                clsList.insert(0, menus.MenuItem)
        elif window_class == "TToolBar":
            stop = (
                top_panel.panel_of(hwnd, obj.processHandle, self.language)
                or explorer.stop_of(hwnd, obj.processHandle, self.language)
                or tray.stop_of(hwnd, obj.processHandle, self.language)
                or player.stop_of(hwnd, obj.processHandle, self.language)
            )
            overlay = None if stop is None else toolbar_stops.overlay_class(obj, stop)
            if overlay is not None:
                clsList.insert(0, overlay)
        # Added to what the window class gives: these forms hold controls of several classes.
        # The items of a list have focus in place of the list.
        if (client or child_id > 0) and tab_order.form_of(hwnd):
            clsList.insert(0, tab_order.ScreenOrderControl)
        if client and options.form_of(hwnd):
            clsList.insert(0, options.OptionsControl)
        # Any window may hold controls without windows.
        if child_id == 0:
            clsList.insert(0, windowless.Holder if client else windowless.Sibling)

    def _choose_list_classes(self, obj, clsList):
        role = obj.IAccessibleRole
        if file_lists.is_main_window_list(obj.windowHandle):
            if role == oleacc.ROLE_SYSTEM_OUTLINEITEM:
                clsList.insert(0, file_lists.MainFileListItem)
                return
            if role == oleacc.ROLE_SYSTEM_OUTLINE:
                clsList.insert(0, file_lists.MainWindowList)
            # The list itself, or a file as ezcd shows it while busy.
            clsList.insert(0, cells.BetweenEditors)
        elif role == oleacc.ROLE_SYSTEM_OUTLINEITEM:
            clsList.insert(0, file_lists.TreeItem)
        elif role == oleacc.ROLE_SYSTEM_OUTLINE:
            if file_lists.is_conversion_list(obj.windowHandle):
                clsList.insert(0, file_lists.ConversionFileList)
            else:
                clsList.insert(0, file_lists.DialogList)
