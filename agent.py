"""
agent.py

Planning loop and state management for FitFindr.
"""

from __future__ import annotations

from typing import Any

from tools import create_fit_card, search_listings, suggest_outfit
from utils.data_loader import get_example_wardrobe


def run_agent(
    description: str,
    size: str | None = None,
    max_price: float | None = None,
    wardrobe: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """
    Run one FitFindr interaction.

    The planning loop branches based on tool output:
    - If search finds no listings, stop early.
    - If search succeeds, store selected_item and continue.
    - If outfit suggestion is empty, stop early.
    - If fit card succeeds, return the completed session.
    """
    if wardrobe is None:
        wardrobe = get_example_wardrobe()

    clean_description = (description or "").strip()
    clean_size = size.strip() if isinstance(size, str) and size.strip() else None

    parsed_price: float | None = None
    if max_price not in (None, ""):
        try:
            parsed_price = float(max_price)
        except (TypeError, ValueError):
            parsed_price = None

    session: dict[str, Any] = {
        "description": clean_description,
        "size": clean_size,
        "max_price": parsed_price,
        "wardrobe": wardrobe,
        "results": [],
        "selected_item": None,
        "outfit_suggestion": None,
        "fit_card": None,
        "error": None,
    }

    if not clean_description:
        session["error"] = "Tell me what kind of item you want to search for first."
        return session

    # Step 1: Search listings.
    results = search_listings(clean_description, clean_size, parsed_price)
    session["results"] = results

    if not results:
        session["error"] = (
            "I couldn't find listings that matched that description, size, and budget. "
            "Try a broader search, removing the size filter, or increasing your max price."
        )
        return session

    # Step 2: Store selected item and suggest outfit.
    selected_item = results[0]
    session["selected_item"] = selected_item

    outfit = suggest_outfit(selected_item, wardrobe)
    session["outfit_suggestion"] = outfit

    if not outfit or not str(outfit).strip():
        session["error"] = "I found an item, but I couldn't generate an outfit suggestion for it."
        return session

    # Step 3: Create fit card.
    fit_card = create_fit_card(outfit, selected_item)
    session["fit_card"] = fit_card

    if not fit_card or not str(fit_card).strip():
        session["error"] = "I found an item and outfit, but I couldn't create the final fit card."
        return session

    return session


def format_selected_item(item: dict[str, Any] | None) -> str:
    """Format a listing for display in the UI or terminal."""
    if not item:
        return "No item selected."

    brand = item.get("brand") or "Unbranded"
    tags = ", ".join(item.get("style_tags", []) or [])
    colors = ", ".join(item.get("colors", []) or [])
    return (
        f"{item.get('title', 'Untitled')} — ${float(item.get('price', 0)):.0f} on {item.get('platform', 'unknown')}\n"
        f"Size: {item.get('size', 'unknown')} | Condition: {item.get('condition', 'unknown')} | Brand: {brand}\n"
        f"Category: {item.get('category', 'unknown')} | Colors: {colors}\n"
        f"Style tags: {tags}\n"
        f"Description: {item.get('description', '')}"
    )


if __name__ == "__main__":
    print("Happy path test")
    happy = run_agent("vintage graphic tee", size=None, max_price=30)
    print("Error:", happy["error"])
    print("Selected item:", format_selected_item(happy["selected_item"]))
    print("Outfit:", happy["outfit_suggestion"])
    print("Fit card:", happy["fit_card"])

    print("\nNo-results path test")
    miss = run_agent("designer ballgown", size="XXS", max_price=5)
    print("Error:", miss["error"])
    print("Fit card should be None:", miss["fit_card"])
