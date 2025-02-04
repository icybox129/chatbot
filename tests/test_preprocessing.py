# tests/test_preprocessing.py

import os
import shutil
import pytest
from unittest import mock
from pathlib import Path
from langchain.schema import Document
from preprocessing.preprocessing import (
    load_documents_from_local,
    load_documents_from_s3,
    split_text,
    save_to_chroma_local
)

# Constants for testing (ensure these match those in conftest.py)
TEST_BUCKET_NAME = "test-bucket"
TEST_RAW_PREFIX = "data/raw"
TEST_CHROMA_PREFIX = "data/chroma"

@pytest.fixture(scope="module")
def setup_test_data():
    """Fixture to set up test data in the local filesystem."""
    test_data_dir = Path("./tests/test_data")
    test_data_dir.mkdir(parents=True, exist_ok=True)
    
    sample1_path = test_data_dir / "sample1.md"
    sample2_path = test_data_dir / "sample2.md"

    sample1_path.write_text("# Sample Document 1\n\nThis is the first test document.")
    sample2_path.write_text("# Sample Document 2\n\nThis is the second test document.")

    # Debugging output
    print(f"DEBUG: Checking test files - {sample1_path.exists()}, {sample2_path.exists()}")
    
    yield test_data_dir
    
    # Teardown
    shutil.rmtree(test_data_dir)

def test_load_documents_from_local(setup_test_data):
    """Test that documents are loaded successfully from a local directory."""
    # Mock DATA_PATH in preprocessing.py
    with mock.patch("preprocessing.DATA_PATH", str(setup_test_data)):
        documents = load_documents_from_local()
        
        assert len(documents) == 2, "Should load exactly 2 documents from local directory."
        for doc in documents:
            assert hasattr(doc, 'page_content'), "Document should have 'page_content' attribute."
            assert hasattr(doc, 'metadata'), "Document should have 'metadata' attribute."
            assert isinstance(doc.page_content, str), "'page_content' should be a string."
            assert isinstance(doc.metadata, dict), "'metadata' should be a dictionary."

def test_split_text():
    """Test that documents are split into chunks correctly."""
    # Provide a Document object with realistic Markdown
    markdown_content = (
        "# Heading\n\n"
        "Content here.\n\n"
        "## Subheading\n\n"
        "More content here.\n\n"
        "```python\nprint('Hello, World!')\n```"
    )
    documents = [Document(page_content=markdown_content, metadata={})]
    chunks = split_text(documents)
    
    assert len(chunks) >= 2, "Should split into multiple chunks based on headings."
    for chunk in chunks:
        assert hasattr(chunk, 'page_content'), "Chunk should have 'page_content' attribute."
        assert isinstance(chunk.page_content, str), "'page_content' should be a string."

        if "```python" in chunk.page_content:
            assert chunk.page_content.count("```python") == 1, "Code blocks should remain intact."

def test_load_documents_from_s3(setup_test_data, moto_s3):
    """Test that documents are loaded successfully from S3."""
    # Mock the constants in preprocessing.py
    with mock.patch("preprocessing.preprocessing.S3_BUCKET_NAME", TEST_BUCKET_NAME), \
         mock.patch("preprocessing.preprocessing.S3_RAW_PREFIX", TEST_RAW_PREFIX):
         
        documents = load_documents_from_s3()
        
        assert len(documents) == 2, "Should load exactly 2 documents from S3."
        for doc in documents:
            assert hasattr(doc, 'page_content'), "Document should have 'page_content' attribute."
            assert hasattr(doc, 'metadata'), "Document should have 'metadata' attribute."
            assert isinstance(doc.page_content, str), "'page_content' should be a string."
            assert isinstance(doc.metadata, dict), "'metadata' should be a dictionary."

def test_extract_metadata():
    from preprocessing.preprocessing import extract_metadata
    
    content_with_frontmatter = (
        "---\n"
        "title: \"Test Document\"\n"
        "author: \"ChatGPT\"\n"
        "---\n"
        "# Heading\n\nContent here."
    )
    metadata, content = extract_metadata(content_with_frontmatter)
    
    assert metadata.get("title") == "Test Document", "Metadata 'title' should be extracted correctly."
    assert metadata.get("author") == "ChatGPT", "Metadata 'author' should be extracted correctly."
    assert content.startswith("# Heading"), "Content should start after frontmatter."

def test_save_to_chroma_local(setup_test_data):
    """Test saving chunks to the local Chroma database."""
    from preprocessing.preprocessing import save_to_chroma_local
    
    # Mock DATA_PATH and CHROMA_PATH
    chroma_path = Path("./tests/temp_chroma")
    with mock.patch("preprocessing.preprocessing.DATA_PATH", str(setup_test_data)), \
         mock.patch("preprocessing.preprocessing.CHROMA_PATH", str(chroma_path)):
         
        documents = load_documents_from_local()
        chunks = split_text(documents)
        save_to_chroma_local(chunks)
        
        # Verify that Chroma DB files are created
        assert chroma_path.exists(), "Chroma DB directory should exist after saving."
        assert any(chroma_path.iterdir()), "Chroma DB directory should contain files."
        
        # Cleanup
        shutil.rmtree(chroma_path)
