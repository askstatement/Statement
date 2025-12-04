from abc import ABC, abstractmethod
from core.logger import Logger
from core.base_database import BaseDatabase

logger = Logger(__name__)

class BaseCronJob(ABC, BaseDatabase):
    """
    Base class for all cron jobs. 
    Subclasses automatically register themselves in MongoDB.
    """

    name: str = None          # Human-readable job name
    # convert schedule to hunan readable format
    schedule: str = "1m"  # Default: every minute
    active: bool = True       # Enable/disable job
    max_runtime_sec: int = 600
    file: str = None          # Auto-resolved module name

    def __init__(self, params: dict = None):
        self.params = params or {}

        # Infer job file path
        self.file = self.__class__.__module__.split(".")[-1]

    @abstractmethod
    async def run(self):
        """Define the main logic for the cron job."""
        pass

    async def before_run(self):
        logger.debug(f"Preparing to run {self.__class__.__name__}")

    async def after_run(self):
        logger.debug(f"Completed execution of {self.__class__.__name__}")
