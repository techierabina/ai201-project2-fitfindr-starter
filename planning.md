Tool 1: search_listings

What it does:
Searches the mock listings dataset for secondhand items that match a text description, optional size, and optional price ceiling. Returns a ranked list of matches sorted by keyword relevance.

Input parameters:


description (str): Keywords describing the item the user wants (e.g., "vintage graphic tee"). Used to score each listing by keyword overlap against title, description, style_tags, category, and colors.
size (str | None): Size string to filter by (e.g., "M", "S/M"). Case-insensitive. If None, size filtering is skipped.
max_price (float | None): Maximum price inclusive. If None, price filtering is skipped.


What it returns:
A list of listing dicts sorted by relevance score (highest first). Each dict contains:
id, title, description, category, style_tags (list), size, condition, price (float), colors (list), brand, platform.
Returns an empty list [] if nothing matches — never raises an exception.

What happens if it fails or returns nothing:
The agent sets session["error"] to a helpful message like: "No listings found for '[description]' in size [size] under $[max_price]. Try broadening your search — remove the size filter or raise your budget." The agent returns the session immediately and does NOT call suggest_outfit.


Tool 2: suggest_outfit

What it does:
Given a thrifted item and the user's wardrobe, calls the LLM to suggest 1–2 complete outfit combinations using pieces the user already owns.

Input parameters:


new_item (dict): A listing dict — the item the user is considering buying. Used for title, category, colors, style_tags.
wardrobe (dict): A wardrobe dict with an items key containing a list of wardrobe item dicts (each with name, category, colors, style_tags, notes). May be empty.


What it returns:
A non-empty string with specific outfit suggestions. If wardrobe is populated, suggestions reference named wardrobe pieces. If wardrobe is empty, returns general styling advice for the item type.

What happens if it fails or returns nothing:
If wardrobe["items"] is empty, the LLM is prompted for general styling advice (what bottoms, shoes, and layers pair well with this item type and vibe) rather than crashing. If the LLM call fails, returns a fallback string: "Couldn't generate outfit suggestions right now — try pairing this with basics in a similar color palette."


Tool 3: create_fit_card

What it does:
Calls the LLM to generate a short, casual 2–4 sentence Instagram/TikTok-style caption for the outfit, mentioning the item name, price, and platform naturally.

Input parameters:


outfit (str): The outfit suggestion string from suggest_outfit().
new_item (dict): The listing dict for the thrifted item — used for title, price, platform.


What it returns:
A 2–4 sentence caption string that sounds like a real OOTD post — casual, specific, authentic. Varies each time for different inputs (LLM temperature set to 1.2).
If outfit is empty or whitespace-only, returns the error string: "Can't generate a fit card without an outfit suggestion — make sure suggest_outfit ran successfully first."

What happens if it fails or returns nothing:
Returns the descriptive error string above rather than raising an exception. Agent stores this in session["fit_card"] and still returns the session.


Planning Loop

The agent runs a fixed sequence with one conditional branch:


Parse the query to extract description, size, and max_price using the LLM.
Call search_listings(description, size, max_price).
Branch: If results is empty → set session["error"], return session early. Stop here.
If results found → set session["selected_item"] = results[0].
Call suggest_outfit(selected_item, wardrobe) → store in session["outfit_suggestion"].
Call create_fit_card(outfit_suggestion, selected_item) → store in session["fit_card"].
Return session.


The loop does NOT call all tools unconditionally — step 3 is the gate. If search returns nothing, suggest_outfit and create_fit_card are never called.


State Management

All state lives in the session dict initialized by _new_session(). Fields are written once and read by the next step:


session["parsed"] — written after query parsing, read by search_listings call
session["search_results"] — written after search_listings, read to pick selected_item
session["selected_item"] — written as results[0], passed directly into suggest_outfit and create_fit_card
session["outfit_suggestion"] — written after suggest_outfit, passed directly into create_fit_card
session["fit_card"] — written last, read by app.py to display to user
session["error"] — written on early exit, checked by app.py before displaying results


No tool re-fetches data already in the session. The user never has to re-enter the item between steps.


Error Handling

ToolFailure modeAgent responsesearch_listingsNo results match the querySet session["error"] = "No listings found for '[description]'[size/price context]. Try broadening your search." Return session early. Do not call suggest_outfit.suggest_outfitWardrobe is emptyPrompt LLM for general styling advice for this item type instead of wardrobe-specific combos. Return that string — never crash.create_fit_cardOutfit input is missing or empty stringReturn error string: "Can't generate a fit card without an outfit suggestion." Do not call LLM.


Architecture

User query (natural language)
    │
    ▼
run_agent()
    │
    ├─► Step 1: Parse query → extract description, size, max_price
    │       │
    │       └─► session["parsed"] = {description, size, max_price}
    │
    ├─► Step 2: search_listings(description, size, max_price)
    │       │
    │       ├── results == [] ──► session["error"] = "No listings found..."
    │       │                         │
    │       │                         └─► RETURN SESSION (early exit)
    │       │
    │       └── results found ──► session["search_results"] = [...]
    │                                 session["selected_item"] = results[0]
    │
    ├─► Step 3: suggest_outfit(selected_item, wardrobe)
    │       │
    │       ├── wardrobe empty ──► LLM: general styling advice
    │       └── wardrobe has items ──► LLM: specific outfit combos
    │               │
    │               └─► session["outfit_suggestion"] = "..."
    │
    ├─► Step 4: create_fit_card(outfit_suggestion, selected_item)
    │       │
    │       ├── outfit empty ──► return error string
    │       └── outfit valid ──► LLM: generate caption
    │               │
    │               └─► session["fit_card"] = "..."
    │
    └─► RETURN SESSION


AI Tool Plan

Milestone 3 — Individual tool implementations:

For search_listings: Give Claude the Tool 1 spec block (inputs, return value, failure mode) plus the load_listings() signature from data_loader.py. Ask it to implement the function with keyword scoring across title, description, style_tags, category, and colors. Verify: test with 3 queries — one that returns results, one that returns empty, one with a price filter. Confirm empty returns [] not an exception.

For suggest_outfit: Give Claude the Tool 2 spec block plus the wardrobe schema structure. Ask it to implement with two branches (empty vs populated wardrobe), calling Groq llama-3.3-70b-versatile. Verify: test with get_example_wardrobe() and get_empty_wardrobe() — both should return non-empty strings.

For create_fit_card: Give Claude the Tool 3 spec block. Ask it to implement with the empty-outfit guard and temperature=1.2. Verify: run 3 times on same input and confirm outputs differ. Test with empty outfit string and confirm error message returned.

Milestone 4 — Planning loop and state management:

Give Claude the Architecture diagram above plus the State Management and Planning Loop sections. Ask it to implement run_agent() following the 7 steps in the TODO. Verify: run the CLI test cases in agent.py — happy path should populate all session fields, no-results path should set session["error"] and leave fit_card as None.


A Complete Interaction (Step by Step)

Example user query: "I'm looking for a vintage graphic tee under $30. I mostly wear baggy jeans and chunky sneakers. What's out there and how would I style it?"

Step 1:
Agent parses the query. Extracts: description="vintage graphic tee", size=None (not specified), max_price=30.0. Stores in session["parsed"].

Step 2:
Calls search_listings("vintage graphic tee", size=None, max_price=30.0). The function loads all 40 listings, filters to price ≤ $30, scores each by keyword overlap with "vintage graphic tee" against title/description/style_tags. Returns matches sorted by score — e.g., lst_006 "Graphic Tee — 2003 Tour Bootleg Style" ($24) and lst_033 "Vintage Band Tee — Faded Grey" ($19). Stores in session["search_results"]. Sets session["selected_item"] = lst_006.

Step 3:
Calls suggest_outfit(lst_006, example_wardrobe). Wardrobe has 10 items — not empty. LLM receives the item details and wardrobe list, returns: "Pair this boxy graphic tee with your baggy straight-leg jeans and chunky white sneakers for a classic 90s streetwear look. Tuck the front corner slightly and add your black crossbody bag to keep it clean." Stores in session["outfit_suggestion"].

Step 4:
Calls create_fit_card(outfit_suggestion, lst_006). LLM generates: "found this faded bootleg tee on depop for $24 and it was made for my baggy jeans tucked the front, threw on my chunky sneakers, and called it a day. thrift szn never misses." Stores in session["fit_card"].

Final output to user:
Three panels in the Gradio UI populate:


Search result: "Graphic Tee — 2003 Tour Bootleg Style — $24, depop, good condition"
Outfit suggestion: the LLM styling paragraph
Fit card: the caption string