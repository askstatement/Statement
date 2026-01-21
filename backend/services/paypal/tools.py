from core.base_tools import BaseTool
from core.registry import ServiceRegistry
from core.logger import Logger

logger = Logger(__name__)

class ReactDatabaseTools(BaseTool):
    """Tool class to interact with MongoDB and Elasticsearch databases"""
    
ServiceRegistry.register_toolset("paypal", ReactDatabaseTools)
