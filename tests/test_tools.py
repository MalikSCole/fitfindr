from tools import create_fit_card, search_listings, suggest_outfit
from utils.data_loader import get_empty_wardrobe, get_example_wardrobe


def test_search_returns_results():
    results = search_listings("vintage graphic tee", size=None, max_price=50)
    assert isinstance(results, list)
    assert len(results) > 0
    assert all(isinstance(item, dict) for item in results)


def test_search_empty_results():
    results = search_listings("designer ballgown", size="XXS", max_price=5)
    assert results == []


def test_search_price_filter():
    results = search_listings("jacket", size=None, max_price=40)
    assert len(results) > 0
    assert all(float(item["price"]) <= 40 for item in results)


def test_search_size_filter():
    results = search_listings("graphic tee", size="M", max_price=50)
    assert len(results) > 0
    assert all("m" in item["size"].lower() for item in results)


def test_suggest_outfit_with_example_wardrobe():
    item = search_listings("vintage graphic tee", size=None, max_price=50)[0]
    outfit = suggest_outfit(item, get_example_wardrobe())
    assert isinstance(outfit, str)
    assert len(outfit.strip()) > 0


def test_suggest_outfit_with_empty_wardrobe():
    item = search_listings("vintage graphic tee", size=None, max_price=50)[0]
    outfit = suggest_outfit(item, get_empty_wardrobe())
    assert isinstance(outfit, str)
    assert len(outfit.strip()) > 0


def test_create_fit_card_returns_text():
    item = search_listings("vintage graphic tee", size=None, max_price=50)[0]
    outfit = "Pair it with baggy jeans and chunky sneakers for a relaxed grunge look."
    caption = create_fit_card(outfit, item)
    assert isinstance(caption, str)
    assert len(caption.strip()) > 0


def test_create_fit_card_empty_outfit():
    item = search_listings("vintage graphic tee", size=None, max_price=50)[0]
    caption = create_fit_card("", item)
    assert isinstance(caption, str)
    assert "couldn't create" in caption.lower() or "missing" in caption.lower()
