"""Job Analyzer service for matching resumes to job descriptions"""

import re
import logging
from typing import Optional
from dataclasses import dataclass

from src.rag import ResumeRAG
from ..models.responses import AnalysisResponse, MatchResult, GapAnalysis

logger = logging.getLogger(__name__)


@dataclass
class ParsedJob:
    """Parsed job description"""
    title: Optional[str]
    company: Optional[str]
    required_skills: list[str]
    preferred_skills: list[str]
    responsibilities: list[str]
    requirements: list[str]
    keywords: list[str]


class AnalyzerService:
    """Service for analyzing job descriptions against resume"""

    # Common skill keywords to look for
    TECH_SKILLS = [
        "python", "javascript", "typescript", "java", "c++", "c#", "go", "rust",
        "react", "vue", "angular", "node", "django", "flask", "fastapi", "spring",
        "sql", "postgresql", "mysql", "mongodb", "redis", "elasticsearch",
        "aws", "azure", "gcp", "docker", "kubernetes", "terraform",
        "git", "ci/cd", "jenkins", "github actions",
        "machine learning", "ml", "ai", "deep learning", "nlp", "computer vision",
        "data science", "pandas", "numpy", "pytorch", "tensorflow",
        "api", "rest", "graphql", "microservices", "distributed systems",
        "agile", "scrum", "jira", "confluence",
    ]

    SOFT_SKILLS = [
        "leadership", "communication", "teamwork", "problem-solving",
        "analytical", "creative", "detail-oriented", "self-motivated",
        "collaboration", "mentoring", "project management",
    ]

    def __init__(self, rag: ResumeRAG):
        self.rag = rag

    def parse_job_description(self, job_description: str) -> ParsedJob:
        """Parse a job description to extract key information"""
        text_lower = job_description.lower()

        # Extract skills mentioned
        required_skills = []
        preferred_skills = []

        for skill in self.TECH_SKILLS + self.SOFT_SKILLS:
            if skill in text_lower:
                # Check if it's in a "required" context
                if self._is_required_skill(job_description, skill):
                    required_skills.append(skill)
                else:
                    preferred_skills.append(skill)

        # Extract requirements (lines with years of experience, degree, etc.)
        requirements = self._extract_requirements(job_description)

        # Extract responsibilities
        responsibilities = self._extract_section(job_description, [
            "responsibilities", "what you'll do", "role", "duties"
        ])

        # Extract keywords (unique terms that appear multiple times)
        keywords = self._extract_keywords(job_description)

        # Try to extract title and company
        title = self._extract_title(job_description)
        company = self._extract_company(job_description)

        return ParsedJob(
            title=title,
            company=company,
            required_skills=list(set(required_skills)),
            preferred_skills=list(set(preferred_skills)),
            responsibilities=responsibilities,
            requirements=requirements,
            keywords=keywords,
        )

    def _is_required_skill(self, text: str, skill: str) -> bool:
        """Check if a skill appears in a required context"""
        required_patterns = [
            r"required[:\s].*?" + re.escape(skill),
            r"must have[:\s].*?" + re.escape(skill),
            r"essential[:\s].*?" + re.escape(skill),
            skill + r".*?required",
            skill + r".*?must",
        ]
        text_lower = text.lower()
        return any(re.search(p, text_lower) for p in required_patterns)

    def _extract_requirements(self, text: str) -> list[str]:
        """Extract requirement statements"""
        requirements = []
        lines = text.split('\n')

        requirement_patterns = [
            r'\d+\+?\s*years?\s*(of)?\s*experience',
            r"bachelor'?s?|master'?s?|phd|degree",
            r'must have|required|essential',
            r'proficient in|expertise in|strong knowledge',
        ]

        for line in lines:
            line = line.strip()
            if not line:
                continue
            line_lower = line.lower()
            if any(re.search(p, line_lower) for p in requirement_patterns):
                # Clean up the line
                clean_line = re.sub(r'^[-•*]\s*', '', line)
                if len(clean_line) > 10:
                    requirements.append(clean_line)

        return requirements[:10]  # Limit to top 10

    def _extract_section(self, text: str, headers: list[str]) -> list[str]:
        """Extract content from a section"""
        items = []
        lines = text.split('\n')
        in_section = False

        for line in lines:
            line_lower = line.lower().strip()

            # Check if we're entering the section
            if any(h in line_lower for h in headers):
                in_section = True
                continue

            # Check if we're leaving the section
            if in_section and line_lower and line_lower[0].isupper() and ':' in line:
                in_section = False
                continue

            # Collect items in the section
            if in_section and line.strip():
                clean_line = re.sub(r'^[-•*]\s*', '', line.strip())
                if len(clean_line) > 10:
                    items.append(clean_line)

        return items[:10]

    def _extract_keywords(self, text: str) -> list[str]:
        """Extract important keywords from job description"""
        # Remove common words
        stop_words = {
            'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for',
            'of', 'with', 'by', 'from', 'as', 'is', 'was', 'are', 'were', 'been',
            'be', 'have', 'has', 'had', 'do', 'does', 'did', 'will', 'would',
            'could', 'should', 'may', 'might', 'must', 'shall', 'can', 'need',
            'we', 'you', 'your', 'our', 'their', 'this', 'that', 'these', 'those',
            'it', 'its', 'they', 'them', 'he', 'she', 'him', 'her', 'his',
            'who', 'which', 'what', 'where', 'when', 'why', 'how', 'all', 'each',
            'every', 'both', 'few', 'more', 'most', 'other', 'some', 'such', 'no',
            'not', 'only', 'own', 'same', 'so', 'than', 'too', 'very', 'just',
            'about', 'across', 'after', 'before', 'between', 'into', 'through',
            'during', 'above', 'below', 'up', 'down', 'out', 'off', 'over', 'under',
        }

        # Extract words
        words = re.findall(r'\b[a-zA-Z]{3,}\b', text.lower())
        word_counts = {}
        for word in words:
            if word not in stop_words:
                word_counts[word] = word_counts.get(word, 0) + 1

        # Get words that appear multiple times
        keywords = [w for w, c in sorted(word_counts.items(), key=lambda x: -x[1]) if c >= 2]
        return keywords[:20]

    def _extract_title(self, text: str) -> Optional[str]:
        """Try to extract job title"""
        lines = text.split('\n')
        for line in lines[:5]:
            line = line.strip()
            if line and len(line) < 100:
                # Check if it looks like a title
                title_patterns = [
                    r'(senior|junior|lead|principal|staff)?\s*(software|data|ml|devops|platform|backend|frontend|full.?stack)\s*(engineer|developer|scientist)',
                    r'engineering\s*manager',
                    r'technical\s*(lead|architect)',
                ]
                for pattern in title_patterns:
                    match = re.search(pattern, line.lower())
                    if match:
                        return line
        return None

    def _extract_company(self, text: str) -> Optional[str]:
        """Try to extract company name"""
        patterns = [
            r'at\s+([A-Z][a-zA-Z]+(?:\s+[A-Z][a-zA-Z]+)?)',
            r'company:\s*([A-Za-z]+(?:\s+[A-Za-z]+)?)',
            r'([A-Z][a-zA-Z]+(?:\s+[A-Z][a-zA-Z]+)?)\s+is\s+(?:looking|hiring|seeking)',
        ]
        for pattern in patterns:
            match = re.search(pattern, text)
            if match:
                return match.group(1)
        return None

    async def analyze(
        self,
        job_description: str,
        focus_areas: list[str] = None
    ) -> AnalysisResponse:
        """Analyze job description against resume"""
        import time
        start_time = time.time()

        # Parse job description
        parsed = self.parse_job_description(job_description)

        # Get resume context for analysis
        all_skills = parsed.required_skills + parsed.preferred_skills
        skill_query = f"What skills and experience do I have related to: {', '.join(all_skills[:10])}"

        resume_context = self.rag.retriever.get_context(skill_query, n_results=10)

        # Analyze skill matches
        matching_skills = []
        for skill in all_skills:
            matched = skill.lower() in resume_context.lower()
            evidence = None
            if matched:
                # Find the relevant sentence
                for sentence in resume_context.split('.'):
                    if skill.lower() in sentence.lower():
                        evidence = sentence.strip()[:150]
                        break

            matching_skills.append(MatchResult(
                item=skill,
                matched=matched,
                resume_evidence=evidence
            ))

        # Analyze gaps
        gaps = []
        for req in parsed.requirements:
            # Check if requirement is met
            req_lower = req.lower()
            status = "met"
            suggestion = None

            # Check for years of experience
            years_match = re.search(r'(\d+)\+?\s*years?', req_lower)
            if years_match:
                required_years = int(years_match.group(1))
                # Use RAG to check experience
                exp_check = self.rag.retriever.get_context(
                    "How many years of experience do I have?", n_results=3
                )
                if str(required_years) not in exp_check and str(required_years - 1) not in exp_check:
                    status = "partial"
                    suggestion = f"Highlight relevant experience that demonstrates {required_years}+ years equivalent"

            # Check for degree requirements
            if 'degree' in req_lower or "bachelor" in req_lower or "master" in req_lower:
                edu_check = self.rag.retriever.get_context("education degree", n_results=2)
                if 'degree' not in edu_check.lower() and 'bachelor' not in edu_check.lower():
                    status = "partial"
                    suggestion = "Emphasize equivalent experience or certifications"

            # Check for skill requirements
            for skill in self.TECH_SKILLS:
                if skill in req_lower and skill not in resume_context.lower():
                    status = "missing"
                    suggestion = f"Consider highlighting experience with {skill} or related technologies"
                    break

            gaps.append(GapAnalysis(
                requirement=req,
                status=status,
                suggestion=suggestion
            ))

        # Calculate match score
        matched_count = sum(1 for m in matching_skills if m.matched)
        total_skills = len(matching_skills) if matching_skills else 1
        skill_score = (matched_count / total_skills) * 100

        met_requirements = sum(1 for g in gaps if g.status == "met")
        partial_requirements = sum(1 for g in gaps if g.status == "partial")
        total_requirements = len(gaps) if gaps else 1
        req_score = ((met_requirements + partial_requirements * 0.5) / total_requirements) * 100

        match_score = (skill_score * 0.6 + req_score * 0.4)

        # Generate keywords to add
        keywords_to_add = [
            kw for kw in parsed.keywords
            if kw not in resume_context.lower() and kw in [s.lower() for s in all_skills]
        ][:10]

        # Generate suggestions using LLM
        suggestions = await self._generate_suggestions(
            job_description, resume_context, matching_skills, gaps
        )

        # Generate summary
        summary = self._generate_summary(match_score, matching_skills, gaps, parsed)

        processing_time = int((time.time() - start_time) * 1000)

        return AnalysisResponse(
            match_score=round(match_score, 1),
            matching_skills=matching_skills,
            gaps=gaps,
            keywords_to_add=keywords_to_add,
            suggestions=suggestions,
            summary=summary,
            processing_time_ms=processing_time,
        )

    async def _generate_suggestions(
        self,
        job_description: str,
        resume_context: str,
        matching_skills: list[MatchResult],
        gaps: list[GapAnalysis]
    ) -> list[str]:
        """Generate actionable suggestions"""
        suggestions = []

        # Skill-based suggestions
        missing_skills = [m.item for m in matching_skills if not m.matched]
        if missing_skills:
            suggestions.append(
                f"Consider adding related experience for: {', '.join(missing_skills[:5])}"
            )

        # Gap-based suggestions
        missing_reqs = [g for g in gaps if g.status == "missing"]
        if missing_reqs:
            suggestions.append(
                "Address missing requirements by highlighting transferable skills"
            )

        # General suggestions
        matched_skills = [m.item for m in matching_skills if m.matched]
        if matched_skills:
            suggestions.append(
                f"Emphasize your strongest matches: {', '.join(matched_skills[:5])}"
            )

        # Try to get LLM-generated suggestions
        try:
            prompt = f"""Based on this job description and resume context, give 2-3 specific suggestions for improving the application.

Job Description (excerpt):
{job_description[:1000]}

Resume Context:
{resume_context[:1000]}

Provide brief, actionable suggestions (one sentence each):"""

            llm_suggestions = self.rag.llm_backend.generate(prompt)
            if llm_suggestions:
                # Parse suggestions from response
                for line in llm_suggestions.split('\n'):
                    line = line.strip()
                    if line and len(line) > 20 and not line.startswith('#'):
                        clean = re.sub(r'^[\d\.\-\*]+\s*', '', line)
                        if clean:
                            suggestions.append(clean)

        except Exception as e:
            logger.warning(f"Failed to generate LLM suggestions: {e}")

        return suggestions[:7]  # Limit suggestions

    def _generate_summary(
        self,
        match_score: float,
        matching_skills: list[MatchResult],
        gaps: list[GapAnalysis],
        parsed: ParsedJob
    ) -> str:
        """Generate a summary of the analysis"""
        matched_count = sum(1 for m in matching_skills if m.matched)
        total_skills = len(matching_skills)

        if match_score >= 80:
            strength = "excellent"
        elif match_score >= 60:
            strength = "good"
        elif match_score >= 40:
            strength = "moderate"
        else:
            strength = "limited"

        title_str = f"for {parsed.title}" if parsed.title else "for this role"

        summary = f"Your resume shows {strength} alignment {title_str} ({match_score:.0f}% match). "
        summary += f"You match {matched_count} of {total_skills} key skills. "

        missing_gaps = [g for g in gaps if g.status == "missing"]
        if missing_gaps:
            summary += f"There are {len(missing_gaps)} requirements that need attention."
        else:
            summary += "All key requirements appear to be addressed."

        return summary
