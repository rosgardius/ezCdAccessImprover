# Copyright (C) 2026 Rosgardius
# This file is covered by the GNU General Public License.
# See the file COPYING.txt for more details.

"""The set of facts for the version of ezcd that the app module runs with."""

import fileUtils
from logHandler import log

from .facts import VERSIONS, Facts, Match, select

facts: Facts = VERSIONS[-1]
"""Chosen by ``choose`` as the app module starts; ezcd's processes on one machine run one version."""


def choose(app_path: str | None):
    """Takes the set of facts for the version of ``ezcd.exe`` at the path.

    A version without its own set gets the nearest one and a line in the log; the user is not told: what
    breaks, breaks as it would without sets of facts.
    """
    global facts
    product_version = None
    if app_path:
        try:
            product_version = fileUtils.getFileVersionInfo(app_path, "ProductVersion")["ProductVersion"]
        except RuntimeError:
            log.debugWarning(f"No version of {app_path}", exc_info=True)
    selection = select(product_version)
    facts = selection.facts
    if selection.match != Match.KNOWN:
        since = ".".join(map(str, facts.since))
        log.info(
            f"ezcd version {product_version!r} {selection.match.name.lower()}: facts of ezcd {since} used"
        )
