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

Why this design — tradeoffs you should be able to defend:

1. Precompute embeddings offline, score at rank-time. The 5-min CPU budget kills any per-candidate LLM call. So we trade model size for speed: a small (384-dim) sentence-transformer, embedded once, then dot-product is just matrix
   multiply. Cheaper, faster, reproducible.
2. Hybrid (semantic + structured) over pure embedding. Pure cosine fails on honeypots and on hard constraints like "must be in Bangalore" or "5+ years". Pure rules fail on synonyms ("PyTorch" vs "deep learning framework"). Hybrid gets
   both. You can defend this in the interview.
3. Multiplicative availability, not additive. Engagement should scale a candidate's fit, not add a flat bonus — a low-fit engaged candidate shouldn't outrank a high-fit less-active one. That's a design choice with reasoning behind it.
4. JD is fixed → embed once. No dynamic API calls, fully offline, deterministic.
5. Reasoning from real JSON fields, rotated templates. Avoids hallucination (Stage 4 red flag) and passes the variation check. We pick different fields per rank position (top ranks get strengths cited, mid ranks get balanced, bottom
   ranks acknowledge gaps honestly).

What we are NOT doing (and why):

- No hosted LLM at rank-time → violates compute rules
- No GPU → violates compute rules
- No per-candidate API call → won't fit 5 min
- No fine-tuned model → small data, would overfit, and we don't have labels

# Project Implementation Plan

- [x] **Step 1:** Read JD, extract requirements
    - **Output file:** `jd_spec.md`
    - **Status:** ✅ Done (I extracted it for you)

- [ ] **Step 2:** Inspect candidate schema, list which fields map to which scoring layer
    - **Output file:** `field_map.md`
    - **Status:** 🔴 Do this next

- [ ] **Step 3:** Build consulting-only detector (red flag #1)
    - **Output file:** `red_flags.py`
    - **Status:** 🔴 After step 2

- [ ] **Step 4:** Build signal extractor (YoE, location, notice period)
    - **Output file:** `signals.py`
    - **Status:** 🔴 After step 3

- [ ] **Step 5:** Build profile text builder (concatenate JD-relevant fields into one string per candidate)
    - **Output file:** `profile_text.py`
    - **Status:** Then

- [ ] **Step 6:** Embed all 100K profiles offline, save to disk
    - **Output file:** `precompute_embeddings.py`
    - **Status:** Then

- [ ] **Step 7:** Embed JD, save vector
    - **Output file:** `embed_jd.py`
    - **Status:** Then

- [ ] **Step 8:** Build scoring formula (semantic + structured - red flags \* availability - honeypot penalty)
    - **Output file:** `score.py`
    - **Status:** Then

- [ ] **Step 9:** Rank top 100, write reasoning, output CSV
    - **Output file:** `rank.py`
    - **Status:** Then

- [ ] **Step 10:** Validate CSV against spec
    - **Output file:** `validate.py`
    - **Status:** Then

- [ ] **Step 11:** Build Streamlit sandbox
    - **Output file:** `app.py`
    - **Status:** Day 5

- [ ] **Step 12:** Write README + PDF deck
    - **Output file:** —
    - **Status:** Day 5
