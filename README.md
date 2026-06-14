# FitFindr 🛍️

A multi-tool AI agent that helps users find secondhand pieces and figure out how to wear them.

## Setup

```bash
python3.11 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
# Add your GROQ_API_KEY to a .env file
python3 app.py
```

## Tool Inventory

| Tool | Inputs | Output | Purpose |
|------|--------|--------|---------|
| `search_listings` | `description` (str), `size` (str\|None), `max_price` (float\|None) | list[dict] | Filters and ranks mock listings by keyword relevance |
| `suggest_outfit` | `new_item` (dict), `wardrobe` (dict) | str | LLM-generated outfit combinations using wardrobe pieces |
| `create_fit_card` | `outfit` (str), `new_item` (dict) | str | LLM-generated Instagram-style caption for the outfit |

## How the Planning Loop Works

The agent runs a fixed sequence with one conditional branch:

1. Parse the user query with the LLM to extract `description`, `size`, and `max_price`
2. Call `search_listings()` with parsed parameters
3. **Branch:** if results are empty → set error message, return early. `suggest_outfit` and `create_fit_card` are never called with empty input
4. Select `results[0]` as the item to style
5. Call `suggest_outfit()` with the item and wardrobe
6. Call `create_fit_card()` with the outfit suggestion and item
7. Return the session

The loop is not a fixed sequence — step 3 is a hard gate. The agent's behavior changes based on what `search_listings` returns.

## State Management

All state lives in a session dict initialized at the start of each interaction:

- `session["parsed"]` — written after query parsing, read by search_listings call
- `session["search_results"]` — written after search, read to pick selected_item
- `session["selected_item"]` — top result, passed into both suggest_outfit and create_fit_card
- `session["outfit_suggestion"]` — written after suggest_outfit, passed into create_fit_card
- `session["fit_card"]` — final output, read by app.py
- `session["error"]` — set on early exit, checked by app.py before displaying results

No tool re-fetches data already in the session. The user never re-enters the item between steps.

## Error Handling

| Tool | Failure mode | Agent response |
|------|-------------|----------------|
| `search_listings` | No results match | Sets `session["error"]` with helpful message suggesting broader search. Returns session early — `suggest_outfit` never called with empty input. |
| `suggest_outfit` | Empty wardrobe | Prompts LLM for general styling advice instead of wardrobe-specific combos. Always returns a non-empty string. |
| `create_fit_card` | Empty outfit string | Returns descriptive error string immediately without calling LLM. No exception raised. |

**Concrete example:** querying "designer ballgown size XXS under $5" returns:
`"No listings found for 'designer ballgown' in size XXS under $5.0. Try broadening your search — remove the size filter or raise your budget."`

## Spec Reflection

The planning.md spec helped most during the error handling design — deciding upfront what each tool returns on failure meant the planning loop could be written with clear conditional branches rather than try/catch everywhere.

One divergence: the spec described scoring keyword overlap across title, description, style_tags, category, and colors — but in practice the Y2K Baby Tee consistently ranked first for "vintage graphic tee" because "graphic tee" appeared in its style_tags, even though neither word appears in the title. The scoring works correctly; the spec assumption that the top result would have matching title keywords was wrong.

## AI Usage

**Instance 1 — search_listings implementation:** Gave Claude the Tool 1 spec block from planning.md (inputs, return value, failure mode) and the load_listings() signature. Claude generated the keyword scoring loop. Verified by testing 3 queries before trusting it — adjusted the scoring to include colors field which the initial version missed.

**Instance 2 — planning loop:** Gave Claude the architecture diagram and Planning Loop + State Management sections from planning.md. Claude generated run_agent(). Reviewed before running — confirmed it branched on empty results and stored values in the session dict at each step rather than using local variables.