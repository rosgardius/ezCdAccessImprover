"""The running EZ CD Audio Converter: its process, main window, version, language and what it shows."""

import ctypes
import functools
import os
import winreg
from dataclasses import dataclass

from . import win
from .addon import facts

MAIN_CLASS = "TMainform"
_EXECUTABLE = "ezcd.exe"
# The windows VCL styles lay over scroll bars: only the dark themes are styles.
_STYLE_CLASSES = frozenset(("TScrollingStyleHook.TScrollWindow", "TVclStyleScrollBarsHook.TScrollWindow"))


_ACCESS = win.PROCESS_QUERY_LIMITED_INFORMATION | win.PROCESS_VM_READ | win.PROCESS_VM_OPERATION


class Unavailable(Exception):
    """ezcd cannot be checked now; the message says why and what to do."""


@dataclass(frozen=True)
class Ezcd:
    process_id: int
    thread_id: int
    main: int
    """The main window."""
    path: str
    process: int
    """A handle that reads ezcd's memory and makes buffers in it, open while the checker runs."""

    @classmethod
    def find(cls) -> "Ezcd":
        """The running ezcd with its main window and no dialog open; raises ``Unavailable`` otherwise."""
        for hwnd in win.top_level_windows():
            if win.class_name(hwnd) != MAIN_CLASS:
                continue
            thread_id, process_id = win.thread_and_process(hwnd)
            process = win.open_process(process_id, _ACCESS)
            if not process:
                query = win.open_process(process_id, win.PROCESS_QUERY_LIMITED_INFORMATION)
                path = win.process_path(query) if query else ""
                if query:
                    win.close(query)
                if os.path.basename(path).lower() == _EXECUTABLE:
                    raise Unavailable(
                        "Windows refuses access to the memory of ezcd: it runs as administrator. "
                        "Run the checker as administrator too, or ezcd without it."
                    )
                continue
            path = win.process_path(process)
            if os.path.basename(path).lower() != _EXECUTABLE:
                win.close(process)
                continue
            ezcd = cls(process_id, thread_id, hwnd, path, process)
            ezcd.require_main_window()
            return ezcd
        raise Unavailable("EZ CD Audio Converter is not running: start it and run the checker again.")

    def require_main_window(self):
        """Raises ``Unavailable`` if ezcd shows a dialog or does not answer."""
        if win.send(self.main, win.WM_NULL) is None:
            raise Unavailable("ezcd does not answer messages: wait until it is idle and try again.")
        if not win.is_enabled(self.main):
            raise Unavailable("A dialog of ezcd is open: close it and run the checker again.")

    def close(self):
        win.close(self.process)

    def is_foreground(self) -> bool:
        foreground = win.user32.GetForegroundWindow()
        return bool(foreground) and win.thread_and_process(foreground)[1] == self.process_id

    def active_window(self) -> int:
        """ezcd's active window; 0 while ezcd has none."""
        return win.gui_info(self.thread_id).hwndActive or 0

    def read(self, address: int, target: ctypes.Array | ctypes.Structure):
        """Reads ezcd's memory; raises ``OSError`` if it cannot."""
        win.read_memory(self.process, address, target)

    def window_object(self, hwnd: int) -> int:
        """The address of the window's VCL object; 0 if it has none."""
        instance = win.user32.GetWindowLongPtrW(hwnd, win.GWLP_HINSTANCE)
        thread_id, _process_id = win.thread_and_process(hwnd)
        return win.user32.GetPropW(hwnd, facts.objects.window_property(instance, thread_id)) or 0

    def controls(self, hwnd: int, class_names: frozenset[str], offsets) -> list:
        """The window's ``facts.objects.Control``s of the VCL classes, read at the ``Vcl`` offsets; none if
        the window has no VCL object. Raises ``OSError`` if they cannot be read."""
        window = self.window_object(hwnd)
        return facts.objects.controls(self.read, window, class_names, offsets) if window else []

    @functools.cached_property
    def version(self) -> str | None:
        """The ProductVersion of ``ezcd.exe``; ``None`` if it has none."""
        return win.product_version(self.path)

    @functools.cached_property
    def language_files(self) -> dict[str, dict[int, str]]:
        """The strings of each language file, by its name without ``.uni``; none for a file that cannot be
        read."""
        try:
            paths = facts.language.files(self.path)
        except OSError:
            return {}
        found = {}
        for name, path in paths.items():
            try:
                found[name] = facts.language.strings(path)
            except (OSError, UnicodeError):
                found[name] = {}
        return found

    def tab_captions(self) -> set[str]:
        """The captions of the main window's tabs."""
        return {
            win.text(tab)
            for pages in win.children(self.main, "TPageControl")
            for tab in win.children(pages, "TTabSheet")
        } - {""}

    @functools.cached_property
    def language(self) -> str:
        """The name of the language file whose strings ezcd shows: the one with the most captions of the
        main window's tabs, of several the one of ezcd's settings; empty if none has any."""
        known = facts.select(self.version).facts
        tabs = known.strings
        numbers = (tabs.converter_tab.number, tabs.ripper_tab.number, tabs.burner_tab.number)
        captions = self.tab_captions()
        counts = {
            name: len(captions & {strings.get(n) for n in numbers})
            for name, strings in self.language_files.items()
        }
        most = max(counts.values(), default=0)
        if not most:
            return ""
        candidates = [name for name, count in counts.items() if count == most]
        setting = self._language_setting(known.language)
        return next((name for name in candidates if name == setting), candidates[0])

    def _language_setting(self, language) -> str:
        """The language file that ezcd's settings name; empty if none."""
        try:
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, language.registry_key) as key:
                value, _type = winreg.QueryValueEx(key, language.registry_value)
        except OSError:
            return ""
        number = language.name.number
        return next((n for n, s in self.language_files.items() if s.get(number) == str(value).strip()), "")

    @property
    def dpi(self) -> int:
        return win.dpi(self.main)

    @property
    def theme(self) -> str:
        """``dark`` while ezcd shows a VCL style, else ``light``."""
        return (
            "dark"
            if any(win.class_name(w) in _STYLE_CLASSES for w in win.descendants(self.main))
            else "light"
        )
