# FitFindr — planning.md

> Complete this document before writing any implementation code.
> Your spec and agent diagram are what you'll use to direct AI tools (Claude, Copilot, etc.) to generate your implementation — the more specific they are, the more useful the generated code will be.
> Your planning.md will be reviewed as part of your submission.
> Update it before starting any stretch features.

---

## Tools

### Tool 1: search_listings

**What it does:**
`search_listings` searches the mock secondhand clothing listings dataset for items that match the user's description, optional size, and optional maximum price. It filters the dataset first, scores the remaining listings by relevance, and returns the strongest matches first.

**Input parameters:**
- `description` (str): Keywords describing what the user is looking for, such as `"vintage graphic tee"`, `"black denim jacket"`, or `"chunky sneakers"`.
- `size` (str | None): Optional size filter, such as `"S"`, `"M"`, `"L"`, `"8"`, or `"One Size"`. If `None` or blank, the search does not filter by size.
- `max_price` (float | None): Optional maximum price. If provided, only listings with `price <= max_price` are returned. If `None`, the search does not filter by price.

**What it returns:**
A list of listing dictionaries sorted by relevance. Each result contains these fields: `id`, `title`, `description`, `category`, `style_tags`, `size`, `condition`, `price`, `colors`, `brand`, and `platform`. The function returns an empty list `[]` when no listing matches.

**What happens if it fails or returns nothing:**
If the search returns no results, the agent stores a helpful message in `session["error"]`, stops the workflow, and does not call `suggest_outfit` or `create_fit_card`. The user is told to try a broader description, remove the size filter, or increase the max price.

---

### Tool 2: suggest_outfit

**What it does:**
`suggest_outfit` takes the selected listing from `search_listings` and the user's current wardrobe, then suggests 1–2 complete outfit combinations. If the wardrobe has items, it uses specific pieces from the wardrobe. If the wardrobe is empty, it gives general styling advice instead of crashing.

**Input parameters:**
- `new_item` (dict): The listing dictionary selected from `search_listings`. It includes fields like `title`, `description`, `category`, `style_tags`, `size`, `condition`, `price`, `colors`, `brand`, and `platform`.
- `wardrobe` (dict): A wardrobe dictionary with an `"items"` key containing a list of wardrobe item dictionaries. It may contain example wardrobe items or be empty.

**What it returns:**
A non-empty string with 1–2 outfit ideas. The string should explain what to pair with the selected item, mention specific wardrobe pieces when available, and describe the overall outfit vibe.

**What happens if it fails or returns nothing:**
If the wardrobe is empty, the tool returns general styling advice using common clothing categories instead of named wardrobe pieces. If the LLM call fails or the API key is missing, the tool returns a rule-based fallback suggestion using the selected item's category, colors, and style tags.

---

### Tool 3: create_fit_card

**What it does:**
`create_fit_card` turns the selected item and outfit suggestion into a short, shareable outfit caption. It should sound like a real social media caption, not a product description.

**Input parameters:**
- `outfit` (str): The outfit suggestion returned by `suggest_outfit`.
- `new_item` (dict): The selected listing dictionary from `search_listings`, including title, price, platform, colors, and style tags.

**What it returns:**
A 2–4 sentence caption that naturally mentions the item name, price, platform, and outfit vibe. The caption should be casual and specific enough to use as an Instagram/TikTok-style fit card.

**What happens if it fails or returns nothing:**
If `outfit` is empty, missing, or whitespace-only, the tool returns a descriptive error string instead of raising an exception. If the LLM call fails or the API key is missing, the tool returns a rule-based fallback caption.

---

### Additional Tools (if any)

No additional tools are planned for the base version. I am focusing on fully implementing and testing the three required tools before attempting stretch features.

---

## Planning Loop

**How does your agent decide which tool to call next?**

The agent uses conditional logic instead of calling every tool no matter what. The next tool call depends on what the previous tool returned.

1. The user enters an item description, optional size, optional maximum price, and wardrobe context.
2. The agent creates a `session` dictionary with keys for the query, filters, results, selected item, wardrobe, outfit suggestion, fit card, and error.
3. The agent calls `search_listings(description, size, max_price)`.
4. The agent checks the search results.
   - If `results == []`, the agent stores a no-results error message in `session["error"]` and returns early.
   - If results exist, the agent stores all results in `session["results"]`, selects `results[0]`, and stores it in `session["selected_item"]`.
5. The agent calls `suggest_outfit(session["selected_item"], session["wardrobe"])`.
6. The agent checks the outfit suggestion.
   - If the suggestion is empty, it stores an outfit error message in `session["error"]` and returns early.
   - If the suggestion is non-empty, it stores the string in `session["outfit_suggestion"]`.
7. The agent calls `create_fit_card(session["outfit_suggestion"], session["selected_item"])`.
8. The agent stores the returned caption in `session["fit_card"]`.
9. The agent returns the session to the UI.

The loop ends when either an error branch returns early or all three required tools have completed.

---

## State Management

**How does information from one tool get passed to the next?**

The agent stores all interaction data in one `session` dictionary. This lets later tools use information returned by earlier tools without asking the user to re-enter anything.

The session tracks:
- `description`: Original item description.
- `size`: Optional size filter.
- `max_price`: Optional price filter.
- `wardrobe`: Wardrobe dictionary used for styling.
- `results`: Full list returned by `search_listings`.
- `selected_item`: The top listing selected from `results`.
- `outfit_suggestion`: The string returned by `suggest_outfit`.
- `fit_card`: The caption returned by `create_fit_card`.
- `error`: A user-facing error message when a step fails.

State flow:
1. `search_listings` returns matching listing dictionaries.
2. The agent stores the full list in `session["results"]`.
3. The agent stores the first listing in `session["selected_item"]`.
4. `session["selected_item"]` is passed into `suggest_outfit`.
5. The outfit suggestion is stored in `session["outfit_suggestion"]`.
6. `session["outfit_suggestion"]` and `session["selected_item"]` are passed into `create_fit_card`.
7. The final caption is stored in `session["fit_card"]`.

---

## Error Handling

| Tool | Failure mode | Agent response |
|------|-------------|----------------|
| search_listings | No results match the query | Store a message in `session["error"]`: `"I couldn't find listings that matched that description, size, and budget. Try a broader search, removing the size filter, or increasing your max price."` Stop early and do not call the other tools. |
| suggest_outfit | Wardrobe is empty | Return general styling advice for the selected item using common clothing categories. Continue the workflow if the returned string is non-empty. |
| suggest_outfit | LLM/API call fails | Return a fallback rule-based outfit suggestion using the selected item's title, category, colors, and style tags. |
| create_fit_card | Outfit input is missing or incomplete | Return a clear error string explaining that the fit card could not be created because the outfit suggestion was missing. |
| create_fit_card | LLM/API call fails | Return a fallback caption using the selected item's title, price, platform, and style vibe. |

---

## Architecture

```mermaid
flowchart TD
    A[User query: description, size, max price, wardrobe] --> B[run_agent planning loop]
    B --> C[Initialize session state]
    C --> D[search_listings description size max_price]
    D --> E{Any results?}
    E -- No --> F[Set session error]
    F --> G[Return early to UI]
    E -- Yes --> H[Store results and selected_item]
    H --> I[suggest_outfit selected_item wardrobe]
    I --> J{Outfit text returned?}
    J -- No --> K[Set outfit error]
    K --> G
    J -- Yes --> L[Store outfit_suggestion]
    L --> M[create_fit_card outfit_suggestion selected_item]
    M --> N{Caption returned?}
    N -- No --> O[Set fit card error]
    O --> G
    N -- Yes --> P[Store fit_card]
    P --> Q[Return completed session]
    Q --> R[UI displays item, outfit, and fit card]

    subgraph Session State
      S1[description]
      S2[size]
      S3[max_price]
      S4[wardrobe]
      S5[results]
      S6[selected_item]
      S7[outfit_suggestion]
      S8[fit_card]
      S9[error]
    end

    B <--> Session State
    D <--> Session State
    I <--> Session State
    M <--> Session State
```

---

## AI Tool Plan

**Milestone 3 — Individual tool implementations:**

I will use ChatGPT to help implement each tool separately. For `search_listings`, I will provide the Tool 1 spec and ask for a function that uses `load_listings()`, filters by price and size, scores by keyword overlap, and returns `[]` when no matches are found. I will verify it by testing a normal query, an impossible query, and a price-filtered query.

For `suggest_outfit`, I will provide the Tool 2 spec and ask for a function that uses Groq when available but still handles an empty wardrobe and API failure gracefully. I will verify it by testing with `get_example_wardrobe()` and `get_empty_wardrobe()`.

For `create_fit_card`, I will provide the Tool 3 spec and ask for a function that creates a casual caption and returns an error string when the outfit input is empty. I will verify it by testing a normal outfit string and an empty outfit string.

**Milestone 4 — Planning loop and state management:**

I will use ChatGPT to help implement `run_agent()` using the Planning Loop, State Management section, Error Handling table, and Architecture diagram from this file. I expect the generated code to branch after `search_listings`, stop early on no results, store the selected item in the session, pass that same selected item into `suggest_outfit`, then pass the outfit suggestion and selected item into `create_fit_card`.

Before accepting the code, I will check that it does not call all three tools unconditionally. I will print the final session dictionary during testing to confirm that values are being stored and passed correctly between tools.

---

## A Complete Interaction (Step by Step)

**Example user query:** "I'm looking for a vintage graphic tee under $30. I mostly wear baggy jeans and chunky sneakers. What's out there and how would I style it?"

**Step 1:**
The agent extracts the search values:
- `description = "vintage graphic tee"`
- `size = None`
- `max_price = 30.0`

The agent calls:
`search_listings(description="vintage graphic tee", size=None, max_price=30.0)`

The tool returns matching listings sorted by relevance. The agent stores the list in `session["results"]`.

**Step 2:**
The agent checks whether the list is empty. If it is empty, the agent stops and displays a helpful no-results message. If it has results, the agent selects the top listing:
`session["selected_item"] = session["results"][0]`

For example, the selected item may be `Faded Band Tee — $22 on depop`.

**Step 3:**
The agent calls:
`suggest_outfit(new_item=session["selected_item"], wardrobe=session["wardrobe"])`

The tool returns an outfit suggestion such as pairing the tee with baggy jeans, chunky sneakers, and a silver chain for a 90s grunge look. The agent stores this string in `session["outfit_suggestion"]`.

**Step 4:**
The agent calls:
`create_fit_card(outfit=session["outfit_suggestion"], new_item=session["selected_item"])`

The tool returns a short caption. The agent stores this in `session["fit_card"]`.

**Final output to user:**
The user sees:
1. Found item: `Faded Band Tee — $22 on depop`
2. Outfit suggestion: a complete styling idea using the selected item and wardrobe context.
3. Fit card: a casual social caption for the outfit.

If search returns no matches, the user instead sees: `I couldn't find listings that matched that description, size, and budget. Try a broader search, removing the size filter, or increasing your max price.` In that case, the agent does not call the outfit or fit card tools.
