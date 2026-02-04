"""RAG Evaluation Framework with RAGAS Integration"""

from typing import List, Dict, Any, Optional, TYPE_CHECKING
from dataclasses import dataclass, field
from pathlib import Path
import json
import asyncio

if TYPE_CHECKING:
    from ..llm_backends import LLMRouter


@dataclass
class EvaluationScores:
    """Scores from RAG evaluation"""
    faithfulness: float = 0.0       # Is answer grounded in context?
    answer_relevancy: float = 0.0   # Does answer address the question?
    context_precision: float = 0.0  # Is retrieved context relevant?
    context_recall: float = 0.0     # Is all needed info retrieved?
    overall: float = 0.0            # Weighted average


@dataclass
class TestCase:
    """A test case for RAG evaluation"""
    question: str
    ground_truth: str
    expected_sections: List[str] = field(default_factory=list)
    category: str = "general"


@dataclass
class EvaluationResult:
    """Result of evaluating a single RAG response"""
    test_case: TestCase
    generated_answer: str
    retrieved_contexts: List[str]
    scores: EvaluationScores
    passed: bool


@dataclass
class BenchmarkResult:
    """Result of benchmarking a RAG system"""
    total_tests: int
    passed_tests: int
    average_scores: EvaluationScores
    results_by_category: Dict[str, EvaluationScores]
    individual_results: List[EvaluationResult]


class RAGEvaluator:
    """
    RAG Evaluation Framework.

    Provides evaluation capabilities using RAGAS-style metrics:
    - Faithfulness: Is the answer grounded in the provided context?
    - Answer Relevancy: Does the answer address the question?
    - Context Precision: Is the retrieved context relevant to the question?
    - Context Recall: Does the context contain all information needed?

    Can be used with or without the RAGAS library:
    - With RAGAS: Uses official implementation for accurate metrics
    - Without RAGAS: Uses simplified heuristic-based evaluation

    Benefits:
    - Enables measurement of RAG improvements
    - Identifies weak areas (retrieval vs generation)
    - Provides baseline for A/B testing
    """

    # Default passing thresholds
    DEFAULT_THRESHOLDS = {
        "faithfulness": 0.8,
        "answer_relevancy": 0.7,
        "context_precision": 0.6,
        "context_recall": 0.6,
        "overall": 0.7
    }

    def __init__(
        self,
        llm_router: Optional["LLMRouter"] = None,
        use_ragas: bool = True,
        thresholds: Optional[Dict[str, float]] = None
    ):
        """
        Initialize RAG evaluator.

        Args:
            llm_router: LLM router for evaluation (required for some metrics)
            use_ragas: Whether to use RAGAS library (falls back to heuristics if unavailable)
            thresholds: Custom passing thresholds for metrics
        """
        self._llm_router = llm_router
        self.use_ragas = use_ragas
        self.thresholds = thresholds or self.DEFAULT_THRESHOLDS
        self._ragas_available = None

    @property
    def llm_router(self) -> "LLMRouter":
        """Lazy-load LLM router"""
        if self._llm_router is None:
            from ..llm_backends import LLMRouter
            self._llm_router = LLMRouter()
        return self._llm_router

    @property
    def ragas_available(self) -> bool:
        """Check if RAGAS library is available"""
        if self._ragas_available is None:
            try:
                import ragas
                self._ragas_available = True
            except ImportError:
                self._ragas_available = False
        return self._ragas_available

    def _calculate_faithfulness_heuristic(
        self,
        answer: str,
        contexts: List[str]
    ) -> float:
        """
        Heuristic faithfulness calculation.

        Checks what percentage of answer terms appear in context.
        """
        if not answer or not contexts:
            return 0.0

        # Combine contexts
        context_text = " ".join(contexts).lower()

        # Extract significant words from answer (4+ chars)
        answer_words = set(
            word.lower() for word in answer.split()
            if len(word) >= 4 and word.isalpha()
        )

        if not answer_words:
            return 1.0  # No significant words to verify

        # Count how many appear in context
        found = sum(1 for word in answer_words if word in context_text)

        return found / len(answer_words)

    def _calculate_relevancy_heuristic(
        self,
        question: str,
        answer: str
    ) -> float:
        """
        Heuristic answer relevancy calculation.

        Checks if answer addresses key terms from question.
        """
        if not question or not answer:
            return 0.0

        # Extract key terms from question
        question_words = set(
            word.lower() for word in question.split()
            if len(word) >= 4 and word.isalpha()
        )

        # Remove common question words
        stop_words = {"what", "where", "when", "which", "would", "could", "should", "have", "does", "about", "with"}
        question_words -= stop_words

        if not question_words:
            return 1.0  # No key terms to match

        answer_lower = answer.lower()

        # Count how many question terms appear in answer
        found = sum(1 for word in question_words if word in answer_lower)

        return found / len(question_words)

    def _calculate_context_precision_heuristic(
        self,
        question: str,
        contexts: List[str]
    ) -> float:
        """
        Heuristic context precision calculation.

        Checks if retrieved contexts contain question terms.
        """
        if not question or not contexts:
            return 0.0

        question_lower = question.lower()
        question_words = set(
            word for word in question_lower.split()
            if len(word) >= 4 and word.isalpha()
        )

        # Remove common words
        stop_words = {"what", "where", "when", "which", "would", "could", "should", "have", "does", "about", "with"}
        question_words -= stop_words

        if not question_words:
            return 1.0

        # Check each context for relevance
        relevant_contexts = 0
        for ctx in contexts:
            ctx_lower = ctx.lower()
            matches = sum(1 for word in question_words if word in ctx_lower)
            if matches / len(question_words) >= 0.3:
                relevant_contexts += 1

        return relevant_contexts / len(contexts) if contexts else 0.0

    def _calculate_context_recall_heuristic(
        self,
        ground_truth: str,
        contexts: List[str]
    ) -> float:
        """
        Heuristic context recall calculation.

        Checks if contexts contain information from ground truth.
        """
        if not ground_truth or not contexts:
            return 0.0

        # Extract key terms from ground truth
        truth_words = set(
            word.lower() for word in ground_truth.split()
            if len(word) >= 4 and word.isalpha()
        )

        if not truth_words:
            return 1.0

        # Combine contexts
        context_text = " ".join(contexts).lower()

        # Count how many ground truth terms appear in context
        found = sum(1 for word in truth_words if word in context_text)

        return found / len(truth_words)

    def evaluate_single(
        self,
        question: str,
        answer: str,
        contexts: List[str],
        ground_truth: Optional[str] = None
    ) -> EvaluationScores:
        """
        Evaluate a single RAG response.

        Args:
            question: The user's question
            answer: The generated answer
            contexts: Retrieved context chunks
            ground_truth: Expected answer (optional, improves recall metric)

        Returns:
            EvaluationScores with all metrics
        """
        # Try RAGAS evaluation first
        if self.use_ragas and self.ragas_available:
            try:
                return self._evaluate_with_ragas(question, answer, contexts, ground_truth)
            except Exception as e:
                print(f"RAGAS evaluation failed, using heuristics: {e}")

        # Fall back to heuristic evaluation
        faithfulness = self._calculate_faithfulness_heuristic(answer, contexts)
        relevancy = self._calculate_relevancy_heuristic(question, answer)
        precision = self._calculate_context_precision_heuristic(question, contexts)

        # Recall requires ground truth
        if ground_truth:
            recall = self._calculate_context_recall_heuristic(ground_truth, contexts)
        else:
            recall = precision  # Approximate with precision if no ground truth

        # Calculate overall score (weighted average)
        overall = (
            faithfulness * 0.3 +
            relevancy * 0.3 +
            precision * 0.2 +
            recall * 0.2
        )

        return EvaluationScores(
            faithfulness=faithfulness,
            answer_relevancy=relevancy,
            context_precision=precision,
            context_recall=recall,
            overall=overall
        )

    def _evaluate_with_ragas(
        self,
        question: str,
        answer: str,
        contexts: List[str],
        ground_truth: Optional[str] = None
    ) -> EvaluationScores:
        """
        Evaluate using RAGAS library.

        Note: RAGAS requires an LLM for evaluation, which may incur costs.
        """
        from ragas import evaluate
        from ragas.metrics import (
            faithfulness,
            answer_relevancy,
            context_precision,
            context_recall
        )
        from datasets import Dataset

        # Prepare data
        data = {
            "question": [question],
            "answer": [answer],
            "contexts": [contexts],
        }

        if ground_truth:
            data["ground_truth"] = [ground_truth]
            metrics = [faithfulness, answer_relevancy, context_precision, context_recall]
        else:
            metrics = [faithfulness, answer_relevancy, context_precision]

        dataset = Dataset.from_dict(data)

        # Run evaluation
        result = evaluate(dataset, metrics=metrics)

        return EvaluationScores(
            faithfulness=result.get("faithfulness", 0.0),
            answer_relevancy=result.get("answer_relevancy", 0.0),
            context_precision=result.get("context_precision", 0.0),
            context_recall=result.get("context_recall", 0.0) if ground_truth else 0.0,
            overall=sum(result.values()) / len(result) if result else 0.0
        )

    def evaluate_test_case(
        self,
        test_case: TestCase,
        generated_answer: str,
        retrieved_contexts: List[str]
    ) -> EvaluationResult:
        """
        Evaluate a single test case.

        Args:
            test_case: Test case with question and ground truth
            generated_answer: RAG-generated answer
            retrieved_contexts: Retrieved context chunks

        Returns:
            EvaluationResult with scores and pass/fail status
        """
        scores = self.evaluate_single(
            question=test_case.question,
            answer=generated_answer,
            contexts=retrieved_contexts,
            ground_truth=test_case.ground_truth
        )

        # Check if passed thresholds
        passed = scores.overall >= self.thresholds["overall"]

        return EvaluationResult(
            test_case=test_case,
            generated_answer=generated_answer,
            retrieved_contexts=retrieved_contexts,
            scores=scores,
            passed=passed
        )

    def benchmark(
        self,
        test_cases: List[TestCase],
        rag_system: Any,
        verbose: bool = True
    ) -> BenchmarkResult:
        """
        Benchmark a RAG system against test cases.

        Args:
            test_cases: List of test cases to evaluate
            rag_system: RAG system with search() and chat() methods
            verbose: Whether to print progress

        Returns:
            BenchmarkResult with aggregate statistics
        """
        results = []
        category_scores: Dict[str, List[EvaluationScores]] = {}

        for i, test_case in enumerate(test_cases):
            if verbose:
                print(f"Evaluating {i+1}/{len(test_cases)}: {test_case.question[:50]}...")

            try:
                # Get RAG response
                contexts = rag_system.retriever.search(test_case.question, n_results=5)
                context_texts = [c["content"] for c in contexts]

                # Generate answer (sync)
                answer = rag_system.chat_sync(test_case.question)

                # Evaluate
                result = self.evaluate_test_case(test_case, answer, context_texts)
                results.append(result)

                # Track by category
                if test_case.category not in category_scores:
                    category_scores[test_case.category] = []
                category_scores[test_case.category].append(result.scores)

            except Exception as e:
                if verbose:
                    print(f"  Error: {e}")

        # Calculate aggregates
        if results:
            avg_scores = EvaluationScores(
                faithfulness=sum(r.scores.faithfulness for r in results) / len(results),
                answer_relevancy=sum(r.scores.answer_relevancy for r in results) / len(results),
                context_precision=sum(r.scores.context_precision for r in results) / len(results),
                context_recall=sum(r.scores.context_recall for r in results) / len(results),
                overall=sum(r.scores.overall for r in results) / len(results)
            )
            passed = sum(1 for r in results if r.passed)
        else:
            avg_scores = EvaluationScores()
            passed = 0

        # Calculate category averages
        results_by_category = {}
        for category, scores_list in category_scores.items():
            results_by_category[category] = EvaluationScores(
                faithfulness=sum(s.faithfulness for s in scores_list) / len(scores_list),
                answer_relevancy=sum(s.answer_relevancy for s in scores_list) / len(scores_list),
                context_precision=sum(s.context_precision for s in scores_list) / len(scores_list),
                context_recall=sum(s.context_recall for s in scores_list) / len(scores_list),
                overall=sum(s.overall for s in scores_list) / len(scores_list)
            )

        return BenchmarkResult(
            total_tests=len(test_cases),
            passed_tests=passed,
            average_scores=avg_scores,
            results_by_category=results_by_category,
            individual_results=results
        )

    def generate_test_cases(
        self,
        resume_content: str,
        n_questions: int = 10
    ) -> List[TestCase]:
        """
        Generate test cases from resume content.

        Creates questions that can be answered from the resume,
        along with ground truth answers.

        Args:
            resume_content: Full resume text
            n_questions: Number of test cases to generate

        Returns:
            List of TestCase objects
        """
        # Default test questions that work for most resumes
        default_questions = [
            TestCase(
                question="What programming languages do you know?",
                ground_truth="",  # Will be filled from resume
                expected_sections=["skills"],
                category="skills"
            ),
            TestCase(
                question="What is your most recent work experience?",
                ground_truth="",
                expected_sections=["experience"],
                category="experience"
            ),
            TestCase(
                question="What is your educational background?",
                ground_truth="",
                expected_sections=["education"],
                category="education"
            ),
            TestCase(
                question="What projects have you worked on?",
                ground_truth="",
                expected_sections=["projects"],
                category="projects"
            ),
            TestCase(
                question="How many years of experience do you have?",
                ground_truth="",
                expected_sections=["experience", "summary"],
                category="experience"
            ),
            TestCase(
                question="What cloud platforms have you used?",
                ground_truth="",
                expected_sections=["skills", "experience"],
                category="skills"
            ),
            TestCase(
                question="What databases are you familiar with?",
                ground_truth="",
                expected_sections=["skills"],
                category="skills"
            ),
            TestCase(
                question="Describe your backend development experience.",
                ground_truth="",
                expected_sections=["experience", "skills"],
                category="experience"
            ),
            TestCase(
                question="What certifications do you have?",
                ground_truth="",
                expected_sections=["certifications", "education"],
                category="education"
            ),
            TestCase(
                question="What are your key achievements?",
                ground_truth="",
                expected_sections=["experience", "projects"],
                category="achievements"
            ),
        ]

        return default_questions[:n_questions]

    def save_results(self, result: BenchmarkResult, path: Path) -> None:
        """Save benchmark results to JSON file"""
        data = {
            "total_tests": result.total_tests,
            "passed_tests": result.passed_tests,
            "pass_rate": result.passed_tests / result.total_tests if result.total_tests > 0 else 0,
            "average_scores": {
                "faithfulness": result.average_scores.faithfulness,
                "answer_relevancy": result.average_scores.answer_relevancy,
                "context_precision": result.average_scores.context_precision,
                "context_recall": result.average_scores.context_recall,
                "overall": result.average_scores.overall
            },
            "results_by_category": {
                cat: {
                    "faithfulness": scores.faithfulness,
                    "answer_relevancy": scores.answer_relevancy,
                    "context_precision": scores.context_precision,
                    "context_recall": scores.context_recall,
                    "overall": scores.overall
                }
                for cat, scores in result.results_by_category.items()
            }
        }

        with open(path, "w") as f:
            json.dump(data, f, indent=2)

    def load_test_cases(self, path: Path) -> List[TestCase]:
        """Load test cases from JSON file"""
        with open(path) as f:
            data = json.load(f)

        return [
            TestCase(
                question=tc["question"],
                ground_truth=tc.get("ground_truth", ""),
                expected_sections=tc.get("expected_sections", []),
                category=tc.get("category", "general")
            )
            for tc in data
        ]

    def __repr__(self) -> str:
        return f"RAGEvaluator(use_ragas={self.use_ragas}, ragas_available={self.ragas_available})"
