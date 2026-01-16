from typing import Optional
from datetime import datetime
from cron.base_cron import BaseCronJob
from cron.registry import cron_job
from core.logger import Logger
from .models import InsightsData
from agents.agent_router import AgentRouter
from llm.providers.openai.openai_provider import OpenAIProvider

logger = Logger(__name__)

@cron_job
class GenerateInsightsJob(BaseCronJob):
    name = "Generate Daily Insights"
    schedule = "1d"
    active = True

    async def run(self):
        try:
            await self.run_for_today()
        except Exception as e:
            logger.error(f"Error in generate insights : {str(e)}")
            raise
    
    
    async def run_for_today(self):
        active_projects = await self.get_all_active_projects()
        if not active_projects:
            logger.warning("No active projects found.")
            return
        for project in active_projects:
            project_id = str(project["_id"])
            logger.info(f"Generating insights for project: {project_id} for today")
            await self.run_for_day(datetime.utcnow(), project_id)
        return True

    async def get_all_active_projects(self) -> Optional[list]:
        projects_collection = self.mongodb.get_collection("projects")
        projects = await projects_collection.find({"archived": False}).to_list(length=None)
        return projects if projects else []
    
    async def get_rotation_for_day(self, day: int):
        if 1 <= day <= 30:
            insight_rotation = self.mongodb.get_collection("insight_rotations")
            rotatio = await insight_rotation.find_one({"day": day})
            matrics_str = rotatio.get("metrics", "") if rotatio else []
            if matrics_str:
                return [metric.strip() for metric in matrics_str.split(",")]
        return []
    
    async def run_for_day(self, run_date: datetime, project_id: str):
        day_of_month = run_date.day

        metrics_for_day = await self.get_rotation_for_day(day_of_month)
        for metric in metrics_for_day:
            logger.info(f"Running metric: {metric} for day {day_of_month}")
            # Here you would call the actual function to compute the metric
            # For example: result = compute_metric(m, run_date)
            # For demonstration, we'll just print the metric name
            insight_templates = self.mongodb.get_collection("insight_templates")
            notes_insights = self.mongodb.get_collection("notes_insights")
            template = await insight_templates.find_one({"archived": False, "slug": metric})
            logger.info(f"Template fetched: {template}")
            if not template:
                logger.info(f"No template found for metric: {metric}")
                continue
            title = template.get("title", "")
            prompt = template.get("prompt", "")
            description_tmpl = template.get("description", "")
            # modify prompt to make model understand the context
            prompt = (
                f"Based on the data, give me a metrics like:{prompt}\n"
                "Make sure the response is concise and to the point."
            )
            # new agent router with provider
            agent_router = AgentRouter(provider=OpenAIProvider)
            router_response = await agent_router.handle_request(
                query=prompt,
                project_id=project_id,
                agent_scope=[],
                messages=[], 
                conversation_id=None
            )
            response = router_response.get("response_text", "")
            explanation = ""
            description = f"{response}\n\n{description_tmpl}"
            # Save the generated insight to the database
            insert_doc = InsightsData(
                project_id=project_id,
                title=title,
                description=description,
                explanation=explanation,
                created_at=run_date,
                updated_at=run_date
            )
            await notes_insights.insert_one(insert_doc.dict())
            # TODO: add credit usage logging logic later after discussing with team
            token_usage = router_response.get("token_usage", {})
        return True