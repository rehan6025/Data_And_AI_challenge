"""
signals.py — Step 4 of the ranking pipeline.

Computes structured-signal bonus/penalty for a candidate using the
non-semantic, non-behavioral rules. Each function returns a small float
(positive = good, negative = bad). Final bonus is clamped to [-0.3, +0.3]
so this layer alone never overrules semantic + red-flag layers.

Signals covered (per field_map.md):
    1. yoe_bonus             — years of experience tier
    2. location_bonus        — Noida/Pune/Tier-1 India match
    3. notice_period_bonus   — shorter notice = better
    4. work_mode_bonus       — onsite/hybrid alignment with JD
    5. company_size_bonus    — startup-to-large-product sweet spot
    6. salary_soft_signal    — extreme misalignment (tie-breaker only)
    7. github_activity_bonus — only when GitHub IS linked

Usage:
    from signals import compute_structured_bonus
    bonus = compute_structured_bonus(candidate_dict)
"""

from __future__ import annotations

from typing import Any


# -----------------------------------------------------------------------------
# Constants
# -----------------------------------------------------------------------------

# JD says 4-5+ years, ideal 6-8. Tiered bonuses below.
YOE_BANDS: tuple[tuple[float, float], ...] = (
    # (min_yoe_inclusive, bonus)
    (0.0, -0.10),   # too junior
    (2.0, -0.05),   # still too junior
    (4.0,  0.00),   # floor of acceptable
    (5.0,  0.05),   # good
    (6.0,  0.10),   # ideal
    (8.0,  0.05),   # over-band, slight dim
    (10.0, 0.00),   # over-band, neutral
)

# Tier-1 India cities (JD says Noida/Pune preferred, Tier-1 flexible).
TIER_1_CITIES: tuple[str, ...] = (
    "noida", "pune", "mumbai", "bangalore", "bengaluru",
    "hyderabad", "delhi", "new delhi", "gurgaon", "gurugram",
    "chennai", "kolkata", "ahmedabad",
)

# Notice-period tiers (days). JD red flag: > 30 = bar gets higher.
NOTICE_TIERS: tuple[tuple[int, float], ...] = (
    (0,   0.05),   # immediate / serving notice — best
    (31,  0.00),   # 1 month
    (61, -0.10),   # 2 months — bar higher
    (91, -0.25),   # 3 months — strong penalty
)

# Work-mode alignment with JD (which implies onsite/hybrid in Noida/Pune).
WORK_MODE_BONUS: dict[str, float] = {
    "onsite":   0.05,
    "hybrid":   0.05,
    "flexible": 0.00,
    "remote":  -0.05,
}

# Company-size sweet spot. JD wants product-company experience.
# Solo freelancers / tiny shops = less evidence of scale.
# Mega IT-services = handled by red_flags, but huge generic corps = neutral.
COMPANY_SIZE_BONUS: dict[str, float] = {
    "1-10":       -0.02,  # too small
    "11-50":       0.03,
    "51-200":      0.05,  # startup sweet spot
    "201-500":     0.07,  # growth-stage — best
    "501-1000":    0.05,
    "1001-5000":   0.03,
    "5001-10000":  0.00,
    "10001+":      0.00,  # neutral here; red_flags handles IT-services
}

# Senior salary band. JD is for a senior IC at a startup; market ~ 30-60 LPA.
# Anything > 2x the band is misaligned. -1 / missing = no signal.
SALARY_BAND_MIN_LPA: float = 15.0
SALARY_BAND_MAX_LPA: float = 80.0
SALARY_MISALIGN_PENALTY: float = -0.05

# GitHub activity bonus. Only positive if linked AND active.
GITHUB_LINKED_BONUS: float = 0.03
GITHUB_GOOD_THRESHOLD: int = 30   # commits/PRs/stars score 0-100

# Final-clamp range.
BONUS_FLOOR: float = -0.30
BONUS_CEIL: float = 0.30


# -----------------------------------------------------------------------------
# Helpers
# -----------------------------------------------------------------------------

def _norm(s: Any) -> str:
    if not isinstance(s, str):
        return ""
    return " ".join(s.lower().strip().split())


def _city_in_list(city: str, choices: tuple[str, ...]) -> bool:
    c = _norm(city)
    if not c:
        return False
    return any(choice in c for choice in choices)


# -----------------------------------------------------------------------------
# Individual signal functions
# -----------------------------------------------------------------------------

def yoe_bonus(candidate: dict) -> float:
    """Tiered bonus based on years_of_experience (JD: 4-5+ yrs, ideal 6-8)."""
    yoe = candidate.get("profile", {}).get("years_of_experience", 0) or 0
    if not isinstance(yoe, (int, float)):
        return 0.0
    # Walk bands high-to-low so the first match wins.
    for min_yoe, bonus in reversed(YOE_BANDS):
        if yoe >= min_yoe:
            return bonus
    return 0.0  # unreachable, but safe


def location_bonus(candidate: dict) -> float:
    """
    India-resident in a Tier-1 city = full bonus.
    India-resident elsewhere = small bonus (willing_to_relocate rescues it).
    Non-India = no bonus (sponsorship risk per JD).
    """
    profile = candidate.get("profile", {})
    city = profile.get("location", "")
    country = _norm(profile.get("country", ""))
    signals = candidate.get("redrob_signals", {}) or {}
    willing = bool(signals.get("willing_to_relocate", False))

    # Non-India
    if country and country not in ("india", "in"):
        return 0.0

    # India, Tier-1 city
    if _city_in_list(city, TIER_1_CITIES):
        return 0.10

    # India, non-Tier-1 but willing to relocate
    if country in ("india", "in") and willing:
        return 0.05

    # India, non-Tier-1, not willing to relocate
    return 0.0


def notice_period_bonus(candidate: dict) -> float:
    """Shorter notice = better. >90 days is a hard hit."""
    signals = candidate.get("redrob_signals", {}) or {}
    days = signals.get("notice_period_days", 0) or 0
    if not isinstance(days, (int, float)):
        return 0.0
    # Walk tiers high-to-low.
    for min_days, bonus in reversed(NOTICE_TIERS):
        if days >= min_days:
            return bonus
    return 0.0


def work_mode_bonus(candidate: dict) -> float:
    """Onsite/hybrid aligns with JD (Noida/Pune). Pure-remote gets a small ding."""
    signals = candidate.get("redrob_signals", {}) or {}
    mode = _norm(signals.get("preferred_work_mode", ""))
    if not mode:
        return 0.0
    return WORK_MODE_BONUS.get(mode, 0.0)


def company_size_bonus(candidate: dict) -> float:
    """Bucketed size -> small bonus. Red_flags handles the IT-services case."""
    profile = candidate.get("profile", {})
    size = profile.get("current_company_size", "")
    if not size:
        return 0.0
    return COMPANY_SIZE_BONUS.get(size, 0.0)


def salary_soft_signal(candidate: dict) -> float:
    """
    Soft tie-breaker only. If expected salary band is wildly above market,
    tiny penalty. -1 / missing / 0 salary = no signal.
    """
    signals = candidate.get("redrob_signals", {}) or {}
    band = signals.get("expected_salary_range_inr_lpa", {}) or {}
    lo = band.get("min", 0) or 0
    hi = band.get("max", 0) or 0
    if not isinstance(lo, (int, float)) or not isinstance(hi, (int, float)):
        return 0.0
    if hi <= 0:
        return 0.0
    # 2x the top of the band = misaligned.
    if hi > 2 * SALARY_BAND_MAX_LPA:
        return SALARY_MISALIGN_PENALTY
    return 0.0


def github_activity_bonus(candidate: dict) -> float:
    """
    Bonus only if GitHub IS linked AND score is healthy.
    -1 (not linked) = no bonus, no penalty. Inactive (already penalized in
    red_flags if senior) gets no extra bonus here.
    """
    signals = candidate.get("redrob_signals", {}) or {}
    gh = signals.get("github_activity_score", -1)
    if not isinstance(gh, (int, float)):
        return 0.0
    if gh < 0:  # not linked
        return 0.0
    if gh >= GITHUB_GOOD_THRESHOLD:
        return GITHUB_LINKED_BONUS
    return 0.0


# -----------------------------------------------------------------------------
# Wrapper
# -----------------------------------------------------------------------------

def compute_structured_bonus(candidate: dict) -> float:
    """
    Sum all structured signals, clamp to [-0.3, +0.3].
    """
    total = (
        yoe_bonus(candidate)
        + location_bonus(candidate)
        + notice_period_bonus(candidate)
        + work_mode_bonus(candidate)
        + company_size_bonus(candidate)
        + salary_soft_signal(candidate)
        + github_activity_bonus(candidate)
    )
    return max(BONUS_FLOOR, min(BONUS_CEIL, total))


# -----------------------------------------------------------------------------
# CLI sanity check
# -----------------------------------------------------------------------------

if __name__ == "__main__":
    import json
    import sys

    path = sys.argv[1] if len(sys.argv) > 1 else "docs/sample_candidates.json"
    with open(path, "r", encoding="utf-8") as f:
        sample = json.load(f)

    print(f"Loaded {len(sample)} candidates from {path}\n")
    headers = ["yoe", "loc", "notice", "mode", "size", "salary", "gh", "TOTAL"]
    print(f"{'candidate_id':<14} " + " ".join(f"{h:>7}" for h in headers))
    print("-" * (14 + 8 * len(headers)))
    for c in sample[:20]:
        cid = c.get("candidate_id", "?")
        parts = [
            yoe_bonus(c),
            location_bonus(c),
            notice_period_bonus(c),
            work_mode_bonus(c),
            company_size_bonus(c),
            salary_soft_signal(c),
            github_activity_bonus(c),
        ]
        total = compute_structured_bonus(c)
        line = " ".join(f"{p:>+7.2f}" for p in parts) + f" {total:>+7.2f}"
        print(f"{cid:<14} {line}")
