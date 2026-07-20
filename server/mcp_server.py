"""Run with: python -m server.mcp_server"""
from mcp.server.fastmcp import FastMCP

from .db import get_database, reviewer_with_most_assignments
from .tools import ApplicationStatus, cycle_summary, get_application, reassign_reviewer, search_applications

mcp = FastMCP("Grant Workflow")

@mcp.tool(name="search_applications")
def search_applications_tool(status: str | None = None, cycleId: str | None = None, minAmount: float | None = None, maxAmount: float | None = None, limit: int = 20, skip: int = 0):
    """Search grant applications by status, cycle, and requested amount with bounded pagination."""
    return search_applications(get_database(), status=status, cycleId=cycleId, minAmount=minAmount, maxAmount=maxAmount, limit=limit, skip=skip)

@mcp.tool(name="get_application")
def get_application_tool(applicationId: str):
    """Get one application with resolved assigned-reviewer names and submitted reviews."""
    return get_application(get_database(), applicationId)

@mcp.tool(name="cycle_summary")
def cycle_summary_tool(cycleId: str):
    """Return MongoDB-computed application counts, total requested amount, and average review score for a cycle."""
    return cycle_summary(get_database(), cycleId)

@mcp.tool(name="reviewer_workload_summary")
def reviewer_workload_summary_tool():
    """Return the reviewer or tied reviewers with the highest active assignment count."""
    rows = reviewer_with_most_assignments(get_database())
    maximum = rows[0]["activeAssignmentsCount"] if rows else 0
    return {"reviewers": [{"id": row["_id"], "name": row["name"]} for row in rows if row["activeAssignmentsCount"] == maximum], "activeAssignmentsCount": maximum}

@mcp.tool(name="reassign_reviewer")
def reassign_reviewer_tool(from_reviewer_id: str, to_reviewer_id: str, cycle_id: str | None = None, status_filter: ApplicationStatus | None = None, dry_run: bool = True, expectedCount: int | None = None):
    """Safely preview or commit a scoped reviewer reassignment. Dry run is the default; commits require a matching preview count."""
    return reassign_reviewer(get_database(), from_reviewer_id, to_reviewer_id, cycle_id, status_filter, dry_run, expectedCount)

if __name__ == "__main__":
    mcp.run()
