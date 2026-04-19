"""
Scoring framework for evaluating agent pipeline outputs.

Provides pluggable scorers: exact match, numeric comparison,
regex extraction, and LLM-as-judge.
"""

import re
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, Optional

from core.llm import call_llm


@dataclass
class ScoreResult:
    """Result of a single scoring evaluation."""

    scorer_name: str
    score: float  # Normalized 0-1 where possible, raw otherwise
    raw_value: Any = None  # The raw computed value before normalization
    details: Optional[str] = None  # Human-readable explanation


class BaseScorer(ABC):
    """Abstract base for all scorers."""

    name: str = "base"

    @abstractmethod
    async def score(
        self, prediction: str, reference: str, **kwargs
    ) -> ScoreResult:
        ...


class ExactMatchScorer(BaseScorer):
    """Case-insensitive exact string match."""

    name = "exact_match"

    def __init__(self, case_sensitive: bool = False):
        self.case_sensitive = case_sensitive

    async def score(self, prediction: str, reference: str, **kwargs) -> ScoreResult:
        if self.case_sensitive:
            match = prediction.strip() == reference.strip()
        else:
            match = prediction.strip().lower() == reference.strip().lower()
        return ScoreResult(
            scorer_name=self.name,
            score=1.0 if match else 0.0,
            raw_value=match,
        )


class NumericScorer(BaseScorer):
    """
    Compare numeric values with configurable tolerance.
    Useful for grading datasets where scores are floats.
    """

    name = "numeric"

    def __init__(self, tolerance: float = 0.5, max_score: float = 5.0):
        self.tolerance = tolerance
        self.max_score = max_score

    async def score(self, prediction: str, reference: str, **kwargs) -> ScoreResult:
        try:
            # Extract first number from prediction
            pred_num = _extract_number(prediction)
            ref_num = float(reference)

            if pred_num is None:
                return ScoreResult(
                    scorer_name=self.name,
                    score=0.0,
                    details=f"Could not extract number from prediction: {prediction[:100]}",
                )

            abs_diff = abs(pred_num - ref_num)
            # Normalize: 1.0 if within tolerance, decreasing linearly to 0
            if abs_diff <= self.tolerance:
                normalized = 1.0
            else:
                normalized = max(0.0, 1.0 - (abs_diff - self.tolerance) / self.max_score)

            return ScoreResult(
                scorer_name=self.name,
                score=round(normalized, 4),
                raw_value={"predicted": pred_num, "reference": ref_num, "abs_diff": abs_diff},
                details=f"pred={pred_num}, ref={ref_num}, diff={abs_diff:.2f}",
            )
        except (ValueError, TypeError) as e:
            return ScoreResult(
                scorer_name=self.name,
                score=0.0,
                details=f"Scoring error: {e}",
            )


class RegexScorer(BaseScorer):
    """Extract a value via regex from prediction, then compare to reference."""

    name = "regex"

    def __init__(self, pattern: str, group: int = 1):
        self.pattern = re.compile(pattern)
        self.group = group

    async def score(self, prediction: str, reference: str, **kwargs) -> ScoreResult:
        match = self.pattern.search(prediction)
        if not match:
            return ScoreResult(
                scorer_name=self.name,
                score=0.0,
                details="Pattern not found in prediction",
            )
        extracted = match.group(self.group)
        is_match = extracted.strip().lower() == reference.strip().lower()
        return ScoreResult(
            scorer_name=self.name,
            score=1.0 if is_match else 0.0,
            raw_value=extracted,
            details=f"Extracted: '{extracted}', Reference: '{reference}'",
        )


class LLMJudgeScorer(BaseScorer):
    """Use an LLM to evaluate the quality of a prediction."""

    name = "llm_judge"

    def __init__(
        self,
        model: str = "gpt-4o",
        provider: str = "openai",
        judge_prompt: Optional[str] = None,
        temperature: float = 0.0,
    ):
        self.model = model
        self.provider = provider
        self.temperature = temperature
        self.judge_prompt = judge_prompt or self._default_judge_prompt()

    @staticmethod
    def _default_judge_prompt() -> str:
        return (
            "You are an expert evaluator. Rate the quality of the following "
            "prediction compared to the reference answer.\n\n"  # noqa: E501
            "Reference: {reference}\n\n"
            "Prediction: {prediction}\n\n"
            "Rate on a scale of 0 to 5, where 0 is completely wrong and "
            "5 is perfect. Respond with ONLY a single number."
        )

    async def score(self, prediction: str, reference: str, **kwargs) -> ScoreResult:
        prompt = self.judge_prompt.format(
            prediction=prediction, reference=reference
        )
        try:
            response = await call_llm(
                model=self.model,
                provider=self.provider,
                messages=[{"role": "user", "content": prompt}],
                temperature=self.temperature,
                max_tokens=10,
            )
            score_num = _extract_number(response.content)
            if score_num is None:
                return ScoreResult(
                    scorer_name=self.name,
                    score=0.0,
                    details=f"Could not parse judge response: {response.content}",
                )
            # Normalize to 0-1
            normalized = min(1.0, max(0.0, score_num / 5.0))
            return ScoreResult(
                scorer_name=self.name,
                score=round(normalized, 4),
                raw_value=score_num,
                details=f"LLM judge score: {score_num}/5",
            )
        except Exception as e:
            return ScoreResult(
                scorer_name=self.name,
                score=0.0,
                details=f"LLM judge error: {e}",
            )


def _extract_number(text: str) -> Optional[float]:
    """Extract the first number (int or float) from text."""
    match = re.search(r"-?\d+\.?\d*", text)
    if match:
        return float(match.group())
    return None


def create_scorer(config: dict) -> BaseScorer:
    """
    Factory: create a scorer from a config dict.

    Config examples:
        {"type": "exact_match"}
        {"type": "numeric", "tolerance": 0.5, "max_score": 5.0}
        {"type": "regex", "pattern": r"Score:\\s*(\\d+)"}
        {"type": "llm_judge", "model": "gpt-4o", "provider": "openai"}
    """
    scorer_type = config.get("type", "exact_match")

    if scorer_type == "exact_match":
        return ExactMatchScorer(case_sensitive=config.get("case_sensitive", False))
    elif scorer_type == "numeric":
        return NumericScorer(
            tolerance=config.get("tolerance", 0.5),
            max_score=config.get("max_score", 5.0),
        )
    elif scorer_type == "regex":
        return RegexScorer(
            pattern=config["pattern"],
            group=config.get("group", 1),
        )
    elif scorer_type == "llm_judge":
        return LLMJudgeScorer(
            model=config.get("model", "gpt-4o"),
            provider=config.get("provider", "openai"),
            judge_prompt=config.get("judge_prompt"),
            temperature=config.get("temperature", 0.0),
        )
    else:
        raise ValueError(f"Unknown scorer type: {scorer_type}")
