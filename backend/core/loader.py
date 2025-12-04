import importlib
import pkgutil
import sys
from pathlib import Path

from core.logger import Logger
logger = Logger(__name__)


def load_from_directory(base_path: str = "services", submodules=None, recursive=True):
    """
    Dynamically load project modules and submodules (api, service, websocket, cron).
    Supports recursive discovery for deeper packages like services.*, modules.*, etc.
    """
    submodules = submodules or ("service", "api", "websocket", "cron")

    base_dir = Path(base_path).resolve()
    logger.info(f"Scanning base path: {base_dir}")

    # Ensure parent dir is on sys.path
    if str(base_dir.parent) not in sys.path:
        sys.path.insert(0, str(base_dir.parent))

    if not base_dir.exists():
        logger.warning(f"Directory not found: {base_dir}")
        return

    # Walk recursively if enabled
    walker = pkgutil.walk_packages([str(base_dir)], prefix=f"{base_path}.") if recursive else pkgutil.iter_modules([str(base_dir)])
    
    for module_info in walker:
        name = module_info.name
        try:
            # Try to import main package
            importlib.import_module(name)
            logger.debug(f"Imported module: {name}")

            # Try loading known submodules (api, service, websocket, cron)
            for sub in submodules:
                submodule_path = f"{name}.{sub}"
                try:
                    importlib.import_module(submodule_path)
                    logger.info(f"Loaded submodule: {submodule_path}")
                except ModuleNotFoundError:
                    continue
                except Exception as e:
                    logger.error(f"Failed to load {submodule_path}: {e}")

        except Exception as e:
            logger.error(f"Error loading module {name}: {e}")
                
def auto_load_all():
    for base in ["services", "modules", "interfaces"]:
        load_from_directory(base)
        
def dynamic_import(module_path: str, class_name: str):
    """
    Dynamically import and return a class from a module path.
    e.g., module_path='cron.jobs.sync_external_data', class_name='SyncExternalDataJob'
    """
    try:
        module = importlib.import_module(module_path)
        cls = getattr(module, class_name)
        return cls
    except (ImportError, AttributeError) as e:
        raise ImportError(f"Failed to import {class_name} from {module_path}: {e}")
