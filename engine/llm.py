
import os
from typing import List
import openai

# Guardrail: DO NOT add facts. Only rephrase provided bullets.
SYSTEM_PROMPT = (
    "You are a rewriter. Do not add or infer new facts or numbers. "
    "Rephrase each bullet clearly for a 12-year-old audience. "
    "If an item is based on last season, keep '(based on last season)' text."
)

def rewrite(bullets: List[str]) -> List[str]:
    """Rewrite bullets using OpenAI if available, otherwise return unchanged"""
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key or not bullets:
        return bullets
    
    try:
        client = openai.OpenAI(api_key=api_key)
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": "\n".join(bullets)}
            ],
            max_tokens=500,
            temperature=0.3
        )
        return response.choices[0].message.content.strip().split('\n')
    except Exception:
        # If OpenAI fails, return original bullets
        return bullets
