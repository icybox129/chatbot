"""
Test Suite for app.py Flask Routes
==================================

This test file verifies:
1. The Flask application responds correctly on the home page route (`/`).
2. The /api/query endpoint works, returning a JSON payload with a 'response' and 'sources'.
3. The /new_conversation endpoint clears conversation history.

Fixtures:
- `client`: A test client for the Flask app, configured with `TESTING = True`.
"""

import pytest
from app import app

@pytest.fixture
def client():
    """
    Pytest fixture that configures the Flask test client.

    - Sets app.config['TESTING'] to True.
    - Returns a test client that can make requests to the Flask endpoints.
    """
    app.config['TESTING'] = True
    with app.test_client() as client:
        yield client

def test_home_page(client):
    """Test the home page loads successfully"""
    response = client.get('/')
    assert response.status_code == 200

def test_handle_query(client):
    """Test the query API"""
    response = client.post('/api/query', json={"query": "Create an EC2 instance"})
    assert response.status_code == 200
    data = response.get_json()
    assert 'response' in data
    assert 'sources' in data

def test_new_conversation(client):
    """Test starting a new conversation"""
    response = client.post('/new_conversation')
    assert response.status_code == 200