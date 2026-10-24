# Copyright (C) 2026 Rosgardius
# This file is covered by the GNU General Public License.
# See the file COPYING.txt for more details.

"""VCL objects in ezcd's memory, read by a function given: the controls of a window without windows."""

import ctypes
from collections.abc import Callable
from dataclasses import dataclass

type Read = Callable[[int, ctypes.Array | ctypes.Structure], None]
"""Reads ezcd's memory at the address into the object; raises ``OSError`` if it cannot."""

_MAX_TEXT_LENGTH = 1024


@dataclass(frozen=True)
class Vcl:
    """Offsets in the objects of VCL, ezcd's framework, in bytes; ezcd is a 64-bit program."""

    vmt_class_name: int
    """Before the virtual method table an object points to: the pointer to the class name, a short string."""
    controls: int
    """TWinControl.FControls: a TList of the controls without windows, nil before the first."""
    list_items: int
    """TList: the pointer to the array of items."""
    list_count: int
    """TList: the number of items."""
    bounds: int
    """TControl: FLeft, FTop, FWidth, FHeight in the parent's client pixels."""
    visible_enabled: int
    """TControl: FVisible, then FEnabled."""
    on_click: int
    """TControl.FOnClick: the code pointer, nil without a handler."""
    text: int
    """TControl.FText: the caption, a null-terminated string made by StrAlloc, which keeps the size of the
    block in bytes, these 4 included, right before it."""
    rating_stars: int
    """TRating: the number of stars."""
    check_state: int
    """The object of the check box of a ``TCheckListBox`` item, whose address is the item's data: after the
    pointer to its class and the item's own data comes the state, 0 unchecked, 1 checked, 2 grayed."""


class _Bounds(ctypes.Structure):
    _fields_ = (
        ("left", ctypes.c_int32),
        ("top", ctypes.c_int32),
        ("width", ctypes.c_int32),
        ("height", ctypes.c_int32),
    )


@dataclass(frozen=True)
class Control:
    """A control without a window."""

    address: int
    class_name: str
    left: int
    """In the client pixels of the window holding it, as ``top``."""
    top: int
    width: int
    height: int
    visible: bool
    enabled: bool
    on_click: bool
    """Whether the control has a handler of clicks."""
    text: str
    """The caption, empty if none."""


def window_property(instance: int, thread_id: int) -> str:
    """The name of the window property holding the address of the window's VCL object: VCL names it after
    the module (its instance handle) and the thread that made the window."""
    return f"ControlOfs{instance:08X}{thread_id:08X}"


def pointer(read: Read, address: int) -> int:
    value = (ctypes.c_uint64 * 1)()
    read(address, value)
    return value[0]


def class_name(read: Read, address: int, offsets: Vcl) -> str:
    name = pointer(read, pointer(read, address) + offsets.vmt_class_name)
    length = (ctypes.c_ubyte * 1)()
    read(name, length)
    text = (ctypes.c_char * length[0])()
    read(name + 1, text)
    return text.raw.decode("latin-1")


def text(read: Read, address: int, offsets: Vcl) -> str:
    """The control's caption; empty if none or if it cannot be read, as the offset may be another one in
    another version of ezcd."""
    try:
        caption = pointer(read, address + offsets.text)
        if not caption:
            return ""
        size = (ctypes.c_uint32 * 1)()
        read(caption - 4, size)
        length = (size[0] - 4) // 2 - 1
        if not 0 < length <= _MAX_TEXT_LENGTH:
            return ""
        chars = (ctypes.c_wchar * length)()
        read(caption, chars)
    except OSError:
        return ""
    return chars.value


def controls(read: Read, window: int, class_names: frozenset[str], offsets: Vcl) -> list[Control]:
    """The controls without windows of the VCL classes in the window's object at the address; raises
    ``OSError`` if they cannot be read."""
    control_list = pointer(read, window + offsets.controls)
    if not control_list:
        return []
    count = (ctypes.c_int32 * 1)()
    read(control_list + offsets.list_count, count)
    if count[0] <= 0:
        return []
    items = (ctypes.c_uint64 * count[0])()
    read(pointer(read, control_list + offsets.list_items), items)
    found = []
    for address in items:
        name = class_name(read, address, offsets)
        if name not in class_names:
            continue
        bounds = _Bounds()
        read(address + offsets.bounds, bounds)
        flags = (ctypes.c_ubyte * 2)()
        read(address + offsets.visible_enabled, flags)
        visible, enabled = (bool(flag) for flag in flags)
        on_click = bool(pointer(read, address + offsets.on_click))
        found.append(
            Control(
                address,
                name,
                bounds.left,
                bounds.top,
                bounds.width,
                bounds.height,
                visible,
                enabled,
                on_click,
                text(read, address, offsets),
            )
        )
    return found
