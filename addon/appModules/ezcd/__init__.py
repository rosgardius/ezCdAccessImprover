# Copyright (C) 2026 Rosgardius
# This file is covered by the GNU General Public License.
# See the file COPYING.txt for more details.

"""App module for EZ CD Audio Converter (ezcd.exe)."""

import ctypes
from ctypes.wintypes import DWORD

import addonHandler
import appModuleHandler
import winKernel
from logHandler import log
from NVDAObjects.IAccessible import IAccessible
from winBindings import kernel32

from . import top_panel
from .language import LanguageFiles

addonHandler.initTranslation()

PROCESS_QUERY_LIMITED_INFORMATION = 0x1000
_MAX_PATH_LENGTH = 32767


class AppModule(appModuleHandler.AppModule):
    # Translators: The name of this add-on's category in NVDA's Input Gestures dialog.
    scriptCategory = _("EZ CD Audio Converter")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._language = LanguageFiles(self._executable_path())

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

    def chooseNVDAObjectOverlayClasses(self, obj, clsList):
        if not isinstance(obj, IAccessible) or obj.windowClassName != top_panel.TOOLBAR_CLASS:
            return
        found = top_panel.identify(obj.windowHandle, obj.processHandle, self._language)
        if found is None:
            return
        if obj.IAccessibleChildID == 0:
            clsList.insert(0, top_panel.TopPanelToolbarWindow)
        elif found.is_main:
            clsList.insert(0, top_panel.MainButton)
        else:
            clsList.insert(0, top_panel.TopPanelButton)
