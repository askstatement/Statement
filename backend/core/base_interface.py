from core.base_api import BaseAPI
from core.logger import Logger

logger = Logger(__name__)

class BaseInterface(BaseAPI):
    """
    Base class for external/public-facing APIs.
    Extends BaseAPI with versioning and optional authentication.
    """

    version: str = "v1"   # Default version

    def __init__(self, prefix: str, version: str = None):
        self.version = version or self.version
        # Prefix becomes like "/v1/chat"
        full_prefix = f"/{self.version}{prefix}"
        super().__init__(full_prefix)
        logger.info(f"Initialized interface: {self.__class__.__name__} at {full_prefix}")
