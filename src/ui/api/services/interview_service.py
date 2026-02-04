"""Interview Prep service for generating STAR stories and practice feedback"""

import json
import logging
import random
from pathlib import Path
from typing import Optional
from dataclasses import dataclass

from src.rag import ResumeRAG
from ..models.responses import InterviewQuestion, StarStory, PracticeFeedback

logger = logging.getLogger(__name__)


@dataclass
class QuestionBank:
    """Container for interview questions"""
    questions: list[dict]
    categories: list[dict]
    role_types: list[dict]


class InterviewService:
    """Service for interview preparation"""

    def __init__(self, rag: ResumeRAG):
        self.rag = rag
        self._question_bank: Optional[QuestionBank] = None

    def _load_questions(self) -> QuestionBank:
        """Load question bank from JSON file"""
        if self._question_bank is None:
            data_path = Path(__file__).parent.parent / "data" / "questions.json"
            try:
                with open(data_path, 'r') as f:
                    data = json.load(f)
                self._question_bank = QuestionBank(
                    questions=data.get("questions", []),
                    categories=data.get("categories", []),
                    role_types=data.get("role_types", []),
                )
            except Exception as e:
                logger.error(f"Failed to load questions: {e}")
                self._question_bank = QuestionBank([], [], [])

        return self._question_bank

    def get_questions(
        self,
        category: Optional[str] = None,
        role_type: Optional[str] = None,
        difficulty: Optional[str] = None,
        limit: int = 10,
    ) -> list[InterviewQuestion]:
        """Get filtered list of interview questions"""
        bank = self._load_questions()
        questions = bank.questions

        # Apply filters
        if category:
            questions = [q for q in questions if q.get("category") == category]

        if role_type:
            questions = [
                q for q in questions
                if role_type in q.get("role_types", [])
            ]

        if difficulty:
            questions = [q for q in questions if q.get("difficulty") == difficulty]

        # Shuffle and limit
        random.shuffle(questions)
        questions = questions[:limit]

        return [
            InterviewQuestion(
                id=q["id"],
                question=q["question"],
                category=q["category"],
                role_types=q.get("role_types", []),
                difficulty=q.get("difficulty", "medium"),
                tips=q.get("tips"),
            )
            for q in questions
        ]

    def get_categories(self) -> list[dict]:
        """Get list of question categories"""
        bank = self._load_questions()
        return bank.categories

    def get_role_types(self) -> list[dict]:
        """Get list of role types"""
        bank = self._load_questions()
        return bank.role_types

    async def generate_star_story(
        self,
        situation: str,
        question_context: Optional[str] = None,
    ) -> StarStory:
        """Generate a STAR story from a situation description"""
        # Get relevant resume context
        resume_context = self.rag.retriever.get_context(
            f"experience achievement: {situation}",
            n_results=5
        )

        # Build prompt for STAR story generation
        prompt = f"""Generate a STAR story based on the following situation from my resume.

Situation/Achievement to expand:
{situation}

Resume Context:
{resume_context}

{"Question this story should answer: " + question_context if question_context else ""}

Please structure the response as a complete STAR story:

SITUATION: Set the context - where, when, what was the challenge or goal

TASK: What was your specific responsibility or objective

ACTION: What specific steps did you take (use "I" statements, be specific)

RESULT: What was the outcome (quantify if possible - numbers, percentages, impact)

Make it detailed but concise (2-3 sentences per section). Use specific details from the resume context."""

        try:
            response = self.rag.llm_backend.generate(prompt)

            # Parse the STAR components
            star = self._parse_star_response(response)

            # Identify questions this story could answer
            question_fit = self._identify_question_fit(situation, star)

            return StarStory(
                situation=star.get("situation", ""),
                task=star.get("task", ""),
                action=star.get("action", ""),
                result=star.get("result", ""),
                question_fit=question_fit,
            )

        except Exception as e:
            logger.error(f"Failed to generate STAR story: {e}")
            # Return a basic structure
            return StarStory(
                situation=f"In my role, I encountered: {situation}",
                task="I was responsible for addressing this challenge.",
                action="I took the following steps to resolve the situation.",
                result="This resulted in a positive outcome for the team/company.",
                question_fit=None,
            )

    def _parse_star_response(self, response: str) -> dict:
        """Parse STAR components from LLM response"""
        star = {
            "situation": "",
            "task": "",
            "action": "",
            "result": "",
        }

        current_section = None
        current_text = []

        for line in response.split('\n'):
            line = line.strip()
            if not line:
                continue

            line_upper = line.upper()

            # Check for section headers
            if line_upper.startswith("SITUATION"):
                if current_section and current_text:
                    star[current_section] = ' '.join(current_text)
                current_section = "situation"
                current_text = []
                # Get text after the header
                text_after = line.split(':', 1)[-1].strip()
                if text_after:
                    current_text.append(text_after)

            elif line_upper.startswith("TASK"):
                if current_section and current_text:
                    star[current_section] = ' '.join(current_text)
                current_section = "task"
                current_text = []
                text_after = line.split(':', 1)[-1].strip()
                if text_after:
                    current_text.append(text_after)

            elif line_upper.startswith("ACTION"):
                if current_section and current_text:
                    star[current_section] = ' '.join(current_text)
                current_section = "action"
                current_text = []
                text_after = line.split(':', 1)[-1].strip()
                if text_after:
                    current_text.append(text_after)

            elif line_upper.startswith("RESULT"):
                if current_section and current_text:
                    star[current_section] = ' '.join(current_text)
                current_section = "result"
                current_text = []
                text_after = line.split(':', 1)[-1].strip()
                if text_after:
                    current_text.append(text_after)

            elif current_section:
                current_text.append(line)

        # Don't forget the last section
        if current_section and current_text:
            star[current_section] = ' '.join(current_text)

        return star

    def _identify_question_fit(self, situation: str, star: dict) -> list[str]:
        """Identify interview questions this story could answer"""
        bank = self._load_questions()
        fitting_questions = []

        keywords = {
            "challenge": ["difficult", "challenge", "obstacle", "problem"],
            "deadline": ["deadline", "time", "pressure", "urgent"],
            "mistake": ["mistake", "error", "failure", "wrong"],
            "team": ["team", "collaboration", "conflict", "disagreement"],
            "leadership": ["lead", "mentor", "manage", "guide"],
            "learning": ["learn", "new", "technology", "skill"],
            "improvement": ["improve", "optimize", "efficient", "better"],
            "achievement": ["proud", "success", "accomplish", "achieve"],
        }

        story_text = f"{situation} {star.get('situation', '')} {star.get('action', '')} {star.get('result', '')}".lower()

        for q in bank.questions:
            if q.get("category") != "behavioral":
                continue

            q_text = q["question"].lower()
            for theme, kws in keywords.items():
                if any(kw in story_text for kw in kws) and any(kw in q_text for kw in kws):
                    fitting_questions.append(q["question"])
                    break

        return fitting_questions[:5]

    async def evaluate_practice_answer(
        self,
        question_id: str,
        question_text: str,
        user_answer: str,
    ) -> PracticeFeedback:
        """Evaluate a practice interview answer"""
        # Get the question details
        bank = self._load_questions()
        question = next(
            (q for q in bank.questions if q["id"] == question_id),
            None
        )

        is_behavioral = question and question.get("category") == "behavioral"

        # Get resume context for relevance check
        resume_context = self.rag.retriever.get_context(
            "skills experience achievements",
            n_results=5
        )

        # Build evaluation prompt
        prompt = f"""Evaluate this interview answer and provide constructive feedback.

Question: {question_text}

Answer: {user_answer}

Resume Context (for relevance check):
{resume_context}

Evaluate the answer on these criteria:
1. RELEVANCE: Does it directly answer the question? Does it use relevant experience?
2. STRUCTURE: {"Is it in STAR format (Situation, Task, Action, Result)?" if is_behavioral else "Is it well-organized and clear?"}
3. SPECIFICITY: Are there specific examples, numbers, or concrete details?

For each criterion, provide:
- A brief assessment (1-2 sentences)
- Score out of 100

Then provide:
- 2-3 specific improvements
- 2-3 strengths

Format your response as:
RELEVANCE: [assessment]
RELEVANCE_SCORE: [number]
STRUCTURE: [assessment]
STRUCTURE_SCORE: [number]
SPECIFICITY: [assessment]
SPECIFICITY_SCORE: [number]
IMPROVEMENTS: [bullet points]
STRENGTHS: [bullet points]"""

        try:
            response = self.rag.llm_backend.generate(prompt)
            feedback = self._parse_feedback_response(response)
            return feedback

        except Exception as e:
            logger.error(f"Failed to evaluate answer: {e}")
            return PracticeFeedback(
                score=70,
                relevance_feedback="Unable to fully evaluate relevance.",
                structure_feedback="Answer structure could not be analyzed.",
                specificity_feedback="Consider adding more specific details.",
                improvements=["Add more specific examples", "Quantify results when possible"],
                strengths=["Addressed the question"],
            )

    def _parse_feedback_response(self, response: str) -> PracticeFeedback:
        """Parse feedback from LLM response"""
        lines = response.split('\n')

        relevance = ""
        structure = ""
        specificity = ""
        relevance_score = 70
        structure_score = 70
        specificity_score = 70
        improvements = []
        strengths = []

        current_list = None

        for line in lines:
            line = line.strip()
            if not line:
                continue

            line_upper = line.upper()

            if line_upper.startswith("RELEVANCE:"):
                relevance = line.split(':', 1)[-1].strip()
            elif line_upper.startswith("RELEVANCE_SCORE:"):
                try:
                    relevance_score = int(''.join(c for c in line if c.isdigit())[:3])
                except:
                    pass
            elif line_upper.startswith("STRUCTURE:"):
                structure = line.split(':', 1)[-1].strip()
            elif line_upper.startswith("STRUCTURE_SCORE:"):
                try:
                    structure_score = int(''.join(c for c in line if c.isdigit())[:3])
                except:
                    pass
            elif line_upper.startswith("SPECIFICITY:"):
                specificity = line.split(':', 1)[-1].strip()
            elif line_upper.startswith("SPECIFICITY_SCORE:"):
                try:
                    specificity_score = int(''.join(c for c in line if c.isdigit())[:3])
                except:
                    pass
            elif line_upper.startswith("IMPROVEMENTS:"):
                current_list = "improvements"
            elif line_upper.startswith("STRENGTHS:"):
                current_list = "strengths"
            elif current_list and (line.startswith("-") or line.startswith("•") or line.startswith("*")):
                item = line.lstrip("-•* ").strip()
                if current_list == "improvements":
                    improvements.append(item)
                else:
                    strengths.append(item)

        # Calculate overall score
        overall_score = (relevance_score + structure_score + specificity_score) / 3

        return PracticeFeedback(
            score=round(overall_score, 1),
            relevance_feedback=relevance or "Consider how well your answer addresses the question.",
            structure_feedback=structure or "Review the structure and flow of your answer.",
            specificity_feedback=specificity or "Add more specific details and examples.",
            improvements=improvements[:5] or ["Add more specific examples", "Quantify your results"],
            strengths=strengths[:5] or ["Good attempt at answering the question"],
        )

    async def research_company(self, company_name: str) -> dict:
        """Research a company for interview preparation"""
        # This would ideally use web search, but for now we return a template
        return {
            "company": company_name,
            "note": "Company research requires web search integration.",
            "suggestions": [
                f"Research {company_name}'s recent news and announcements",
                f"Review {company_name}'s mission, values, and culture",
                f"Look up {company_name} on Glassdoor for interview insights",
                f"Check {company_name}'s engineering blog if available",
                "Prepare questions about the team and role",
            ],
        }
