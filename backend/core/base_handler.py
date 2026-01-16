import asyncio
from abc import ABC, abstractmethod
from datetime import datetime
from typing import List, Tuple, Callable, Any
from core.base_utils import BaseUtils
from core.logger import Logger

logger = Logger(__name__)


class BaseSyncHandler(ABC):
    """
    A base handler for managing long-running data synchronization tasks.
    It abstracts the process of iterating through sync steps, executing them,
    and reporting progress via BaseUtils.
    """

    service_name: str = "default"
    concurrency_limit: int = 1  # Default to sequential execution

    def __init__(self):
        self.utils = BaseUtils()

    # -------------------------------------------------------------------------
    # Sync Progress Management
    # -------------------------------------------------------------------------

    async def update_sync_progress(
        self,
        project_id: str,
        service: str,
        status: str,
        step: str,
        progress: str,
        message: str = "",
    ):
        """
        Updates or creates a progress document for a given project and service.
        """
        collection = self.utils.mongodb.get_collection("sync_progress")
        await collection.create_index("last_updated", expireAfterSeconds=3600)
        query = {"project_id": project_id, "service": service}
        update = {
            "$set": {
                "service": service,
                "status": status,
                "step": step,
                "progress": progress,
                "message": message,
                "last_updated": datetime.utcnow(),
            }
        }
        result = await collection.update_one(query, update, upsert=True)

    @abstractmethod
    def get_steps(self) -> List[Tuple[str, Callable]]:
        """
        Must be implemented by subclasses to return a list of sync steps.
        Each step is a tuple of (step_name, step_function).
        """
        pass

    async def trigger_sync(self, project_id: str, *args: Any, **kwargs: Any):
        """
        Initiates the synchronization process in the background.
        """
        if not project_id:
            raise ValueError("No project_id provided")

        # IMMEDIATELY save initial progress status
        await self.update_sync_progress(
            project_id,
            self.service_name,
            "in-progress",
            "",
            "0/0",
            f"starting {self.service_name} sync ...",
        )

        # Run the actual sync process in the background
        asyncio.create_task(self._run_sync_process(project_id, *args, **kwargs))

    async def _run_sync_process(self, project_id: str, *args: Any, **kwargs: Any):
        steps = self.get_steps()
        total_steps = len(steps) + 2

        # Use a mutable container for shared state across async tasks
        state = {"completed": 0}
        MIN_STEP_DURATION_SECONDS = 2

        # Update progress with actual step count
        await self.update_sync_progress(
            project_id,
            self.service_name,
            "in-progress",
            "starting",
            f"0/{total_steps}",
            f"Beginning {total_steps} sync steps...",
        )

        try:
            semaphore = asyncio.Semaphore(self.concurrency_limit)

            async def limited_run(
                step_name: str, step_fn: Callable, *step_args, **step_kwargs
            ):
                # Remove project_id from kwargs if present to avoid multiple values error
                # when calling _run_step which takes project_id as a positional argument.
                if "project_id" in step_kwargs:
                    step_kwargs.pop("project_id")
                async with semaphore:
                    await self._run_step(
                        project_id,
                        step_name,
                        step_fn,
                        total_steps,
                        state,
                        MIN_STEP_DURATION_SECONDS,
                        *step_args,
                        **step_kwargs,
                    )

            tasks = [
                limited_run(name, fn, *args, project_id=project_id, **kwargs)
                for name, fn in steps
            ]
            await asyncio.gather(*tasks, return_exceptions=False)

            await self.update_sync_progress(
                project_id,
                self.service_name,
                "in-progress",
                "saving_creds",
                f"{total_steps-2}/{total_steps}",
            )
            await asyncio.sleep(MIN_STEP_DURATION_SECONDS)

            await self.update_sync_progress(
                project_id,
                self.service_name,
                "in-progress",
                "insights",
                f"{total_steps-1}/{total_steps}",
            )
            await asyncio.sleep(MIN_STEP_DURATION_SECONDS)

            await self.update_sync_progress(
                project_id,
                self.service_name,
                "done",
                "completed",
                f"{total_steps}/{total_steps}",
                "All sync steps completed.",
            )

        except Exception as e:
            logger.error(
                f"An error occurred during the {self.service_name} sync for project {project_id}: {e}"
            )
            if project_id:
                await self.update_sync_progress(
                    project_id,
                    self.service_name,
                    "error",
                    "sync_failed",
                    "",
                    f"Sync failed: {e}",
                )

    async def _run_step(
        self,
        project_id: str,
        step_name: str,
        step_fn: Callable,
        total_steps: int,
        state: dict,
        min_duration: int,
        *args,
        **kwargs,
    ):
        """
        Executes a single sync step and updates progress.
        """
        start_time = asyncio.get_event_loop().time()
        try:
            state["completed"] += 1
            completed_count = state["completed"]

            await self.update_sync_progress(
                project_id,
                self.service_name,
                "in-progress",
                step_name,
                f"{completed_count}/{total_steps}",
            )
            await step_fn(*args, project_id=project_id, **kwargs)

            # Enforce a minimum step duration for a smoother frontend experience.
            elapsed = asyncio.get_event_loop().time() - start_time
            if elapsed < min_duration:
                await asyncio.sleep(min_duration - elapsed)
        except Exception as e:
            logger.error(
                f"Error during {self.service_name} sync step '{step_name}': {e}"
            )
            await self.update_sync_progress(
                project_id,
                self.service_name,
                "error",
                step_name,
                f"{state['completed']}/{total_steps}",
                str(e),
            )
            raise
