import json
from datetime import datetime

from llm.agent import Agent
from llm.message import (
    LLMMessage,
    LLMMessageRole,
    LLMRequest,
)
from llm.prompt_template import PromptTemplate

from .prompts.pre_router import AVAILABLE_AGENTS_PROMPT, PRE_ROUTER_PROMPT

MODEL_NAME = "gpt-5.1"
REASONING_EFFORT = "none"


class PreRouterAgent(Agent):
    def planner_prompt(self):
        return PromptTemplate(PRE_ROUTER_PROMPT)

    def available_agent_context(self, available_agents: list, agent_scope: list):
        available_agent_template = PromptTemplate(AVAILABLE_AGENTS_PROMPT)

        return available_agent_template.bind(
            available_agents=available_agents,
            agent_scope=agent_scope,
        )

    def user_context_prompt(self, user_query: str):
        context = """
            User Context:
            - Current Datetime : (UTC): [[now]]
            - User Query: [[user_query]]
            """
        user_context_template = PromptTemplate(context)

        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        return user_context_template.bind(
            user_query=user_query,
            now=now,
        )

    def handle_request(
        self,
        user_query: str,
        previous_messages: [LLMMessage],
        available_agents: list,
        agent_scope: list,
    ):
        # SYSTEM PROMPT
        system_prompt = (
            self.planner_prompt()
            + self.user_context_prompt(user_query)
            + self.available_agent_context(available_agents, agent_scope)
        )
        messages = []
        messages.append(
            LLMMessage(
                LLMMessageRole.SYSTEM,
                content=system_prompt.render(),
            )
        )

        # ADD PREVIOUS MESSAGES
        messages.extend(previous_messages)

        request = LLMRequest(
            messages=messages,
            model=MODEL_NAME,
            params={
                "reasoning": {"effort": REASONING_EFFORT},
            },
        )

        # Generate React Loop Response
        response = self.generate_structured_response(request)
        return response.json_data
