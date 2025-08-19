"""
Auto-import all `*_outer` callables from Python modules in this package and subpackages.
"""

from importlib import import_module
from pkgutil import walk_packages

__all__: list[str] = []

for mod in walk_packages(__path__, prefix=__name__ + "."):
    if mod.ispkg:
        continue
    module = import_module(mod.name)
    for name, obj in vars(module).items():
        if name.endswith("_outer") and callable(obj):
            globals()[name] = obj
            __all__.append(name)