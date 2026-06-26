PRECOMPUTE (once, offline, no limits)
──────────────────────────────────────
candidates.jsonl → embed all 100K → save vectors to disk
job_description.md → embed JD → save vector to disk

RANK TIME (5 min, CPU, no internet)
──────────────────────────────────────
Load candidate vectors from disk
Load JD vector from disk
Score each candidate:
= dot_product(candidate, JD) ← semantic match

- structured_signals ← YoE, location, notice period

* red_flag_penalties ← consulting-only, wrong domain
  × availability_multiplier ← behavioral signals
  Sort descending
  Take top 100
  Build reasoning from JSON fields
  Write CSV
