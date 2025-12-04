import os
from typing import Dict
from core.logger import Logger

logger = Logger(__name__)

SKIP_INDEX_REGISTRATION = os.getenv("SKIP_INDEX_REGISTRATION", "false").lower() == "true"

class ServiceRegistry:
    _services: Dict[str, object] = {}
    _toolsets: Dict[str, object] = {}
    _apis: Dict[str, object] = {}
    _websockets: Dict[str, object] = {}

    @classmethod
    def register_service(cls, name: str, service: object):
        """Register a service and its Elasticsearch indices if applicable."""
        cls._services[name] = service
        cls.register_es_indices(service)
        
    @classmethod
    def register_toolset(cls, name: str, toolset: object):
        """Register a toolset for the service."""
        cls._toolsets[name] = toolset
        
    @classmethod
    def register_es_indices(cls, service: object):
        """Register Elasticsearch indices for the service if applicable."""
        if service.elastic and service.es_mapping:
            for schema in service.es_mapping:
                try:
                    index = schema.get("index")
                    body = schema.get("schema", {})
                    if not index or not body:
                        logger.warning(f"Invalid ES mapping for service {service}: {schema}")
                        continue
                    if SKIP_INDEX_REGISTRATION:
                        logger.info(f"Skipping ES index registration for {index} due to SKIP_INDEX_REGISTRATION setting.")
                        continue
                    service.elastic.create_index(index, body)
                except Exception as e:
                    logger.error(f"Failed to create ES index {index} for service {service}: {e}")
                
    @classmethod
    def register_api(cls, name: str, router):
        """Register an API router for the service."""
        if name in cls._apis:
            logger.warning(f"API name conflict for name {name}, {router.prefix} is already registered under route {cls._apis[name].prefix}, overwriting.")
        cls._apis[name] = router

    @classmethod
    def register_websocket(cls, name: str, websocket_handler):
        """Register a WebSocket handler for the service."""
        cls._websockets[name] = websocket_handler

    @classmethod
    def get_all_apis(cls):
        """Get all registered API routers."""
        return cls._apis.values()

    @classmethod
    def get_websocket_handler(cls, name: str):
        """Get the WebSocket handler for a given service."""
        return cls._websockets.get(name)
