from zoom_to_text.summarizer import _chunk_text

def test_chunk_text_preserves_words():
    text = "hello world example"
    chunks = _chunk_text(text, 7)
    assert chunks == ["hello", "world", "example"]
