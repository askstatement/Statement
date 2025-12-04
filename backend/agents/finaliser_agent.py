import json
from datetime import datetime

from llm.agent import Agent
from llm.message import (
    LLMMessage,
    LLMMessageRole,
    LLMRequest,
)
from llm.prompt_template import PromptTemplate

from .prompts.finaliser import ROUTER_AGENT_FINALISER_PROMPT

MAX_PLANNER_STEPS = 10
MODEL_NAME = "gpt-5.1"
REASONING_EFFORT = "none"


class FinaliserAgent(Agent):
    def planner_prompt(self):
        return PromptTemplate(ROUTER_AGENT_FINALISER_PROMPT)

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

    def agents_response_context_prompt(self, agent_responses: list):
        context = """
            Agents Responses:
            - [[agent_responses]]
            """
        user_context_template = PromptTemplate(context)

        return user_context_template.bind(agent_responses=json.dumps(agent_responses))

    def finalise_response(self, user_query: str, agent_responses: list):
        # SYSTEM PROMPT
        system_prompt = (
            self.planner_prompt()
            + self.user_context_prompt(user_query)
            + self.agents_response_context_prompt(agent_responses)
        )
        messages = []
        messages.append(
            LLMMessage(
                LLMMessageRole.SYSTEM,
                content=system_prompt.render(),
            )
        )

        request = LLMRequest(
            messages=messages,
            model=MODEL_NAME,
            params={
                "reasoning": {"effort": REASONING_EFFORT},
            },
        )

        # Generate React Loop Response
        response = self.generate_response(request)
        return response.text
