"""
Test Suite for preprocessing.py
==============================
Validates the functionality of the preprocessing module, which handles:
- Loading markdown documents (from local or S3),
- Splitting them into chunks,
- Extracting YAML frontmatter metadata,
- Saving them to a local Chroma database.

Fixtures:
- `setup_test_data`: Creates a local directory with sample markdown files for testing.
- `moto_s3`: (imported from conftest.py) provides a mocked S3 environment.

Tests:
- test_load_documents_from_local: Checks local loading and metadata extraction.
- test_split_text: Ensures document chunking works properly.
- test_load_documents_from_s3: Ensures S3-based loading with mock is successful.
- test_extract_metadata: Verifies YAML frontmatter is parsed correctly.
- test_save_to_chroma_local: Tests local Chroma DB saving.
"""

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
    """
    Fixture to set up test data in the local filesystem.
    Creates a temporary directory with sample .md files, 
    then removes it after tests complete.
    """
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
    """
    Test: load_documents_from_local
    Ensures that loading markdown files from a local directory 
    returns a list of Document objects with valid content and metadata.
    """
    # Mock DATA_PATH in preprocessing.py
    with mock.patch("preprocessing.preprocessing.DATA_PATH", str(setup_test_data)):
        documents = load_documents_from_local()
        
        assert len(documents) == 2, "Should load exactly 2 documents from local directory."
        for doc in documents:
            assert hasattr(doc, 'page_content'), "Document should have 'page_content' attribute."
            assert hasattr(doc, 'metadata'), "Document should have 'metadata' attribute."
            assert isinstance(doc.page_content, str), "'page_content' should be a string."
            assert isinstance(doc.metadata, dict), "'metadata' should be a dictionary."

def test_split_text():
    """
    Test: split_text
    Checks that a Document with Markdown headings and code blocks 
    is split into multiple chunks while preserving code blocks.
    """
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
    """
    Test: load_documents_from_s3
    Ensures that markdown files can be downloaded from mocked S3 
    and correctly turned into Document objects.
    """
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
    """
    Test: extract_metadata
    Verifies that YAML frontmatter is correctly parsed 
    and removed from the document content.
    """
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
    """
    Test: save_to_chroma_local
    Checks that chunks can be saved to a local Chroma database, 
    and that the database folder is created with files.
    """
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
