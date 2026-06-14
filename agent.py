"""
agent.py

The FitFindr planning loop. Orchestrates the three tools in response to a
natural language user query, passing state between them via a session dict.
"""

import json
import os

from dotenv import load_dotenv
from groq import Groq

from tools import search_listings, suggest_outfit, create_fit_card

load_dotenv()


# ── session state ─────────────────────────────────────────────────────────────

def _new_session(query: str, wardrobe: dict) -> dict:
    return {
        "query": query,
        "parsed": {},
        "search_results": [],
        "selected_item": None,
        "wardrobe": wardrobe,
        "outfit_suggestion": None,
        "fit_card": None,
        "error": None,
    }


# ── planning loop ─────────────────────────────────────────────────────────────

def run_agent(query: str, wardrobe: dict) -> dict:
    # Step 1: Initialize session
    session = _new_session(query, wardrobe)

    # Step 2: Parse query with LLM
    client = Groq(api_key=os.environ.get("GROQ_API_KEY"))

    parse_prompt = f"""Extract search parameters from this thrift shopping query.
Query: "{query}"

Reply with ONLY a JSON object with these fields:
- description (str): keywords describing the item
- size (str or null): size if mentioned, otherwise null
- max_price (float or null): maximum price if mentioned, otherwise null

Example: {{"description": "vintage graphic tee", "size": "M", "max_price": 30.0}}"""

    parse_response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[{"role": "user", "content": parse_prompt}],
        max_tokens=100,
    )

    raw = parse_response.choices[0].message.content.strip()
    raw = raw.replace("```json", "").replace("```", "").strip()

    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError:
        parsed = {"description": query, "size": None, "max_price": None}

    session["parsed"] = parsed
    description = parsed.get("description", query)
    size = parsed.get("size")
    max_price = parsed.get("max_price")

    # Step 3: Search listings
    results = search_listings(description, size, max_price)
    session["search_results"] = results

    if not results:
        size_str = f" in size {size}" if size else ""
        price_str = f" under ${max_price}" if max_price else ""
        session["error"] = (
            f"No listings found for '{description}'{size_str}{price_str}. "
            f"Try broadening your search — remove the size filter or raise your budget."
        )
        return session

    # Step 4: Select top result
    session["selected_item"] = results[0]

    # Step 5: Suggest outfit
    session["outfit_suggestion"] = suggest_outfit(results[0], wardrobe)

    # Step 6: Create fit card
    session["fit_card"] = create_fit_card(session["outfit_suggestion"], results[0])

    # Step 7: Return session
    return session


# ── CLI test ──────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    from utils.data_loader import get_example_wardrobe, get_empty_wardrobe

    print("=== Happy path: graphic tee ===\n")
    session = run_agent(
        query="looking for a vintage graphic tee under $30",
        wardrobe=get_example_wardrobe(),
    )
    if session["error"]:
        print(f"Error: {session['error']}")
    else:
        print(f"Found: {session['selected_item']['title']}")
        print(f"\nOutfit: {session['outfit_suggestion']}")
        print(f"\nFit card: {session['fit_card']}")

    print("\n\n=== No-results path ===\n")
    session2 = run_agent(
        query="designer ballgown size XXS under $5",
        wardrobe=get_example_wardrobe(),
    )
    print(f"Error message: {session2['error']}")