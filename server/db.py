"""Mongo queries live here so MCP handlers remain thin and testable."""

from collections.abc import Iterable
from typing import Any

from pymongo import MongoClient
from pymongo.client_session import ClientSession

from .config import MONGODB_DATABASE, MONGODB_URI


def get_database():
    return MongoClient(MONGODB_URI, serverSelectionTimeoutMS=3_000)[MONGODB_DATABASE]


def find_applications(db, filters: dict[str, Any], limit: int, skip: int):
    total = db.applications.count_documents(filters)
    documents = list(
        db.applications.find(filters)
        .sort("submittedAt", -1)
        .skip(skip)
        .limit(limit)
    )
    return documents, total


def get_application_by_id(db, app_id: str):
    return db.applications.find_one({"_id": app_id}, {"_id": 0})


def get_reviews_for_application(db, app_id: str):
    return list(db.reviews.find({"applicationId": app_id}, {"_id": 0})
                .sort("submittedAt", -1))


def get_reviewers_by_ids(db, ids: Iterable[str]):
    # Keep _id here because callers need it to resolve application references.
    return list(db.reviewers.find({"_id": {"$in": list(ids)}}))


def get_reviewer(db, reviewer_id: str):
    return db.reviewers.find_one({"_id": reviewer_id}, {"_id": 0})


def reviewer_with_most_assignments(db):
    return list(db.reviewers.find({}, 
                                  {"_id": 1, "name": 1, "activeAssignmentsCount": 1})
                                  .sort("activeAssignmentsCount", -1))


def cycle_summary_aggregation(db, cycle_id: str):
    # $facet keeps the status, amount, and review aggregates in Mongo in one request.
    pipeline = [
        #Filters the applications collection. It only keeps documents where cycleId matches the provided cycle_id.
        {"$match": {"cycleId": cycle_id}},
        # $lookup: Performs a left outer join. It pulls in matching documents from the reviews 
        # collection where the review's applicationId equals the application's _id. 
        # It stores them in a reviews array.
        {"$lookup": 
         {"from": "reviews", "localField": "_id", "foreignField": "applicationId", "as": "reviews"}},
        #$facet: Executes multiple sub-pipelines in parallel on the joined data.
        {"$facet": {
            #statusCounts: Groups the applications by their status field and counts how many applications are in each status.
            "statusCounts": [{"$group": {"_id": "$status", "count": {"$sum": 1}}}],
            #totals: Groups everything together to count the total number of applications and calculate the sum of all requestedAmount fields.
            "totals": [{"$group": {"_id": None, "applicationCount": {"$sum": 1}, "totalRequested": {"$sum": "$requestedAmount"}}}],
            #scores: Flattens the joined reviews array using $unwind and calculates the overall mathematical average of the score field across all reviews.
            "scores": [{"$unwind": "$reviews"}, {"$group": {"_id": None, "averageScore": {"$avg": "$reviews.score"}}}],
        }},
    ]
    return next(db.applications.aggregate(pipeline), None)

#Finds applications assigned to a given reviewer, optionally filtered by cycle/status.
def matching_reassignments(db, from_id: str, cycle_id: str | None, status_filter: str | None):
    query: dict[str, Any] = {"assignedReviewerIds": from_id}
    if cycle_id:
        query["cycleId"] = cycle_id
    if status_filter:
        query["status"] = status_filter
    return list(db.applications.find(query, {"_id": 1, "assignedReviewerIds": 1}))


def reassign_reviewer_commit(db, applications: list[dict[str, Any]], from_id: str, to_id: str):
    """Commit application and reviewer changes in one transaction when supported.
    
    Args:
        db: Database instance
        applications: List of applications to reassign
        from_id: Current reviewer ID
        to_id: New reviewer ID
    Returns:
        A structured result that identifies transactional versus standalone fallback.
        
    Raises:
        ValueError: If new reviewer does not exist
    """
    # Validate that the new reviewer exists
    to_reviewer = db.reviewers.find_one({"_id": to_id})
    if not to_reviewer:
        raise ValueError(f"Reviewer {to_id} does not exist")
    
    def apply(session: ClientSession | None = None):
        for app in applications:
            db.applications.update_one(
                {"_id": app["_id"], "assignedReviewerIds": from_id},
                {"$set": {"assignedReviewerIds": [to_id if rid == from_id else rid for rid in app["assignedReviewerIds"]]}},
                session=session,
            )
        count = len(applications)
        db.reviewers.update_one({"_id": from_id}, {"$inc": {"activeAssignmentsCount": -count}}, session=session)
        db.reviewers.update_one({"_id": to_id}, {"$inc": {"activeAssignmentsCount": count}}, session=session)
    
    try:
        with db.client.start_session() as session:
            with session.start_transaction():
                apply(session)
    except Exception as exc:
        # Standalone local Mongo cannot transact; the caller gets an explicit warning.
        if "Transaction numbers are only allowed" not in str(exc):
            raise
        apply()
        return {"status": "non_atomic_fallback", "affectedCount": len(applications)}
    return {"status": "transaction", "affectedCount": len(applications)}
