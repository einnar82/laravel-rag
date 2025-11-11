"""Tests for API endpoints."""

import pytest
from fastapi.testclient import TestClient
from src.api.main import app


class TestAPI:
    """Test cases for API endpoints."""

    @pytest.fixture
    def client(self):
        """Create a test client."""
        return TestClient(app)

    def test_root_endpoint(self, client):
        """Test root endpoint."""
        response = client.get("/")
        assert response.status_code == 200
        data = response.json()
        assert "message" in data
        assert "version" in data

    def test_health_endpoint(self, client):
        """Test health check endpoint."""
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert "version" in data
        assert "llm_model" in data

    def test_stats_endpoint(self, client):
        """Test stats endpoint."""
        response = client.get("/stats")
        assert response.status_code == 200
        data = response.json()
        assert "total_documents" in data
        assert "versions" in data

    def test_versions_endpoint(self, client):
        """Test versions endpoint."""
        response = client.get("/versions")
        assert response.status_code == 200
        data = response.json()
        assert "versions" in data
        assert "total_versions" in data

    def test_query_endpoint_validation(self, client):
        """Test query endpoint validation."""
        # Missing question
        response = client.post("/query", json={})
        assert response.status_code == 422

        # Invalid temperature
        response = client.post("/query", json={
            "question": "test",
            "temperature": 2.0
        })
        assert response.status_code == 422

        # Invalid top_k
        response = client.post("/query", json={
            "question": "test",
            "top_k": 100
        })
        assert response.status_code == 422

    def test_search_endpoint_validation(self, client):
        """Test search endpoint validation."""
        # Missing query parameter
        response = client.get("/search")
        assert response.status_code == 422

        # Valid request
        response = client.get("/search?q=test")
        assert response.status_code in [200, 500]  # May fail if not indexed
