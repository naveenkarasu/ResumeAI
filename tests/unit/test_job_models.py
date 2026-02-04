"""Unit Tests for Job Matching Models"""

import sys
import os

# Add project root to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

import pytest
from datetime import datetime
from pydantic import ValidationError

# Import directly from the models file to avoid loading the full API
from src.ui.api.models.job_models import (
    JobMatchRequest,
    JobMatchResponse,
    ScoreBreakdown,
    MatchedSkill,
    MissingSkill,
    Recommendation,
    ExtractedRequirements,
    SkillImportance,
    MatchQuality,
    JobHistoryItem,
)


class TestJobMatchRequest:
    """Test JobMatchRequest model"""

    def test_valid_request(self):
        """Test creating a valid request"""
        request = JobMatchRequest(
            job_description="A" * 100,  # At least 50 chars
            job_title="Software Engineer",
            company="TechCorp"
        )
        assert request.job_description == "A" * 100
        assert request.job_title == "Software Engineer"
        assert request.company == "TechCorp"

    def test_minimal_request(self):
        """Test creating request with only required field"""
        request = JobMatchRequest(job_description="A" * 50)
        assert len(request.job_description) >= 50
        assert request.job_title is None
        assert request.company is None

    def test_short_description_fails(self):
        """Test that short description fails validation"""
        with pytest.raises(ValidationError):
            JobMatchRequest(job_description="too short")


class TestScoreBreakdown:
    """Test ScoreBreakdown model"""

    def test_valid_scores(self):
        """Test creating valid score breakdown"""
        scores = ScoreBreakdown(
            skills_match=85.0,
            experience_match=90.0,
            education_match=100.0,
            keywords_match=70.0
        )
        assert scores.skills_match == 85.0
        assert scores.experience_match == 90.0

    def test_weighted_average(self):
        """Test weighted average calculation"""
        scores = ScoreBreakdown(
            skills_match=100.0,
            experience_match=100.0,
            education_match=100.0,
            keywords_match=100.0
        )
        assert scores.weighted_average == 100.0

    def test_weighted_average_mixed(self):
        """Test weighted average with mixed scores"""
        scores = ScoreBreakdown(
            skills_match=80.0,    # 40% weight = 32
            experience_match=60.0,  # 25% weight = 15
            education_match=100.0,  # 15% weight = 15
            keywords_match=50.0   # 20% weight = 10
        )
        # 32 + 15 + 15 + 10 = 72
        assert scores.weighted_average == 72.0

    def test_invalid_score_too_high(self):
        """Test that scores over 100 fail validation"""
        with pytest.raises(ValidationError):
            ScoreBreakdown(
                skills_match=150.0,
                experience_match=90.0,
                education_match=100.0,
                keywords_match=70.0
            )

    def test_invalid_score_negative(self):
        """Test that negative scores fail validation"""
        with pytest.raises(ValidationError):
            ScoreBreakdown(
                skills_match=-10.0,
                experience_match=90.0,
                education_match=100.0,
                keywords_match=70.0
            )


class TestMatchedSkill:
    """Test MatchedSkill model"""

    def test_valid_matched_skill(self):
        """Test creating a valid matched skill"""
        skill = MatchedSkill(
            skill="Python",
            source="Skills section",
            relevance=0.95,
            context="5+ years of Python development"
        )
        assert skill.skill == "Python"
        assert skill.relevance == 0.95

    def test_relevance_bounds(self):
        """Test relevance must be between 0 and 1"""
        with pytest.raises(ValidationError):
            MatchedSkill(skill="Python", source="Resume", relevance=1.5)


class TestMissingSkill:
    """Test MissingSkill model"""

    def test_valid_missing_skill(self):
        """Test creating a valid missing skill"""
        skill = MissingSkill(
            skill="Kubernetes",
            importance=SkillImportance.REQUIRED,
            suggestion="Consider getting certified",
            related_skills=["Docker", "AWS"]
        )
        assert skill.skill == "Kubernetes"
        assert skill.importance == SkillImportance.REQUIRED

    def test_importance_enum_values(self):
        """Test skill importance enum values"""
        assert SkillImportance.REQUIRED.value == "required"
        assert SkillImportance.PREFERRED.value == "preferred"
        assert SkillImportance.NICE_TO_HAVE.value == "nice-to-have"


class TestRecommendation:
    """Test Recommendation model"""

    def test_valid_recommendation(self):
        """Test creating a valid recommendation"""
        rec = Recommendation(
            title="Improve Skills",
            description="Add more Python projects",
            priority=1,
            category="skills"
        )
        assert rec.title == "Improve Skills"
        assert rec.priority == 1

    def test_priority_bounds(self):
        """Test priority must be 1-5"""
        with pytest.raises(ValidationError):
            Recommendation(
                title="Test",
                description="Test",
                priority=0,  # Invalid
                category="test"
            )

        with pytest.raises(ValidationError):
            Recommendation(
                title="Test",
                description="Test",
                priority=6,  # Invalid
                category="test"
            )


class TestMatchQuality:
    """Test MatchQuality enum"""

    def test_quality_values(self):
        """Test match quality enum values"""
        assert MatchQuality.EXCELLENT.value == "excellent"
        assert MatchQuality.GOOD.value == "good"
        assert MatchQuality.FAIR.value == "fair"
        assert MatchQuality.POOR.value == "poor"


class TestExtractedRequirements:
    """Test ExtractedRequirements model"""

    def test_valid_requirements(self):
        """Test creating valid extracted requirements"""
        reqs = ExtractedRequirements(
            required_skills=["Python", "Django"],
            preferred_skills=["React"],
            experience_years=5,
            experience_level="senior",
            education="Bachelor's in CS",
            keywords=["backend", "api"],
            responsibilities=["Design systems"]
        )
        assert len(reqs.required_skills) == 2
        assert reqs.experience_years == 5

    def test_default_values(self):
        """Test default values"""
        reqs = ExtractedRequirements()
        assert reqs.required_skills == []
        assert reqs.preferred_skills == []
        assert reqs.experience_years is None
        assert reqs.keywords == []


class TestJobHistoryItem:
    """Test JobHistoryItem model"""

    def test_valid_history_item(self):
        """Test creating a valid history item"""
        item = JobHistoryItem(
            match_id="match_123",
            job_title="Engineer",
            company="TechCorp",
            overall_score=85.0,
            quality=MatchQuality.EXCELLENT,
            analyzed_at=datetime.utcnow()
        )
        assert item.match_id == "match_123"
        assert item.overall_score == 85.0
