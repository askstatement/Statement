import hashlib
import inspect
from datetime import datetime
from core.base_database import BaseDatabase
from core.logger import Logger

logger = Logger(__name__)

class CronRegistry(BaseDatabase):
    """
    Global registry for all cron jobs.
    Jobs can register themselves by calling register_cron().
    The registry ensures DB consistency and avoids duplicates.
    """

    _registry = {}

    @classmethod
    async def register_cron(cls, job_class, params: dict = None):
        """
        Register a cron job class with optional parameters.
        Handles deduplication and automatic DB sync.
        """
        params = params or {}
        module_path = job_class.__module__
        job_name = job_class.__name__
        job_id = f"{module_path}.{job_name}"

        # Compute source hash for change detection
        try:
            # consider job_class, name, schedule, active, params, max_runtime_sec in hash
            hash_text = (
                inspect.getsource(job_class) +
                str(getattr(job_class, "name", "")) +
                str(getattr(job_class, "schedule", "")) +
                str(getattr(job_class, "active", "")) +
                str(params) +
                str(getattr(job_class, "max_runtime_sec", ""))
            )
            job_hash = hashlib.md5(hash_text.encode("utf-8")).hexdigest()
        except OSError:
            job_hash = None

        # Store in registry
        cls._registry[job_id] = {
            "class": job_class,
            "params": params,
            "hash": job_hash,
        }

        # Sync to DB
        await cls._sync_to_db(job_class, params, job_id, job_hash)

    @classmethod
    async def _sync_to_db(cls, job_class, params, job_id, job_hash):
        """Insert or update job in MongoDB."""
        collection = cls.mongodb.get_collection("cron_jobs")

        now = datetime.utcnow()
        job_data = {
            "_id": job_id,
            "name": getattr(job_class, "name", job_class.__name__),
            "file": job_class.__module__,
            "class": job_class.__name__,
            "schedule": getattr(job_class, "schedule", "1m"),
            "active": getattr(job_class, "active", True),
            "params": params,
            "job_hash": job_hash,
            "max_runtime_sec": getattr(job_class, "max_runtime_sec", 600),
            "updated_at": now,
        }

        existing = await collection.find_one({"_id": job_id})

        if not existing:
            job_data.update({
                "created_at": now,
                "last_run": None,
                "next_run": now,
                "running": False
            })
            await collection.insert_one(job_data)
            logger.info(f"Registered new cron job: {job_id}")

        elif existing.get("job_hash") != job_hash:
            await collection.update_one({"_id": job_id}, {"$set": job_data})
            logger.info(f"Updated cron job: {job_id}")

        else:
            logger.debug(f"Cron job already up-to-date: {job_id}")

    @classmethod
    def list_registered_jobs(cls):
        """List all in-memory registered jobs."""
        return list(cls._registry.keys())
    
    @classmethod
    async def sync_all_to_db(cls):
        """Sync all registered jobs to the database."""
        for job_id, job_info in cls._registry.items():
            job_class = job_info["class"]
            params = job_info["params"]
            job_hash = job_info["hash"]
            await cls._sync_to_db(job_class, params, job_id, job_hash)
    
    
def register_cron(job_class, params=None):
    """Helper function to register a cron job."""
    return CronRegistry.register_cron(job_class, params)

def cron_job(cls):
    """Class decorator to register a cron job."""
    # Store the class in the registry without DB sync for now
    # DB sync will happen later when databases are initialized
    module_path = cls.__module__
    job_name = cls.__name__
    job_id = f"{module_path}.{job_name}"
    
    try:
        hash_text = (
            inspect.getsource(cls) +
            str(getattr(cls, "name", "")) +
            str(getattr(cls, "schedule", "")) +
            str(getattr(cls, "active", "")) +
            str({}) +
            str(getattr(cls, "max_runtime_sec", ""))
        )
        job_hash = hashlib.md5(hash_text.encode("utf-8")).hexdigest()
    except OSError:
        job_hash = None
    
    CronRegistry._registry[job_id] = {
        "class": cls,
        "params": {},
        "hash": job_hash,
    }
    return cls
