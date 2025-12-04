import json
from bson import ObjectId
from fastapi import WebSocket
from datetime import datetime, timedelta
from core.base_utils import BaseUtils
from .models import PromptData
from core.logger import Logger

logger = Logger(__name__)

# Lazy, cached initializers to avoid heavy model load at import time
_summarizer_pipeline = None
_title_generator_pipeline = None

def _get_summarizer():
    global _summarizer_pipeline
    if _summarizer_pipeline is None:
        from transformers import pipeline
        _summarizer_pipeline = pipeline(
            "summarization",
            model="facebook/bart-large-cnn",
        )
    return _summarizer_pipeline

def _get_title_generator():
    global _title_generator_pipeline
    if _title_generator_pipeline is None:
        from transformers import pipeline
        _title_generator_pipeline = pipeline(
            "text2text-generation",
            model="google/flan-t5-small",
        )
    return _title_generator_pipeline

class ChatUtils(BaseUtils):
    
    def __init__(self):
        super().__init__()
        
    async def parse_ws_message(self, message: str) -> dict:
        """
        Parse the incoming websocket message which is expected to be a JSON string.
        Extracts 'agentsSelected' and 'message' fields.
        Args:
            message (str): The incoming message string.
        Returns:
            dict: Parsed message with 'agents_selected' and 'message' keys.
        """
        try:
            msg_obj = json.loads(message)
            agents_selected = msg_obj.get("agents_selected", [])
            user_message = msg_obj.get("message", "")
            return {
                "agents_selected": agents_selected,
                "message": user_message
            }
        except json.JSONDecodeError:
            logger.error("Failed to decode websocket message as JSON.")
            return {
                "agents_selected": [],
                "message": message
            }
        
    async def check_ws_token_limit(self, project_id: str, limit: str, websocket: WebSocket) -> bool:
        """
        Check if inside websocket the project has exceeded its token limit based on the provided rate string.
        Args:
            project_id (str): The project ID to check.
            limit (str): The token limit string (e.g., "10000/tpm").
            websocket (WebSocket): The WebSocket connection object.
        Returns:
            bool: True if within limit, False if exceeded.
        """
        max_tokens, window_seconds = self.parse_token_rate(limit)
        
        path_key = websocket.url.path
        projects_collection = self.mongodb.get_collection("projects")
        token_usage_collection = self.mongodb.get_collection("project_token_usage")
        project = await projects_collection.find_one({"_id": ObjectId(project_id)})
        if not project:
            return False
        
        now = datetime.utcnow()
        window_start = now - timedelta(seconds=window_seconds)

        # Get total tokens used in current window
        query = {"project_id": project_id, "path": path_key, "timestamp": {"$gte": window_start}}
        records = await token_usage_collection.find(query).to_list(length=None)
        total_tokens_used = sum(rec.get("total_tokens", 0) for rec in records)
        
        if total_tokens_used >= max_tokens:
            logger.warning(f"Token limit exceeded for project={project_id} path={path_key}")
            return False
        return True
    
    async def get_project_from_convo(self, convoId):
        conversations_collection = self.mongodb.get_collection("conversations")
        convoObj = await conversations_collection.find_one({"_id": ObjectId(convoId)})
        return str(convoObj.get("project_id")) if convoObj else None
    
    async def save_prompt(self, prompt: PromptData):
        doc = prompt.dict()
        prompts_collection = self.mongodb.get_collection("prompts")
        prompt = await prompts_collection.insert_one(doc)
        return prompt.inserted_id
    
    async def generate_title_and_summary(self, convId):
        def clean_output(text: str) -> str:
            blacklist = ["USATODAY.com", "REUTERS", "CNN", "AP"]
            for bad in blacklist:
                text = text.replace(bad, "")
            return text.strip(" -:–")

        try:
            if not convId:
                return

            conversations_collection = self.mongodb.get_collection("conversations")
            prompts_collection = self.mongodb.get_collection("prompts")
            conversation = await conversations_collection.find_one({"_id": ObjectId(convId)})
            prompts = await prompts_collection.find({"conversation_id": convId, "type": "prompt"}).limit(5).to_list(length=None)

            merged_prompts = []
            seen = set()
            for p in prompts:
                content = p.get("content", "").strip()
                if len(content) > 10 and content not in seen:
                    merged_prompts.append(content)
                    seen.add(content)
            
            # Skip if already has title+summary and enough prompts
            if not conversation or (conversation.get("name") and conversation.get("summary") and len(merged_prompts) > 5):
                return

            prompt_str = " ".join(merged_prompts)
            if not prompt_str:
                return

            word_count = len(prompt_str.split())

            # --- Fallback for very short input ---
            if word_count < 15:
                words = prompt_str.split()
                title = " ".join(words[:12])
                summary = prompt_str
            else:
                # --- Dynamic token settings ---
                max_new_title_tokens = min(max(8, word_count // 2), 8)
                max_summary_len = min(100, max(15, word_count))

                summary = _get_summarizer()( 
                    prompt_str,
                    max_length=max_summary_len,
                    min_length=max(10, max_summary_len // 3),
                    do_sample=False
                )[0]['summary_text']

                title_prompt = f"Generate a short, clear title for this text:\n\n{prompt_str}"
                title = _get_title_generator()( 
                    title_prompt,
                    max_new_tokens=max_new_title_tokens,
                    min_length=4,
                    do_sample=False
                )[0]['generated_text']

            title = clean_output(title)
            summary = clean_output(summary)

            if title and summary:
                await conversations_collection.update_one(
                    {"_id": ObjectId(convId)},
                    {"$set": {"name": title, "summary": summary}}
                )

        except Exception as e:
            logger.error(f"Error generating title and summary: {e}")
