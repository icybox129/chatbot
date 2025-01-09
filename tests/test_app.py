import pytest
from app import app

@pytest.fixture
def client():
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