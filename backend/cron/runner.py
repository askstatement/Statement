import asyncio
from cron.scheduler import start_scheduler
from core.logger import Logger

logger = Logger(__name__)

async def init_cron_background():
    """
    Launch the cron scheduler as a background task in the current event loop.
    This should be called from the FastAPI startup event.
    """
    logger.debug("Starting background cron scheduler...")
    # Create a task that runs the scheduler in the background
    asyncio.create_task(start_scheduler(60))
