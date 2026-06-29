# Field Map — Where every candidate field feeds the scoring formula

Scoring layers (recap):
- **SEMANTIC** → text that gets embedded and dot-producted with the JD vector
- **STRUCTURED** → numeric/boolean rules (YoE, location, notice period)
- **RED_FLAG** → triggers that subtract score (consulting, title-chasing, wrong domain, inactive coder)
- **AVAILABILITY** → the multiplier (engagement/responsiveness signals)
- **UNUSED** → in the data but not feeding any score (defended as "deliberately ignored to avoid noise")

## candidate_id
- Layer: **UNUSED** — just an identifier, written to output CSV as-is.

## profile.anonymized_name
- Layer: **UNUSED** — fake name, no signal value.

## profile.headline
- Layer: **SEMANTIC**
- Why: One-line self-description — dense signal for role/seniority match. Goes into the profile text we embed.

## profile.summary
- Layer: **SEMANTIC**
- Why: Long-form paragraph — highest-signal text in the whole record. Where people describe what they actually did.

## profile.location
- Layer: **STRUCTURED**
- Why: Feeds location match (JD wants Noida/Pune/Tier-1 India). Compare against a city preference list.

## profile.country
- Layer: **STRUCTURED** (soft)
- Why: India-resident = no visa risk (JD says no sponsorship). Non-India = small penalty, not disqualifier.

## profile.years_of_experience
- Layer: **STRUCTURED**
- Why: Authoritative total YoE. Drives the 4-5+ year gate from the JD. Wins over summing career_history durations (which is capped at 10 roles).

## profile.current_title
- Layer: **SEMANTIC + STRUCTURED (soft)**
- Why: Embedded as text. Also scanned with a regex for "Senior/Staff/Principal" — title-inflation check (red-flag if "Principal" with <3 yrs experience).

## profile.current_company
- Layer: **RED_FLAG + SEMANTIC**
- Why: Exact-match against the consulting blacklist (Mindtree, TCS, Infosys, etc.). Also goes into the profile text for context.

## profile.current_company_size
- Layer: **STRUCTURED**
- Why: JD implies product-company experience. Bucketed values need a lookup ("11-50" / "51-200" = startup, "10001+" = mega-corp/IT services).

## profile.current_industry
- Layer: **RED_FLAG + STRUCTURED**
- Why: "IT Services" is the consulting-industry smoking gun (saw it on CAND_0000001). Also soft penalty for "Staffing/Recruitment".

## career_history[].company
- Layer: **RED_FLAG + SEMANTIC**
- Why: Same consulting list, applied to every past role (one consulting stint 5 yrs ago is fine; 3+ consulting-only roles = red flag).

## career_history[].title
- Layer: **SEMANTIC**
- Why: Goes into embedded text. Lets the model see career trajectory (ML Engineer → Senior ML → Staff ML scores higher than random jumps).

## career_history[].start_date / end_date
- Layer: **UNUSED**
- Why: `duration_months` is already derived — re-deriving dates is wasted work.

## career_history[].duration_months
- Layer: **STRUCTURED** (red-flag)
- Why: Job-hopping detector. Median tenure < 18 months across 3+ roles = title-chaser red flag.

## career_history[].is_current
- Layer: **UNUSED**
- Why: Redundant with `end_date == null`. Skip.

## career_history[].industry
- Layer: **RED_FLAG + STRUCTURED**
- Why: Same industry-penalty logic as `profile.current_industry`, but per-role. A candidate with 1 consulting role + 2 product roles should NOT be killed.

## career_history[].company_size
- Layer: **STRUCTURED**
- Why: Same startup-vs-megacorp lookup as current. Helps confirm "did they actually work at a product company, or just claim to".

## career_history[].description
- Layer: **SEMANTIC**
- Why: Highest-value embedded text after `profile.summary`. Where the real work-history lives.

## education[].*
- Layer: **UNUSED** (institution, degree, field_of_study, start/end_year, grade, tier)
- Why: JD does not require any specific degree/institution. Using education tier would introduce bias (tier-3 college ≠ bad engineer) and isn't defensible against the JD text. **Deliberate omission, will defend in interview.**

## skills[].name
- Layer: **SEMANTIC**
- Why: Goes into the embedded text. List of skill names is high-signal for "do they know FAISS / sentence-transformers / NDCG".

## skills[].proficiency
- Layer: **SEMANTIC** (light boost)
- Why: "expert" in a skill adds a small text marker (e.g., "expert in FAISS") before embedding. Marginal effect, kept simple.

## skills[].endorsements
- Layer: **UNUSED**
- Why: Endorsements are vanity metric on LinkedIn-style platforms — not predictive of fit, easy to game.

## skills[].duration_months
- Layer: **STRUCTURED** (red-flag, soft)
- Why: "FAISS" listed with 2 months = suspect; 24+ months = real experience. Used to downgrade keyword-stuffing honeypots. Will be appended as a marker in the embedded text, e.g., "FAISS (24 months)".

## certifications[]
- Layer: **SEMANTIC**
- Why: Concatenated into the embedded profile text. Most candidates have 0, but it's free signal when present.

## languages[]
- Layer: **UNUSED**
- Why: JD doesn't ask for languages. Indian-candidate bias risk if we used English-proficiency as a gate.

## redrob_signals.profile_completeness_score
- Layer: **AVAILABILITY** (soft)
- Why: Profiles < 40% complete usually have garbage skills/summary — penalty, not hard filter.

## redrob_signals.signup_date
- Layer: **UNUSED**
- Why: Tenure on platform is not the same as engagement. `last_active_date` already captures freshness.

## redrob_signals.last_active_date
- Layer: **AVAILABILITY** (key)
- Why: The "down-weight inactive candidates" signal the JD explicitly asks for. Computed as days-since-active, fed into the multiplier.

## redrob_signals.open_to_work_flag
- Layer: **AVAILABILITY** (boost)
- Why: Self-reported openness → small upward nudge on the multiplier. Not a hard requirement (people leave it off when employed).

## redrob_signals.profile_views_received_30d
- Layer: **UNUSED**
- Why: Demand-side signal (other recruiters looking), not candidate-side availability. Not what the JD is asking for.

## redrob_signals.applications_submitted_30d
- Layer: **UNUSED**
- Why: Too noisy. High value can mean "mass-applying, low quality" or "active and searching" — can't distinguish.

## redrob_signals.recruiter_response_rate
- Layer: **AVAILABILITY** (key)
- Why: Direct responsiveness measure. Low rate → candidate will ghost recruiters → strong penalty.

## redrob_signals.avg_response_time_hours
- Layer: **AVAILABILITY**
- Why: Same responsiveness signal, finer-grained. Combined with response_rate in the multiplier.

## redrob_signals.skill_assessment_scores
- Layer: **SEMANTIC** (verified boost)
- Why: Verified scores beat self-reported skills. Top scores appended to the embedded text as "verified: Python 92, FAISS 88".

## redrob_signals.connection_count
- Layer: **UNUSED**
- Why: Vanity metric. LinkedIn connection counts are not predictive.

## redrob_signals.endorsements_received
- Layer: **UNUSED**
- Why: Same as skills.endorsements — vanity.

## redrob_signals.notice_period_days
- Layer: **STRUCTURED**
- Why: JD red flag: > 30 days = bar gets higher. Hard tier: ≤ 30 = full credit, 31-60 = -10%, 61-90 = -25%, > 90 = -50%.

## redrob_signals.expected_salary_range_inr_lpa
- Layer: **STRUCTURED** (soft)
- Why: Not in the JD as a hard constraint, but >2× the band is a soft misalignment signal. Used only to break ties, not to penalize.

## redrob_signals.preferred_work_mode
- Layer: **STRUCTURED**
- Why: JD implies onsite/hybrid (Noida/Pune). "Remote-only" + not willing to relocate = small penalty.

## redrob_signals.willing_to_relocate
- Layer: **STRUCTURED**
- Why: Boosts location match for non-locals. Combined with `preferred_work_mode` and `location`.

## redrob_signals.github_activity_score
- Layer: **STRUCTURED** (red-flag, soft)
- Why: Proxy for "still writes code". JD red flag: "Senior eng who hasn't written code in 18+ months". -1 (no GitHub linked) ≠ 0 (inactive) — handle separately.

## redrob_signals.search_appearance_30d
- Layer: **UNUSED**
- Why: Demand-side noise. Same reason as profile_views_received_30d.

## redrob_signals.saved_by_recruiters_30d
- Layer: **UNUSED**
- Why: Same — popularity ≠ fit for *this* JD.

## redrob_signals.interview_completion_rate
- Layer: **AVAILABILITY**
- Why: No-show rate. Low rate = candidate will waste recruiter time → multiplier penalty.

## redrob_signals.offer_acceptance_rate
- Layer: **AVAILABILITY** (soft)
- Why: Low rate = candidate is shopping / won't convert. -1 = no history → skip, don't penalize.

## redrob_signals.verified_email
- Layer: **AVAILABILITY** (baseline gate)
- Why: Unverified email = can't even reach them. Mild penalty (not hard filter — could be a new signup).

## redrob_signals.verified_phone
- Layer: **UNUSED**
- Why: Redundant with email verification as a "real person" signal. Don't double-penalize.

## redrob_signals.linkedin_connected
- Layer: **UNUSED**
- Why: Not predictive of fit. Just a platform feature flag.

---

## Summary count
- SEMANTIC: 8 fields (drive the embedding)
- STRUCTURED: 11 fields (drive the rules)
- RED_FLAG: 5 fields (drive the penalties)
- AVAILABILITY: 8 fields (drive the multiplier)
- UNUSED: 16 fields (deliberate omissions)

## What this means in practice
1. **One embedding per candidate** = concatenation of all SEMANTIC fields (headline + summary + titles + descriptions + skills + assessments).
2. **Structured layer** = a small Python function that turns 11 fields into bonus/penalty numbers.
3. **Red-flag layer** = hard-coded penalty triggers (consulting list, wrong industry, short tenures).
4. **Availability layer** = a single multiplier in [0.4, 1.1] computed from the 8 fields, then applied multiplicatively to the final score.
5. **Final formula**: `final = (semantic_score + structured_bonus - red_flag_penalty) × availability_multiplier - honeypot_penalty`