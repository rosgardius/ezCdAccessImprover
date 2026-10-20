# Copyright (C) 2026 Rosgardius
# This file is covered by the GNU General Public License.
# See the file COPYING.txt for more details.

"""App module for EZ CD Audio Converter (ezcd.exe)."""

import ctypes
from ctypes.wintypes import DWORD

import addonHandler
import api
import appModuleHandler
import braille
import eventHandler
import inputCore
import oleacc
import winKernel
import winUser
from keyboardHandler import KeyboardInputGesture
from logHandler import log
from NVDAObjects.IAccessible import IAccessible, getNVDAObjectFromEvent
from winBindings import kernel32

from . import convert_window, converters, file_lists, top_panel
from .language import LanguageFiles

addonHandler.initTranslation()

PROCESS_QUERY_LIMITED_INFORMATION = 0x1000
_MENU_CLASS = "#32768"
_MAX_PATH_LENGTH = 32767


class AppModule(appModuleHandler.AppModule):
    # Translators: The name of this add-on's category in NVDA's Input Gestures dialog.
    scriptCategory = _("EZ CD Audio Converter")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.language = LanguageFiles(self._executable_path())
        self.remembered_buttons: dict[int, tuple[int, int]] = {}
        """``PanelButton.key`` of the last focused button of each top panel, by ``TopPanel.key``."""
        self._focus_window = 0
        self._tab_menu_tab = 0
        self._tab_pressed = False
        self._tab_kept = False
        self._conversion_status = convert_window.ConversionStatus()
        self.converter_steps = converters.StepAnnouncer()
        self.closed_editor = file_lists.ClosedEditor()
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

    def _note_gesture(self, gesture) -> bool:
        # Called in NVDA's keyboard hook thread for every gesture, in any application.
        is_key = isinstance(gesture, KeyboardInputGesture)
        self._tab_pressed = is_key and gesture.vkCode == winUser.VK_TAB and not gesture.modifiers
        if is_key:
            self.closed_editor.note_key(gesture)
        return True

    def event_gainFocus(self, obj, nextHandler):
        previous, self._focus_window = self._focus_window, obj.windowHandle
        tab_pressed, self._tab_pressed = self._tab_pressed, False
        self._tab_kept = False
        if self.closed_editor.is_left_focus(obj):
            braille.handler.handleGainFocus(obj)
            return
        if self.closed_editor.is_unasked(obj):
            self.closed_editor.close(obj.windowHandle)
            return
        if self._tab_menu_tab and obj.windowClassName != _MENU_CLASS:
            # Whichever tab was chosen, VCL puts focus on the tab's first control.
            panel = top_panel.panel_after_tab_menu(self._tab_menu_tab, obj.processHandle, self.language)
            self._tab_menu_tab = 0
            if (
                panel is not None
                and top_panel.is_beside_panel(panel, obj.windowHandle)
                and top_panel.focus_button(self, panel, panel.buttons[0])
            ):
                return
        # VCL skips the top panel on Tab; stop at it instead of the tab labels.
        if tab_pressed and previous and obj.windowClassName == top_panel.PAGE_CONTROL_CLASS:
            panel = top_panel.panel_left_by_tab(obj.windowHandle, previous, obj.processHandle, self.language)
            if panel is not None and top_panel.focus_button(
                self, panel, panel.entry(self.remembered_buttons)
            ):
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

    def event_focusEntered(self, obj, nextHandler):
        # Focus stayed in the tab: the tab labels in between were not announced.
        if self._tab_kept and obj.windowClassName == top_panel.TAB_CLASS:
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
        if obj.windowClassName == convert_window.PROGRESS_BAR_CLASS:
            if convert_window.bar_kind(obj.windowHandle) == convert_window.Bar.TOTAL:
                clsList.insert(0, convert_window.TotalProgressBar)
            return
        if obj.windowClassName == converters.EDIT_CLASS:
            if obj.IAccessibleChildID == 0 and converters.is_converters_edit(obj.windowHandle):
                if obj.IAccessibleRole == oleacc.ROLE_SYSTEM_WINDOW:
                    clsList.insert(0, converters.ConvertersSpinWindow)
                else:
                    clsList.insert(0, converters.ConvertersSpinBox)
            return
        if obj.windowClassName == file_lists.TREE_CLASS and obj.IAccessibleChildID == 0:
            if obj.IAccessibleRole == oleacc.ROLE_SYSTEM_OUTLINEITEM:
                if file_lists.is_conversion_list(obj.windowHandle):
                    clsList.insert(0, file_lists.FileListItem)
                else:
                    clsList.insert(0, file_lists.MainFileListItem)
            elif obj.IAccessibleRole == oleacc.ROLE_SYSTEM_OUTLINE and file_lists.is_conversion_list(
                obj.windowHandle
            ):
                clsList.insert(0, file_lists.ConversionFileList)
            return
        if obj.windowClassName == top_panel.PAGE_CONTROL_CLASS:
            clsList.insert(0, top_panel.TabLabels)
            return
        if obj.windowClassName == top_panel.TAB_CLASS:
            if top_panel.is_main_window_tab(obj.windowHandle):
                clsList.insert(0, top_panel.MainWindowTab)
            return
        if obj.windowClassName == top_panel.PANEL_CLASS:
            panel = top_panel.read_top_panel(obj.windowHandle, obj.processHandle, self.language)
            if obj.IAccessibleChildID == 0 and panel is not None:
                clsList.insert(0, top_panel.TopPanelWindow)
            return
        if obj.windowClassName != top_panel.TOOLBAR_CLASS:
            return
        panel = top_panel.panel_of(obj.windowHandle, obj.processHandle, self.language)
        if panel is None:
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
