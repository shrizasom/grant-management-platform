from typing import Literal, Any, Dict

from pydantic import BaseModel, Field, model_validator

from .config import MAX_REASSIGN
from .db import (cycle_summary_aggregation, find_applications, get_application_by_id,
                 get_reviewer, get_reviewers_by_ids, get_reviews_for_application,
                 matching_reassignments, reassign_reviewer_commit)

ApplicationStatus = Literal["submitted", "under_review", "approved", "rejected", "waitlisted"]


class SearchApplicationsInput(BaseModel):
    status: ApplicationStatus | None = None
    cycleId: str | None = None
    minAmount: float | None = Field(default=None, ge=0)
    maxAmount: float | None = Field(default=None, ge=0)
    limit: int = Field(default=20, ge=1, le=100)
    skip: int = Field(default=0, ge=0)

    @model_validator(mode="after")
    def amount_range_is_valid(self):
        if self.minAmount is not None and self.maxAmount is not None and self.minAmount > self.maxAmount:
            raise ValueError("minAmount cannot exceed maxAmount")
        return self


def search_applications(db, **kwargs):
    request = SearchApplicationsInput(**kwargs)
    query: Dict[str, Any] = {key: value for key, value in 
             {"status": request.status, "cycleId": request.cycleId}.items() 
             if value is not None}
    if request.minAmount is not None or request.maxAmount is not None:
        query["requestedAmount"] = {}
        if request.minAmount is not None: 
            query["requestedAmount"]["$gte"] = request.minAmount
        if request.maxAmount is not None: 
            query["requestedAmount"]["$lte"] = request.maxAmount
    documents, total = find_applications(db, query, request.limit, request.skip)
    fields = ("_id", "applicantName", "projectTitle", "status", "requestedAmount", "cycleId", "submittedAt")
    results = [{("id" if key == "_id" else key): document.get(key) for key in fields} for document in documents]
    return {"applications": results, "totalCount": total, "hasMore": request.skip + len(results) < total}


def get_application(db, applicationId: str):
    app = get_application_by_id(db, applicationId)
    if not app:
        raise ValueError(f"Application '{applicationId}' was not found")
    reviewer_names = {item["_id"]: item["name"] for item in get_reviewers_by_ids(db, app.get("assignedReviewerIds", []))}
    reviews = get_reviews_for_application(db, applicationId)
    for review in reviews:
        review["reviewerName"] = reviewer_names.get(review["reviewerId"], "Unknown reviewer")
        review.pop("reviewerId", None)
    return {**app, "id": applicationId, "assignedReviewers": [reviewer_names.get(rid, "Unknown reviewer") for rid in app.get("assignedReviewerIds", [])], "reviews": reviews}


def cycle_summary(db, cycleId: str):
    result = cycle_summary_aggregation(db, cycleId) or {}
    totals = (result.get("totals") or [{}])[0]
    scores = (result.get("scores") or [{}])[0]
    return {"cycleId": cycleId, "countsByStatus": {x["_id"]: x["count"] for x in result.get("statusCounts", [])}, "applicationCount": totals.get("applicationCount", 0), "totalRequested": totals.get("totalRequested", 0), "averageScore": scores.get("averageScore")}


def reassign_reviewer(db, from_reviewer_id: str, to_reviewer_id: str, cycle_id: str | None = None, status_filter: ApplicationStatus | None = None, dry_run: bool = True, expectedCount: int | None = None):
    if not cycle_id and not status_filter:
        raise ValueError("Provide cycle_id or status_filter; global reassignment is prohibited")
    if from_reviewer_id == to_reviewer_id:
        raise ValueError("Source and destination reviewers must differ")
    if not get_reviewer(db, from_reviewer_id) or not get_reviewer(db, to_reviewer_id):
        raise ValueError("Both reviewer IDs must exist")
    matches = matching_reassignments(db, from_reviewer_id, cycle_id, status_filter)
    if any(to_reviewer_id in item["assignedReviewerIds"] for item in matches):
        raise ValueError("Destination reviewer is already assigned to at least one matching application; split the operation to avoid duplicates")
    diffs = [{"applicationId": item["_id"], "before": item["assignedReviewerIds"], "after": [to_reviewer_id if rid == from_reviewer_id else rid for rid in item["assignedReviewerIds"]]} for item in matches]
    preview = {"affectedCount": len(matches), "affectedApplicationIds": [item["_id"] for item in matches], "changes": diffs, "dryRun": dry_run}
    if dry_run:
        preview["commitInstructions"] = "Repeat with dry_run=false and expectedCount equal to affectedCount. Maximum commit size is 50."
        return preview
    if len(matches) > MAX_REASSIGN:
        raise ValueError(f"Commit exceeds MAX_REASSIGN ({MAX_REASSIGN}); split the operation")
    if expectedCount is None or expectedCount != len(matches):
        raise ValueError("expectedCount must exactly match the current preview count")
    preview["commitResult"] = reassign_reviewer_commit(db, matches, from_reviewer_id, to_reviewer_id)
    return preview
