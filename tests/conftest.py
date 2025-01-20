# tests/conftest.py

import sys
import os
import pytest
from moto import mock_s3  # Updated import for moto 4.x
import boto3

# Add the project root directory to sys.path
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
    """Fixture to mock S3 using moto."""
    with mock_s3():
        # Initialize the S3 client
        s3 = boto3.client("s3", region_name="us-east-1")
        
        # Create the test bucket
        s3.create_bucket(Bucket=TEST_BUCKET_NAME)
        
        # Upload test files to the bucket
        for key, content in TEST_S3_CONTENT.items():
            s3.put_object(Bucket=TEST_BUCKET_NAME, Key=key, Body=content)
        
        yield s3  # Provide the mocked S3 client to the tests
