from datetime import datetime
import json
import boto3

bedrock = boto3.client("bedrock-runtime", region_name="us-east-1", verify=False)


def score_adjusters_with_llm(adjusters: list, extracted_fields: dict) -> list:
    """Use LLM to score and rank adjusters based on claim context."""

    prompt = f"""
You are an insurance claims manager. Score each adjuster below (0-100) based on how well they match this claim.
Consider: geographic region, claim type expertise, loss complexity, and experience years.

Claim Details:
{json.dumps(extracted_fields, indent=2)}

Adjusters:
{json.dumps(adjusters, indent=2)}

Return ONLY a valid JSON array, one object per adjuster, in descending score order:
[
  {{
    "id": "<adjuster id>",
    "score": <0-100>,
    "reasons": ["<reason1>", "<reason2>"]
  }}
]
Return only the JSON array, nothing else.
"""

    response = bedrock.converse(
        modelId="openai.gpt-oss-120b-1:0",
        messages=[{"role": "user", "content": [{"text": prompt}]}],
        inferenceConfig={"maxTokens": 1000, "temperature": 0.3}
    )

    content_items = response["output"]["message"]["content"]
    raw = next(item["text"] for item in content_items if "text" in item)
    llm_scores = json.loads(raw)

    adj_map = {a["id"]: a for a in adjusters}
    return [
        {
            "adjuster": adj_map[item["id"]],
            "score": item["score"],
            "reasons": item["reasons"]
        }
        for item in llm_scores
        if item["id"] in adj_map
    ]


def adjuster_agent(state: dict) -> dict:
    """LLM-powered adjuster assignment based on claim context."""

    with open("config/adjusters.json") as f:
        adjusters = json.load(f)

    extracted = state.get("extracted_fields", {})
    ranked = score_adjusters_with_llm(adjusters, extracted)
    recommendation = ranked[0] if ranked else None

    print(f"✅ Adjuster Agent: LLM ranked {len(ranked)} adjusters")

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