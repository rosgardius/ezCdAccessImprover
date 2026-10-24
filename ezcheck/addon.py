"""The add-on's facts about ezcd, loaded from its files: the package ``ezcd`` that holds them needs NVDA."""

import importlib
import importlib.util
import sys
from pathlib import Path

_PACKAGE = Path(__file__).resolve().parent.parent / "addon" / "appModules" / "ezcd" / "facts"
_NAME = "ezcd_facts"


def _load():
    spec = importlib.util.spec_from_file_location(
        _NAME, _PACKAGE / "__init__.py", submodule_search_locations=[str(_PACKAGE)]
    )
    module = importlib.util.module_from_spec(spec)
    sys.modules[_NAME] = module
    spec.loader.exec_module(module)
    for submodule in ("groups", "language", "objects"):
        importlib.import_module(f"{_NAME}.{submodule}")
    return module


facts = _load()
"""The package ``facts`` of the add-on: ``facts.select``, ``facts.groups``, ``facts.language``,
``facts.objects``."""
