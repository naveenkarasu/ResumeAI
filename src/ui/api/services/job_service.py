"""Enhanced Job Matching Service for comprehensive resume-to-job analysis"""

import re
import json
import logging
import uuid
from pathlib import Path
from datetime import datetime
from typing import Optional, List, Dict, Any

from src.rag import ResumeRAG
from ..models.job_models import (
    JobMatchRequest,
    JobMatchResponse,
    BatchJobMatchResponse,
    JobHistoryItem,
    JobHistoryResponse,
    SkillsAnalytics,
    SkillFrequency,
    MatchedSkill,
    MissingSkill,
    Recommendation,
    ScoreBreakdown,
    ExtractedRequirements,
    SkillImportance,
    MatchQuality,
)

logger = logging.getLogger(__name__)


class JobMatchingService:
    """Enhanced service for matching resumes to job descriptions"""

    # Comprehensive skill lists
    TECH_SKILLS = {
        # Programming Languages
        "python", "javascript", "typescript", "java", "c++", "c#", "go", "rust",
        "ruby", "php", "swift", "kotlin", "scala", "r", "matlab", "perl",
        # Frontend
        "react", "vue", "angular", "svelte", "next.js", "nuxt", "html", "css",
        "sass", "less", "tailwind", "bootstrap", "webpack", "vite",
        # Backend
        "node.js", "express", "django", "flask", "fastapi", "spring", "rails",
        ".net", "asp.net", "laravel", "gin", "echo",
        # Databases
        "sql", "postgresql", "mysql", "mongodb", "redis", "elasticsearch",
        "dynamodb", "cassandra", "sqlite", "oracle", "neo4j", "graphql",
        # Cloud & DevOps
        "aws", "azure", "gcp", "docker", "kubernetes", "terraform", "ansible",
        "jenkins", "github actions", "gitlab ci", "circleci", "argocd",
        "prometheus", "grafana", "datadog", "splunk",
        # AI/ML
        "machine learning", "deep learning", "nlp", "computer vision", "llm",
        "pytorch", "tensorflow", "keras", "scikit-learn", "pandas", "numpy",
        "huggingface", "langchain", "openai", "rag",
        # Data
        "data science", "data engineering", "etl", "airflow", "spark", "kafka",
        "hadoop", "snowflake", "databricks", "dbt", "looker", "tableau",
        # Other
        "api", "rest", "grpc", "microservices", "distributed systems",
        "event-driven", "serverless", "lambda", "agile", "scrum", "jira",
    }

    SOFT_SKILLS = {
        "leadership", "communication", "teamwork", "problem-solving",
        "analytical", "creative", "detail-oriented", "self-motivated",
        "collaboration", "mentoring", "project management", "stakeholder management",
        "presentation", "documentation", "time management", "adaptability",
    }

    EXPERIENCE_LEVELS = {
        "junior": (0, 2),
        "mid": (2, 5),
        "senior": (5, 8),
        "staff": (8, 12),
        "principal": (10, 15),
        "lead": (5, 10),
        "manager": (5, 12),
        "director": (10, 20),
    }

    def __init__(self, rag: ResumeRAG, data_dir: Path = None):
        self.rag = rag
        self.data_dir = data_dir or Path("data")
        self.history_file = self.data_dir / "job_history.json"
        self._ensure_data_dir()

    def _ensure_data_dir(self):
        """Ensure data directory exists"""
        self.data_dir.mkdir(parents=True, exist_ok=True)
        if not self.history_file.exists():
            self._save_history([])

    def _load_history(self) -> List[Dict]:
        """Load job match history from file"""
        try:
            if self.history_file.exists():
                return json.loads(self.history_file.read_text())
            return []
        except Exception as e:
            logger.error(f"Failed to load history: {e}")
            return []

    def _save_history(self, history: List[Dict]):
        """Save job match history to file"""
        try:
            self.history_file.write_text(json.dumps(history, indent=2, default=str))
        except Exception as e:
            logger.error(f"Failed to save history: {e}")

    async def extract_requirements(self, job_description: str) -> ExtractedRequirements:
        """Extract structured requirements from job description using LLM"""

        # Try LLM extraction first
        try:
            prompt = f"""Analyze this job description and extract the requirements in JSON format.

Job Description:
{job_description[:3000]}

Return a JSON object with these fields:
- required_skills: array of technical skills that are required/must-have
- preferred_skills: array of skills that are nice-to-have/preferred
- experience_years: number of years of experience required (integer or null)
- experience_level: one of "junior", "mid", "senior", "staff", "lead", "principal", "manager" or null
- education: education requirement as a string or null
- keywords: array of important ATS keywords from the job description
- responsibilities: array of key responsibilities (max 5)

Return ONLY valid JSON, no other text."""

            response = await self.rag.llm_backend.achat(prompt)

            # Try to parse JSON from response
            json_match = re.search(r'\{[\s\S]*\}', response.content)
            if json_match:
                data = json.loads(json_match.group())
                return ExtractedRequirements(
                    required_skills=data.get("required_skills", []),
                    preferred_skills=data.get("preferred_skills", []),
                    experience_years=data.get("experience_years"),
                    experience_level=data.get("experience_level"),
                    education=data.get("education"),
                    keywords=data.get("keywords", []),
                    responsibilities=data.get("responsibilities", []),
                )
        except Exception as e:
            logger.warning(f"LLM extraction failed, using fallback: {e}")

        # Fallback to rule-based extraction
        return self._extract_requirements_fallback(job_description)

    def _extract_requirements_fallback(self, job_description: str) -> ExtractedRequirements:
        """Fallback rule-based requirement extraction"""
        text_lower = job_description.lower()

        required_skills = []
        preferred_skills = []

        # Extract skills
        for skill in self.TECH_SKILLS | self.SOFT_SKILLS:
            if skill in text_lower:
                if self._is_required_context(job_description, skill):
                    required_skills.append(skill)
                else:
                    preferred_skills.append(skill)

        # Extract experience years
        experience_years = None
        years_match = re.search(r'(\d+)\+?\s*(?:years?|yrs?)\s*(?:of)?\s*experience', text_lower)
        if years_match:
            experience_years = int(years_match.group(1))

        # Extract experience level
        experience_level = None
        for level in self.EXPERIENCE_LEVELS:
            if level in text_lower:
                experience_level = level
                break

        # Extract education
        education = None
        edu_patterns = [
            r"(bachelor'?s?|master'?s?|phd|doctorate)\s*(degree)?\s*(in\s+[\w\s]+)?",
            r"(bs|ba|ms|ma|mba|phd)\s+(?:in\s+)?([\w\s]+)",
        ]
        for pattern in edu_patterns:
            match = re.search(pattern, text_lower)
            if match:
                education = match.group(0).strip()
                break

        # Extract keywords
        keywords = self._extract_keywords(job_description)

        # Extract responsibilities
        responsibilities = self._extract_section(job_description, [
            "responsibilities", "what you'll do", "you will", "duties"
        ])

        return ExtractedRequirements(
            required_skills=list(set(required_skills)),
            preferred_skills=list(set(preferred_skills)),
            experience_years=experience_years,
            experience_level=experience_level,
            education=education,
            keywords=keywords,
            responsibilities=responsibilities[:5],
        )

    def _is_required_context(self, text: str, skill: str) -> bool:
        """Check if skill appears in required context"""
        required_patterns = [
            rf"required[:\s].*?{re.escape(skill)}",
            rf"must have[:\s].*?{re.escape(skill)}",
            rf"essential[:\s].*?{re.escape(skill)}",
            rf"{re.escape(skill)}.*?required",
            rf"{re.escape(skill)}.*?\(required\)",
        ]
        text_lower = text.lower()
        return any(re.search(p, text_lower) for p in required_patterns)

    def _extract_keywords(self, text: str) -> List[str]:
        """Extract important keywords"""
        stop_words = {
            'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for',
            'of', 'with', 'by', 'from', 'as', 'is', 'was', 'are', 'were', 'been',
            'be', 'have', 'has', 'had', 'do', 'does', 'did', 'will', 'would',
            'could', 'should', 'may', 'might', 'must', 'shall', 'can', 'need',
            'we', 'you', 'your', 'our', 'their', 'this', 'that', 'these', 'those',
            'about', 'work', 'team', 'role', 'position', 'company', 'looking',
            'experience', 'ability', 'skills', 'knowledge', 'understanding',
        }

        words = re.findall(r'\b[a-zA-Z]{3,}\b', text.lower())
        word_counts = {}
        for word in words:
            if word not in stop_words:
                word_counts[word] = word_counts.get(word, 0) + 1

        keywords = [w for w, c in sorted(word_counts.items(), key=lambda x: -x[1]) if c >= 2]
        return keywords[:25]

    def _extract_section(self, text: str, headers: List[str]) -> List[str]:
        """Extract content from a section"""
        items = []
        lines = text.split('\n')
        in_section = False

        for line in lines:
            line_lower = line.lower().strip()

            if any(h in line_lower for h in headers):
                in_section = True
                continue

            if in_section and line_lower and line_lower[0].isupper() and ':' in line:
                in_section = False
                continue

            if in_section and line.strip():
                clean_line = re.sub(r'^[-•*]\s*', '', line.strip())
                if len(clean_line) > 15:
                    items.append(clean_line)

        return items[:10]

    async def match_skills(
        self,
        requirements: ExtractedRequirements,
        resume_context: str
    ) -> tuple[List[MatchedSkill], List[MissingSkill]]:
        """Match skills between job requirements and resume"""
        matched = []
        missing = []

        all_skills = [
            (skill, SkillImportance.REQUIRED) for skill in requirements.required_skills
        ] + [
            (skill, SkillImportance.PREFERRED) for skill in requirements.preferred_skills
        ]

        resume_lower = resume_context.lower()

        for skill, importance in all_skills:
            skill_lower = skill.lower()

            # Check for exact or fuzzy match
            if skill_lower in resume_lower:
                # Find context where skill appears
                context = None
                for sentence in resume_context.split('.'):
                    if skill_lower in sentence.lower():
                        context = sentence.strip()[:200]
                        break

                # Calculate relevance based on frequency and position
                count = resume_lower.count(skill_lower)
                relevance = min(0.5 + (count * 0.1), 1.0)

                matched.append(MatchedSkill(
                    skill=skill,
                    source="Resume",
                    relevance=relevance,
                    context=context
                ))
            else:
                # Check for related skills
                related = self._find_related_skills(skill_lower, resume_lower)

                suggestion = self._generate_skill_suggestion(skill, related)

                missing.append(MissingSkill(
                    skill=skill,
                    importance=importance,
                    suggestion=suggestion,
                    related_skills=related if related else None
                ))

        return matched, missing

    def _find_related_skills(self, skill: str, resume_text: str) -> List[str]:
        """Find related skills that might substitute"""
        skill_relations = {
            "kubernetes": ["docker", "containers", "k8s", "helm", "openshift"],
            "aws": ["cloud", "ec2", "s3", "lambda", "azure", "gcp"],
            "azure": ["cloud", "aws", "gcp", "microsoft"],
            "gcp": ["cloud", "aws", "azure", "google cloud"],
            "react": ["vue", "angular", "frontend", "javascript", "typescript"],
            "vue": ["react", "angular", "frontend", "javascript"],
            "angular": ["react", "vue", "frontend", "typescript"],
            "django": ["flask", "fastapi", "python", "web framework"],
            "flask": ["django", "fastapi", "python"],
            "fastapi": ["flask", "django", "python", "api"],
            "postgresql": ["mysql", "sql", "database", "postgres"],
            "mysql": ["postgresql", "sql", "database", "mariadb"],
            "mongodb": ["nosql", "database", "dynamodb"],
            "terraform": ["ansible", "cloudformation", "infrastructure as code", "iac"],
            "jenkins": ["github actions", "gitlab ci", "ci/cd", "circleci"],
            "pytorch": ["tensorflow", "deep learning", "machine learning", "keras"],
            "tensorflow": ["pytorch", "deep learning", "machine learning", "keras"],
        }

        related = []
        skill_lower = skill.lower()

        if skill_lower in skill_relations:
            for rel in skill_relations[skill_lower]:
                if rel in resume_text:
                    related.append(rel)

        return related[:3]

    def _generate_skill_suggestion(self, skill: str, related: List[str]) -> str:
        """Generate suggestion for addressing missing skill"""
        if related:
            return f"You have related experience with {', '.join(related)}. Highlight transferable knowledge."

        skill_lower = skill.lower()

        if skill_lower in self.TECH_SKILLS:
            return f"Consider adding {skill} to your skillset or highlighting any related project experience."
        elif skill_lower in self.SOFT_SKILLS:
            return f"Include examples that demonstrate your {skill} abilities in your experience section."
        else:
            return f"Research {skill} and consider how your existing experience relates to it."

    def calculate_scores(
        self,
        requirements: ExtractedRequirements,
        matched_skills: List[MatchedSkill],
        missing_skills: List[MissingSkill],
        resume_context: str
    ) -> ScoreBreakdown:
        """Calculate detailed match scores"""

        # Skills score
        total_skills = len(requirements.required_skills) + len(requirements.preferred_skills)
        if total_skills > 0:
            required_matched = sum(
                1 for m in matched_skills
                if m.skill in requirements.required_skills
            )
            preferred_matched = sum(
                1 for m in matched_skills
                if m.skill in requirements.preferred_skills
            )

            # Weight required skills more heavily
            required_weight = len(requirements.required_skills) * 2
            preferred_weight = len(requirements.preferred_skills)
            total_weight = required_weight + preferred_weight

            if total_weight > 0:
                weighted_matched = (required_matched * 2) + preferred_matched
                skills_score = (weighted_matched / total_weight) * 100
            else:
                skills_score = 100.0
        else:
            skills_score = 100.0

        # Experience score
        experience_score = 100.0
        if requirements.experience_years:
            # Check resume for experience indicators
            resume_lower = resume_context.lower()

            # Look for years mentioned
            year_patterns = re.findall(r'(\d+)\+?\s*(?:years?|yrs?)', resume_lower)
            max_years = max([int(y) for y in year_patterns]) if year_patterns else 0

            if max_years >= requirements.experience_years:
                experience_score = 100.0
            elif max_years >= requirements.experience_years * 0.7:
                experience_score = 80.0
            elif max_years >= requirements.experience_years * 0.5:
                experience_score = 60.0
            else:
                experience_score = 40.0

        # Education score
        education_score = 100.0
        if requirements.education:
            edu_lower = requirements.education.lower()
            resume_lower = resume_context.lower()

            edu_keywords = ["bachelor", "master", "phd", "doctorate", "degree", "bs", "ba", "ms", "mba"]
            has_edu = any(kw in resume_lower for kw in edu_keywords)

            if "phd" in edu_lower or "doctorate" in edu_lower:
                education_score = 100.0 if "phd" in resume_lower or "doctorate" in resume_lower else 60.0
            elif "master" in edu_lower:
                if "master" in resume_lower or "phd" in resume_lower:
                    education_score = 100.0
                elif "bachelor" in resume_lower:
                    education_score = 70.0
                else:
                    education_score = 50.0
            elif has_edu:
                education_score = 100.0
            else:
                education_score = 70.0  # Experience might substitute

        # Keywords score (ATS optimization)
        keywords_score = 100.0
        if requirements.keywords:
            resume_lower = resume_context.lower()
            matched_keywords = sum(1 for kw in requirements.keywords if kw.lower() in resume_lower)
            keywords_score = (matched_keywords / len(requirements.keywords)) * 100

        return ScoreBreakdown(
            skills_match=round(skills_score, 1),
            experience_match=round(experience_score, 1),
            education_match=round(education_score, 1),
            keywords_match=round(keywords_score, 1)
        )

    def generate_recommendations(
        self,
        requirements: ExtractedRequirements,
        matched_skills: List[MatchedSkill],
        missing_skills: List[MissingSkill],
        scores: ScoreBreakdown
    ) -> List[Recommendation]:
        """Generate actionable recommendations"""
        recommendations = []
        priority = 1

        # Critical missing skills
        required_missing = [m for m in missing_skills if m.importance == SkillImportance.REQUIRED]
        if required_missing:
            skills_list = ", ".join([m.skill for m in required_missing[:3]])
            recommendations.append(Recommendation(
                title="Address Required Skills Gap",
                description=f"The following required skills are not evident in your resume: {skills_list}. Consider highlighting any related experience or projects.",
                priority=priority,
                category="skills"
            ))
            priority += 1

        # Experience gap
        if scores.experience_match < 80:
            recommendations.append(Recommendation(
                title="Highlight Experience Duration",
                description="Your experience level may not be clear. Explicitly mention years of experience or total professional tenure in your summary.",
                priority=priority,
                category="experience"
            ))
            priority += 1

        # Keywords optimization
        if scores.keywords_match < 70:
            keywords_to_add = requirements.keywords[:5]
            recommendations.append(Recommendation(
                title="Improve ATS Keywords",
                description=f"Add these keywords to improve ATS matching: {', '.join(keywords_to_add)}",
                priority=priority,
                category="keywords"
            ))
            priority += 1

        # Leverage strengths
        if matched_skills:
            strong_skills = sorted(matched_skills, key=lambda x: -x.relevance)[:3]
            skills_list = ", ".join([s.skill for s in strong_skills])
            recommendations.append(Recommendation(
                title="Emphasize Your Strengths",
                description=f"Your resume strongly matches: {skills_list}. Lead with these in your summary and cover letter.",
                priority=priority,
                category="skills"
            ))
            priority += 1

        # Preferred skills opportunity
        preferred_missing = [m for m in missing_skills if m.importance == SkillImportance.PREFERRED][:2]
        if preferred_missing:
            skills_list = ", ".join([m.skill for m in preferred_missing])
            recommendations.append(Recommendation(
                title="Nice-to-Have Skills",
                description=f"Consider mentioning any experience with: {skills_list}. These could differentiate your application.",
                priority=priority,
                category="skills"
            ))

        return recommendations

    def _determine_quality(self, score: float) -> MatchQuality:
        """Determine match quality category"""
        if score >= 85:
            return MatchQuality.EXCELLENT
        elif score >= 70:
            return MatchQuality.GOOD
        elif score >= 50:
            return MatchQuality.FAIR
        else:
            return MatchQuality.POOR

    async def match(self, request: JobMatchRequest) -> JobMatchResponse:
        """Perform full job matching analysis"""
        import time
        start_time = time.time()

        match_id = f"match_{uuid.uuid4().hex[:12]}"

        # Extract requirements from job description
        requirements = await self.extract_requirements(request.job_description)

        # Get comprehensive resume context
        all_skills = requirements.required_skills + requirements.preferred_skills
        queries = [
            f"Skills and experience with: {', '.join(all_skills[:10])}",
            "Professional experience and achievements",
            "Education and certifications",
        ]

        resume_context = ""
        for query in queries:
            context = self.rag.retriever.get_context(query, n_results=5)
            resume_context += context + "\n\n"

        # Match skills
        matched_skills, missing_skills = await self.match_skills(requirements, resume_context)

        # Calculate scores
        scores = self.calculate_scores(requirements, matched_skills, missing_skills, resume_context)

        # Calculate overall score
        overall_score = scores.weighted_average

        # Generate recommendations
        recommendations = self.generate_recommendations(
            requirements, matched_skills, missing_skills, scores
        )

        # Determine quality
        quality = self._determine_quality(overall_score)

        # Create response
        response = JobMatchResponse(
            match_id=match_id,
            overall_score=round(overall_score, 1),
            quality=quality,
            scores=scores,
            requirements=requirements,
            matched_skills=matched_skills,
            missing_skills=missing_skills,
            recommendations=recommendations,
            job_title=request.job_title,
            company=request.company,
            job_url=request.job_url,
            analyzed_at=datetime.utcnow(),
        )

        # Save to history
        self._add_to_history(response)

        logger.info(f"Job match completed in {time.time() - start_time:.2f}s: {overall_score:.1f}%")

        return response

    async def batch_match(self, jobs: List[JobMatchRequest]) -> BatchJobMatchResponse:
        """Match resume against multiple jobs"""
        results = []

        for job in jobs:
            try:
                result = await self.match(job)
                results.append(result)
            except Exception as e:
                logger.error(f"Failed to match job: {e}")

        if not results:
            return BatchJobMatchResponse(
                results=[],
                total_jobs=len(jobs),
                average_score=0,
                best_match=None
            )

        average_score = sum(r.overall_score for r in results) / len(results)
        best_match = max(results, key=lambda x: x.overall_score)

        return BatchJobMatchResponse(
            results=results,
            total_jobs=len(jobs),
            average_score=round(average_score, 1),
            best_match=best_match
        )

    def _add_to_history(self, match: JobMatchResponse):
        """Add match to history"""
        history = self._load_history()

        item = {
            "match_id": match.match_id,
            "job_title": match.job_title,
            "company": match.company,
            "overall_score": match.overall_score,
            "quality": match.quality.value,
            "analyzed_at": match.analyzed_at.isoformat(),
            "job_url": match.job_url,
            "scores": match.scores.model_dump(),
            "matched_skills_count": len(match.matched_skills),
            "missing_skills_count": len(match.missing_skills),
            # Store skills for analytics
            "matched_skills": [s.skill for s in match.matched_skills],
            "missing_skills": [
                {"skill": s.skill, "importance": s.importance.value}
                for s in match.missing_skills
            ],
            "required_skills": match.requirements.required_skills,
            "preferred_skills": match.requirements.preferred_skills,
        }

        history.insert(0, item)
        history = history[:100]  # Keep last 100 matches

        self._save_history(history)

    def get_history(self, limit: int = 50) -> JobHistoryResponse:
        """Get job match history"""
        history = self._load_history()[:limit]

        if not history:
            return JobHistoryResponse(
                items=[],
                total_count=0,
                average_score=0,
                best_score=0,
                worst_score=0
            )

        items = [
            JobHistoryItem(
                match_id=h["match_id"],
                job_title=h.get("job_title"),
                company=h.get("company"),
                overall_score=h["overall_score"],
                quality=MatchQuality(h["quality"]),
                analyzed_at=datetime.fromisoformat(h["analyzed_at"]),
                job_url=h.get("job_url"),
            )
            for h in history
        ]

        scores = [h["overall_score"] for h in history]

        return JobHistoryResponse(
            items=items,
            total_count=len(history),
            average_score=round(sum(scores) / len(scores), 1),
            best_score=max(scores),
            worst_score=min(scores)
        )

    def get_match_by_id(self, match_id: str) -> Optional[Dict]:
        """Get a specific match from history"""
        history = self._load_history()
        for item in history:
            if item["match_id"] == match_id:
                return item
        return None

    def get_skills_analytics(self) -> SkillsAnalytics:
        """Analyze skills across all job matches"""
        history = self._load_history()

        if not history:
            return SkillsAnalytics()

        # Track skill frequencies
        skill_stats: Dict[str, Dict[str, int]] = {}

        for item in history:
            # Get all required/preferred skills from this job
            all_required = item.get("required_skills", []) + [
                s["skill"] for s in item.get("missing_skills", [])
                if s.get("importance") == "required"
            ]
            all_preferred = item.get("preferred_skills", [])
            matched = item.get("matched_skills", [])

            # Process each skill
            for skill in set(all_required + all_preferred):
                skill_lower = skill.lower()
                if skill_lower not in skill_stats:
                    skill_stats[skill_lower] = {
                        "skill": skill,
                        "times_required": 0,
                        "times_matched": 0,
                    }

                skill_stats[skill_lower]["times_required"] += 1
                if skill in matched:
                    skill_stats[skill_lower]["times_matched"] += 1

        # Convert to SkillFrequency objects
        frequencies = []
        for stats in skill_stats.values():
            if stats["times_required"] > 0:
                match_rate = (stats["times_matched"] / stats["times_required"]) * 100
                frequencies.append(SkillFrequency(
                    skill=stats["skill"],
                    times_required=stats["times_required"],
                    times_matched=stats["times_matched"],
                    match_rate=round(match_rate, 1)
                ))

        # Sort for different categories
        by_match_rate = sorted(frequencies, key=lambda x: -x.match_rate)
        by_required = sorted(frequencies, key=lambda x: -x.times_required)
        by_weakness = sorted(
            [f for f in frequencies if f.match_rate < 50],
            key=lambda x: x.match_rate
        )

        # Identify improvement areas
        improvement_areas = [
            f.skill for f in by_weakness[:5]
            if f.times_required >= 2  # Only skills requested multiple times
        ]

        return SkillsAnalytics(
            strongest_skills=by_match_rate[:10],
            weakest_skills=by_weakness[:10],
            most_requested=by_required[:10],
            improvement_areas=improvement_areas
        )
