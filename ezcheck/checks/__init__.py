"""The checks: each module registers its own as it is imported."""

from ..core import CHECKS
from . import files

__all__ = ["CHECKS", "files"]
