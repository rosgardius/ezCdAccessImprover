"""The checks: each module registers its own as it is imported."""

from ..core import CHECKS
from . import dialogs, files, main_window

__all__ = ["CHECKS", "dialogs", "files", "main_window"]
