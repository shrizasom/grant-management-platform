"""Deliberately small agent loop; tool orchestration is not needed at this scale."""
import os
import time
from typing import Any, cast

from anthropic import Anthropic
from anthropic.types import MessageParam, ToolParam

from server.db import get_database, reviewer_with_most_assignments
from server.tools import cycle_summary, get_application, reassign_reviewer, search_applications

TOOL_SCHEMAS = [
    {"name": "search_applications", "description": "Search bounded application summaries by status, cycle ID, and amount.", "input_schema": {"type": "object", "properties": {"status": {"type": "string"}, "cycleId": {"type": "string"}, "minAmount": {"type": "number"}, "maxAmount": {"type": "number"}, "limit": {"type": "integer"}, "skip": {"type": "integer"}}}},
    {"name": "get_application", "description": "Get an application with reviews and reviewer names.", "input_schema": {"type": "object", "properties": {"applicationId": {"type": "string"}}, "required": ["applicationId"]}},
    {"name": "cycle_summary", "description": "Get status counts, requested total, and review-score average for a cycle ID.", "input_schema": {"type": "object", "properties": {"cycleId": {"type": "string"}}, "required": ["cycleId"]}},
    {"name": "reassign_reviewer", "description": "Preview a scoped reviewer reassignment; commits require dry_run false and the matching expectedCount.", "input_schema": {"type": "object", "properties": {"from_reviewer_id": {"type": "string"}, "to_reviewer_id": {"type": "string"}, "cycle_id": {"type": "string"}, "status_filter": {"type": "string"}, "dry_run": {"type": "boolean"}, "expectedCount": {"type": "integer"}}, "required": ["from_reviewer_id", "to_reviewer_id"]}},
    {"name": "reviewer_workload_summary", "description": "Return the reviewer or tied reviewers with the highest active assignment count.", "input_schema": {"type": "object", "properties": {}}},
]
tools = cast(list[ToolParam], TOOL_SCHEMAS)

def execute_tool(name: str, arguments: dict[str, Any]) -> Any:
    db = get_database()
    handlers = {"search_applications": search_applications, "get_application": get_application, "cycle_summary": cycle_summary, "reassign_reviewer": reassign_reviewer}
    if name == "reviewer_workload_summary":
        rows = reviewer_with_most_assignments(db)
        maximum = rows[0]["activeAssignmentsCount"] if rows else 0
        return {"reviewers": [{"id": row["_id"], "name": row["name"]} for row in rows if row["activeAssignmentsCount"] == maximum], "activeAssignmentsCount": maximum}
    return handlers[name](db, **arguments)


def run_agent(question: str) -> tuple[str, dict[str, int | float]]:
    """Answer a question and return response text plus aggregate latency/token metrics."""
    cycles = list(get_database().programCycles.find({}, {"_id": 1, "name": 1}))
    catalog = "; ".join(f"{row['name']} = {row['_id']}" for row in cycles)
    client = Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
    messages: list[MessageParam] = [
    cast(MessageParam, {"role": "user", "content": question})]
    started = time.perf_counter(); input_tokens = output_tokens = 0
    while True:
        response = client.messages.create(model=os.getenv("ANTHROPIC_MODEL", "claude-sonnet-4-20250514"), 
                                          max_tokens=700, 
                                          system=f"You are a concise grants assistant. Cycle ID catalog: {catalog}. Never claim a write completed unless its tool result says so.", 
                                          tools=tools, 
                                          messages=messages)
        input_tokens += response.usage.input_tokens; output_tokens += response.usage.output_tokens
        if response.stop_reason != "tool_use":
            answer = "\n".join(block.text for block in response.content if block.type == "text")
            return answer, {"latencySeconds": round(time.perf_counter() - started, 3), "inputTokens": input_tokens, "outputTokens": output_tokens}
        messages.append({"role": "assistant", "content": response.content})
        results = []
        for block in response.content:
            if block.type == "tool_use":
                try: payload = execute_tool(block.name, block.input)
                except Exception as exc: payload = {"error": str(exc)}
                results.append({"type": "tool_result", "tool_use_id": block.id, "content": str(payload)})
        messages.append({"role": "user", "content": results})
