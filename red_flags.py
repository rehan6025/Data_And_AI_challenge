"""
red_flags.py — Step 3 of the ranking pipeline.

Computes red-flag penalties for a candidate. Each penalty is a non-positive
float (0 means no penalty, more negative = worse). Final red_flag_penalty is
clamped to [-0.6, 0] so no single candidate gets nuked beyond recovery.

Penalties (per field_map.md):
    1. consulting_penalty      — career spent at IT-services / consulting shops
    2. title_chaser_penalty    — job-hopping or inflated senior title
    3. inactive_coder_penalty  — senior eng with no recent code activity
    4. domain_mismatch_penalty — entire career in non-tech / unrelated domains

Usage:
    from red_flags import compute_red_flags
    penalty = compute_red_flags(candidate_dict)
"""

from __future__ import annotations

from statistics import median
from typing import Any


# -----------------------------------------------------------------------------
# Constants
# -----------------------------------------------------------------------------

# Consulting / IT-services company blacklist.
# Sourced from jd_spec.md ("consulting-only career ... -> no").
# Match is case-insensitive substring against company name.
CONSULTING_COMPANIES: tuple[str, ...] = (
    "tcs", "tata consultancy",
    "infosys", "wipro", "hcl", "hcltech",
    "accenture", "cognizant", "capgemini",
    "mindtree", "ltimindtree", "mphasis", "persistent",
    "tech mahindra", "ltts", "larsen & toubro infotech",
    "ibm consult", "deloitte", "pwc", "kpmg", "ey", "ernst & young",
    "genpact", "wns", "exl service",
    "hexaware", "cyient", "zensar", "birlasoft",
)

# Industry strings that strongly indicate a consulting / staffing career.
# Match is case-insensitive substring against the industry string.
CONSULTING_INDUSTRIES: tuple[str, ...] = (
    "it services",
    "it consulting",
    "staffing & recruiting",
    "staffing and recruiting",
    "management consulting",
)

# Domains that disqualify for a Senior AI Engineer role.
# If the *entire* career is in these, that's a mismatch.
NON_TECH_INDUSTRIES: tuple[str, ...] = (
    "education", "non-profit", "nonprofit",
    "staffing & recruiting", "staffing and recruiting",
    "hospital & health care", "hospital and health care",
    "food & beverages", "food and beverages",
    "fashion", "retail",
    "construction", "real estate",
    "oil & energy", "oil and energy",
)

# Senior eng titles. If held with < INFLATION_MIN_YOE, that's suspicious.
SENIOR_TITLES: tuple[str, ...] = (
    "principal", "staff", "distinguished", "fellow", "chief",
)
INFLATION_MIN_YOE: float = 5.0

# Job-hopping thresholds.
HOP_MIN_ROLES: int = 3
HOP_MAX_MEDIAN_MONTHS: int = 18

# GitHub: senior + inactive = bad. Junior without GitHub = neutral.
INACTIVE_GITHUB_THRESHOLD: int = 5
SENIOR_YOE_FOR_INACTIVE: float = 5.0

# Final-clamp range. Never reduce a candidate by more than -0.6 from flags alone.
RED_FLAG_FLOOR: float = -0.6


# -----------------------------------------------------------------------------
# Helpers
# -----------------------------------------------------------------------------

def _norm(s: Any) -> str:
    """Lowercase, strip, collapse spaces. Safe for None / non-str."""
    if not isinstance(s, str):
        return ""
    return " ".join(s.lower().split())


def _is_consulting_company(name: str) -> bool:
    n = _norm(name)
    if not n:
        return False
    return any(black in n for black in CONSULTING_COMPANIES)


def _is_consulting_industry(industry: str) -> bool:
    n = _norm(industry)
    if not n:
        return False
    return any(ind in n for ind in CONSULTING_INDUSTRIES)


def _is_non_tech_industry(industry: str) -> bool:
    n = _norm(industry)
    if not n:
        return False
    return any(ind in n for ind in NON_TECH_INDUSTRIES)


# -----------------------------------------------------------------------------
# Individual penalty functions
# -----------------------------------------------------------------------------

def consulting_penalty(candidate: dict) -> float:
    """
    How much of the candidate's career has been at consulting / IT-services shops?

    Counts both current and past roles. Looks at *both* company name AND
    industry (either signal triggers). 0% = 0, 1 hit = -0.05, 2 = -0.15,
    3+ = -0.30. The kill threshold is high because one consulting stint
    5 years ago is fine — it's the all-consulting-career that should die.
    """
    hits = 0

    # Current role
    cur_company = candidate.get("profile", {}).get("current_company", "")
    cur_industry = candidate.get("profile", {}).get("current_industry", "")
    if _is_consulting_company(cur_company) or _is_consulting_industry(cur_industry):
        hits += 1

    # Past roles
    for role in candidate.get("career_history", []) or []:
        company = role.get("company", "")
        industry = role.get("industry", "")
        if _is_consulting_company(company) or _is_consulting_industry(industry):
            hits += 1

    if hits == 0:
        return 0.0
    if hits == 1:
        return -0.05
    if hits == 2:
        return -0.15
    return -0.30  # 3+ hits = career is consulting-only


def title_chaser_penalty(candidate: dict) -> float:
    """
    Two signals:

    (a) Title inflation: current title contains 'Principal'/'Staff'/etc.
        but candidate has < 5 years of experience.
    (b) Job-hopping: median tenure across 3+ roles is < 18 months.

    Each signal contributes. Capped at -0.30 combined.
    """
    penalty = 0.0

    yoe = candidate.get("profile", {}).get("years_of_experience", 0) or 0
    title = _norm(candidate.get("profile", {}).get("current_title", ""))

    inflated = any(t in title for t in SENIOR_TITLES)
    if inflated and yoe < INFLATION_MIN_YOE:
        penalty += -0.15

    # Job-hopping
    durations = []
    for role in candidate.get("career_history", []) or []:
        d = role.get("duration_months")
        if isinstance(d, (int, float)) and d > 0:
            durations.append(int(d))

    if len(durations) >= HOP_MIN_ROLES:
        med = median(durations)
        if med < HOP_MAX_MEDIAN_MONTHS:
            penalty += -0.20

    return max(penalty, -0.30)


def inactive_coder_penalty(candidate: dict) -> float:
    """
    Junior eng without GitHub linked = no penalty (-1 = not linked, not 0).
    Senior eng with very low / zero GitHub activity = -0.15.
    """
    signals = candidate.get("redrob_signals", {}) or {}
    gh = signals.get("github_activity_score", -1)

    # -1 means "no GitHub linked" — don't punish absence.
    if gh == -1:
        return 0.0

    # Junior eng without GitHub is normal.
    yoe = candidate.get("profile", {}).get("years_of_experience", 0) or 0
    if yoe < SENIOR_YOE_FOR_INACTIVE:
        return 0.0

    if isinstance(gh, (int, float)) and gh <= INACTIVE_GITHUB_THRESHOLD:
        return -0.15
    return 0.0


def domain_mismatch_penalty(candidate: dict) -> float:
    """
    If *every* career role is in non-tech industries AND there are no
    ML/software/data-industry roles, treat as domain mismatch.

    Empty career_history is not a mismatch (insufficient data).
    """
    history = candidate.get("career_history", []) or []
    if not history:
        return 0.0

    all_non_tech = all(
        _is_non_tech_industry(r.get("industry", "")) for r in history
    )
    if not all_non_tech:
        return 0.0

    # Also check current_industry as a tie-breaker.
    cur_industry = candidate.get("profile", {}).get("current_industry", "")
    if _is_non_tech_industry(cur_industry):
        return -0.25
    # History says non-tech, current says tech — partial credit, no penalty.
    return 0.0


# -----------------------------------------------------------------------------
# Wrapper
# -----------------------------------------------------------------------------

def compute_red_flags(candidate: dict) -> float:
    """
    Aggregate all red-flag penalties, clamp to [-0.6, 0].

    Returns a non-positive float. 0 = clean. -0.6 = worst possible from flags.
    """
    total = (
        consulting_penalty(candidate)
        + title_chaser_penalty(candidate)
        + inactive_coder_penalty(candidate)
        + domain_mismatch_penalty(candidate)
    )
    return max(total, RED_FLAG_FLOOR)


# -----------------------------------------------------------------------------
# CLI sanity check (runs only if executed directly)
# -----------------------------------------------------------------------------

if __name__ == "__main__":
    import json
    import sys

    path = sys.argv[1] if len(sys.argv) > 1 else "docs/sample_candidates.json"
    with open(path, "r", encoding="utf-8") as f:
        sample = json.load(f)

    print(f"Loaded {len(sample)} candidates from {path}\n")
    print(f"{'candidate_id':<14} {'consult':>8} {'chaser':>8} {'inactive':>9} {'domain':>7} {'TOTAL':>7}")
    print("-" * 60)
    for c in sample[:20]:
        cid = c.get("candidate_id", "?")
        cons = consulting_penalty(c)
        chaser = title_chaser_penalty(c)
        inactive = inactive_coder_penalty(c)
        domain = domain_mismatch_penalty(c)
        total = compute_red_flags(c)
        print(f"{cid:<14} {cons:>+8.2f} {chaser:>+8.2f} {inactive:>+9.2f} {domain:>+7.2f} {total:>+7.2f}")
