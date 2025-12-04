from fastapi import WebSocket
from typing import Callable, Dict, Awaitable
from core.base_database import BaseDatabase

from core.logger import Logger
logger = Logger(__name__)

def register_route(route: str):
    """
    Class-level decorator to register WebSocket route functions.
    It adds the decorated function to a special _ws_routes dict.
    """
    def decorator(func):
        func._ws_route = route
        return func
    return decorator

class BaseWebSocketHandler(BaseDatabase):
    routes: Dict[str, Callable[[WebSocket, dict], Awaitable[None]]] = {}
    
    def __init__(self):
        self._init_utils()
        self._init_service()

    def __init_subclass__(cls, **kwargs):
        """Automatically collect @register_route methods when subclassing."""
        super().__init_subclass__(**kwargs)
        annotations = getattr(cls, '__annotations__', {})
        for attr_name, attr_type in annotations.items():
            if attr_name == 'utils':
                # Store the utils class for later initialization
                cls._utils_class = attr_type
            if attr_name == 'service':
                # Store the service class for later initialization
                cls.service_class = attr_type
        cls.routes = {}
        for name, value in cls.__dict__.items():
            route_name = getattr(value, "_ws_route", None)
            if route_name:
                cls.routes[route_name] = value
                logger.debug(f"Registered WebSocket route '{route_name}' in {cls.__name__}")
            
    def _init_utils(self):
        """Initialize utils if the subclass has declared one"""
        if hasattr(self.__class__, '_utils_class'):
            utils_class = self.__class__._utils_class
            self.utils = utils_class()
            
    def _init_service(self):
        """Initialize service if the subclass has declared one"""
        if hasattr(self.__class__, 'service_class'):
            service_class = self.__class__.service_class
            self.service = service_class()

    async def handle_message(self, websocket: WebSocket, message: dict):
        route = message.get("route")
        if not route or route not in self.routes:
            await websocket.send_json({
                "error": f"Invalid or missing route '{route}'",
                "available_routes": list(self.routes.keys())
            })
            return

        handler = self.routes[route]
        await handler(self, websocket, message.get("data"))
