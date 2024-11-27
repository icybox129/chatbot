import os
from langchain.schema import Document
from preprocessing.preprocessing import load_documents, split_text

def test_load_documents():
    """Test that documents are loaded successfully"""
    # Override the path for test data
    os.environ['DATA_PATH'] = './tests/test_data'

    documents = load_documents()
    assert len(documents) > 0  # Ensure at least one document is loaded
    for doc in documents:
        assert hasattr(doc, 'page_content')  # Check the attribute exists
        assert hasattr(doc, 'metadata')     # Check the attribute exists

def test_split_text():
    """Test that documents are split into chunks"""
    # Provide a Document object with realistic Markdown
    documents = [Document(page_content="# Heading\n\nContent here\n\n## Subheading\n\nMore content", metadata={})]
    chunks = split_text(documents)
    assert len(chunks) > 0  # Ensure splitting works
    for chunk in chunks:
        assert hasattr(chunk, 'page_content')
        assert isinstance(chunk.page_content, str)