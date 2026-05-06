from datetime import datetime
import json
def adjuster_agent(state: dict) -> dict:


    with open("config/adjusters.json") as f:
        adjusters = json.load(f)
    """
    Agentic adjuster assignment based on claim context.
    """
    extracted = state.get("extracted_fields", {})
    claim_type = extracted.get("Claim Type", "").lower()
    address = (extracted.get("State of Loss Location") or "").upper()
    loss_desc = (extracted.get("Loss Description") or "").lower()

    scored = []

    for adj in adjusters:
        score = 0
        reasons = []

        matched_region = next(
            (r for r in adj["regions"] if r in address),
            None
        )

        if matched_region:
            score += 40
            reasons.append(f"Region match: {matched_region}")

            # --- Claim type match ---
        matched_claim_type = next(
            (ct for ct in adj["claim_types"] if ct.lower() in claim_type),
            None
        )

        if matched_claim_type:
            score += 30
            reasons.append(f"Claim type expertise: {matched_claim_type}")

        complex_reasons = []

        if "tree" in loss_desc:
            complex_reasons.append("tree damage")

        if "structure" in loss_desc:
            complex_reasons.append("structure damage")

        if complex_reasons and adj["experience_years"] >= 10:
            score += 10
            reasons.append(
                f"Complex loss experience ({', '.join(complex_reasons)}, "
                f"{adj['experience_years']} yrs exp)"
            )
        # --- Experience heuristic ---
            score += min(adj["experience_years"], 20)
            # reasons.append("Experience weighting", adj["experience_years"])

        scored.append({
            "adjuster": adj,
            "score": score,
            "reasons": reasons
        })

    ranked = sorted(scored, key=lambda x: x["score"], reverse=True)

    recommendation = ranked[0] if ranked else None
    return {
        **state,
        "adjuster_evaluation": ranked,
        "recommended_adjuster": {
            "id": recommendation["adjuster"]["id"],
            "name": recommendation["adjuster"]["name"],
            "score": recommendation["score"],
            "reasons": recommendation["reasons"],
            "recommended_at": datetime.utcnow().isoformat()
        } if recommendation else None
    }