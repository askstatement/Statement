# db_agent/db_query_agent.py

import datetime
import inspect
import json
import re
import sys
import traceback
from binhex import REASONABLY_LARGE
from typing import Any, Dict, List

from agents.prompts.query_agent import (
    CONSTRAINTS_TEMPLATE,
    JSON_OUTPUT_TEMPLATE,
    OPS_SCHEMA_TEMPLATE,
    QUESTION_TEMPLATE,
    SYSTEM_TEMPLATE,
    TOOLS_TEMPLATE,
)
from elastic_tool_schema import build_elastic_tool_schema
from elasticsearch import exceptions
from llm.agent import Agent
from llm.message import JSONLLMResponse, LLMMessage, LLMMessageRole, LLMRequest
from llm.tool import Tool
from schema.elasticschema import ES_SCHEMA  # your existing ES schema description
from services.elastic import es, get_mapping

from backend.llm.prompt_template import PromptTemplate

from .summarizer_tools import SummariserTools

MODEL = "gpt-5.1"
REASONING_EFFORT = "low"


def build_system_prompt(
    index_metadata: Dict[str, Any], tools: List[Dict[str, Any]]
) -> str:
    index_metadata_json = json.dumps(index_metadata, indent=2)
    tools_json = json.dumps(tools, indent=2)
    return (
        PromptTemplate(SYSTEM_TEMPLATE)
        .concat(PromptTemplate(TOOLS_TEMPLATE))
        .render(
            index_metadata_json=index_metadata_json,
            tools_json=tools_json,
        )
    )


def build_user_prompt(
    db_tools_schema: List[Dict[str, Any]],
    project_id: str,
    user_request: str,
    now: datetime,
) -> str:
    db_tools_schema_json = json.dumps(db_tools_schema, indent=2)
    now_str = now.strftime("%Y-%m-%d %H:%M:%S")

    pt = PromptTemplate(OPS_SCHEMA_TEMPLATE).concat(
        PromptTemplate(CONSTRAINTS_TEMPLATE),
        PromptTemplate(JSON_OUTPUT_TEMPLATE),
        PromptTemplate(QUESTION_TEMPLATE),
    )
    return pt.render(
        db_tools_schema_json=db_tools_schema_json,
        project_id=project_id,
        user_request=user_request,
        now_str=now_str,
    )


def build_db_agent_request(
    index_metadata: Dict[str, Any],
    tools: List[Dict[str, Any]],
    db_tools_schema: List[Dict[str, Any]],
    project_id: str,
    user_request: str,
    model: str = "gpt-5",
) -> LLMRequest:
    """
    Build an LLMRequest for the DB agent, ready to be passed to a provider.
    """
    now = datetime.now()
    system_prompt = build_system_prompt(index_metadata, tools)
    user_prompt = build_user_prompt(db_tools_schema, project_id, user_request, now)

    messages = [
        LLMMessage(LLMMessageRole.SYSTEM, system_prompt),
        LLMMessage(LLMMessageRole.USER, user_prompt),
    ]

    return LLMRequest(
        messages=messages,
        model=model,
        params={
            "reasoning": {"effort": REASONING_EFFORT},
        },
    )


def _build_index_metadata() -> Dict[str, Any]:
    """
    Build a compact index metadata dict from ES_SCHEMA.

    Expected ES_SCHEMA shape (your existing module):
    [
      {
        "index": "stripe_customers",
        "description": "...",
        "index_body": {...}
      },
      ...
    ]
    """
    index_metadata: Dict[str, Any] = {}

    for index in ES_SCHEMA:
        index_name = index.get("index")
        if not index_name:
            continue
        index_metadata[index_name] = {
            "description": index.get("description") or "",
            "index_body": index.get("index_body") or {},
            # You can add more if you want (field lists, etc.)
        }
    return index_metadata


def _build_db_tools_schema() -> List[Dict[str, Any]]:
    """
    Introspect SummariserTools methods and turn them into JSON tool specs
    using your generic Tool infrastructure. This is *only* for documentation
    to the LLM; these tools are not invoked via tool-calls.
    """
    specs: List[Dict[str, Any]] = []
    for name, func in inspect.getmembers(SummariserTools, predicate=inspect.isfunction):
        if name.startswith("_"):
            continue
        tool = Tool.from_function(func)
        specs.append(tool.to_schema())
    return specs


class QueryAgent(Agent):
    """
    Concrete Agent that:
    - Asks the LLM to design one call to `perform_elasticsearch_query`
      (index + ES body + summarisation pipeline).
    - Validates and executes that ES query safely.
    - Runs the local SummariserTools pipeline on the ES results.
    """

    def __init__(self, provider):
        super().__init__(name="db_query_agent", provider=provider)

        self.es = es
        self.index_metadata = _build_index_metadata()
        self.summarizer = SummariserTools()

        # Tool schema for perform_elasticsearch_query (what the LLM sees)
        summariser_operations = list(self.summarizer._get_operations().keys())
        self.tools = build_elastic_tool_schema(
            index_metadata=self.index_metadata,
            summariser_operations=summariser_operations,
        )

        # Optional: doc schema for summariser operations
        self.db_tools_schema = _build_db_tools_schema()

    # ---------- ES helpers ----------

    def is_valid_index(self, index: str) -> bool:
        if not index:
            return False
        if index.startswith("."):
            return False
        return bool(re.match(r"^[a-zA-Z0-9-_]+$", index))

    def sanitize_date_math(self, query: Any) -> Any:
        """
        Recursively sanitize date math strings in an Elasticsearch query.
        Fixes invalid formats like '/M-1ms' etc.
        """

        def fix_date_math(value: Any) -> Any:
            if not isinstance(value, str):
                return value
            if value.startswith("/"):
                value = "now" + value
            # Extremely conservative; mostly just ensures `now/...` shape.
            return value

        if isinstance(query, dict):
            new_query: Dict[str, Any] = {}
            for k, v in query.items():
                if k == "range" and isinstance(v, dict):
                    new_range: Dict[str, Any] = {}
                    for field, range_dict in v.items():
                        if isinstance(range_dict, dict):
                            new_range[field] = {
                                key: fix_date_math(val)
                                if key in ("gte", "lte", "gt", "lt")
                                else val
                                for key, val in range_dict.items()
                            }
                        else:
                            new_range[field] = range_dict
                    new_query[k] = new_range
                else:
                    new_query[k] = self.sanitize_date_math(v)
            return new_query
        if isinstance(query, list):
            return [self.sanitize_date_math(item) for item in query]
        return query

    def validate_query(self, body: Dict[str, Any]) -> None:
        if not isinstance(body, dict):
            raise ValueError("Query body must be a dictionary.")

        if "query" not in body:
            raise ValueError("Missing 'query' key in body.")
        if not isinstance(body["query"], dict):
            raise ValueError("'query' must be a dictionary.")

        if "size" in body and not isinstance(body["size"], int):
            raise ValueError("'size' must be an integer if present.")

        forbidden = {
            "script_score",
            "scripted_metric",
            "runtime_mappings",
            "profile",
            "rescore",
            "highlight",
        }
        query_str = json.dumps(body.get("query", {})).lower()
        for f in forbidden:
            if f in query_str:
                raise ValueError(f"Forbidden query feature used: {f}")

        if "aggs" in body and not isinstance(body["aggs"], dict):
            raise ValueError("'aggs' must be an object if present.")

    def rewrite_text_to_keyword(
        self, body: Dict[str, Any], mapping: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Convert text fields in aggs/sort to their `.keyword` subfield when a keyword multi-field exists.
        """

        if not isinstance(body, dict):
            return body

        def get_field_type(field_path: str, mapping_dict: Dict[str, Any]):
            parts = field_path.split(".")
            cur = mapping_dict.get("properties", mapping_dict)
            for p in parts:
                if (
                    isinstance(cur, dict)
                    and "properties" in cur
                    and p in cur["properties"]
                ):
                    cur = cur["properties"][p]
                elif isinstance(cur, dict) and p in cur:
                    cur = cur[p]
                else:
                    return None, {}
            if not isinstance(cur, dict):
                return None, {}
            return cur.get("type"), cur.get("fields", {})

        def rewrite_dict(d: Dict[str, Any]) -> Dict[str, Any]:
            for key, value in list(d.items()):
                if key in ("aggs", "aggregations") and isinstance(value, dict):
                    d[key] = rewrite_dict(value)
                elif key == "terms" and isinstance(value, dict) and "field" in value:
                    field = value["field"]
                    field_type, subfields = get_field_type(field, mapping)
                    if field_type == "text" and "keyword" in subfields:
                        value["field"] = field + ".keyword"
                elif key == "sort" and isinstance(value, list):
                    for i, s in enumerate(value):
                        if isinstance(s, dict):
                            new_s: Dict[str, Any] = {}
                            for f, opts in s.items():
                                field_type, subfields = get_field_type(f, mapping)
                                if field_type == "text" and "keyword" in subfields:
                                    new_s[f + ".keyword"] = opts
                                else:
                                    new_s[f] = opts
                            value[i] = new_s
                elif isinstance(value, dict):
                    d[key] = rewrite_dict(value)
                elif isinstance(value, list):
                    d[key] = [
                        rewrite_dict(v) if isinstance(v, dict) else v for v in value
                    ]
            return d

        return rewrite_dict(body)

    def add_project_id_filter(
        self, body: Dict[str, Any], project_id: str
    ) -> Dict[str, Any]:
        if not isinstance(body, dict):
            body = {}
        body = dict(body)  # shallow copy

        if "query" not in body:
            body["query"] = {"bool": {"filter": []}}
        elif "bool" not in body["query"]:
            body["query"] = {"bool": {"filter": [body["query"]]}}
        elif "filter" not in body["query"]["bool"]:
            body["query"]["bool"]["filter"] = []

        project_filter = {"term": {"project_id": project_id}}
        filters = body["query"]["bool"]["filter"]
        if project_filter not in filters:
            filters.append(project_filter)
        return body

    def _flatten_aggregations(self, aggs: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Turn ES aggregation results into a flat list of dicts
        usable by the summarisation pipeline.
        """
        results: List[Dict[str, Any]] = []

        def _flatten_bucket(bucket: Dict[str, Any]):
            if "buckets" in bucket:
                for b in bucket["buckets"]:
                    entry = {"key": b.get("key"), "doc_count": b.get("doc_count")}
                    for k, v in b.items():
                        if k not in ("key", "doc_count"):
                            entry[k] = v
                    results.append(entry)
            elif "value" in bucket:
                results.append({"value": bucket["value"]})

        for _, agg_val in aggs.items():
            _flatten_bucket(agg_val)

        return results

    def run_pipeline(
        self, pipeline: List[Dict[str, Any]], documents: List[Dict[str, Any]]
    ) -> Any:
        results: Any = documents
        try:
            for step in pipeline:
                results = self.summarizer._execute_plan(step, results)

                if step.get("operation") in [
                    "sum",
                    "avg",
                    "min",
                    "max",
                    "median",
                    "mode",
                    "stddev",
                    "variance",
                    "unique_count",
                    "percentile",
                ]:
                    return results

                if isinstance(results, Dict):
                    results = [{"group": k, "docs": v} for k, v in results.items()]

            return results
        except Exception as e:
            _, _, exc_tb = sys.exc_info()
            tb_list = traceback.extract_tb(exc_tb)
            last_call = tb_list[-1] if tb_list else None
            fn_name = last_call.name if last_call else "unknown"
            return {"error": f"Summariser pipeline error [{fn_name}]: {str(e)}"}

    def perform_query_and_summarise(
        self,
        index: str,
        body: Dict[str, Any],
        pipeline: List[Dict[str, Any]],
        scroll_size: int = 1000,
        scroll_timeout: str = "2m",
    ) -> Any:
        """
        Execute ES query safely and run summariser pipeline.
        """
        try:
            if not self.is_valid_index(index):
                raise ValueError(f"Invalid or restricted index: {index}")

            mapping = get_mapping(index)
            if not mapping:
                raise ValueError(f"Could not retrieve mapping for index: {index}")

            body = self.rewrite_text_to_keyword(body, mapping)
            self.validate_query(body)
            body = self.sanitize_date_math(body)

            # Respect explicit size
            body = dict(body)
            requested_size = body.pop("size", None)

            # If size = 0, we only care about aggregations; no scroll needed.
            if requested_size == 0:
                result = self.es.search(index=index, body=body)
                if "aggregations" in result:
                    aggs = self._flatten_aggregations(result["aggregations"])
                    return self.run_pipeline(pipeline, aggs)
                docs = result.get("hits", {}).get("hits", [])
                return self.run_pipeline(pipeline, docs)

            if requested_size is not None:
                scroll_size = requested_size

            body.pop("track_total_hits", None)

            result = self.es.search(
                index=index,
                body=body,
                scroll=scroll_timeout,
                size=scroll_size,
            )
            scroll_id = result.get("_scroll_id")
            documents: List[Dict[str, Any]] = result.get("hits", {}).get("hits", [])

            hard_scroll_limit = 10000
            iterations = 0

            while True:
                iterations += 1
                if iterations > hard_scroll_limit:
                    break
                if not scroll_id:
                    break

                next_scroll = self.es.scroll(scroll_id=scroll_id, scroll=scroll_timeout)
                hits = next_scroll.get("hits", {}).get("hits", [])
                if not hits:
                    break
                documents.extend(hits)
                scroll_id = next_scroll.get("_scroll_id")

            summary = self.run_pipeline(pipeline, documents)
            return summary

        except exceptions.AuthenticationException:
            raise PermissionError("Authentication failed for Elasticsearch")
        except exceptions.AuthorizationException:
            raise PermissionError("Not authorized to query this index")
        except exceptions.RequestError as e:
            raise ValueError(f"Bad ES query request: {e.info}")
        except Exception as e:
            _, _, exc_tb = sys.exc_info()
            tb_list = traceback.extract_tb(exc_tb)
            last_call = tb_list[-1] if tb_list else None
            fn_name = last_call.name if last_call else "unknown"
            raise RuntimeError(f"Unexpected Elasticsearch error [{fn_name}]: {str(e)}")

    # ---------- Agent API ----------

    def handle_request(
        self,
        user_request: str,
        project_id: str,
    ) -> Dict[str, Any]:
        """
        Main entrypoint.

        1. Ask the LLM (via provider) for a JSON plan:
           - tool: "perform_elasticsearch_query"
           - input: { index, body, pipeline }
        2. Execute the ES query + pipeline locally.
        3. Return result + explanation + token usage.
        """
        llm_req = build_db_agent_request(
            index_metadata=self.index_metadata,
            tools=self.tools,
            db_tools_schema=self.db_tools_schema,
            project_id=project_id,
            user_request=user_request,
            model=MODEL,
        )

        # Use provider to get JSON response
        resp: JSONLLMResponse = self.generate_structured_response(llm_req)
        data = resp.json_data

        # Extract tool call
        action = data.get("action", {}) or {}
        tool_name = action.get("tool")
        tool_input = action.get("input", {}) or {}
        explanation = data.get("explanation", "")

        if tool_name != "perform_elasticsearch_query":
            return {
                "error": f"Unexpected tool requested: {tool_name}",
                "raw_plan": data,
                "token_usage": self.total_token_usage,
            }

        # Be tolerant: input might be stringified JSON
        if isinstance(tool_input, str):
            try:
                tool_input = json.loads(tool_input)
            except Exception as e:
                return {
                    "error": f"Tool input is not valid JSON: {e}",
                    "raw_plan": data,
                    "token_usage": self.total_token_usage,
                }

        index = tool_input.get("index")
        body = tool_input.get("body", {}) or {}
        pipeline = tool_input.get("pipeline", []) or []

        body = self.add_project_id_filter(body, project_id)
        result = self.perform_query_and_summarise(index, body, pipeline)

        # If result is a big list, clip to 10 for safety
        if isinstance(result, list) and len(result) > 10:
            result = result[:10]

        return {
            "result": result,
            "plan": data,
            "explanation": explanation,
            "token_usage": self.total_token_usage,
        }
