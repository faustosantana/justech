# Prediction Locking

States: DRAFT → READY_TO_LOCK → LOCKED → AWAITING_RESULTS → EVALUATED | EXPIRED | CANCELLED

LOCKED is immutable: no edits to inputs, candidates, ranking, scores, classifications, tiebreak rule, or engine version.

New evaluation needs a new prediction id.
