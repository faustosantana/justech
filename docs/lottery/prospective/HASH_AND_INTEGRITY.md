# Hash and Integrity

Canonical JSON (sorted keys) hashed with SHA-256 at lock time.

Payload includes inputs, target_date, lotteries, positions, candidates, ranking, scores, classifications, tiebreak rule, engine/table versions, locked_at, engine_commit.

On evaluate, hash is recomputed. Mismatch → INTEGRITY_ERROR.
