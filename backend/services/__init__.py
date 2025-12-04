import importlib
import pkgutil

# Automatically import all submodules under services/
for _, module_name, is_pkg in pkgutil.iter_modules(__path__):
    full_module_name = f"{__name__}.{module_name}"
    importlib.import_module(full_module_name)