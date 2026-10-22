# Copyright (C) 2026 Rosgardius
# This file is covered by the GNU General Public License.
# See the file COPYING.txt for more details.

"""App module for EZ CD Audio Converter (ezcd.exe)."""

import ctypes
import time
from collections.abc import Hashable
from ctypes.wintypes import DWORD

import addonHandler
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
)
from .language import LanguageFiles

addonHandler.initTranslation()

PROCESS_QUERY_LIMITED_INFORMATION = 0x1000
# Seconds from pressing View Explorer to the focus ezcd moves as it hides the button.
_TOGGLE_FOCUS_TIMEOUT = 1.5
_MENU_CLASS = "#32768"
_MAX_PATH_LENGTH = 32767


class AppModule(appModuleHandler.AppModule):
    # Translators: The name of this add-on's category in NVDA's Input Gestures dialog.
    scriptCategory = _("EZ CD Audio Converter")

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
        handle = winKernel.openProcess(PROCESS_QUERY_LIMITED_INFORMATION, False, self.processID)
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

    def pass_focus(self, hwnd: int) -> bool:
        """Moves ezcd's focus to the window for the key that follows, without NVDA reporting it."""
        self._passing = hwnd
        if toolbar.set_focus(hwnd):
            return True
        self._passing = 0
        return False

    def explorer_toggled(self, toolbar_hwnd: int):
        """View Explorer is being pressed on the toolbar: ezcd will hide it and show the other one."""
        self._explorer_toggle = toolbar_hwnd
        self._toggle_pressed_at = time.monotonic()

    def _toolbar_passed(self, window: int, previous: int, tab_key: int) -> int:
        """The explorer's toolbar that Tab or Shift+Tab passed by, once for the focus and its ancestors."""
        if not tab_key:
            return 0
        key = (window, previous, tab_key)
        if self._passed_toolbar[0] != key:
            self._passed_toolbar = (key, explorer.toolbar_passed(window, previous, tab_key == 1))
        return self._passed_toolbar[1]

    def _note_gesture(self, gesture) -> bool:
        # Called in NVDA's keyboard hook thread for every gesture, in any application.
        is_key = isinstance(gesture, KeyboardInputGesture)
        self._tab_key = 0
        self._passing = 0
        self._passed_toolbar = (None, 0)
        if is_key and gesture.vkCode == winUser.VK_TAB:
            modifiers = gesture.modifierNames
            self._tab_key = 1 if not modifiers else -1 if modifiers == ["shift"] else 0
        if is_key:
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
        if self._tab_menu_tab and obj.windowClassName != _MENU_CLASS:
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
        if tab_key == 1 and previous and obj.windowClassName == top_panel.PAGE_CONTROL_CLASS:
            panel = top_panel.panel_left_by_tab(obj.windowHandle, previous, obj.processHandle, self.language)
            if panel is not None and toolbar_stops.focus_button(
                self, panel, panel.entry(self.remembered_buttons)
            ):
                self._tab_kept = True
                return
        # VCL skips the explorer's toolbars; stop at the one that Tab or Shift+Tab passed by.
        passed = self._toolbar_passed(obj.windowHandle, previous, tab_key)
        if passed:
            stop = explorer.stop_of(passed, obj.processHandle, self.language)
            if stop is not None and toolbar_stops.focus_button(
                self, stop, stop.entry(self.remembered_buttons)
            ):
                # Shift+Tab from the tab's first control passed by the tab labels.
                self._tab_kept = True
                return
        nextHandler()

    def event_nameChange(self, obj, nextHandler):
        if obj.windowClassName == file_lists.TREE_CLASS:
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
        if obj.windowClassName == convert_window.PROGRESS_BAR_CLASS:
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
            obj.windowClassName == top_panel.TOOLBAR_CLASS
            and time.monotonic() - self._toggle_pressed_at < _TOGGLE_FOCUS_TIMEOUT
        ):
            return
        nextHandler()

    def _get_statusBar(self):
        window = winUser.getAncestor(api.getForegroundObject().windowHandle, winUser.GA_ROOT)
        panel = convert_window.summary_panel(window)
        if panel is None:
            raise NotImplementedError
        return getNVDAObjectFromEvent(panel, winUser.OBJID_CLIENT, 0)

    def getStatusBarText(self, obj):
        window = winUser.getAncestor(obj.windowHandle, winUser.GA_ROOT)
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
        if self._tab_kept and obj.windowClassName in (top_panel.TAB_CLASS, top_panel.PAGE_CONTROL_CLASS):
            return
        # Focus is passing by, or about to go on to a toolbar of the explorer: the control is not announced.
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
        if (
            obj.IAccessibleChildID == 0
            and obj.IAccessibleRole == oleacc.ROLE_SYSTEM_CLIENT
            and dialogs.is_dialog(obj.windowHandle)
        ):
            clsList.insert(0, dialogs.EzcdDialog)
            return
        if obj.windowClassName == convert_window.PROGRESS_BAR_CLASS:
            if convert_window.bar_kind(obj.windowHandle) == convert_window.Bar.TOTAL:
                clsList.insert(0, convert_window.TotalProgressBar)
            return
        if (
            obj.windowClassName == converters.EDIT_CLASS
            and obj.IAccessibleChildID == 0
            and converters.is_converters_edit(obj.windowHandle)
        ):
            if obj.IAccessibleRole == oleacc.ROLE_SYSTEM_WINDOW:
                clsList.insert(0, converters.ConvertersSpinWindow)
            else:
                clsList.insert(0, converters.ConvertersSpinBox)
            return
        if (
            obj.windowClassName in metadata.FIELD_CLASSES
            and obj.IAccessibleChildID == 0
            and obj.IAccessibleRole != oleacc.ROLE_SYSTEM_WINDOW
            and metadata.is_metadata_field(obj.windowHandle)
        ):
            clsList.insert(0, metadata.MetadataField)
            return
        if obj.windowClassName in names.BUTTON_CLASSES:
            if obj.IAccessibleChildID == 0 and obj.IAccessibleRole != oleacc.ROLE_SYSTEM_WINDOW:
                clsList.insert(0, names.CaptionedButton)
            return
        if obj.windowClassName == names.COMBO_BOX_EX_CHILD_CLASS:
            if (
                obj.IAccessibleChildID == 0
                and obj.IAccessibleRole != oleacc.ROLE_SYSTEM_WINDOW
                and names.is_combo_box_ex_child(obj.windowHandle)
            ):
                clsList.insert(0, names.Captioned)
            return
        if obj.windowClassName in captions.CLASSES:
            if obj.IAccessibleChildID == 0 and obj.IAccessibleRole != oleacc.ROLE_SYSTEM_WINDOW:
                clsList.insert(0, names.Captioned)
            elif obj.IAccessibleChildID > 0 and obj.windowClassName in list_items.CLASSES:
                clsList.insert(0, list_items.ListItem)
            return
        if obj.windowClassName == metadata.COVER_CLASS:
            if obj.IAccessibleChildID == 0 and obj.IAccessibleRole != oleacc.ROLE_SYSTEM_WINDOW:
                clsList.insert(0, metadata.CoverArt)
            return
        if obj.windowClassName == file_lists.EDITOR_CLASS:
            if cells.is_main_list_editor(obj.windowHandle):
                clsList.insert(0, cells.CellEditor)
            return
        if obj.windowClassName == file_lists.TREE_CLASS and obj.IAccessibleChildID == 0:
            if file_lists.is_main_window_list(obj.windowHandle):
                if obj.IAccessibleRole == oleacc.ROLE_SYSTEM_OUTLINEITEM:
                    clsList.insert(0, file_lists.MainFileListItem)
                else:
                    if obj.IAccessibleRole == oleacc.ROLE_SYSTEM_OUTLINE:
                        clsList.insert(0, file_lists.MainWindowList)
                    # The list itself, or a file as ezcd shows it while busy.
                    clsList.insert(0, cells.BetweenEditors)
            elif obj.IAccessibleRole == oleacc.ROLE_SYSTEM_OUTLINEITEM:
                clsList.insert(0, file_lists.TreeItem)
            elif obj.IAccessibleRole == oleacc.ROLE_SYSTEM_OUTLINE:
                if file_lists.is_conversion_list(obj.windowHandle):
                    clsList.insert(0, file_lists.ConversionFileList)
                else:
                    clsList.insert(0, file_lists.DialogList)
            return
        if obj.windowClassName == top_panel.MAIN_WINDOW_CLASS:
            if obj.IAccessibleChildID == 0:
                clsList.insert(0, cells.BetweenEditors)
            return
        if obj.windowClassName == top_panel.PAGE_CONTROL_CLASS:
            clsList.insert(0, top_panel.TabLabels)
            return
        if obj.windowClassName == top_panel.TAB_CLASS:
            if top_panel.is_main_window_tab(obj.windowHandle):
                clsList.insert(0, top_panel.MainWindowTab)
            return
        if obj.windowClassName == top_panel.PANEL_CLASS:
            if obj.IAccessibleChildID != 0:
                return
            if top_panel.read_top_panel(obj.windowHandle, obj.processHandle, self.language) is not None:
                clsList.insert(0, top_panel.TopPanelWindow)
            elif explorer.is_hidden_explorer_row(obj.windowHandle):
                clsList.insert(0, explorer.HiddenExplorerRow)
            return
        if obj.windowClassName != top_panel.TOOLBAR_CLASS:
            return
        panel = top_panel.panel_of(obj.windowHandle, obj.processHandle, self.language)
        if panel is None:
            self._choose_explorer_classes(obj, clsList)
            return
        if obj.IAccessibleChildID == 0:
            clsList.insert(0, top_panel.TopPanelToolbarWindow)
            return
        button = panel.find(obj.windowHandle, obj.IAccessibleChildID - 1)
        if button is None:
            return
        if button == panel.main and panel.main_shortcut:
            clsList.insert(0, top_panel.MainButton)
        elif panel.has_menu(button):
            clsList.insert(0, top_panel.MenuButton)
        else:
            clsList.insert(0, top_panel.TopPanelButton)

    def _choose_explorer_classes(self, obj, clsList):
        stop = explorer.stop_of(obj.windowHandle, obj.processHandle, self.language)
        if stop is None:
            return
        child_id = toolbar_stops.button_child_id(obj)
        if child_id == 0:
            clsList.insert(0, explorer.ExplorerToolbarWindow)
            return
        button = stop.find(obj.windowHandle, child_id - 1)
        if button is not None:
            clsList.insert(
                0, explorer.ExplorerMenuButton if stop.has_menu(button) else explorer.ExplorerButton
            )
