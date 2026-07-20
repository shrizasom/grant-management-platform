# Dataset

Four JSON-lines files (one JSON object per line), ready for `mongoimport`:

- `programCycles.json` — 5 funding cycles (grants/scholarships/fellowships), some active, some closed
- `applications.json` — 50 applications, each with `cycleId`, `status`, `requestedAmount`, `assignedReviewerIds`
- `reviewers.json` — 8 reviewers with `specialties` and `activeAssignmentsCount`
- `reviews.json` — 45 reviews linking `applicationId` + `reviewerId` with `score`, `recommendation`, `comments`

## Load with mongoimport
```bash
mongoimport --db grants --collection programCycles --file programCycles.json
mongoimport --db grants --collection applications  --file applications.json
mongoimport --db grants --collection reviewers     --file reviewers.json
mongoimport --db grants --collection reviews       --file reviews.json
```

## Relationships
- `applications.cycleId` → `programCycles._id`
- `applications.assignedReviewerIds[]` → `reviewers._id`
- `reviews.applicationId` → `applications._id`
- `reviews.reviewerId` → `reviewers._id`

`status` values: `submitted`, `under_review`, `approved`, `rejected`, `waitlisted`.
