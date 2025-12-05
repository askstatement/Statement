from typing import Any, Dict, List

ELASTIC_TOOL_DESCRIPTION = (
    "Run a safe Elasticsearch query against available indices and summarise "
    "results using a local pipeline of operations. Always include a "
    "`project_id` filter in the query body."
)

ELASTIC_BODY_DESCRIPTION = """
Generate a valid Elasticsearch search body for es.search(index=index, body=body).

Rules:
- Allowed top-level keys: query, from, _source, sort, aggs, size.
- Required: Must always include a `query` object, even if it is a match_all.
- Filtering:
    * Always filter by `project_id` using a term query in bool.filter.
    * Use bool.filter for multiple filters (faster than must).
- Document limiting:
    * Prefer aggregations (aggs) to summarise results instead of returning many raw hits.
    * If returning documents, explicitly set "size": 10 (never omit size).
- Aggregations (aggs):
    * Allowed types: terms, avg, sum, min, max, date_histogram.
    * When using terms or sort on a text field, always use its .keyword subfield if available.
    * Never enable fielddata or scripted fields.
- Date handling:
    * Only use date math (now, now-7d/d, now-1M/M, now/M) on fields mapped as date.
    * If the field is numeric (e.g., a UNIX timestamp), use numeric range filters instead of `now`.
- Safety & performance:
    * Never use keys like script_score, runtime_mappings, profile, rescore, highlight, scripted_metric.
    * Avoid queries that can fetch unbounded results or overload the server.
- Output:
    * Return a well-structured JSON object that Elasticsearch can execute directly.
    * Do not include explanations or comments in the output.
""".strip()

PIPELINE_DESCRIPTION = """
A list representing a sequential pipeline of operations to process query results.

Rules:
- Each operation must be an object with an `operation` key specifying the operation name.
- The final output must not be a huge list of documents:
    * Prefer aggregations, counts, averages, sums, or filters.
    * If you extract documents, limit to at most 10.
""".strip()


def build_elastic_tool_schema(
    index_metadata: Dict[str, Any],
    summariser_operations: List[str],
) -> List[Dict[str, Any]]:
    """
    Build the tool schema list for the DB query agent.
    Returns a list with a single function spec for `perform_elasticsearch_query`.
    """
    return [
        {
            "type": "function",
            "function": {
                "name": "perform_elasticsearch_query",
                "description": ELASTIC_TOOL_DESCRIPTION,
                "parameters": {
                    "type": "object",
                    "properties": {
                        "index": {
                            "type": "string",
                            "enum": list(index_metadata.keys()),
                            "description": "The Elasticsearch index to query.",
                        },
                        "body": {
                            "type": "object",
                            "description": ELASTIC_BODY_DESCRIPTION,
                        },
                        "pipeline": {
                            "type": "array",
                            "description": PIPELINE_DESCRIPTION,
                            "items": {
                                "type": "object",
                                "properties": {
                                    "operation": {
                                        "type": "string",
                                        "enum": summariser_operations,
                                        "description": (
                                            "Operation to apply "
                                            "(filter, sort, limit, project, sum, avg, etc.)."
                                        ),
                                    },
                                    "field": {
                                        "type": "string",
                                        "description": (
                                            "Field to use for this operation (if required)."
                                        ),
                                    },
                                    "group_by": {
                                        "type": "string",
                                        "description": (
                                            "Optional field to group by (for aggregations). "
                                            "Avoid *_id unless necessary."
                                        ),
                                    },
                                    "conditions": {
                                        "type": "object",
                                        "description": (
                                            "Key-value pairs for filtering "
                                            "(only when operation is 'filter')."
                                        ),
                                    },
                                    "order": {
                                        "type": "string",
                                        "enum": ["asc", "desc"],
                                        "description": (
                                            "Sort order (only when operation is 'sort')."
                                        ),
                                    },
                                    "n": {
                                        "type": "integer",
                                        "description": (
                                            "Number of results to return "
                                            "(for first_n, limit, skip)."
                                        ),
                                    },
                                    "fields": {
                                        "type": "array",
                                        "items": {"type": "string"},
                                        "description": (
                                            "List of fields to project (only for 'project')."
                                        ),
                                    },
                                    "percentile": {
                                        "type": "number",
                                        "description": (
                                            "Required only if operation is 'percentile'."
                                        ),
                                    },
                                },
                                "required": ["operation"],
                            },
                        },
                    },
                    "required": ["index", "body", "pipeline"],
                    "additionalProperties": False,
                },
            },
        }
    ]
