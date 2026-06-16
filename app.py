"""
app.py

Gradio UI for FitFindr.
"""

from __future__ import annotations

import gradio as gr

from agent import format_selected_item, run_agent
from utils.data_loader import get_empty_wardrobe, get_example_wardrobe


def handle_query(description: str, size: str, max_price: float | None, wardrobe_mode: str):
    """
    Run FitFindr and map the session dictionary to Gradio output panels.
    """
    wardrobe = get_empty_wardrobe() if wardrobe_mode == "Empty wardrobe" else get_example_wardrobe()
    session = run_agent(description=description, size=size, max_price=max_price, wardrobe=wardrobe)

    if session.get("error"):
        return session["error"], "", "", repr(session)

    item_display = format_selected_item(session.get("selected_item"))
    outfit_display = session.get("outfit_suggestion") or ""
    fit_card_display = session.get("fit_card") or ""
    return item_display, outfit_display, fit_card_display, repr(session)


with gr.Blocks(title="FitFindr") as demo:
    gr.Markdown("# FitFindr\nFind a secondhand item, style it with a wardrobe, and create a shareable fit card.")

    with gr.Row():
        description = gr.Textbox(
            label="What are you looking for?",
            value="vintage graphic tee",
            placeholder="ex: vintage graphic tee, black cargo pants, chunky sneakers",
        )
        size = gr.Textbox(label="Size optional", value="", placeholder="ex: M, S, 8, One Size")
        max_price = gr.Number(label="Max price optional", value=30)

    wardrobe_mode = gr.Radio(
        choices=["Example wardrobe", "Empty wardrobe"],
        value="Example wardrobe",
        label="Wardrobe mode",
    )

    button = gr.Button("Find and style it")

    with gr.Row():
        selected_item = gr.Textbox(label="Selected listing", lines=7)
        outfit = gr.Textbox(label="Outfit suggestion", lines=7)
        fit_card = gr.Textbox(label="Fit card", lines=7)

    debug_state = gr.Textbox(label="Session state for demo/debugging", lines=10)

    button.click(
        fn=handle_query,
        inputs=[description, size, max_price, wardrobe_mode],
        outputs=[selected_item, outfit, fit_card, debug_state],
    )


if __name__ == "__main__":
    demo.launch()
