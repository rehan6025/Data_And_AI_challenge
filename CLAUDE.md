# CLAUDE.md — Context for future Claude sessions

## What this project is
A take-home challenge: **rank the top 100 candidates out of 100,000 for a Senior AI Engineer JD (Redrob AI)**. Output a CSV with `candidate_id, rank, score, reasoning`.

## Hard constraints (the whole design revolves around these)
- 5-minute rank-time budget
- CPU only — no GPU
- No internet at rank-time
- No hosted LLM at rank-time (no API calls per candidate)

The only "AI" work allowed is **precomputing embeddings offline**, then dot-producting at rank-time.

## Read these files FIRST, in this order, every time
1. `jd_spec.md` — what the JD actually demands (must-haves + red flags)
2. `field_map.md` — which JSON field feeds which scoring layer, and why
3. `plan.md` — the 12-step implementation roadmap
4. `Implementation.md` — short status notes

Do NOT redesign the architecture without reading these. The design is locked in for a reason (compute budget).

## The scoring formula (the design, in plain English)
```
final = (semantic_match + structured_bonus − red_flag_penalty) × availability_multiplier − honeypot_penalty
```
- **semantic_match** = dot product of candidate embedding with JD embedding (offline-computed once)
- **structured_bonus** = small +/- for years of experience, location, notice period
- **red_flag_penalty** = hard subtraction for consulting-only, title-chasing, inactive senior coder, domain mismatch
- **availability_multiplier** = a number in [0.4, 1.1] derived from response rate, last-active, interview completion, etc. **Multiplicative, not additive** — engagement scales fit, doesn't add to it
- **honeypot_penalty** = extra kick for keyword-stuffers (e.g., Content Writer who lists "Python, TensorFlow")

## Where things live
- `docs/candidates.jsonl` — full 100K candidate pool (input)
- `docs/candidate_schema.json` — JSON schema for the input
- `docs/sample_candidates.json` — small sample for inspection
- `docs/sample_submission.csv` — example output format
- `jd_text.txt` — raw JD text
- `extract_jd.py` / `script.py` — earlier scratch scripts (read-only reference, do not extend)
- `field_map.md` — per-field scoring-layer assignment
- Output: top-100 CSV with `candidate_id,rank,score,reasoning`

## Project status
- ✅ Step 1: JD spec extracted (`jd_spec.md`)
- ✅ Step 2: Field map built (`field_map.md`)
- 🔴 Step 3: Build `red_flags.py` (consulting + title-chaser + inactive coder + domain mismatch)
- Steps 4–12: see `plan.md`

## Why fields are marked UNUSED in field_map.md
On purpose, not by oversight. The 16 unused fields (education tier, connection count, endorsements, vanity metrics, demand-side signals like search-appearance) are **deliberately ignored** to avoid noise and bias. If the user asks "why didn't you use X?", point to `field_map.md` — there's a reason for every one.

## Workflow notes
- This is on Windows (win32), Git Bash shell. Use Unix paths and forward slashes in commands.
- Python is the implementation language. No external services.
- Precompute stage: full Python, slow is fine.
- Rank stage: tight 5-min budget, prefer numpy matrix ops over loops.
- Don't add dependencies unless absolutely required.
- Don't push, don't commit unless asked.

## How the user works
- Wants short, plain-English explanations after each step (not jargon dumps).
- Prefers building the project piece by piece, with the user coding key files themselves.
- Wants design rationale to be **defensible in an interview** — every choice should have a stated "why".
