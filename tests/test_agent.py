from agent import run_agent
from utils.data_loader import get_example_wardrobe


def test_agent_happy_path_uses_all_steps():
    session = run_agent("vintage graphic tee", size=None, max_price=30, wardrobe=get_example_wardrobe())
    assert session["error"] is None
    assert session["results"]
    assert session["selected_item"] is not None
    assert session["outfit_suggestion"]
    assert session["fit_card"]


def test_agent_stops_on_no_results():
    session = run_agent("designer ballgown", size="XXS", max_price=5, wardrobe=get_example_wardrobe())
    assert session["error"] is not None
    assert session["results"] == []
    assert session["selected_item"] is None
    assert session["outfit_suggestion"] is None
    assert session["fit_card"] is None
