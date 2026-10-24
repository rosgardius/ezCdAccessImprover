"""The checks: each module registers its own as it is imported."""

from ..core import CHECKS
from . import audit, dialogs, files, main_window

__all__ = ["CHECKS", "audit", "dialogs", "files", "main_window"]
