# FitFindr

FitFindr is a small tool-using AI agent that helps a user find a secondhand clothing item, style it with their wardrobe, and generate a short shareable fit-card caption.

A complete interaction looks like this:

1. Search the mock listings dataset for a matching item.
2. Select the top result and store it in session state.
3. Suggest an outfit using the selected item and the user's wardrobe.
4. Create a short social caption from the selected item and outfit suggestion.

If the search step fails, the agent stops early and tells the user what to try differently instead of calling later tools with missing data.

---

## Setup

```bash
python -m venv .venv
source .venv/bin/activate          # Mac/Linux
# .venv\Scripts\activate          # Windows Command Prompt
pip install -r requirements.txt
```

Create a `.env` file in the project root:

```bash
GROQ_API_KEY=your_key_here
```

The app still has rule-based fallbacks if the API key is missing, which makes local testing easier. For the full LLM experience, add your Groq key.

---

## Run the app

```bash
python app.py
```

Open the URL shown in the terminal. Gradio usually starts at `http://localhost:7860`, but use the exact URL printed by your terminal.

---

## Run tests

```bash
pytest tests/
```

The tests cover the happy path and the required failure modes:

- Search returns results.
- Search returns an empty list without crashing.
- Price filtering works.
- Size filtering works.
- Outfit suggestions work with an example wardrobe.
- Outfit suggestions work with an empty wardrobe.
- Fit cards return text.
- Fit cards handle empty outfit input.
- The agent stops early when search returns no results.

---

## Project structure

```text
fitfindr_complete/
├── app.py
├── agent.py
├── tools.py
├── planning.md
├── README.md
├── requirements.txt
├── data/
│   ├── listings.json
│   └── wardrobe_schema.json
├── utils/
│   ├── __init__.py
│   └── data_loader.py
└── tests/
    ├── test_agent.py
    └── test_tools.py
```

---

## Tool inventory

### 1. `search_listings(description, size, max_price) -> list[dict]`

**Purpose:** Searches the mock secondhand listings dataset for items matching the user's query.

**Inputs:**

- `description` (`str`): The item keywords, such as `"vintage graphic tee"`.
- `size` (`str | None`): Optional size filter. Blank or `None` means no size filter.
- `max_price` (`float | None`): Optional maximum price filter.

**Output:**

Returns a list of listing dictionaries sorted by relevance. Each listing includes:

- `id`
- `title`
- `description`
- `category`
- `style_tags`
- `size`
- `condition`
- `price`
- `colors`
- `brand`
- `platform`

If nothing matches, it returns `[]`.

**Failure handling:**

If no results match, this tool returns an empty list. The agent then stops early and displays a helpful message instead of calling the other tools.

---

### 2. `suggest_outfit(new_item, wardrobe) -> str`

**Purpose:** Suggests 1–2 complete outfits using the selected listing and the user's wardrobe.

**Inputs:**

- `new_item` (`dict`): The selected listing from `search_listings`.
- `wardrobe` (`dict`): A dictionary with an `"items"` key containing wardrobe items.

**Output:**

Returns a non-empty outfit suggestion string. If the wardrobe has items, the suggestion names specific wardrobe pieces. If the wardrobe is empty, it gives general styling advice.

**Failure handling:**

If the wardrobe is empty, the tool still returns general styling advice. If the Groq call fails or the API key is missing, it returns a rule-based fallback suggestion.

---

### 3. `create_fit_card(outfit, new_item) -> str`

**Purpose:** Creates a short, shareable outfit caption from the selected item and outfit suggestion.

**Inputs:**

- `outfit` (`str`): The outfit suggestion from `suggest_outfit`.
- `new_item` (`dict`): The selected listing from `search_listings`.

**Output:**

Returns a 2–4 sentence caption that mentions the item, price, platform, and outfit vibe in a casual way.

**Failure handling:**

If the outfit input is empty, the tool returns a clear error string. If the Groq call fails, it returns a rule-based fallback caption.

---

## Planning loop

The planning loop is implemented in `run_agent()` inside `agent.py`.

The agent does not call all tools unconditionally. It branches based on what each tool returns:

1. Initialize a `session` dictionary.
2. Call `search_listings(description, size, max_price)`.
3. If the result list is empty:
   - Store a no-results message in `session["error"]`.
   - Return early.
   - Do not call `suggest_outfit` or `create_fit_card`.
4. If results exist:
   - Store all results in `session["results"]`.
   - Store the first result in `session["selected_item"]`.
5. Call `suggest_outfit(session["selected_item"], session["wardrobe"])`.
6. If the outfit string is empty:
   - Store an error in `session["error"]`.
   - Return early.
7. If the outfit string is valid:
   - Store it in `session["outfit_suggestion"]`.
8. Call `create_fit_card(session["outfit_suggestion"], session["selected_item"])`.
9. Store the caption in `session["fit_card"]`.
10. Return the completed session.

This satisfies the agent requirement because the next tool depends on the previous result.

---

## State management

State is stored in a Python dictionary named `session`.

The session stores:

- `description`
- `size`
- `max_price`
- `wardrobe`
- `results`
- `selected_item`
- `outfit_suggestion`
- `fit_card`
- `error`

The important state transfer is:

```text
search_listings returns results
        ↓
session["selected_item"] = results[0]
        ↓
suggest_outfit(selected_item, wardrobe) returns outfit text
        ↓
session["outfit_suggestion"] = outfit text
        ↓
create_fit_card(outfit_suggestion, selected_item) returns caption
        ↓
session["fit_card"] = caption
```

This means the selected item found by the search tool flows into the outfit tool and then into the fit-card tool without the user having to re-enter it.

---

## Error handling strategy

| Tool | Failure mode | Agent response |
|------|-------------|----------------|
| `search_listings` | No results match | The agent stores a helpful error message and returns early. It suggests broadening the search, removing the size filter, or increasing the max price. |
| `suggest_outfit` | Wardrobe is empty | The tool gives general styling advice using common clothing categories instead of named wardrobe pieces. |
| `suggest_outfit` | Groq/API fails | The tool returns a rule-based fallback outfit suggestion. |
| `create_fit_card` | Outfit input is empty | The tool returns a descriptive error string instead of raising an exception. |
| `create_fit_card` | Groq/API fails | The tool returns a rule-based fallback caption. |

Concrete failure example:

```bash
python -c "from agent import run_agent; print(run_agent('designer ballgown', size='XXS', max_price=5)['error'])"
```

Expected output:

```text
I couldn't find listings that matched that description, size, and budget. Try a broader search, removing the size filter, or increasing your max price.
```

---

## Complete demo script

### Happy path

Use this query:

```text
vintage graphic tee
```

Set max price to `30`. Leave size blank or use `M`.

Narration:

> First, the agent calls `search_listings` using the description, size, and max price. It stores the top result in `session["selected_item"]`. Then it passes that selected item and the wardrobe into `suggest_outfit`. Finally, it passes the outfit suggestion and selected item into `create_fit_card`.

Show the UI panels:

- Selected listing
- Outfit suggestion
- Fit card
- Session state/debug panel

### Failure path

Use this query:

```text
designer ballgown
```

Set size to `XXS` and max price to `5`.

Narration:

> Here, `search_listings` returns an empty list. The planning loop stores an error message and stops early, so the outfit and fit-card tools are not called with missing data.

---

## AI usage section

### AI usage instance 1: Tool implementation

I gave ChatGPT the Tool 1, Tool 2, and Tool 3 specs from `planning.md` and asked for implementations that matched the exact function signatures in `tools.py`. I specifically directed it to use `load_listings()` for search, Groq for LLM-based suggestions/captions, and fallback logic for missing API keys or empty inputs.

I revised the output by adding stronger error handling and rule-based fallbacks so the tools could still be tested without a live API key.

### AI usage instance 2: Planning loop and state

I gave ChatGPT the Planning Loop, State Management, Error Handling table, and Architecture diagram from `planning.md`. I asked it to implement a `run_agent()` function that stores state in a session dictionary and stops early when search returns no results.

I checked the output to make sure it did not call all three tools unconditionally. I also added a debug/session output panel in the Gradio app so state passing is visible during the demo.

---

## Spec reflection

One way the spec helped me was by forcing me to define exactly what each tool accepts and returns before coding. That made it easier to test the tools independently and wire them together through the agent loop.

One way implementation diverged from the original spec is that I added rule-based fallback outputs when the Groq API key is missing or an API call fails. The original plan focused mostly on using the LLM, but adding fallbacks made the project easier to test and more reliable during the demo.
