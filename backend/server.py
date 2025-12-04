import os
from contextlib import asynccontextmanager

from dotenv import load_dotenv

load_dotenv()
from fastapi import FastAPI, WebSocket
from fastapi.middleware.cors import CORSMiddleware

from core.base_database import BaseDatabase
from core.db.elastic import ElasticClient
from core.db.mongodb import MongoDBClient
from core.loader import auto_load_all
from core.logger import Logger, setup_logging
from core.registry import ServiceRegistry
from cron.registry import CronRegistry
from cron.runner import init_cron_background

# Initialize logger before anything else
setup_logging()

app_logger = Logger(__name__)
app_logger.info("Logger initialized successfully.")

# establish database connections
mongodb = MongoDBClient()
elastic = ElasticClient()
BaseDatabase.init_databases(mongodb, elastic)


@asynccontextmanager
async def lifespan(app: FastAPI):
    app_logger.info("Starting up application...")
    await mongodb.init()
    auto_load_all()

    # Register routers after auto_load_all() populates ServiceRegistry
    for router in ServiceRegistry.get_all_apis():
        app.include_router(router)

    # Log all registered WebSocket handlers
    app_logger.info(
        f"Registered WebSocket handlers: {list(ServiceRegistry._websockets.keys())}"
    )
    for name, handler in ServiceRegistry._websockets.items():
        app_logger.info(f"WebSocket '{name}' routes: {list(handler.routes.keys())}")

    # Only run cron if ENABLE_CRON environment variable is set to true
    enable_cron = os.environ.get("ENABLE_CRON", "false").lower() == "true"

    if enable_cron:
        await CronRegistry.sync_all_to_db()
        await init_cron_background()
        app_logger.debug("Cron scheduler started in API server.")
    else:
        app_logger.debug("Cron scheduler disabled in this service.")

    yield
    app_logger.info("Shutting down application...")


app = FastAPI(title="Statement", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.websocket("/ws/{service_name}/{route_path:path}")
async def websocket_endpoint(
    websocket: WebSocket, service_name: str, route_path: str = ""
):
    """
    WebSocket endpoint handler.
    Supports both /ws/{service_name} and /ws/{service_name}/{route_path}
    """
    app_logger.info(
        f"WebSocket connection attempt: service_name={service_name}, route_path='{route_path}'"
    )
    handler = ServiceRegistry.get_websocket_handler(service_name)
    if not handler:
        app_logger.warning(f"WebSocket handler for {service_name} not found")
        await websocket.accept()
        await websocket.send_json(
            {"error": f"WebSocket handler for {service_name} not found"}
        )
        await websocket.close()
        return

    # Look for the matching route in the handler
    route_key = f"/{route_path}" if route_path else "/"
    app_logger.info(
        f"Looking for route: {route_key}, available routes: {list(handler.routes.keys())}"
    )
    route_handler = handler.routes.get(route_key)
    if not route_handler:
        app_logger.warning(
            f"WebSocket route {route_key} not found in {service_name}. Available routes: {list(handler.routes.keys())}"
        )
        await websocket.accept()
        await websocket.send_json(
            {"error": f"WebSocket route {route_key} not found in {service_name}"}
        )
        await websocket.close()
        return

    # Call the handler's route method
    app_logger.info(f"Calling WebSocket handler for {service_name}{route_key}")
    try:
        await route_handler(handler, websocket)
    except Exception as e:
        app_logger.error(
            f"Error in WebSocket route {service_name}{route_key}: {e}", exc_info=True
        )
        try:
            await websocket.close()
        except:
            pass
