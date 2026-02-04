"""E2E Tests for Navigation"""

import pytest
from playwright.sync_api import Page, expect


class TestNavigation:
    """Test navigation and routing"""

    def test_home_page_loads(self, page: Page, base_url: str):
        """Test that the home page loads successfully"""
        page.goto(base_url)

        # Check page title or header
        expect(page.locator("h1")).to_contain_text("Resume RAG")

    def test_sidebar_navigation(self, page: Page, base_url: str):
        """Test that sidebar navigation works"""
        page.goto(base_url)

        # Check sidebar exists
        sidebar = page.locator("aside")
        expect(sidebar).to_be_visible()

        # Check navigation links exist
        expect(page.locator("text=Chat")).to_be_visible()
        expect(page.locator("text=Job Matcher")).to_be_visible()
        expect(page.locator("text=Interview Prep")).to_be_visible()
        expect(page.locator("text=Email Generator")).to_be_visible()
        expect(page.locator("text=Settings")).to_be_visible()

    def test_navigate_to_job_matcher(self, page: Page, base_url: str):
        """Test navigation to Job Matcher page"""
        page.goto(base_url)

        # Click Job Matcher link
        page.click("text=Job Matcher")

        # Verify we're on the Job Matcher page
        expect(page).to_have_url(f"{base_url}/jobs")
        expect(page.locator("h1")).to_contain_text("Job Matcher")

    def test_navigate_to_analyzer(self, page: Page, base_url: str):
        """Test navigation to Analyzer page"""
        page.goto(base_url)

        page.click("text=Job Analyzer")

        expect(page).to_have_url(f"{base_url}/analyzer")
        expect(page.locator("h1")).to_contain_text("Job Analyzer")

    def test_navigate_to_interview(self, page: Page, base_url: str):
        """Test navigation to Interview Prep page"""
        page.goto(base_url)

        page.click("text=Interview Prep")

        expect(page).to_have_url(f"{base_url}/interview")

    def test_navigate_to_email(self, page: Page, base_url: str):
        """Test navigation to Email Generator page"""
        page.goto(base_url)

        page.click("text=Email Generator")

        expect(page).to_have_url(f"{base_url}/email")

    def test_navigate_to_settings(self, page: Page, base_url: str):
        """Test navigation to Settings page"""
        page.goto(base_url)

        page.click("text=Settings")

        expect(page).to_have_url(f"{base_url}/settings")

    def test_mobile_menu_toggle(self, page: Page, base_url: str):
        """Test mobile menu toggle on small screens"""
        # Set mobile viewport
        page.set_viewport_size({"width": 375, "height": 667})
        page.goto(base_url)

        # Sidebar should be hidden initially on mobile
        sidebar = page.locator("aside")

        # Find and click hamburger menu button
        menu_button = page.locator("button[aria-label='Menu'], button:has(svg)")
        if menu_button.count() > 0:
            menu_button.first.click()
            # Sidebar should now be visible
            expect(sidebar).to_be_visible()
