"""E2E Tests for API Health and Endpoints"""

import pytest
from playwright.sync_api import Page, APIRequestContext, expect


class TestAPIHealth:
    """Test API health and basic endpoints"""

    def test_api_health_endpoint(self, page: Page, api_url: str):
        """Test API health endpoint"""
        response = page.request.get(f"{api_url}/health")

        assert response.ok, f"Health check failed: {response.status}"

        data = response.json()
        assert data["status"] == "healthy"
        assert "version" in data
        assert "rag_status" in data

    def test_api_root_endpoint(self, page: Page, api_url: str):
        """Test API root endpoint"""
        response = page.request.get(f"{api_url}/")

        assert response.ok
        data = response.json()
        assert "name" in data
        assert "version" in data

    def test_jobs_history_endpoint(self, page: Page, api_url: str):
        """Test jobs history endpoint"""
        response = page.request.get(f"{api_url}/api/jobs/history")

        assert response.ok
        data = response.json()
        assert "items" in data
        assert "total_count" in data

    def test_jobs_analytics_endpoint(self, page: Page, api_url: str):
        """Test jobs analytics endpoint"""
        response = page.request.get(f"{api_url}/api/jobs/analytics")

        assert response.ok
        data = response.json()
        assert "strongest_skills" in data
        assert "weakest_skills" in data

    @pytest.mark.slow
    def test_jobs_match_endpoint(self, page: Page, api_url: str, sample_job_description: str):
        """Test jobs match endpoint"""
        response = page.request.post(
            f"{api_url}/api/jobs/match",
            data={
                "job_description": sample_job_description,
                "job_title": "Test Engineer",
                "company": "Test Co"
            }
        )

        assert response.ok, f"Match failed: {response.status} - {response.text()}"

        data = response.json()
        assert "match_id" in data
        assert "overall_score" in data
        assert "quality" in data
        assert "scores" in data
        assert "matched_skills" in data
        assert "missing_skills" in data
        assert "recommendations" in data


class TestAPIErrors:
    """Test API error handling"""

    def test_invalid_job_description(self, page: Page, api_url: str):
        """Test error handling for invalid job description"""
        response = page.request.post(
            f"{api_url}/api/jobs/match",
            data={
                "job_description": "too short"  # Less than 50 chars
            }
        )

        # Should return validation error
        assert response.status == 422  # Unprocessable Entity

    def test_missing_job_description(self, page: Page, api_url: str):
        """Test error handling for missing job description"""
        response = page.request.post(
            f"{api_url}/api/jobs/match",
            data={}
        )

        assert response.status == 422

    def test_nonexistent_match_id(self, page: Page, api_url: str):
        """Test error handling for nonexistent match ID"""
        response = page.request.get(f"{api_url}/api/jobs/history/nonexistent_id_12345")

        assert response.status == 404
