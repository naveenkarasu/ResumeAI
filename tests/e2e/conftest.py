"""Playwright E2E Test Configuration"""

import pytest
from playwright.sync_api import Page, expect
import os

# Base URL for testing
BASE_URL = os.getenv("TEST_BASE_URL", "http://localhost:5173")
API_URL = os.getenv("TEST_API_URL", "http://localhost:8000")


@pytest.fixture(scope="session")
def base_url():
    """Return the base URL for the frontend"""
    return BASE_URL


@pytest.fixture(scope="session")
def api_url():
    """Return the base URL for the API"""
    return API_URL


@pytest.fixture
def page_with_base(page: Page, base_url: str):
    """Page fixture that navigates to base URL"""
    page.goto(base_url)
    return page


# Sample job description for testing
SAMPLE_JOB_DESCRIPTION = """
Senior Software Engineer

We are looking for a Senior Software Engineer with 5+ years of experience.

Required Skills:
- Python (must have)
- FastAPI or Django
- PostgreSQL
- Docker
- AWS

Preferred Skills:
- Kubernetes
- React
- Machine Learning

Requirements:
- Bachelor's degree in Computer Science or equivalent
- 5+ years of professional software development experience
- Strong communication skills

Responsibilities:
- Design and implement scalable backend services
- Mentor junior developers
- Participate in code reviews
"""


@pytest.fixture
def sample_job_description():
    """Return a sample job description for testing"""
    return SAMPLE_JOB_DESCRIPTION
