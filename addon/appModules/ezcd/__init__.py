# Copyright (C) 2026 Rosgardius
# This file is covered by the GNU General Public License.
# See the file COPYING.txt for more details.

"""App module for EZ CD Audio Converter (ezcd.exe)."""

import addonHandler
import appModuleHandler

addonHandler.initTranslation()


class AppModule(appModuleHandler.AppModule):
    # Translators: The name of this add-on's category in NVDA's Input Gestures dialog.
    scriptCategory = _("EZ CD Audio Converter")
