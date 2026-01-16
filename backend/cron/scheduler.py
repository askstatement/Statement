import os
import asyncio
from pymongo import ReturnDocument
from datetime import datetime, timedelta
from croniter import croniter
from core.loader import dynamic_import
from core.logger import Logger

logger = Logger(__name__)

LOCK_NAME = "cron_scheduler"

async def execute_job(job: dict):
    """Run a single cron job instance asynchronously."""
    from core.base_database import BaseDatabase
    
    collection = BaseDatabase.mongodb.get_collection("cron_jobs")

    start_time = datetime.utcnow()
    job_id = job["_id"]
    logger.info(f"Starting job: {job['name']}")

    try:
        # Load job dynamically
        module_path = str(job['file'])
        class_name = job["class"]
        params = job.get("params", {})
        JobClass = dynamic_import(module_path, class_name)
        job_instance = JobClass(params)

        # Update job as running
        await collection.update_one(
            {"_id": job_id},
            {"$set": {"running": True, "last_heartbeat": start_time}}
        )

        # Run job safely
        await job_instance.before_run()
        await job_instance.run()
        await job_instance.after_run()

        now = datetime.utcnow()
        next_run_cron = await convert_schedule_hrf_to_cron(job["schedule"], now)
        next_run = croniter(next_run_cron, now).get_next(datetime)

        # Mark completed
        await collection.update_one(
            {"_id": job_id},
            {"$set": {
                "last_run": now,
                "next_run": next_run,
                "running": False,
                "last_heartbeat": now,
                "last_error": None
            }}
        )

        logger.info(f"Completed job: {job['name']} (next run: {next_run})")

    except Exception as e:
        logger.error(f"Job {job['name']} failed: {str(e)}")
        await collection.update_one(
            {"_id": job_id},
            {"$set": {"running": False, "last_error": str(e)}}
        )
        
async def convert_schedule_hrf_to_cron(hrf: str, reference: datetime = None) -> str:
    """
    Convert human-readable schedule format to cron expression.
    
    Args:
        hrf (str): Human-readable format (e.g., "1h, 2h, 1d, 1m, 1y etc..").
    """
    units_map = {
        'm': 'minutes',
        'h': 'hours',
        'd': 'days',
        'w': 'weeks',
        'M': 'months',
        'y': 'years'
    }
    
    # Use reference time (now) to preserve minute/hour when converting
    if reference is None:
        reference = datetime.utcnow()

    parts = hrf.split(',')
    cron_parts = ['*', '*', '*', '*', '*']  # minute, hour, day of month, month, day of week

    for part in parts:
        part = part.strip()
        if len(part) < 2:
            continue
        value = part[:-1]
        unit = part[-1]

        if unit in units_map and value.isdigit():
            value = int(value)
            # Minutes: run every N minutes (keep other fields as '*')
            if unit == 'm':
                cron_parts[0] = f"*/{value}"
            # Hours: run every N hours at the same reference minute
            elif unit == 'h':
                cron_parts[0] = str(reference.minute)
                cron_parts[1] = f"*/{value}"
            # Days: run every N days at the same reference hour and minute
            elif unit == 'd':
                cron_parts[0] = str(reference.minute)
                cron_parts[1] = str(reference.hour)
                cron_parts[2] = f"*/{value}"
            # Months: run every N months at the same reference hour and minute
            elif unit == 'M':
                cron_parts[0] = str(reference.minute)
                cron_parts[1] = str(reference.hour)
                cron_parts[3] = f"*/{value}"
            # Weeks: approximate as days (value * 7 days) at same hour/minute
            elif unit == 'w':
                days = value * 7
                cron_parts[0] = str(reference.minute)
                cron_parts[1] = str(reference.hour)
                cron_parts[2] = f"*/{days}"
            # Years: approximate as months (value * 12 months)
            elif unit == 'y':
                cron_parts[0] = str(reference.minute)
                cron_parts[1] = str(reference.hour)
                cron_parts[3] = f"*/{value * 12}"  # Approximate years as months

    return ' '.join(cron_parts)
    

async def recover_stale_jobs(max_runtime_sec: int = 600):
    """
    Recovers jobs stuck in 'running=True' state beyond expected runtime.
    Prevents deadlocks.
    """
    from core.base_database import BaseDatabase
    
    collection = BaseDatabase.mongodb.get_collection("cron_jobs")

    cutoff = datetime.utcnow() - timedelta(seconds=max_runtime_sec)
    stale_jobs = await collection.find({"running": True, "last_heartbeat": {"$lt": cutoff}}).to_list(length=None)

    for job in stale_jobs:
        logger.warning(f"Resetting stale job: {job['name']}")
        await collection.update_one({"_id": job["_id"]}, {"$set": {"running": False}})


async def run_cron_jobs():
    """Run all due cron jobs concurrently."""
    from core.base_database import BaseDatabase
    
    collection = BaseDatabase.mongodb.get_collection("cron_jobs")
    now = datetime.utcnow()

    # Recover any stale jobs
    await recover_stale_jobs()

    # Fetch due jobs (missed or on-time)
    due_jobs = await collection.find({
        "active": True,
        "next_run": {"$lte": now},
        "running": False
    }).to_list(length=None)

    if not due_jobs:
        logger.debug("No cron jobs ready to run.")
        return

    logger.info(f"{len(due_jobs)} cron jobs ready to execute.")

    # Run concurrently
    tasks = [asyncio.create_task(execute_job(job)) for job in due_jobs]
    await asyncio.gather(*tasks)
    
async def check_and_aquire_cron_lock() -> bool:
    now = datetime.utcnow()
    expires_at = now + timedelta(seconds=2)
    from core.base_database import BaseDatabase
    
    startup_locks = BaseDatabase.mongodb.get_collection("startup_locks")
    
    try:
        await startup_locks.create_index("expiresAt", expireAfterSeconds=10)
    except Exception as e:
        logger.error(f"Failed to create index on startup_locks: {e}")

    try:
        result = await startup_locks.find_one_and_update(
            {"_id": LOCK_NAME},
            {
                "$setOnInsert": {
                    "_id": LOCK_NAME,
                    "owner": os.getpid(),
                    "expiresAt": expires_at,
                    "acquiredAt": now,
                }
            },
            upsert=True,
            return_document=ReturnDocument.AFTER,
        )
        return result["owner"] == os.getpid()
    except Exception as e:
        # Another worker won the race
        logger.warning(f"Failed to acquire cron lock: {e}")
        return False


async def start_scheduler(interval_seconds: int = 60):
    """
    Robust cron scheduler that:
      - Runs every N seconds
      - Recovers missed jobs
      - Executes due jobs concurrently
    """
    logger.info(f"Starting cron scheduler (interval={interval_seconds}s)")
    acquired = await check_and_aquire_cron_lock()
    if not acquired:
        logger.warning("Cron scheduler lock not acquired. Another instance may be running. Exiting scheduler.")
        return
    while True:
        try:
            await run_cron_jobs()
        except Exception as e:
            logger.error(f"Scheduler loop error: {e}")
        await asyncio.sleep(interval_seconds)
