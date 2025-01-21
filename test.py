import pytest
import json
from fastapi.testclient import TestClient
from app.main import app
from app.core.logger import logger

client = TestClient(app)

def test_create_room():
    # Load interview config from JSON file
    with open("interview_config.json") as f:
        config = json.load(f)
    
    try:
        # Make POST request to /api/rooms endpoint
        response = client.post("/api/rooms", json=config)
        
        # Assert response status code and structure
        assert response.status_code == 200
        assert "room_url" in response.json()
        assert "token" in response.json()
        
        # Validate response data types
        response_data = response.json()
        assert isinstance(response_data["room_url"], str)
        assert isinstance(response_data["token"], str)
        
        # Log response using logger instead of print
        logger.info(f"Response: {response_data}")
        
    except Exception as e:
        logger.error(f"Error during room creation test: {str(e)}")
        raise

if __name__ == "__main__":
    pytest.main([__file__])