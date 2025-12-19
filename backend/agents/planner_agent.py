import json
from datetime import date, datetime
from typing import Any, Dict, List

from agents.db.query_agent import QueryAgent
from llm.agent import Agent
from llm.message import (
    JSONLLMResponse,
    LLMMessage,
    LLMMessageRole,
    LLMRequest,
    LLMResponse,
)
from llm.prompt_template import PromptTemplate
from llm.provider import BaseLLMProvider
from llm.tool import Tool, ToolSet

from .prompts.planner_react_loop import (
    NEXT_STEP_PROMPT,
    PLANNER_REACT_LOOP_PROMPT,
    TOOL_PROMPT,
)

MAX_PLANNER_STEPS = 10
MODEL_NAME = "gpt-5.1"
REASONING_EFFORT = "none"


class PlannerAgent(Agent):
    def __init__(
        self,
        name,
        toolsets: [ToolSet],
        tool_cls: type,
        provider: BaseLLMProvider,
    ):
        super().__init__(name, provider)
        self.name = name
        self.toolsets = toolsets
        self.tool_cls = tool_cls

    def planner_prompt(self):
        return PromptTemplate(PLANNER_REACT_LOOP_PROMPT)

    def tools_context_prompt(self):
        tools_description = ""
        for toolset in self.toolsets:
            tools_description += json.dumps(toolset.to_schema()) + "\n"

        tool_prompt_template = PromptTemplate(TOOL_PROMPT)
        return tool_prompt_template.bind(tools_description=tools_description)

    def user_context_prompt(self, project_id: str):
        context = """
            User Context:
            - project_id: [[project_id]]
            - Current Datetime : (UTC): [[now]]
            """
        user_context_template = PromptTemplate(context)

        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        return user_context_template.bind(
            project_id=project_id,
            now=now,
        )

    def call_tool(self, tool_name: str, params: dict) -> str:
        if tool_name == "perform_elasticsearch_query":
            query_agent = QueryAgent(f"{self.tool_cls}QueryAgent", provider=self.provider)
            return query_agent.handle_request(
                project_id=self.project_id,
                user_request=params.get("user_message", ""),
            )

        for toolset in self.toolsets:
            tool: Tool = toolset.get_tool_by_name(tool_name)
            if tool:
                return tool.execute(params, tool_cls=self.tool_cls)
        raise ValueError(f"Tool {tool_name} not found in any toolset.")

    def process_tool_call(self, response: JSONLLMResponse) -> str:
        try:
            action = (response.json_data or {}).get("action", {}) or {}
            tool_name = action.get("tool_name")
            tool_params = action.get("tool_params")

            if not tool_name:
                return json.dumps({"observation": {"error": "Missing tool_name"}})

            observations = []

            if isinstance(tool_params, dict):
                param_list = [tool_params]
            elif isinstance(tool_params, list):
                param_list = tool_params
            else:
                return json.dumps(
                    {
                        "observation": {
                            "error": "tool_params must be list[dict] or dict for batchable"
                        }
                    }
                )

            for param_set in param_list:
                res = self.call_tool(tool_name, param_set or {})
                observations.append({"tool_params": param_set, "observation": res})

            payload = {
                "observation": {
                    "tool_name": tool_name,
                    "results": observations,
                }
            }
            return json.dumps(
                payload, default=str
            )  # default=str protects against datetimes, Decimals, etc.

        except Exception as e:
            return json.dumps({"observation": f"Error during tool call: {e}"})

    def check_if_toolset_empty(self) -> bool:
        is_empty = True
        for toolset in self.toolsets:
            if len(toolset) > 0:
                is_empty = False
                break
        return is_empty

    def request_using_query_agent(
        self, project_id: str, user_query: str, previous_messages: [LLMMessage]
    ):
        print(f"Passing request to QueryAgent for task: {user_query}")

    def handle_request(
        self, project_id: str, user_query: str, previous_messages: [LLMMessage]
    ):
        self.project_id = project_id
        print(f"Planning for task: {user_query} by agent: {self.name}")
        if self.check_if_toolset_empty():
            print("No toolsets available for planning. Going to QueryAgent directly.")
            return self.request_using_query_agent(
                project_id, user_query, previous_messages
            )

        # SYSTEM PROMPT
        system_prompt = (
            self.planner_prompt()
            + self.tools_context_prompt()
            + self.user_context_prompt(project_id)
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

        # ADD USER QUERY
        messages.append(
            LLMMessage(
                LLMMessageRole.USER,
                content=user_query,
            )
        )

        num_steps = 0

        while True:
            next_step_prompt = PromptTemplate(NEXT_STEP_PROMPT).render()
            messages.append(LLMMessage(LLMMessageRole.USER, content=next_step_prompt))

            request = LLMRequest(
                messages=messages,
                model=MODEL_NAME,
                params={
                    "reasoning": {"effort": REASONING_EFFORT},
                },
            )

            # Generate React Loop Response
            response = self.generate_structured_response(request)

            messages.append(LLMMessage(LLMMessageRole.ASSISTANT, content=response.text))

            print("Step : " + response.text)

            if "thought" in response.json_data:
                observations = self.process_tool_call(response)
                print("Observations :" + observations)
                messages.append(LLMMessage(LLMMessageRole.USER, content=observations))
            elif "final_answer" in response.json_data:
                is_success = response.json_data.get("is_success", False)
                if not is_success:
                    print("Planner could not find a successful answer.")
                    return self.request_using_query_agent(
                        project_id, user_query, previous_messages
                    )

                else:
                    final_answer = response.json_data.get("final_answer", {})
                    print("Final Answer: " + json.dumps(final_answer))
                    return final_answer

            num_steps += 1
            if num_steps >= MAX_PLANNER_STEPS:
                print("Max planner steps reached. Exiting.")
                return self.request_using_query_agent(
                    project_id, user_query, previous_messages
                )
