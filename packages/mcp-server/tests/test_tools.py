from mcp_server.tools import search_docs


def test_some_function():
    words = "keywords"
    assert search_docs(words) == f"Searching for: {words}"
