"""
tools.py

The three required FitFindr tools. Each tool is a standalone function that can
be called and tested independently before being wired into the agent loop.

Tools:
    search_listings(description, size, max_price)  -> list[dict]
    suggest_outfit(new_item, wardrobe)             -> str
    create_fit_card(outfit, new_item)              -> str
"""

from __future__ import annotations

import os
import re
from typing import Any

try:
    from dotenv import load_dotenv
except ModuleNotFoundError:  # lets tests run before dependencies are installed
    def load_dotenv(*args, **kwargs):
        return False

try:
    from groq import Groq
except ModuleNotFoundError:  # lets fallback mode work before dependencies are installed
    Groq = None

from utils.data_loader import load_listings

load_dotenv()


# ── Groq client ───────────────────────────────────────────────────────────────

def _get_groq_client():
    """Initialize and return a Groq client using GROQ_API_KEY from .env."""
    if Groq is None:
        raise ValueError("Groq package is not installed. Run pip install -r requirements.txt.")
    api_key = os.environ.get("GROQ_API_KEY")
    if not api_key:
        raise ValueError("GROQ_API_KEY not set. Add it to a .env file in the project root.")
    return Groq(api_key=api_key)


def _call_groq(prompt: str, system_message: str, temperature: float = 0.7) -> str:
    """Small wrapper around Groq chat completions."""
    client = _get_groq_client()
    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[
            {"role": "system", "content": system_message},
            {"role": "user", "content": prompt},
        ],
        temperature=temperature,
    )
    content = response.choices[0].message.content
    return content.strip() if content else ""


# ── Shared helpers ────────────────────────────────────────────────────────────

STOPWORDS = {
    "a", "an", "and", "are", "for", "i", "im", "i'm", "in", "is", "it", "of",
    "on", "or", "the", "to", "under", "with", "looking", "find", "want", "would",
    "like", "what", "whats", "there", "how", "style", "mostly", "wear",
}

SYNONYMS = {
    "tee": {"tshirt", "shirt", "top"},
    "tshirt": {"tee", "shirt", "top"},
    "jacket": {"outerwear", "coat", "blazer"},
    "pants": {"bottoms", "jeans", "trousers"},
    "jeans": {"denim", "pants", "bottoms"},
    "sneakers": {"shoes", "kicks"},
    "boots": {"shoes"},
    "bag": {"purse", "accessories", "shoulder"},
    "graphic": {"print", "band"},
}


def _tokens(text: str) -> list[str]:
    """Normalize text into useful search tokens."""
    raw_tokens = re.findall(r"[a-z0-9]+", (text or "").lower())
    useful = [tok for tok in raw_tokens if tok not in STOPWORDS and len(tok) > 1]
    expanded: list[str] = []
    for tok in useful:
        expanded.append(tok)
        expanded.extend(SYNONYMS.get(tok, set()))
    return expanded


def _listing_text(item: dict[str, Any]) -> str:
    """Combine searchable listing fields into one string."""
    fields = [
        item.get("title", ""),
        item.get("description", ""),
        item.get("category", ""),
        " ".join(item.get("style_tags", []) or []),
        " ".join(item.get("colors", []) or []),
        str(item.get("brand") or ""),
        item.get("platform", ""),
    ]
    return " ".join(fields).lower()


def _size_matches(item_size: str, requested_size: str) -> bool:
    """Case-insensitive size matching that handles combined sizes like S/M."""
    if not requested_size or not str(requested_size).strip():
        return True
    item = str(item_size or "").lower().replace(" ", "")
    requested = str(requested_size).lower().replace(" ", "")
    return requested in item or item in requested


def _format_item_name(item: dict[str, Any]) -> str:
    title = item.get("title", "this item")
    price = item.get("price")
    platform = item.get("platform", "a secondhand platform")
    if price is None or price == "":
        return f"{title} from {platform}"
    return f"{title} for ${float(price):.0f} on {platform}"


def _fallback_outfit(new_item: dict[str, Any], wardrobe: dict[str, Any] | None = None) -> str:
    """Rule-based styling fallback used when Groq is unavailable or fails."""
    title = new_item.get("title", "this item")
    category = new_item.get("category", "piece")
    colors = ", ".join(new_item.get("colors", []) or ["neutral"])
    tags = new_item.get("style_tags", []) or []
    vibe = tags[0] if tags else "casual"

    wardrobe_items = []
    if isinstance(wardrobe, dict):
        wardrobe_items = wardrobe.get("items", []) or []

    if wardrobe_items:
        bottoms = [i for i in wardrobe_items if i.get("category") == "bottoms"]
        shoes = [i for i in wardrobe_items if i.get("category") == "shoes"]
        layers = [i for i in wardrobe_items if i.get("category") in {"outerwear", "tops"}]
        accessories = [i for i in wardrobe_items if i.get("category") == "accessories"]

        parts = []
        if bottoms:
            parts.append(bottoms[0].get("name", "your favorite bottoms"))
        if shoes:
            parts.append(shoes[0].get("name", "simple sneakers"))
        if accessories:
            parts.append(accessories[0].get("name", "a simple accessory"))
        if layers and category != "outerwear":
            parts.append(layers[0].get("name", "a light layer"))

        if parts:
            return (
                f"Build the outfit around the {title}. Pair it with {', '.join(parts)} "
                f"for a {vibe} look that keeps the {colors} color palette intentional. "
                f"Keep the rest of the fit relaxed so the new {category} still feels like the main piece."
            )

    return (
        f"Build the outfit around the {title}. Since the wardrobe is empty, try pairing it with "
        f"relaxed denim or neutral bottoms, clean sneakers or boots, and one accessory that picks up the "
        f"{colors} tones. That keeps the look easy but still gives it a clear {vibe} vibe."
    )


def _fallback_caption(outfit: str, new_item: dict[str, Any]) -> str:
    title = new_item.get("title", "this thrifted find")
    price = new_item.get("price", "")
    platform = new_item.get("platform", "a secondhand platform")
    tags = new_item.get("style_tags", []) or ["secondhand"]
    vibe = tags[0]
    price_text = f" for ${float(price):.0f}" if isinstance(price, (int, float)) else ""
    return (
        f"Found this {title}{price_text} on {platform} and built the whole fit around it. "
        f"The outfit leans {vibe} without feeling too forced, just an easy thrifted piece with pieces that already work."
    )


# ── Tool 1: search_listings ───────────────────────────────────────────────────

def search_listings(
    description: str,
    size: str | None = None,
    max_price: float | None = None,
) -> list[dict]:
    """
    Search the mock listings dataset for items matching the description,
    optional size, and optional price ceiling.
    """
    try:
        listings = load_listings()
    except Exception:
        # Tool failure should not crash the agent.
        return []

    query_tokens = _tokens(description)
    if not query_tokens:
        return []

    scored: list[tuple[int, float, dict]] = []

    for item in listings:
        try:
            price = float(item.get("price", 0))
        except (TypeError, ValueError):
            continue

        if max_price is not None and price > float(max_price):
            continue

        if size and not _size_matches(str(item.get("size", "")), size):
            continue

        haystack = _listing_text(item)
        score = 0
        for token in query_tokens:
            if token in haystack:
                score += 1
                # Title/category matches should count a little more.
                if token in str(item.get("title", "")).lower():
                    score += 2
                if token == str(item.get("category", "")).lower():
                    score += 1
                if token in [tag.lower() for tag in item.get("style_tags", [])]:
                    score += 1

        if score > 0:
            scored.append((score, -price, item.copy()))

    scored.sort(key=lambda row: (row[0], row[1]), reverse=True)
    return [item for _, _, item in scored]


# ── Tool 2: suggest_outfit ────────────────────────────────────────────────────

def suggest_outfit(new_item: dict, wardrobe: dict) -> str:
    """
    Given a thrifted item and the user's wardrobe, suggest 1–2 complete outfits.
    """
    if not isinstance(new_item, dict) or not new_item:
        return "I couldn't suggest an outfit because the selected item was missing."

    wardrobe_items = []
    if isinstance(wardrobe, dict):
        wardrobe_items = wardrobe.get("items", []) or []

    item_summary = (
        f"Title: {new_item.get('title', 'Unknown item')}\n"
        f"Description: {new_item.get('description', '')}\n"
        f"Category: {new_item.get('category', '')}\n"
        f"Style tags: {new_item.get('style_tags', [])}\n"
        f"Colors: {new_item.get('colors', [])}\n"
        f"Price/platform: {_format_item_name(new_item)}"
    )

    try:
        if wardrobe_items:
            wardrobe_lines = []
            for item in wardrobe_items:
                wardrobe_lines.append(
                    f"- {item.get('name', 'Unnamed item')} | category: {item.get('category', 'unknown')} | "
                    f"colors: {item.get('colors', [])} | style tags: {item.get('style_tags', [])}"
                )
            prompt = f"""
The user is considering this secondhand item:
{item_summary}

The user owns these wardrobe pieces:
{chr(10).join(wardrobe_lines)}

Suggest 1-2 complete outfits using the new item and specific named wardrobe pieces when possible.
Keep it practical, casual, and specific. Mention the overall vibe of each outfit.
"""
        else:
            prompt = f"""
The user is considering this secondhand item:
{item_summary}

The user's wardrobe is empty or unavailable. Suggest 1-2 complete outfit ideas using general clothing categories instead of named owned pieces.
Keep it practical, casual, and specific. Do not say you cannot help because the wardrobe is empty.
"""

        result = _call_groq(
            prompt=prompt,
            system_message="You are FitFindr, a casual fashion styling assistant.",
            temperature=0.7,
        )
        return result if result else _fallback_outfit(new_item, wardrobe)
    except Exception:
        return _fallback_outfit(new_item, wardrobe)


# ── Tool 3: create_fit_card ───────────────────────────────────────────────────

def create_fit_card(outfit: str, new_item: dict) -> str:
    """
    Generate a short, shareable outfit caption for the thrifted find.
    """
    if not outfit or not str(outfit).strip():
        return "I couldn't create a fit card because the outfit suggestion was missing or incomplete."

    if not isinstance(new_item, dict) or not new_item:
        return "I couldn't create a fit card because the selected item was missing."

    prompt = f"""
Create a short social media fit-card caption based on this thrifted item and outfit idea.

Item: {_format_item_name(new_item)}
Colors: {new_item.get('colors', [])}
Style tags: {new_item.get('style_tags', [])}
Outfit idea: {outfit}

Requirements:
- 2-4 sentences.
- Casual and authentic, like an OOTD caption.
- Mention the item name, price, and platform naturally once.
- Capture the outfit vibe.
- Do not sound like a product listing.
"""
    try:
        result = _call_groq(
            prompt=prompt,
            system_message="You write casual, specific, social media outfit captions.",
            temperature=0.95,
        )
        return result if result else _fallback_caption(outfit, new_item)
    except Exception:
        return _fallback_caption(outfit, new_item)


if __name__ == "__main__":
    from utils.data_loader import get_example_wardrobe

    results = search_listings("vintage graphic tee", size=None, max_price=30)
    print(f"Found {len(results)} result(s).")
    if results:
        print(results[0])
        outfit_text = suggest_outfit(results[0], get_example_wardrobe())
        print("\nOUTFIT:\n", outfit_text)
        print("\nFIT CARD:\n", create_fit_card(outfit_text, results[0]))
 