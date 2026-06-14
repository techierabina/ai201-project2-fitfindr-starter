from tools import search_listings, create_fit_card

def test_search_returns_results():
    results = search_listings("vintage graphic tee", size=None, max_price=50)
    assert isinstance(results, list)
    assert len(results) > 0

def test_search_empty_results():
    results = search_listings("designer ballgown", size="XXS", max_price=5)
    assert results == []

def test_search_price_filter():
    results = search_listings("jacket", size=None, max_price=10)
    assert all(item["price"] <= 10 for item in results)

def test_search_size_filter():
    results = search_listings("tee", size="XL", max_price=None)
    assert all("xl" in item["size"].lower() for item in results)

def test_create_fit_card_empty_outfit():
    results = search_listings("vintage graphic tee", size=None, max_price=50)
    result = create_fit_card("", results[0])
    assert "Can't generate" in result

def test_search_returns_sorted_by_relevance():
    results = search_listings("vintage graphic tee", size=None, max_price=50)
    top = results[0]
    searchable = top["title"].lower() + " ".join(top["style_tags"]).lower()
    assert "graphic" in searchable or "vintage" in searchable or "tee" in searchable
