# Copyright (C) 2026 Rosgardius
# This file is covered by the GNU General Public License.
# See the file COPYING.txt for more details.

"""App module for EZ CD Audio Converter (ezcd.exe)."""

import ctypes
from ctypes.wintypes import DWORD

import addonHandler
import appModuleHandler
import inputCore
import winKernel
import winUser
from keyboardHandler import KeyboardInputGesture
from logHandler import log
from NVDAObjects.IAccessible import IAccessible
from winBindings import kernel32

from . import toolbar, top_panel
from .language import LanguageFiles

addonHandler.initTranslation()

PROCESS_QUERY_LIMITED_INFORMATION = 0x1000
_MAX_PATH_LENGTH = 32767


class AppModule(appModuleHandler.AppModule):
    # Translators: The name of this add-on's category in NVDA's Input Gestures dialog.
    scriptCategory = _("EZ CD Audio Converter")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.language = LanguageFiles(self._executable_path())
        self.remembered_buttons: dict[int, int] = {}
        """The image of the last focused button of each top panel, by ``TopPanel.key``."""
        self._focus_window = 0
        self._tab_pressed = False
        self._tab_kept = False
        inputCore.decide_executeGesture.register(self._note_gesture)

    def terminate(self):
        inputCore.decide_executeGesture.unregister(self._note_gesture)
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

    def _note_gesture(self, gesture) -> bool:
        # Called in NVDA's keyboard hook thread for every gesture, in any application.
        self._tab_pressed = (
            isinstance(gesture, KeyboardInputGesture)
            and gesture.vkCode == winUser.VK_TAB
            and not gesture.modifiers
        )
        return True

    def event_gainFocus(self, obj, nextHandler):
        previous, self._focus_window = self._focus_window, obj.windowHandle
        tab_pressed, self._tab_pressed = self._tab_pressed, False
        self._tab_kept = False
        # VCL skips the top panel on Tab; stop at it instead of the tab labels.
        if tab_pressed and previous and obj.windowClassName == top_panel.PAGE_CONTROL_CLASS:
            panel = top_panel.panel_left_by_tab(obj.windowHandle, previous, obj.processHandle, self.language)
            if panel is not None and toolbar.set_focus(panel.entry(self.remembered_buttons)):
                self._tab_kept = True
                return
        nextHandler()

    def event_focusEntered(self, obj, nextHandler):
        # Focus stayed in the tab: the tab labels in between were not announced.
        if self._tab_kept and obj.windowClassName == top_panel.TAB_CLASS:
            return
        nextHandler()

    def chooseNVDAObjectOverlayClasses(self, obj, clsList):
        if not isinstance(obj, IAccessible):
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
        elif panel.main == obj.windowHandle:
            clsList.insert(0, top_panel.MainButton)
        else:
            clsList.insert(0, top_panel.TopPanelButton)
