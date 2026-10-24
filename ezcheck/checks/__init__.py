"""The checks: each module registers its own as it is imported."""

from ..core import CHECKS
from . import files, main_window

__all__ = ["CHECKS", "files", "main_window"]
