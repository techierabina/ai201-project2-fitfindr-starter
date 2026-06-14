"""
tools.py
The three required FitFindr tools.
"""

import os
from dotenv import load_dotenv
from groq import Groq
from utils.data_loader import load_listings

load_dotenv()


def _get_groq_client():
    api_key = os.environ.get("GROQ_API_KEY")
    if not api_key:
        raise ValueError("GROQ_API_KEY not set.")
    return Groq(api_key=api_key)


def search_listings(
    description: str,
    size: str | None = None,
    max_price: float | None = None,
) -> list[dict]:
    listings = load_listings()
    filtered = []
    for item in listings:
        if max_price is not None and item["price"] > max_price:
            continue
        if size is not None:
            if size.lower() not in item["size"].lower():
                continue
        filtered.append(item)

    keywords = description.lower().split()

    def score(item):
        searchable = " ".join([
            item["title"],
            item["description"],
            item["category"],
            " ".join(item["style_tags"]),
            " ".join(item["colors"]),
        ]).lower()
        return sum(1 for kw in keywords if kw in searchable)

    scored = [(item, score(item)) for item in filtered]
    scored = [(item, s) for item, s in scored if s > 0]
    scored.sort(key=lambda x: x[1], reverse=True)
    return [item for item, _ in scored]


def suggest_outfit(new_item: dict, wardrobe: dict) -> str:
    client = _get_groq_client()

    item_description = f"""
    Item: {new_item['title']}
    Category: {new_item['category']}
    Colors: {', '.join(new_item['colors'])}
    Style: {', '.join(new_item['style_tags'])}
    Description: {new_item['description']}
    """

    if not wardrobe.get("items"):
        prompt = f"""You are a thrift fashion stylist. A user is considering buying this secondhand item:
{item_description}
They haven't told you what's in their wardrobe yet. Give them 1-2 suggestions for what kinds of pieces pair well with this item — what bottoms, shoes, or layers would work, and what overall vibe it suits. Keep it casual and specific."""
    else:
        wardrobe_text = "\n".join([
            f"- {item['name']} ({item['category']}, colors: {', '.join(item['colors'])})"
            for item in wardrobe["items"]
        ])
        prompt = f"""You are a thrift fashion stylist. A user is considering buying this secondhand item:
{item_description}
Here is their current wardrobe:
{wardrobe_text}
Suggest 1-2 complete outfit combinations using the new item and specific pieces from their wardrobe. Name the exact wardrobe pieces. Keep it casual, specific, and fun."""

    try:
        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=300,
        )
        return response.choices[0].message.content
    except Exception:
        return "Couldn't generate outfit suggestions right now — try pairing this with basics in a similar color palette."


def create_fit_card(outfit: str, new_item: dict) -> str:
    if not outfit or not outfit.strip():
        return "Can't generate a fit card without an outfit suggestion — make sure suggest_outfit ran successfully first."

    client = _get_groq_client()

    prompt = f"""You are writing an Instagram caption for a thrift outfit post. 

New thrifted item: {new_item['title']} — ${new_item['price']} from {new_item['platform']}
Outfit: {outfit}

Write a 2-4 sentence caption that sounds like a real OOTD post — casual, authentic, specific. Mention the item name, price, and platform naturally once each. Capture the vibe."""

    try:
        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=150,
            temperature=1.2,
        )
        return response.choices[0].message.content
    except Exception:
        return "Couldn't generate a fit card right now."