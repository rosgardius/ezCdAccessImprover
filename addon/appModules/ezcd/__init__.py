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
from NVDAObjects.IAccessible import IAccessible, getNVDAObjectFromEvent
from speech.speech import speakMessage
from winBindings import kernel32

from . import (
    captions,
    cells,
    convert_window,
    converters,
    dialogs,
    explorer,
    file_lists,
    list_items,
    metadata,
    names,
    toolbar,
    toolbar_stops,
    top_panel,
    tray,
)
from .language import LanguageFiles
from .windows import root

_PROCESS_QUERY_LIMITED_INFORMATION = 0x1000
# Seconds from pressing View Explorer to the focus ezcd moves as it hides the button.
_TOGGLE_FOCUS_TIMEOUT = 1.5
_MAX_PATH_LENGTH = 32767


class AppModule(appModuleHandler.AppModule):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.language = LanguageFiles(self._executable_path())
        self.remembered_buttons: dict[Hashable, tuple[int, int]] = {}
        """``StopButton.key`` of the last focused button of each toolbar stop, by ``ToolbarStop.key``."""
        self._focus_window = 0
        self._tab_menu_tab = 0
        self._tab_key = 0
        """1 after Tab, -1 after Shift+Tab, until the next focus or key."""
        self._passing = 0
        self._passed_toolbar: tuple[tuple[int, int, int] | None, int] = (None, 0)
        """The last answer of ``_toolbar_passed``, until the next key."""
        self._explorer_toggle = 0
        """The toolbar on which View Explorer was pressed, until the next focus."""
        self._toggle_pressed_at = 0.0
        self._quiet_toggle = 0
        """The toolbar of View Explorer that gets focus after the press: only its state is reported."""
        self._tab_kept = False
        self._conversion_status = convert_window.ConversionStatus()
        self.converter_steps = converters.StepAnnouncer()
        self.closed_editor = file_lists.ClosedEditor()
        self.cells = cells.CellTable(self.language)
        inputCore.decide_executeGesture.register(self._note_gesture)

    def terminate(self):
        inputCore.decide_executeGesture.unregister(self._note_gesture)
        self.converter_steps.terminate()
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

    def tab_menu_opened(self, tab: int):
        """The menu that switches the main window's tab is opening on the tab's top panel."""
        self._tab_menu_tab = tab

    def pass_focus(self, hwnd: int):
        """Moves ezcd's focus to the window for the key that follows, without NVDA reporting it."""
        self._passing = hwnd
        if not toolbar.set_focus(hwnd):
            self._passing = 0

    def explorer_toggled(self, toolbar_hwnd: int):
        """View Explorer is being pressed on the toolbar: ezcd will hide it and show the other one."""
        self._explorer_toggle = toolbar_hwnd
        self._toggle_pressed_at = time.monotonic()

    def _toolbar_passed(self, window: int, previous: int, tab_key: int) -> int:
        """The toolbar of the explorer or the tray that Tab or Shift+Tab passed by, once for the focus and
        its ancestors."""
        if not tab_key:
            return 0
        key = (window, previous, tab_key)
        if self._passed_toolbar[0] != key:
            forward = tab_key == 1
            passed = explorer.toolbar_passed(window, previous, forward) or tray.toolbar_passed(
                window, previous, forward
            )
            self._passed_toolbar = (key, passed)
        return self._passed_toolbar[1]

    def _note_gesture(self, gesture) -> bool:
        # Called in NVDA's keyboard hook thread for every gesture, in any application.
        self._tab_key = 0
        self._passing = 0
        self._passed_toolbar = (None, 0)
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
        previous, self._focus_window = self._focus_window, obj.windowHandle
        tab_key, self._tab_key = self._tab_key, 0
        passing, self._passing = self._passing, 0
        self._tab_kept = False
        if passing and obj.windowHandle == passing:
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
        if self.closed_editor.is_left_focus(obj):
            braille.handler.handleGainFocus(obj)
            return
        if self.closed_editor.is_unasked(obj):
            self.closed_editor.close(obj.windowHandle)
            return
        if self.cells.handle_focus(obj, self.helperLocalBindingHandle):
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
        # VCL skips the toolbars of the explorer and the tray; stop at the one Tab or Shift+Tab passed by.
        passed = self._toolbar_passed(obj.windowHandle, previous, tab_key)
        if passed and self._enter_stop(
            explorer.stop_of(passed, obj.processHandle, self.language)
            or tray.stop_of(passed, obj.processHandle, self.language)
        ):
            return
        nextHandler()

    def _enter_stop(self, stop: toolbar_stops.ToolbarStop | None) -> bool:
        """Moves focus to the stop's remembered button; ``False`` if it did not move.

        Focus stays in the tab, but may have passed by the tab labels, as Shift+Tab from its first control.
        """
        if stop is None or not toolbar_stops.focus_button(self, stop, stop.entry(self.remembered_buttons)):
            return False
        self._tab_kept = True
        return True

    def event_nameChange(self, obj, nextHandler):
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
        nextHandler()

    def event_stateChange(self, obj, nextHandler):
        # View Explorer changes its state as ezcd hides it; the state of the other one comes with the focus.
        if (
            obj.windowClassName == "TToolBar"
            and time.monotonic() - self._toggle_pressed_at < _TOGGLE_FOCUS_TIMEOUT
        ):
            return
        nextHandler()

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
        nextHandler()

    def event_focusEntered(self, obj, nextHandler):
        if self.cells.is_coming_back(obj):
            return
        # Focus stayed in the tab: the tab labels or the main form in between were not announced.
        if self._tab_kept and obj.windowClassName in ("TTabSheet", "TPageControl"):
            return
        # Focus is passing by, or about to go on to a toolbar Tab passed by: the control is not announced.
        focus = api.getFocusObject().windowHandle
        if (focus and focus in (self._passing, self._quiet_toggle)) or (
            self._toolbar_passed(focus, self._focus_window, self._tab_key)
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
            clsList.insert(0, dialogs.EzcdDialog)
        elif window_class == "TProgressBar":
            if convert_window.bar_kind(hwnd) == convert_window.Bar.TOTAL:
                clsList.insert(0, convert_window.TotalProgressBar)
        elif window_class == "TEdit" and child_id == 0 and converters.is_converters_edit(hwnd):
            clsList.insert(0, converters.ConvertersSpinBox if client else converters.ConvertersSpinWindow)
        elif window_class in metadata.FIELD_CLASSES and client and metadata.is_metadata_field(hwnd):
            clsList.insert(0, metadata.MetadataField)
        elif window_class in names.BUTTON_CLASSES:
            if client:
                clsList.insert(0, names.CaptionedButton)
        elif window_class == "ComboBox":
            if client and names.is_combo_box_ex_child(hwnd):
                clsList.insert(0, names.Captioned)
        elif window_class in captions.CLASSES:
            if client:
                clsList.insert(0, names.Captioned)
            elif child_id > 0 and window_class in list_items.CLASSES:
                clsList.insert(0, list_items.ListItem)
        elif window_class == metadata.COVER_CLASS:
            if client:
                clsList.insert(0, metadata.CoverArt)
        elif window_class == "TVTEdit":
            if file_lists.is_main_list_editor(hwnd):
                clsList.insert(0, cells.CellEditor)
        elif window_class == "TVirtualStringTree" and child_id == 0:
            self._choose_list_classes(obj, clsList)
        elif window_class == "TMainform":
            if child_id == 0:
                clsList.insert(0, cells.BetweenEditors)
        elif window_class == "TPageControl":
            clsList.insert(0, top_panel.TabLabels)
        elif window_class == "TTabSheet":
            if top_panel.is_main_window_tab(hwnd):
                clsList.insert(0, top_panel.MainWindowTab)
        elif window_class == "TPanel" and child_id == 0:
            if top_panel.read_top_panel(hwnd, obj.processHandle, self.language) is not None:
                clsList.insert(0, top_panel.TopPanelWindow)
            elif explorer.is_hidden_explorer_row(hwnd):
                clsList.insert(0, explorer.HiddenExplorerRow)
        elif window_class == "TToolBar":
            stop = (
                top_panel.panel_of(hwnd, obj.processHandle, self.language)
                or explorer.stop_of(hwnd, obj.processHandle, self.language)
                or tray.stop_of(hwnd, obj.processHandle, self.language)
            )
            overlay = None if stop is None else toolbar_stops.overlay_class(obj, stop)
            if overlay is not None:
                clsList.insert(0, overlay)

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
