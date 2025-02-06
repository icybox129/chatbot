"""
Configuration & Setup for Pytest
================================

This file provides fixtures and setup logic shared across multiple test files.

Key Fixture:
- `moto_s3`: A fixture that mocks AWS S3 interactions using `moto`.
             It creates a test S3 bucket, then uploads sample content.
             Tests can use this to avoid making real network calls.

Constants for Testing:
- TEST_BUCKET_NAME: The name of the mocked S3 bucket.
- TEST_RAW_PREFIX: Prefix for raw markdown documents.
- TEST_CHROMA_PREFIX: Prefix for the Chroma DB directory in S3.
- TEST_S3_CONTENT: A dictionary mapping 'S3 key' -> 'file content' to upload.

Usage:
- Tests that need mocked S3 interactions can include `moto_s3` as a parameter.
"""


import sys
import os
import pytest
from moto import mock_s3
import boto3

# Modify the sys.path to ensure the project root is accessible for imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Constants for testing
TEST_BUCKET_NAME = "test-bucket"
TEST_RAW_PREFIX = "data/raw"
TEST_CHROMA_PREFIX = "data/chroma"
TEST_S3_CONTENT = {
    "data/raw/sample1.md": "# Sample Document 1\n\nThis is the first test document.",
    "data/raw/sample2.md": "# Sample Document 2\n\nThis is the second test document."
}

@pytest.fixture
def moto_s3():
    """
    Fixture that sets up a mocked S3 environment using `moto`.
    
    1. Creates a test S3 bucket.
    2. Uploads sample markdown files to that bucket.
    3. Yields the mocked S3 client for use in tests.

    After tests complete, the context manager tears down the mock.
    """
    with mock_s3():
        # Initialize the S3 client
        s3 = boto3.client("s3", region_name="us-east-1")
        
        # Create the test bucket
        s3.create_bucket(Bucket=TEST_BUCKET_NAME)
        
        # Upload test files to the bucket
        for key, content in TEST_S3_CONTENT.items():
            s3.put_object(Bucket=TEST_BUCKET_NAME, Key=key, Body=content)
        
        # Provide the mocked S3 client to the tests
        yield s3 
