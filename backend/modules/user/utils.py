import json
import random
import string
import calendar
from bson import ObjectId
from typing import Optional
from datetime import datetime, timedelta
from core.base_utils import BaseUtils
from .models import PromptData, InsightsData
from llm.message import LLMRequest
from llm.providers.openai.openai_provider import OpenAIProvider as LLMProvider
from core.logger import Logger

logger = Logger(__name__)


class UserUtils(BaseUtils):
    
    def __init__(self):
        super().__init__()
        
    async def get_last_project_for_user(self, user_id: str) -> Optional[str]:
        projects_collection = self.mongodb.get_collection("projects")
        project = await projects_collection.find_one(
            {"user_id": user_id},
            sort=[("created_at", -1)]
        )
        return str(project["_id"]) if project else None
    
    async def get_insight(self, insight_id):
        notes_insights = self.mongodb.get_collection("notes_insights")
        insight = await notes_insights.find_one({"_id": ObjectId(insight_id)})
        return insight
    
    async def save_prompt(self, prompt: PromptData):
        doc = prompt.dict()
        prompts_collection = self.mongodb.get_collection("prompts")
        prompt = await prompts_collection.insert_one(doc)
        return prompt.inserted_id
    
    async def get_delete_convo(self, convo_id: str) -> Optional[str]:
        conversations_collection = self.mongodb.get_collection("conversations")
        convo = await conversations_collection.update_one(
            {"_id": ObjectId(convo_id)},
            {"$set": {"archived": True}},
        )
        return True if convo.modified_count > 0 else False
    
    async def get_all_convo_from_project(self, projectId):
        conversations_collection = self.mongodb.get_collection("conversations")
        convos = await conversations_collection.find({"project_id": projectId, "archived": False}).to_list(length=None)
        return self.sanitize_mongo_doc(convos)
    
    async def get_chat_history(self, convoId, limit: Optional[int] = None):
        prompts_collection = self.mongodb.get_collection("prompts")
        if limit and isinstance(limit, int) and limit > 0:
            prompts = await prompts_collection.find({"conversation_id": convoId}).sort("_id", -1).limit(limit).to_list(length=None)
        else:
            prompts = await prompts_collection.find({"conversation_id": convoId}).to_list(length=None)
        return self.sanitize_mongo_doc(prompts)
    
    async def update_user_reactions(self, promptId: str, reaction: str) -> bool:
        valid_reactions = {"liked", "disliked"}  # use set for faster lookup
        
        if reaction not in valid_reactions:
            raise ValueError(f"Invalid reaction: {reaction}. Must be one of {valid_reactions}")
        prompts_collection = self.mongodb.get_collection("prompts")
        prompt = await prompts_collection.update_one(
            { "_id": ObjectId(promptId) },
            { "$set": { "reaction": reaction } }
        )
        return True if prompt.modified_count > 0 else False
    
    async def bookmark_prompt(self, promptId: str, status: bool) -> bool:        
        prompts_collection = self.mongodb.get_collection("prompts")
        prompt = await prompts_collection.update_one(
            { "_id": ObjectId(promptId) },
            { "$set": { "is_bookmarked": status } }
        )
        # TODO: write logic to add/remove from user's bookmarked list/ collection
        return status in [True, False] if prompt.modified_count > 0 else None
    
    async def get_insights_for_project(self, project_id, limit: Optional[int] = 20, retry_count: int = 0, recreate: bool = False):
        try:
            if not project_id:
                return []
            if limit and isinstance(limit, int) and limit > 0:
                notes_insights = self.mongodb.get_collection("notes_insights")
                insights = await notes_insights.find({"project_id": project_id}).sort("_id", -1).limit(limit).to_list(length=None)
                insights.reverse()  # to get in chronological order
            else:
                insights = await notes_insights.find({"project_id": project_id}).to_list(length=None)
            if (len(insights) <= 0 and retry_count < 1) or (recreate and retry_count < 1):
                await self.generate_insights(project_id)
                insights = await self.get_insights_for_project(project_id, limit, retry_count=1)
            # Filter out insights with certain words in the title
            exclude_words = ["inconvenience", "apologize", "sorry", "unfortunately", "regret", "issue", "problem", "error", "0%"]
            filtered = [
                item for item in insights
                if not any(word.lower() in item["description"].lower() for word in exclude_words)
            ]
            return self.sanitize_mongo_doc(filtered)
        except Exception as e:
            logger.error(f"Get insight error: {e}")
            return []
        
    async def generate_insights(self, project_id: str):
        if not project_id:
            return None
        insight_templates = self.mongodb.get_collection("insight_templates")
        notes_insights = self.mongodb.get_collection("notes_insights")
        templates = await insight_templates.find({"archived": False}).sort("_id", -1).limit(10).to_list(length=None)
        for template in templates:
            title = template.get("title", "")
            try:
                prompt = template.get("prompt", "")
                description_tmpl = template.get("description", "")
                # modify prompt to make model understand the context
                prompt = (
                    f"Based on the data, give me a metrics like:{prompt}\n"
                    "Please make sure the response is concise and to the point."
                )
                # Run the React Agent loop to get insights
                request = LLMRequest(
                    messages=[{ "role": "user", "content": (
                        f"Based on the data, give me a metrics like:{prompt}\n"
                        "Please make sure the response is concise and to the point."
                    )}], 
                    model="gpt-5", 
                    params={"reasoning": {"effort": "low"}}
                )
                provider = LLMProvider()  # Assuming LLMProvider is defined and imported correctly
                response = provider.generate_response(request)
                response_content = response.text
                # Save the generated insight to the database
                insert_doc = InsightsData(
                    project_id=project_id,
                    title=title,
                    description=response_content,
                    explanation=response_content
                )
                await notes_insights.insert_one(insert_doc.dict())
            except Exception as e:
                logger.error(f"Error while generating insight: {title}, error: {e}")
        # generate graph data for monthly revenue
        xaxis, yaxis = self.generate_mr_graph_data(project_id=project_id)
        if xaxis and yaxis:
            graph_data = {
                "xaxis": xaxis,
                "yaxis": yaxis,
                "title": "Monthly Revenue (MR) Over the Past Year",
                "xaxis_title": "Month",
                "yaxis_title": "Revenue (USD)"
            }
            graph_insight = InsightsData(
                project_id=project_id,
                title="Monthly Recurring Revenue (MRR) Over the Past Year",
                description="This graph shows the trend of Monthly Recurring Revenue (MRR) over the past year.",
                explanation="The graph illustrates how the MRR has changed month over month, providing insights into revenue growth and seasonality.",
                display_type="graph",
                graph_type="line",
                graph_data=json.dumps(graph_data)  # Store as stringified JSON
            )
            await notes_insights.insert_one(graph_insight.dict())
            
    def generate_mr_graph_data(self, project_id):
        """
        Generate monthly MRR graph data using calculate_mrr_in_a_period for each month.
        """
        end_date = datetime.utcnow()
        start_date = end_date - timedelta(days=365)  # last 12 months

        # Prepare month ranges
        months = []
        current = start_date.replace(day=1)
        while current <= end_date:
            next_month = (current.replace(day=28) + timedelta(days=4)).replace(day=1)  # first day of next month
            months.append((current, next_month - timedelta(seconds=1)))  # inclusive of month
            current = next_month

        xaxis = []
        yaxis = []

        for month_start, month_end in months:
            start_str = month_start.strftime("%Y-%m-%d")
            end_str = month_end.strftime("%Y-%m-%d")

            # TODO: invoke llm agent to calculate MRR for the month
            mrr = 0

            xaxis.append(f"{calendar.month_name[month_start.month][:3]}")
            yaxis.append(mrr)

        return xaxis, yaxis
    
    async def get_all_project_for_user(self, user_id: str) -> Optional[str]:
        projects_collection = self.mongodb.get_collection("projects")
        projects = await projects_collection.find(
            {"user_id": user_id},
            sort=[("created_at", -1)]
        ).to_list(length=None)
        return projects
    
    async def archive_convos_for_project(self, project_id: str) -> Optional[str]:
        conversations_collection = self.mongodb.get_collection("conversations")
        convo = await conversations_collection.update_one(
            {"project_id": project_id},
            {"$set": {"archived": True}},
        )
        return True if convo.modified_count > 0 else False
    
    async def delete_insights_by_project(self, project_id):
        notes_insights = self.mongodb.get_collection("notes_insights")
        insights = await notes_insights.delete_many({"project_id": project_id})
        return insights.deleted_count
    
    async def get_delete_project(self, project_id: str) -> Optional[str]:
        projects_collection = self.mongodb.get_collection("projects")
        project = await projects_collection.update_one(
            {"_id": ObjectId(project_id)},
            {"$set": {"archived": True}},
        )
        return True if project.modified_count > 0 else False
    
    async def generate_project_api_key(self, project_id: str, user_id: str, name: str) -> str:
        def generate_random_string(length: int) -> str:
            """Generate unique random string of fixed length."""
            characters = string.ascii_letters + string.digits
            random_string = ''.join(random.choice(characters) for _ in range(length))
            return random_string
        api_key = generate_random_string(124)
        keys_collection = self.mongodb.get_collection("api_keys")
        result = await keys_collection.insert_one({
            "project_id": project_id,
            "user_id": user_id,
            "name": name,
            "api_key": api_key,
            "created_at": datetime.utcnow(),
            "archived": False
        })
        key_document = await keys_collection.find_one({"_id": result.inserted_id})
        return key_document
