import asyncio
import json
import os
from typing import Optional
from bson import ObjectId
from datetime import datetime

from agents.finaliser_agent import FinaliserAgent
from agents.planner_agent import PlannerAgent
from agents.pre_router_agent import PreRouterAgent
from core.base_database import BaseDatabase
from core.logger import Logger
from core.registry import ServiceRegistry
from llm.agent import Agent
from llm.message import LLMMessage, LLMMessageRole
from llm.providers.openai.openai_provider import OpenAIProvider
from llm.tool import ToolSetRegistry

logger = Logger(__name__)


class AgentRouter(Agent):
    def __init__(self, provider=OpenAIProvider):
        super().__init__(
            name="AgentRouter",
            provider=provider(),
        )
        self.agents = {}
        self.db = BaseDatabase()
        self.register_all_agent()

    def register_all_agent(self):
        # load all registered services from core.registry
        loaded_services = ServiceRegistry._services.keys()
        # Get project base path: go up two levels from agents/ to project root
        project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        services_dir = os.path.join(project_root, "services")
        for service_name in loaded_services:
            manifest_json = os.path.join(services_dir, service_name, "manifest.json")
            if os.path.exists(manifest_json):
                # load the manifest file
                with open(manifest_json, "r") as f:
                    manifest = json.load(f)
                    agent_name = manifest.get("agent_name")
                    service_name = manifest.get("service_name")
                    if agent_name:
                        self.agents[agent_name] = {
                            "service_name": service_name,
                            "manifest": manifest,
                        }

    def get_agent(self, agent_name):
        return self.agents.get(agent_name)

    async def get_available_agents_by_project_scope(self, project_id):
        result = []
        service_key_map = {
            "plaid": "plaid_token",
            "quickbooks": "quickbooks_refresh_key",
            "paypal": "paypal_client_secret",
            "stripe": "stripe_key",
            "xero": "xero_refresh_key",
        }
        project = self.db.mongodb.get_collection("projects")
        project_data = await project.find_one({"_id": ObjectId(project_id)})
        # iterate through the service_key_map and check if the project_data has the corresponding key
        for agent_name, service_key in service_key_map.items():
            if service_key in project_data and project_data[service_key]:
                agent_info = self.get_agent(agent_name)
                if agent_info:
                    manifest = agent_info["manifest"]
                    result.append(
                        {
                            "agent_name": agent_name,
                            "service_name": agent_info["service_name"],
                            "description": manifest["description"]
                            if "description" in manifest
                            else "",
                            "version": manifest["version"]
                            if "version" in manifest
                            else "1.0.0",
                        }
                    )
        return result

    async def get_chat_history(self, convoId, limit: Optional[int] = None):
        prompts_collection = self.db.mongodb.get_collection("prompts")
        if limit and isinstance(limit, int) and limit > 0:
            prompts = (
                await prompts_collection.find({"conversation_id": convoId})
                .sort("_id", -1)
                .limit(limit)
                .to_list(length=None)
            )
        else:
            prompts = await prompts_collection.find(
                {"conversation_id": convoId}
            ).to_list(length=None)
        return prompts
    
    def extract_json(self, response_text: str):
        try:
            response_json = json.loads(response_text)
            return response_json
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse JSON response: {e}")
            return {}

    async def handle_request(
        self,
        query,
        project_id,
        agent_scope=[],
        conversation_id=None,
        messages=[],
        prompt_id=None,
    ):
        agent_responses = {}
        available_agents = await self.get_available_agents_by_project_scope(project_id)
        if agent_scope:
            available_agents = [
                agent
                for agent in available_agents
                if agent["agent_name"] in agent_scope
            ]

        # load last n messages from conversation if conversation_id is provided
        previous_messages = []
        if messages:
            previous_messages = [
                LLMMessage(
                    role=LLMMessageRole.USER
                    if msg.get("role") == "prompt"
                    else LLMMessageRole.ASSISTANT,
                    content=msg["content"],
                )
                for msg in [msg.dict() for msg in reversed(messages)]
            ]
        elif conversation_id:
            previous_messages = await self.get_chat_history(conversation_id, limit=10)
            if previous_messages:
                # Convert to LLMMessage format
                previous_messages = [
                    LLMMessage(
                        role=LLMMessageRole.USER
                        if msg.get("role") == "prompt"
                        else LLMMessageRole.ASSISTANT,
                        content=msg["content"],
                    )
                    for msg in reversed(previous_messages)
                ]
        # replace all @agent_name with empty string in the query
        for agent in available_agents:
            at_agent_name = f"@{agent['agent_name']}"
            query = query.replace(at_agent_name, "").strip()
        
        # pass user query through pre-router agent to get structured response
        pre_router_agent = PreRouterAgent(
            name="PreRouterAgent",
            provider=self.provider,
        )
        pre_router_response = pre_router_agent.handle_request(query, previous_messages, available_agents, agent_scope)
        logger.info(f"[{project_id}] Pre-router response: {pre_router_response}")
        if pre_router_response and pre_router_response.get("needs_escalation", False) in [False, "false"]:
            # if no escalation needed, return the direct answer
            final_answer = pre_router_response.get("final_answer", "I'm sorry, I cannot assist with that request.")
            return {
                "response_text": final_answer,
                "token_usage": pre_router_agent.total_token_usage,
                "agent_responses": [
                    {
                        "agent_name": pre_router_agent.name,
                        "finaliser_response": pre_router_response,
                    }
                ],
            }

        toolset_registry = ToolSetRegistry()
        loaded_services = ServiceRegistry._services.keys()

        loaded_tools = ServiceRegistry._toolsets.keys()
        # process each agenet in parallel using asyncio

        step_concurrency = 6
        step_semaphore = asyncio.Semaphore(step_concurrency)
        
        # TODO: fix later, limit only one agent per request for now due to large token usage
        if agent_scope == [] and available_agents and len(available_agents) > 1:
            available_agents = available_agents[:1]

        async def run_agent_loop(agent):
            async with step_semaphore:
                agent_name = agent["agent_name"]
                try:
                    tool_cls = None
                    if agent_name in loaded_services and agent_name in loaded_tools:
                        tool_cls = ServiceRegistry._toolsets[agent_name]
                    toolset_registry.load(tool_cls, namespace=agent_name)

                    # Create PlannerAgent
                    planner_agent = PlannerAgent(
                        name=f"{agent_name}Planner",
                        toolsets=[toolset_registry.get_toolset(agent_name)],
                        tool_cls=tool_cls,
                        provider=self.provider,
                    )

                    # Create a copy of previous_messages for this agent to avoid race conditions
                    agent_messages = previous_messages.copy()
                    agent_messages.append(LLMMessage(LLMMessageRole.USER, content=query))

                    # Run blocking call in thread pool to avoid blocking event loop
                    planner_response = await asyncio.to_thread(planner_agent.handle_request, project_id, query, agent_messages)
                    
                    print(f"[{project_id}] Agent {agent_name} response: {json.dumps(planner_response)}")
                    
                    # Finalise response using FinaliserAgent
                    finaliser = FinaliserAgent(name=agent_name, provider=self.provider)
                    finaliser_response = await asyncio.to_thread(finaliser.finalise_response, query, {
                        "agent_name": agent_name,
                        "response": planner_response
                    })
                    
                    # add finaliser token usage to planner agent token usage
                    planner_agent.add_token_usage(finaliser.total_token_usage)
                    # store raw and final responses
                    agent_responses[agent_name] = {}
                    agent_responses[agent_name]["planner_response"] = planner_response
                    agent_responses[agent_name]["token_usage"] = planner_agent.total_token_usage
                    agent_responses[agent_name]["finaliser_response"] = self.extract_json(finaliser_response)
                    agent_responses[agent_name]["token_usage"] = planner_agent.total_token_usage
                except Exception as e:
                    logger.error(f"[{project_id}] Error in agent {agent_name}: {e}")

        # Run all steps in parallel (with concurrency limit) and wait for all to complete
        await asyncio.gather(*(run_agent_loop(agent) for agent in available_agents))
        
        combined_response = ""
        combined_token_usage = {}
        execution_pipelines_collection = self.db.mongodb.get_collection("execution_pipelines")
        for agent_name, agent_resp in agent_responses.items():
            # prepare combined response
            combined_response += f"{agent_resp['finaliser_response'].get('final_answer', '')}\n"
            
            # prepare token usage
            for token_key, tokens_used in agent_resp["token_usage"].items():
                combined_token_usage[token_key] = combined_token_usage.get(token_key, 0) + tokens_used
            
            # save pipeline details to mongodb collection "execution_pipelines"
            planner_response = agent_resp.get("planner_response", {})
            finaliser_response = agent_resp.get("finaliser_response", {})
            token_usage = agent_resp.get("token_usage", {})
            pipeline = await execution_pipelines_collection.insert_one(
                {
                    "project_id": project_id,
                    "prompt_id": prompt_id,
                    "query": query,
                    "agent": agent_name,
                    "planner_response": planner_response,
                    "finaliser_response": finaliser_response,
                    "token_usage": token_usage,
                    "created_at": datetime.utcnow(),
                }
            )
            agent_responses[agent_name]["pipeline_id"] = str(pipeline.inserted_id)

        # prepare agent_final_responses with pipeline ids
        agent_final_responses = [{ "agent": agent_name } | agent_resp for agent_name, agent_resp in agent_responses.items()]
        return {
            "response_text": combined_response,
            "token_usage": combined_token_usage,
            "agent_responses": agent_final_responses
        }
