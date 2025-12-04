from fastapi import APIRouter
from typing import Callable
from core.base_database import BaseDatabase

from core.logger import Logger
logger = Logger(__name__)

def route(method: str, path: str, **kwargs):
    """Generic decorator to mark a method as a route handler."""
    def decorator(func: Callable):
        func._api_route = (method.lower(), path, kwargs)
        return func
    return decorator

def get(path: str, **kwargs): return route("get", path, **kwargs)
def post(path: str, **kwargs): return route("post", path, **kwargs)
def put(path: str, **kwargs): return route("put", path, **kwargs)
def delete(path: str, **kwargs): return route("delete", path, **kwargs)

class BaseAPI(BaseDatabase):
    """
    Base class for modular FastAPI route groups.
    Subclasses define routes with @get, @post, etc.
    """
    base_prefix: str = "/api"
    
    def __init__(self, prefix: str):
        self.router = APIRouter(prefix= f"{self.base_prefix}{prefix}")
        self._init_utils()
        self._init_service()
        self._register_routes()
    
    def __init_subclass__(cls, **kwargs):
        """Automatically initialize utils attributes declared in subclasses"""
        super().__init_subclass__(**kwargs)
        # Get type annotations to find declared utils
        annotations = getattr(cls, '__annotations__', {})
        for attr_name, attr_type in annotations.items():
            if attr_name == 'utils':
                # Store the utils class for later initialization
                cls._utils_class = attr_type
            if attr_name == 'service':
                # Store the service class for later initialization
                cls.service_class = attr_type
    
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

    def _register_routes(self):
        for attr_name in dir(self):
            method = getattr(self, attr_name)
            if callable(method) and hasattr(method, "_api_route"):
                http_method, path, options = method._api_route
                getattr(self.router, http_method)(path, **options)(method)
                logger.debug(f"Registered route: [{http_method.upper()}] {path} in {self.__class__.__name__}")
