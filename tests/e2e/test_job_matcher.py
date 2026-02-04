"""E2E Tests for Job Matcher Page"""

import pytest
from playwright.sync_api import Page, expect


class TestJobMatcherPage:
    """Test Job Matcher page functionality"""

    def test_page_loads(self, page: Page, base_url: str):
        """Test that Job Matcher page loads"""
        page.goto(f"{base_url}/jobs")

        expect(page.locator("h1")).to_contain_text("Job Matcher")
        expect(page.locator("textarea")).to_be_visible()

    def test_job_description_input(self, page: Page, base_url: str, sample_job_description: str):
        """Test entering job description"""
        page.goto(f"{base_url}/jobs")

        # Find and fill textarea
        textarea = page.locator("textarea")
        textarea.fill(sample_job_description)

        # Check character count updates
        expect(page.locator("text=chars")).to_be_visible()

    def test_match_button_disabled_without_input(self, page: Page, base_url: str):
        """Test that Match button is disabled without sufficient input"""
        page.goto(f"{base_url}/jobs")

        # Find the Match Resume button
        match_button = page.locator("button:has-text('Match Resume')")

        # Should be disabled initially
        expect(match_button).to_be_disabled()

    def test_match_button_enabled_with_input(self, page: Page, base_url: str, sample_job_description: str):
        """Test that Match button is enabled with sufficient input"""
        page.goto(f"{base_url}/jobs")

        # Fill in job description
        textarea = page.locator("textarea")
        textarea.fill(sample_job_description)

        # Match button should now be enabled
        match_button = page.locator("button:has-text('Match Resume')")
        expect(match_button).to_be_enabled()

    def test_optional_fields_exist(self, page: Page, base_url: str):
        """Test that optional title and company fields exist"""
        page.goto(f"{base_url}/jobs")

        # Check for job title input
        title_input = page.locator("input[placeholder*='Software Engineer']")
        expect(title_input).to_be_visible()

        # Check for company input
        company_input = page.locator("input[placeholder*='TechCorp']")
        expect(company_input).to_be_visible()

    def test_history_button_exists(self, page: Page, base_url: str):
        """Test that History button exists"""
        page.goto(f"{base_url}/jobs")

        history_button = page.locator("button:has-text('History')")
        expect(history_button).to_be_visible()

    def test_analytics_button_exists(self, page: Page, base_url: str):
        """Test that Analytics button exists"""
        page.goto(f"{base_url}/jobs")

        analytics_button = page.locator("button:has-text('Analytics')")
        expect(analytics_button).to_be_visible()

    def test_history_sidebar_opens(self, page: Page, base_url: str):
        """Test that clicking History opens sidebar"""
        page.goto(f"{base_url}/jobs")

        # Click History button
        page.click("button:has-text('History')")

        # Sidebar should appear
        expect(page.locator("text=Match History")).to_be_visible()

    def test_analytics_sidebar_opens(self, page: Page, base_url: str):
        """Test that clicking Analytics opens sidebar"""
        page.goto(f"{base_url}/jobs")

        # Click Analytics button
        page.click("button:has-text('Analytics')")

        # Sidebar should appear
        expect(page.locator("text=Skills Analytics")).to_be_visible()

    def test_empty_state_display(self, page: Page, base_url: str):
        """Test empty state is shown when no results"""
        page.goto(f"{base_url}/jobs")

        # Check for empty state message
        expect(page.locator("text=Paste a job description")).to_be_visible()

    @pytest.mark.slow
    def test_job_matching_flow(self, page: Page, base_url: str, sample_job_description: str):
        """Test complete job matching flow (requires backend)"""
        page.goto(f"{base_url}/jobs")

        # Fill in job details
        page.locator("input[placeholder*='Software Engineer']").fill("Senior Software Engineer")
        page.locator("input[placeholder*='TechCorp']").fill("Test Company")
        page.locator("textarea").fill(sample_job_description)

        # Click Match Resume
        page.click("button:has-text('Match Resume')")

        # Wait for results (with longer timeout for API call)
        page.wait_for_selector("text=%", timeout=30000)

        # Verify results appear
        expect(page.locator("text=Score Breakdown")).to_be_visible()
        expect(page.locator("text=Skills Analysis")).to_be_visible()

    @pytest.mark.slow
    def test_results_display_score(self, page: Page, base_url: str, sample_job_description: str):
        """Test that match score is displayed after matching"""
        page.goto(f"{base_url}/jobs")

        # Fill and submit
        page.locator("textarea").fill(sample_job_description)
        page.click("button:has-text('Match Resume')")

        # Wait for score to appear
        page.wait_for_selector("text=Match", timeout=30000)

        # Check for score circle
        expect(page.locator("text=%")).to_be_visible()

    @pytest.mark.slow
    def test_copy_results_button(self, page: Page, base_url: str, sample_job_description: str):
        """Test copy results functionality"""
        page.goto(f"{base_url}/jobs")

        # Fill and submit
        page.locator("textarea").fill(sample_job_description)
        page.click("button:has-text('Match Resume')")

        # Wait for results
        page.wait_for_selector("text=Score Breakdown", timeout=30000)

        # Find and click copy button
        copy_button = page.locator("button[title='Copy results']")
        expect(copy_button).to_be_visible()
