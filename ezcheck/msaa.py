"""What MSAA gives screen readers for ezcd's windows, read from outside ezcd's process."""

import ctypes

import comtypes
import comtypes.client

_OBJID_CLIENT = 0xFFFFFFFC
_CHILDID_SELF = 0
_oleacc = ctypes.oledll.oleacc
_IAccessible = comtypes.client.GetModule("oleacc.dll").IAccessible


def name(hwnd: int) -> str:
    """The name MSAA gives the window's client object; empty if none or if MSAA does not answer."""
    accessible = ctypes.POINTER(_IAccessible)()
    try:
        _oleacc.AccessibleObjectFromWindow(
            hwnd, _OBJID_CLIENT, ctypes.byref(_IAccessible._iid_), ctypes.byref(accessible)
        )
        return accessible.accName(_CHILDID_SELF) or ""
    except (OSError, comtypes.COMError):
        return ""
